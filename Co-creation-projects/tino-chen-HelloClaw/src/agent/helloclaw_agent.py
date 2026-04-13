"""HelloClaw Agent - 基于 HelloAgents SimpleAgent 的个性化 AI 助手"""

import os
from typing import List

from hello_agents import Config
from .enhanced_simple_agent import EnhancedSimpleAgent
from .enhanced_llm import EnhancedHelloAgentsLLM  # HelloClaw 专用 LLM（支持流式工具调用）
from ..memory.memory_flush import MemoryFlushManager
from ..memory.capture import MemoryCaptureManager
from hello_agents.tools import (
    ToolRegistry,
    ReadTool,
    WriteTool,
    EditTool,
    CalculatorTool,
)

from ..workspace.manager import WorkspaceManager
from ..tools import MemoryTool, ExecuteCommandTool, WebSearchTool, WebFetchTool


class HelloClawAgent:
    """HelloClaw Agent - 个性化 AI 助手

    基于 HelloAgents SimpleAgent，增加了：
    - 工作空间管理（配置文件、记忆文件）
    - 从 AGENTS.md 读取系统提示词
    - HelloClaw 专属工具集
    """

    def __init__(
        self,
        workspace_path: str = None,
        name: str = None,
        model_id: str = None,
        api_key: str = None,
        base_url: str = None,
        max_tool_iterations: int = 10,
    ):
        """初始化 HelloClaw Agent

        Args:
            workspace_path: 工作空间路径，默认 ~/.helloclaw/workspace
            name: Agent 名称（从 IDENTITY.md 读取，无需手动指定）
            model_id: LLM 模型 ID
            api_key: API Key
            base_url: API Base URL
            max_tool_iterations: 最大工具调用迭代次数
        """
        # 确保 workspace_path 正确展开 ~/
        self.workspace_path = os.path.expanduser(workspace_path or "~/.helloclaw/workspace")

        # 初始化工作空间管理器
        self.workspace = WorkspaceManager(self.workspace_path)

        # 确保工作空间存在
        self.workspace.ensure_workspace_exists()

        # 从 IDENTITY.md 读取名称，如果没有则使用默认值
        self.name = name or self._read_identity_name() or "HelloClaw"

        # 保存传入的参数（用于热加载时的优先级判断）
        self._override_model_id = model_id
        self._override_api_key = api_key
        self._override_base_url = base_url

        # 构建系统提示词（从 AGENTS.md 读取）
        system_prompt = self._build_system_prompt()

        # 初始化 LLM（从 config.json 读取配置）
        self._init_llm()

        # 初始化配置
        self.config = Config(
            session_enabled=True,
            session_dir=os.path.join(self.workspace_path, "sessions"),
            compression_threshold=0.8,
            min_retain_rounds=10,
            enable_smart_compression=False,
            context_window=128000,
            trace_enabled=False,
            skills_enabled=False,
            todowrite_enabled=False,
            devlog_enabled=False,
            subagent_enabled=True,  # 启用子 Agent 支持
        )

        # 初始化工具注册表
        self.tool_registry = self._setup_tools()

        # 初始化底层 EnhancedSimpleAgent
        self._agent = EnhancedSimpleAgent(
            name=self.name,  # 使用已读取的名字
            llm=self._llm,
            tool_registry=self.tool_registry,
            system_prompt=system_prompt,
            config=self.config,
            enable_tool_calling=True,
            max_tool_iterations=max_tool_iterations,
        )

        # 初始化 Memory Flush 管理器
        self._memory_flush_manager = MemoryFlushManager(
            context_window=self.config.context_window,
            compression_threshold=self.config.compression_threshold,
            soft_threshold_tokens=4000,
            enabled=True,
        )

        # 初始化 Memory Capture 管理器
        self._memory_capture_manager = MemoryCaptureManager(self.workspace)

    def _read_identity_name(self) -> str:
        """从 IDENTITY.md 读取助手名称

        Returns:
            助手名称，如果未设置则返回 None
        """
        import re
        identity = self.workspace.load_config("IDENTITY")
        if not identity:
            return None

        # 尝试匹配名称字段
        # 格式: - **名称：** xxx 或 - **名称:** xxx
        match = re.search(r'\*\*名称[：:]\*\*\s*(.+?)(?:\n|$)', identity)
        if match:
            name = match.group(1).strip()
            # 检查是否是占位符文本（包含下划线或"选一个"等）
            if name and not name.startswith('_') and '选一个' not in name and '（' not in name:
                return name
        return None

    def _init_llm(self):
        """初始化 LLM（从 config.json 读取配置）

        配置优先级：构造函数参数 > config.json > 环境变量 > 默认值
        """
        llm_config = self.workspace.get_llm_config()

        self._model_id = self._override_model_id or llm_config.get("model_id") or "glm-4"
        self._api_key = self._override_api_key or llm_config.get("api_key")
        self._base_url = self._override_base_url or llm_config.get("base_url")

        self._llm = EnhancedHelloAgentsLLM(
            model=self._model_id,
            api_key=self._api_key,
            base_url=self._base_url,
        )

    def _reload_llm_if_changed(self) -> bool:
        """检查配置变化并重新加载 LLM

        如果 config.json 中的配置发生变化，重新创建 LLM 实例。

        Returns:
            是否发生了重新加载
        """
        llm_config = self.workspace.get_llm_config()

        new_model_id = self._override_model_id or llm_config.get("model_id") or "glm-4"
        new_api_key = self._override_api_key or llm_config.get("api_key")
        new_base_url = self._override_base_url or llm_config.get("base_url")

        if (new_model_id != self._model_id or
            new_api_key != self._api_key or
            new_base_url != self._base_url):

            print(f"🔄 检测到配置变化，重新加载 LLM: {self._model_id} -> {new_model_id}")

            self._model_id = new_model_id
            self._api_key = new_api_key
            self._base_url = new_base_url

            self._llm = EnhancedHelloAgentsLLM(
                model=self._model_id,
                api_key=self._api_key,
                base_url=self._base_url,
            )

            # 更新 Agent 的 LLM 引用
            if hasattr(self, '_agent'):
                self._agent.llm = self._llm

            return True
        return False

    def _build_system_prompt(self) -> str:
        """构建系统提示词

        从 AGENTS.md 读取主要内容，附加其他配置文件作为上下文。
        如果入职未完成，注入 BOOTSTRAP.md 引导内容。

        Raises:
            RuntimeError: 如果 AGENTS.md 不存在
        """
        # 从 AGENTS.md 读取（必须存在）
        agents_content = self.workspace.load_config("AGENTS")
        if not agents_content:
            raise RuntimeError("AGENTS.md 配置文件不存在，请检查工作空间初始化")

        base_prompt = agents_content

        # 加载其他配置文件作为上下文
        context_parts = []

        # 检查入职是否完成
        if not self.workspace.is_onboarding_completed():
            bootstrap = self.workspace.load_config("BOOTSTRAP")
            if bootstrap:
                context_parts.append(f"\n## 初始化引导\n\n{bootstrap}")

        # 身份信息
        identity = self.workspace.load_config("IDENTITY")
        if identity:
            context_parts.append(f"\n## 你的身份信息\n{identity}")

        # 用户信息
        user_info = self.workspace.load_config("USER")
        if user_info:
            context_parts.append(f"\n## 用户信息\n{user_info}")

        # 人格模板
        soul = self.workspace.load_config("SOUL")
        if soul:
            context_parts.append(f"\n## 人格模板\n{soul}")

        # 长期记忆
        memory = self.workspace.load_config("MEMORY")
        if memory:
            context_parts.append(f"\n## 长期记忆\n{memory}")

        if context_parts:
            return base_prompt + "\n" + "\n".join(context_parts)

        return base_prompt

    def _setup_tools(self) -> ToolRegistry:
        """设置工具集"""
        registry = ToolRegistry()

        # HelloAgents 内置工具
        registry.register_tool(ReadTool(project_root=self.workspace_path))
        registry.register_tool(WriteTool(project_root=self.workspace_path))
        registry.register_tool(EditTool(project_root=self.workspace_path))
        registry.register_tool(CalculatorTool())

        # HelloClaw 自定义工具
        registry.register_tool(MemoryTool(self.workspace))
        registry.register_tool(ExecuteCommandTool(
            allowed_directories=[self.workspace_path]  # 限制在工作空间目录
        ))
        registry.register_tool(WebSearchTool())  # 网页搜索工具（需要配置 BRAVE_API_KEY）
        registry.register_tool(WebFetchTool())   # 网页抓取工具

        return registry

    def chat(self, message: str, session_id: str = None) -> str:
        """同步聊天"""
        # 热加载配置（检测 config.json 变化）
        self._reload_llm_if_changed()

        # 动态更新系统提示词（检查 BOOTSTRAP 状态、读取最新配置）
        self._agent.system_prompt = self._build_system_prompt()

        # 如果有 session_id，检查是否需要加载或清除历史
        if session_id:
            session_file = os.path.join(self.workspace_path, "sessions", f"{session_id}.json")
            if os.path.exists(session_file):
                self._agent.load_session(session_file)
            else:
                self._agent.clear_history()
        else:
            self._agent.clear_history()

        # LLM 调用参数（防止重复循环）
        llm_kwargs = {
            "frequency_penalty": 0.5,  # 降低重复相同内容的概率
            "presence_penalty": 0.3,   # 鼓励谈论新话题
        }

        # 运行 Agent
        response = self._agent.run(message, **llm_kwargs)

        # 保存会话
        save_id = session_id or self.create_session()
        try:
            self._agent.save_session(save_id)
        except Exception as e:
            print(f"⚠️ 保存会话失败: {e}")

        return response

    async def achat(self, message: str, session_id: str = None):
        """异步聊天（支持流式输出）

        Args:
            message: 用户消息
            session_id: 会话 ID，如果为 None 则创建新会话

        Yields:
            StreamEvent: 流式事件
        """
        import uuid
        import time

        t0 = time.time()
        print(f"[⏱️ {t0:.3f}] achat 开始")

        # 热加载配置（检测 config.json 变化）
        self._reload_llm_if_changed()

        # 动态更新系统提示词（检查 BOOTSTRAP 状态、读取最新配置）
        self._agent.system_prompt = self._build_system_prompt()
        print(f"[⏱️ {time.time():.3f}] 系统提示词构建完成 (+{time.time()-t0:.3f}s)")

        # 如果没有 session_id，创建新的
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
            self._agent.clear_history()
            # 重置 Memory Flush 状态（新会话）
            self._memory_flush_manager.reset()
        else:
            session_file = os.path.join(self.workspace_path, "sessions", f"{session_id}.json")
            if os.path.exists(session_file):
                self._agent.load_session(session_file)
            else:
                self._agent.clear_history()
                self._memory_flush_manager.reset()
        print(f"[⏱️ {time.time():.3f}] 会话加载完成 (+{time.time()-t0:.3f}s)")

        # 保存 session_id 供后续保存使用
        self._current_session_id = session_id

        # LLM 调用参数（防止重复循环）
        llm_kwargs = {
            "frequency_penalty": 0.5,  # 降低重复相同内容的概率
            "presence_penalty": 0.3,   # 鼓励谈论新话题
        }

        t_llm = time.time()
        print(f"[⏱️ {t_llm:.3f}] 开始调用 LLM ({self._model_id})...")
        first_chunk = True

        async for event in self._agent.arun_stream_with_tools(message, **llm_kwargs):
            if first_chunk and event.type.value == "llm_chunk":
                print(f"[⏱️ {time.time():.3f}] 首个 token 到达 (LLM 延迟: {time.time()-t_llm:.3f}s)")
                first_chunk = False
            yield event

        print(f"[⏱️ {time.time():.3f}] LLM 调用完成 (总耗时: {time.time()-t0:.3f}s)")

        # 对话结束后自动捕获记忆（异步执行，不阻塞用户）
        await self._capture_memories(message)

        # 对话结束后检查是否需要触发 Memory Flush（异步执行，不阻塞用户）
        await self._check_and_run_memory_flush()

    async def _capture_memories(self, user_message: str):
        """自动捕获对话中的记忆

        Args:
            user_message: 用户消息
        """
        try:
            # 使用 MemoryCaptureManager 分析并存储记忆
            memories = await self._memory_capture_manager.acapture_and_store(user_message)

            if memories:
                print(f"📝 自动捕获 {len(memories)} 条记忆")
                for m in memories:
                    print(f"   - [{m['category']}] {m['content'][:50]}...")
        except Exception as e:
            print(f"⚠️ 记忆捕获失败: {e}")

    async def _check_and_run_memory_flush(self):
        """检查并执行 Memory Flush

        如果当前 token 数接近压缩阈值，触发一个静默回合提醒 Agent 保存记忆。
        """
        # 估算当前 token 数（简单估算：字符数 / 4）
        estimated_tokens = self._estimate_tokens()

        if self._memory_flush_manager.should_trigger_flush(estimated_tokens):
            print(f"\n🔄 触发 Memory Flush（估算 token: {estimated_tokens}）")

            # 获取 flush 提示词
            flush_prompt = self._memory_flush_manager.get_flush_prompt()

            # 执行静默回合
            try:
                # 使用同步方法执行（不返回给用户）
                response = self._agent.run(flush_prompt)

                # 检查是否是静默响应
                if self._memory_flush_manager.is_silent_response(response):
                    print("📝 Agent 选择不保存记忆")
                else:
                    print(f"📝 Agent 已保存记忆")

            except Exception as e:
                print(f"⚠️ Memory Flush 失败: {e}")

    def _estimate_tokens(self) -> int:
        """估算当前上下文的 token 数

        使用简单的字符估算方法。
        对于中文，大约 1.5 字符/token；对于英文，大约 4 字符/token。
        这里使用保守估算：字符数 / 3。

        Returns:
            估算的 token 数
        """
        total_chars = 0

        # 系统提示词
        if self._agent.system_prompt:
            total_chars += len(self._agent.system_prompt)

        # 历史消息
        for msg in self._agent._history:
            if msg.content:
                total_chars += len(msg.content)

        # 保守估算：字符数 / 3
        return total_chars // 3

    def save_current_session(self):
        """保存当前会话"""
        if hasattr(self, '_current_session_id') and self._current_session_id:
            try:
                self._agent.save_session(self._current_session_id)
                return self._current_session_id
            except Exception as e:
                print(f"⚠️ 保存会话失败: {e}")
        return None

    def create_session(self) -> str:
        """创建新会话"""
        import uuid
        session_id = str(uuid.uuid4())[:8]
        return session_id

    def list_sessions(self) -> List[dict]:
        """列出所有会话"""
        sessions_dir = os.path.join(self.workspace_path, "sessions")
        if not os.path.exists(sessions_dir):
            return []

        sessions = []
        for filename in os.listdir(sessions_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(sessions_dir, filename)
                stat = os.stat(filepath)
                sessions.append({
                    "id": filename[:-5],
                    "created_at": stat.st_ctime,
                    "updated_at": stat.st_mtime,
                })

        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        filepath = os.path.join(self.workspace_path, "sessions", f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def get_session_history(self, session_id: str) -> List[dict]:
        """获取会话历史消息"""
        import json
        filepath = os.path.join(self.workspace_path, "sessions", f"{session_id}.json")
        if not os.path.exists(filepath):
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = []
            raw_history = data.get("history", [])
            for msg in raw_history:
                role = msg.get("role", "")
                # 支持 user, assistant, tool 三种角色
                if role in ("user", "assistant", "tool"):
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                            elif isinstance(part, str):
                                text_parts.append(part)
                        content = "\n".join(text_parts)

                    # 构建消息对象，包含 metadata
                    message_obj: dict = {"role": role, "content": content}
                    # 保留 metadata（包含 tool_calls 或 tool_call_id）
                    if "metadata" in msg:
                        message_obj["metadata"] = msg["metadata"]

                    messages.append(message_obj)

            return messages
        except Exception as e:
            print(f"Error loading session history: {e}")
            return []

    def clear_all_history(self):
        """清除 Agent 内存中的所有历史记录

        用于初始化时重置 Agent 状态。
        """
        self._agent.clear_history()
        self._current_session_id = None

        # 重置 MemoryFlushManager 状态
        if hasattr(self, '_memory_flush_manager'):
            self._memory_flush_manager.reset()

        # 重新读取 name（因为 IDENTITY.md 可能已被重置）
        self.name = self._read_identity_name() or "HelloClaw"
