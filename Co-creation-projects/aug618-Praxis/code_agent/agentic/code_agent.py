from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from agents.react_agent import ReActAgent
from core.config import Config
from core.llm import HelloAgentsLLM
from core.message import Message
from context.builder import ContextBuilder, ContextConfig, ContextPacket
from tools.registry import ToolRegistry
from tools.builtin.note_tool import NoteTool
from tools.builtin.terminal_tool import TerminalTool
from tools.builtin.plan_tool import PlanTool
from tools.builtin.todo_tool import TodoTool
from tools.builtin.context_fetch_tool import ContextFetchTool
from tools.builtin.protocol_tools import MCPTool
from tools.builtin.skills_tool import SkillsTool
from utils.env import env_flag, env_flag_true, env_stripped
from utils.multimodal import image_part_from_path
from utils.references import parse_references
from tools.builtin.ocr_tool import extract_text_from_image



@dataclass
class CodeAgentPaths:
    """CodeAgent 路径配置类，集中管理所有相关目录路径"""
    repo_root: Path
    notes_dir: Path
    memory_dir: Path
    sessions_dir: Path
    logs_dir: Path

    @property
    def helloagents_dir(self) -> Path:
        """返回 .helloagents 目录路径"""
        return self.repo_root / ".helloagents"

    @property
    def prompts_dir(self) -> Path:
        """返回 prompts 目录路径"""
        return self.repo_root / "code_agent" / "prompts"


class CodeAgent:
    """
    类似 Claude Code/Codex 的 CLI 智能体：
    - 核心循环使用 ReActAgent。
    - ContextBuilder 负责拼接：系统提示词 + 最近对话 + 相关笔记 + 情景记忆。
    - 规划能力作为可选工具 (`plan`) 暴露给模型，模型可按需调用。
    """

    def __init__(self, repo_root: Path, llm: Optional[HelloAgentsLLM] = None, config: Optional[Config] = None):
        """
        初始化 CodeAgent

        Args:
            repo_root: 代码仓库根目录
            llm: LLM 实例
            config: 配置对象
        """
        repo_root = repo_root.resolve()
        self.config = config or Config.from_env()

        # 初始化目录结构
        helloagents_dir = Path(self.config.helloagents_dir)
        state_root = helloagents_dir if helloagents_dir.is_absolute() else (repo_root / helloagents_dir)
        self.paths = CodeAgentPaths(
            repo_root=repo_root,
            notes_dir=state_root / "notes",
            memory_dir=state_root / "memory",
            sessions_dir=state_root / "sessions",
            logs_dir=state_root / "logs",
        )
        # 确保所有必要目录存在
        self.paths.helloagents_dir.mkdir(parents=True, exist_ok=True)
        self.paths.notes_dir.mkdir(parents=True, exist_ok=True)
        self.paths.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.paths.logs_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("CODE_AGENT_LOG_DIR", str(self.paths.logs_dir))
        # memory / logs 仅在需要时创建，这里不再预建

        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.llm = llm or HelloAgentsLLM()
        self._quiet = env_flag("CODE_AGENT_QUIET", default=False)

        # 初始化工具 (真实实现)
        self.note_tool = NoteTool(workspace=str(self.paths.notes_dir))
        # 类似 Claude Code：默认允许 Shell 语法 (管道等)，但危险操作需确认
        self.terminal_tool = TerminalTool(
            workspace=str(self.paths.repo_root),
            timeout=60,
            confirm_dangerous=True,
            default_shell_mode=True,
        )
        self.todo_tool = TodoTool(workspace=str(self.paths.helloagents_dir / "todos"))

        # ReActAgent 的工具注册表
        # 核心工具：terminal, note, memory, plan
        # 扩展上下文工具：context_fetch（让模型按需获取更多证据）
        self.registry = ToolRegistry()
        self.registry.register_tool(self.terminal_tool)
        self.registry.register_tool(self.note_tool)
        self.registry.register_tool(PlanTool(self.llm, prompt_path=str(self.paths.prompts_dir / "plan.md")))
        self.registry.register_tool(self.todo_tool)
        
        # 注册上下文获取工具（让模型按需探索）
        self.context_fetch_tool = ContextFetchTool(
            workspace=str(self.paths.repo_root),
            note_tool=self.note_tool,
            memory_tool=None,
            max_tokens_per_source=800,
            context_lines=5,
        )
        self.registry.register_tool(self.context_fetch_tool)

        # ========== Skills（.agents/skills）==========
        # 用于渐进式披露的 SOP/工作流；存在则自动注册
        try:
            # SkillsTool 会按 OpenCode/Claude 的标准路径扫描，
            # 也可用 CODE_AGENT_SKILLS_DIR 覆盖为单一根目录。
            self.registry.register_tool(SkillsTool(repo_root=str(self.paths.repo_root)))
        except Exception:
            pass

        # ========== MCP Monitor 工具（系统监控）==========
        # 通过环境变量 MCP_MONITOR_COMMAND 指定启动命令。
        monitor_cmd: Optional[List[str]] = None
        env_cmd = env_stripped("MCP_MONITOR_COMMAND", "")
        if env_cmd:
            monitor_cmd = shlex.split(env_cmd)

        if monitor_cmd:
            try:
                monitor_tool = MCPTool(
                    name="monitor",
                    server_command=monitor_cmd,
                    auto_expand=True,
                )
                for t in monitor_tool.get_expanded_tools():
                    self.registry.register_tool(t)
                if not self._quiet:
                    print(f"✅ MCP Monitor 已注册（{len(monitor_tool.get_expanded_tools())} 工具）")
            except Exception as e:
                if not self._quiet:
                    print(f"⚠️ MCP Monitor 注册失败: {e}")

        # ========== MCP Playwright 工具（网页自动化）==========
        # 通过环境变量 MCP_PLAYWRIGHT_COMMAND 指定启动命令
        playwright_cmd: Optional[List[str]] = None
        env_playwright = env_stripped("MCP_PLAYWRIGHT_COMMAND", "")
        if env_playwright:
            playwright_cmd = shlex.split(env_playwright)

        if playwright_cmd:
            try:
                playwright_tool = MCPTool(
                    name="playwright",
                    server_command=playwright_cmd,
                    auto_expand=True,
                )
                for t in playwright_tool.get_expanded_tools():
                    self.registry.register_tool(t)
                if not self._quiet:
                    print(f"✅ MCP Playwright 已注册（{len(playwright_tool.get_expanded_tools())} 工具）")
            except Exception as e:
                if not self._quiet:
                    print(f"⚠️ MCP Playwright 注册失败: {e}")

        # 初始化上下文构建器（lazy_fetch=True：只构建保底上下文）
        self.context_builder = ContextBuilder(
            memory_tool=None,
            rag_tool=None,
            config=ContextConfig(
                max_tokens=8000,
                reserve_ratio=0.15,
                max_history_turns=10,
                enable_compression=True,
                include_output_format=False,
                lazy_fetch=True,  # 按需探索模式
            ),
            llm=self.llm,
        )

        # 加载自定义 Prompt 并初始化 ReActAgent
        react_prompt = (self.paths.prompts_dir / "react.md").read_text(encoding="utf-8")
        summarize_prompt = (self.paths.prompts_dir / "summarize_observation.md").read_text(encoding="utf-8")

        def _summarize_observation(tool_name: str, tool_input: str, observation: str) -> str:
            """
            使用 LLM 压缩工具输出 (避免将巨大的原始输出放入 Prompt)
            """
            truncated = observation
            if len(truncated) > 8000:
                truncated = truncated[:8000] + "\n...truncated...\n"
            user_msg = (
                f"Tool: {tool_name}\n"
                f"Input: {tool_input}\n\n"
                f"Output:\n{truncated}"
            )
            return self.llm.invoke(
                [
                    {"role": "system", "content": summarize_prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=400,
            ) or ""

        self.react = ReActAgent(
            name="code_agent",
            llm=self.llm,
            tool_registry=self.registry,
            max_steps=20,
            custom_prompt=react_prompt,
            observation_summarizer=_summarize_observation,
            summarize_threshold_chars=2500,
        )

        base_system = (self.paths.prompts_dir / "system.md").read_text(encoding="utf-8")
        self.tools_reference_path = self.paths.prompts_dir / "tools.md"
        self.system_prompt = base_system
        self.history: List[Message] = []
        self.recent_tool_packets: List[ContextPacket] = []
        self.last_direct_reply: bool = False

    def _is_chitchat(self, text: str) -> bool:
        """判断是否为闲聊，避免不必要的工具调用"""
        t = (text or "").strip().lower()
        return t in {"hi", "hello", "hey", "yo", "你好", "您好", "在吗", "嗨", "哈喽"}

    def _is_history_query(self, text: str) -> bool:
        """判断是否为'回顾刚才说了什么'的元请求"""
        t = (text or "").strip().lower()
        patterns = [
            "说了什么",
            "刚才说了什么",
            "之前说了什么",
            "what did i say",
            "what did we say",
            "recap",
            "summary of conversation",
        ]
        return any(p in t for p in patterns)

    def _reply_with_recent_history(self, limit: int = 6) -> str:
        """生成最近对话的简要回顾"""
        # 只取用户/助手消息（跳过系统等）
        items = [m for m in self.history if m.role in {"user", "assistant"}][-limit * 2 :]
        if not items:
            return "目前还没有可回顾的对话历史。"
        lines = []
        for m in items:
            role = "你" if m.role == "user" else "助手"
            lines.append(f"- {role}: {m.content}")
        return "下面是最近的对话回顾：\n" + "\n".join(lines)

    # 以下两个方法在 lazy_fetch 模式下不再主动调用，
    # 扩展上下文改由模型通过 context_fetch 工具按需获取。
    # 保留这些方法以支持 lazy_fetch=False 的传统模式。
    
    def _note_packets(self, query: str) -> List[ContextPacket]:
        """检索相关笔记并封装为 ContextPacket"""
        packets: List[ContextPacket] = []
        if self._is_chitchat(query):
            return packets
        try:
            # 获取最近的阻碍 (Blocker)
            blockers = self.note_tool.run({"action": "list", "note_type": "blocker", "limit": 2})
            if blockers and isinstance(blockers, str) and "暂无" not in blockers:
                packets.append(ContextPacket(content=f"[Notes:blocker]\n{blockers}", metadata={"source": "note"}))
            # 搜索相关笔记
            hits = self.note_tool.run({"action": "search", "query": query, "limit": 3})
            if hits and isinstance(hits, str) and "未找到" not in hits:
                packets.append(ContextPacket(content=f"[Notes:search]\n{hits}", metadata={"source": "note"}))
        except Exception:
            pass
        return packets

    def _memory_packets(self, query: str) -> List[ContextPacket]:
        """检索相关记忆并封装为 ContextPacket"""
        packets: List[ContextPacket] = []
        if self._is_chitchat(query):
            return packets
        try:
            hits = self.memory_tool.run(
                {"action": "search", "query": query, "memory_types": self.memory_tool.memory_types, "limit": 5, "min_importance": 0.0}
            )
            if hits and isinstance(hits, str) and "未找到" not in hits:
                packets.append(ContextPacket(content=f"[Memory]\n{hits}", metadata={"source": "memory"}))
        except Exception:
            pass
        return packets

    def _persist_session(self) -> None:
        """持久化当前会话到 JSON 文件"""
        p = self.paths.sessions_dir / f"{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "updated_at": datetime.now().isoformat(),
            "history": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in self.history[-50:]
            ],
        }
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _capture_recent_tool_evidence(self) -> tuple[bool, bool]:
        """收集最近一轮 ReAct 工具摘要，并返回 todo 使用情况。"""
        todo_used = False
        todo_listed = False
        tool_summaries: List[str] = []

        try:
            for item in getattr(self.react, "last_trace", [])[-6:]:
                summary = item.get("observation_summary")
                tool_name = item.get("tool_name")
                if tool_name == "todo":
                    todo_used = True
                    if "list" in str(item.get("tool_input", "")):
                        todo_listed = True
                if summary:
                    tool_summaries.append(
                        f"[{tool_name}] {item.get('tool_input')}\n{summary}"
                    )

            if tool_summaries:
                self.recent_tool_packets.append(
                    ContextPacket(
                        content="[Tool Evidence]\n" + "\n\n".join(tool_summaries),
                        metadata={"type": "tool_result", "source": "react"},
                    )
                )
                if len(self.recent_tool_packets) > 8:
                    self.recent_tool_packets = self.recent_tool_packets[-8:]
        except Exception:
            pass

        return todo_used, todo_listed

    def _append_todo_snapshot_if_needed(self, response: str, todo_used: bool, todo_listed: bool) -> str:
        """如果本轮使用过 todo 但未主动 list，则在回复末尾补充看板快照。"""
        if not todo_used or todo_listed:
            return response

        try:
            todo_snapshot = self.todo_tool.run({"action": "list"})
            return f"{response}\n\nTodo board:\n{todo_snapshot}"
        except Exception:
            return response

    def run_turn(self, user_input: str, image_paths: Optional[List[str | Path]] = None) -> str:
        """
        执行一轮对话：
        1. 解析 @file/@dir 引用
        2. 收集上下文 (笔记、记忆、最近工具输出)
        3. 构建完整 Prompt
        4. 运行 ReAct 循环
        5. 更新历史并持久化
        """
        # 空输入：提示而不进入 ReAct
        if not user_input.strip():
            return "请提供具体指令或问题。"

        # ========== 解析 @file/@dir 引用 ==========
        refs = parse_references(user_input, workspace=self.paths.repo_root)
        
        # 如果有解析错误，先报告
        if refs.errors:
            error_msg = "引用解析警告:\n" + "\n".join(f"- {e}" for e in refs.errors)
            print(error_msg)
        
        # 使用清理后的 query（移除了 @file/@dir 标记）
        clean_query = refs.clean_query
        
        # ========== 根据模型类型处理图片 ==========
        # 多模态模型 → 图片作为 attachments 直接发送
        # 文本模型 → 图片走 OCR，提取的文字注入到 context
        all_attachments: List[dict[str, Any]] = []
        ocr_results: List[str] = []
        
        # 收集所有图片路径
        all_image_paths: List[Path] = list(refs.image_paths)
        if image_paths:
            all_image_paths.extend([Path(p) for p in image_paths])
        
        if self.llm.is_multimodal:
            # 多模态模型：图片作为 attachments
            all_attachments = list(refs.image_attachments)
            if image_paths:
                for p in image_paths:
                    all_attachments.append(image_part_from_path(p))
            if all_image_paths:
                print(f"📷 多模态模式：{len(all_image_paths)} 张图片将直接发送给 LLM")
        else:
            # 文本模型：图片走 OCR
            if all_image_paths:
                print(f"🔍 文本模式：{len(all_image_paths)} 张图片将通过 OCR 提取文字")
                for img_path in all_image_paths:
                    ocr_text = extract_text_from_image(img_path)
                    if ocr_text and not ocr_text.startswith("错误") and not ocr_text.startswith("OCR 失败"):
                        ocr_results.append(f"[OCR 识别: {img_path.name}]\n```\n{ocr_text}\n```")
                        print(f"  ✓ {img_path.name}: 提取到 {len(ocr_text)} 字符")
                    else:
                        ocr_results.append(f"[OCR: {img_path.name}] ⚠️ {ocr_text}")
                        print(f"  ✗ {img_path.name}: {ocr_text[:50]}...")
            
            # 移除 context_blocks 中的图片占位符（因为已经用 OCR 结果替代）
            refs.context_blocks = [b for b in refs.context_blocks if not b.startswith("[图片:")]

        # 闲聊/问候：直接回复，避免 ReAct 的严格格式解析失败，也避免无谓的工具调用。
        if self._is_chitchat(clean_query) and not refs.context_blocks and not all_attachments:
            self.last_direct_reply = True
            reply = "你好！我是 奶龙版Code Agent，可以帮你按需探索代码仓库、生成补丁并在确认后落盘。你想做什么？（例如：分析项目结构 / 搜索某个类 / 修复一个报错）"
            self.history.append(Message(content=user_input, role="user", timestamp=datetime.now()))
            self.history.append(Message(content=reply, role="assistant", timestamp=datetime.now()))
            if len(self.history) > 50:
                self.history = self.history[-50:]
            self._persist_session()
            return reply
        self.last_direct_reply = False

        # 元请求：回顾最近对话
        if self._is_history_query(clean_query) and not refs.context_blocks:
            self.last_direct_reply = True
            reply = self._reply_with_recent_history(limit=6)
            self.history.append(Message(content=user_input, role="user", timestamp=datetime.now()))
            self.history.append(Message(content=reply, role="assistant", timestamp=datetime.now()))
            if len(self.history) > 50:
                self.history = self.history[-50:]
            self._persist_session()
            return reply

        # 若检测到明显多步骤词汇，向模型追加轻量提示（不强制，只提高倾向）
        multistep_hint = ""
        multi_patterns = ["分步", "步骤", "三步", "计划", "改造", "完成后", "多步", "多步骤"]
        if any(p in clean_query for p in multi_patterns):
            multistep_hint = "提示：本任务包含多个步骤，先用 todo 记录/更新，再执行；收尾用 todo list 汇总。"

        # Skills 索引（渐进式披露的“目录”）：让模型知道本地有哪些 skills，
        # 从而能在合适时机调用 skills[show] 读取 SKILL.md 的 SOP。
        skills_index = ""
        auto_skill_sop = ""
        try:
            if env_flag_true("CODE_AGENT_ENABLE_SKILLS_INDEX", default=True):
                skills_tool = self.registry.get_tool("skills")
                if skills_tool is not None:
                    # 只注入轻量索引（name/description），不加载全文
                    skills_index = skills_tool.run({"action": "list", "limit": 20})
                    if skills_index and "未找到 skills" not in skills_index:
                        skills_index = "\n\n[Available Skills]\n" + skills_index + "\n\n用法：先 skills[search] 再 skills[show] 加载具体 SOP。"

                    # 外部 skills 发现/安装：用户已经明确表达“去外部找/装 skills”时，
                    # 直接加载 find-skills 的 SOP（仍是按需加载，只对该意图触发）。
                    if env_flag_true("CODE_AGENT_AUTO_LOAD_FIND_SKILLS", default=True):
                        ql = clean_query.lower()
                        external_intent = any(
                            k in ql
                            for k in [
                                "外部",
                                "生态",
                                "安装skill",
                                "安装 skills",
                                "安装 skill",
                                "找skill",
                                "找 skills",
                                "找 skill",
                                "搜索skill",
                                "搜索 skills",
                                "npx skills",
                                "skills add",
                                "skills find",
                            ]
                        )
                        if external_intent:
                            try:
                                sop = skills_tool.run({"action": "show", "id": "find-skills"})
                                if sop and "未找到 skill" not in sop:
                                    auto_skill_sop = (
                                        "\n\n[Auto-loaded Skill SOP: find-skills]\n"
                                        + sop
                                        + "\n\n要求：当用户要在外部生态查找/安装技能时，严格按上面的 SOP 执行。"
                                    )
                            except Exception:
                                auto_skill_sop = ""
        except Exception:
            skills_index = ""
            auto_skill_sop = ""

        # 构建保底上下文（系统提示 + 对话历史 + 上次工具摘要 + 可选 hint）
        # 扩展上下文由模型通过 context_fetch 工具按需获取
        tool_summaries = []
        for packet in self.recent_tool_packets[-3:]:
            tool_summaries.append(packet.content)
        
        # 如果有 @file/@dir 引用的内容或 OCR 结果，作为额外上下文注入
        ref_context = ""
        all_context_parts = []
        if refs.context_blocks:
            all_context_parts.extend(refs.context_blocks)
        if ocr_results:
            all_context_parts.extend(ocr_results)
        if all_context_parts:
            ref_context = "\n\n[用户引用的文件/目录]\n" + "\n\n".join(all_context_parts)
        
        context_text = self.context_builder.build_base(
            user_query=clean_query + ref_context,
            conversation_history=self.history,
            system_instructions=self.system_prompt
            + (("\n" + multistep_hint) if multistep_hint else "")
            + (skills_index or "")
            + (auto_skill_sop or ""),
            tool_summaries=tool_summaries if tool_summaries else None,
        )
        
        # 准备多模态附件
        attachments: Optional[List[dict[str, Any]]] = all_attachments if all_attachments else None
        
        # 将拼接好的上下文作为"问题"输入给 ReAct
        response = self.react.run(context_text, max_tokens=8000, attachments=attachments)

        # 收集本轮的工具执行证据 (已在 ReActAgent 内部摘要)
        todo_used, todo_listed = self._capture_recent_tool_evidence()

        # 更新历史记录 (保留最近 50 条)
        # 记录原始输入（包含 @file/@dir 标记，便于回顾）
        user_for_history = user_input
        if image_paths:
            rendered = "\n".join([f"- {str(Path(p))}" for p in image_paths])
            user_for_history = f"{user_input}\n\n[附加图片]\n{rendered}"
        self.history.append(Message(content=user_for_history, role="user", timestamp=datetime.now()))
        self.history.append(Message(content=response, role="assistant", timestamp=datetime.now()))
        if len(self.history) > 50:
            self.history = self.history[-50:]
        self._persist_session()
        return self._append_todo_snapshot_if_needed(response, todo_used, todo_listed)
