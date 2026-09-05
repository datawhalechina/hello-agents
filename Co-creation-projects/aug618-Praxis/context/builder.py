"""ContextBuilder - GSSC流水线实现

实现 Gather-Select-Structure-Compress 上下文构建流程：
1. Gather: 从多源收集候选信息（历史、记忆、RAG、工具结果）
2. Select: 基于优先级、相关性、多样性筛选
3. Structure: 组织成结构化上下文模板
4. Compress: 在预算内压缩与规范化
"""

from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING, Any as TypingAny
from dataclasses import dataclass, field
from datetime import datetime
import tiktoken
from utils.observability import log_event
import math

from core.message import Message
from core.llm import HelloAgentsLLM

if TYPE_CHECKING:
    # Optional, only for type checking. Importing tools at runtime may pull in heavy optional deps.
    from tools import MemoryTool, RAGTool
else:
    MemoryTool = TypingAny  # type: ignore[assignment,misc]
    RAGTool = TypingAny  # type: ignore[assignment,misc]


@dataclass
class ContextPacket:
    """上下文信息包"""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    relevance_score: float = 0.0  # 0.0-1.0
    
    def __post_init__(self):
        """自动计算token数"""
        if self.token_count == 0:
            self.token_count = count_tokens(self.content)


@dataclass
class ContextConfig:
    """上下文构建配置"""
    max_tokens: int = 8000  # 总预算
    reserve_ratio: float = 0.15  # 生成余量（10-20%）
    min_relevance: float = 0.3  # 最小相关性阈值（仅对扩展上下文生效）
    max_history_turns: int = 10  # 最大保留对话轮数
    enable_mmr: bool = True  # 启用最大边际相关性（多样性）
    mmr_lambda: float = 0.7  # MMR平衡参数（0=纯多样性, 1=纯相关性）
    system_prompt_template: str = ""  # 系统提示模板
    enable_compression: bool = True  # 启用压缩
    include_output_format: bool = True  # 是否附加固定输出格式约束
    # 按需探索模式：不主动查询 memory/rag，由模型通过工具按需获取
    lazy_fetch: bool = True
    
    def get_available_tokens(self) -> int:
        """获取可用token预算（扣除余量）"""
        return int(self.max_tokens * (1 - self.reserve_ratio))


class ContextBuilder:
    """上下文构建器 - GSSC流水线
    
    设计理念（借鉴 Claude Code）：
    - 保底上下文：系统提示 + 对话历史 + 上次工具摘要（自动注入，不可或缺）
    - 扩展上下文：memory/rag/notes（通过工具按需获取，模型自行决定）
    
    用法示例：
    ```python
    # 方式1：只构建保底上下文（推荐，让模型按需获取扩展上下文）
    builder = ContextBuilder(config=ContextConfig(lazy_fetch=True))
    context = builder.build_base(
        user_query="用户问题",
        conversation_history=[...],
        system_instructions="系统指令",
        tool_summaries=[...]  # 上次工具调用摘要
    )
    
    # 方式2：传统模式，主动收集所有上下文
    builder = ContextBuilder(
        memory_tool=memory_tool,
        rag_tool=rag_tool,
        config=ContextConfig(lazy_fetch=False)
    )
    context = builder.build(user_query="用户问题", ...)
    ```
    """
    
    def __init__(
        self,
        memory_tool: Optional[MemoryTool] = None,
        rag_tool: Optional[RAGTool] = None,
        config: Optional[ContextConfig] = None,
        llm: Optional[HelloAgentsLLM] = None,
    ):
        self.memory_tool = memory_tool
        self.rag_tool = rag_tool
        self.config = config or ContextConfig()
        self.llm = llm
        self._encoding = tiktoken.get_encoding("cl100k_base")
    
    def build_base(
        self,
        user_query: str,
        conversation_history: Optional[List[Message]] = None,
        system_instructions: Optional[str] = None,
        tool_summaries: Optional[List[str]] = None,
        pending_state: Optional[str] = None,
    ) -> str:
        """构建保底上下文（推荐使用）
        
        只包含必需的基础上下文，不主动查询 memory/rag。
        扩展上下文由模型通过 context_fetch 工具按需获取。
        
        保底上下文包括：
        - 系统指令/安全约束
        - 最近 N 轮对话历史
        - 上次工具调用摘要
        - 待确认的补丁/计划状态
        
        Args:
            user_query: 用户查询
            conversation_history: 对话历史
            system_instructions: 系统指令
            tool_summaries: 上次工具调用摘要列表
            pending_state: 待确认的状态（补丁/计划等）
            
        Returns:
            结构化上下文字符串
        """
        packets = []
        
        # P0: 系统指令（必须）
        if system_instructions:
            packets.append(ContextPacket(
                content=system_instructions,
                metadata={"type": "instructions"}
            ))
        
        # P1: 对话历史（必须）
        if conversation_history:
            recent_history = conversation_history[-self.config.max_history_turns:]
            history_text = "\n".join([
                f"[{msg.role}] {msg.content}"
                for msg in recent_history
            ])
            packets.append(ContextPacket(
                content=history_text,
                metadata={"type": "history", "count": len(recent_history)}
            ))
        
        # P2: 上次工具调用摘要（如有）
        if tool_summaries:
            summary_text = "\n".join(tool_summaries[-3:])  # 最多保留最近 3 条
            packets.append(ContextPacket(
                content=f"[上次工具结果摘要]\n{summary_text}",
                metadata={"type": "tool_summary"}
            ))
        
        # P3: 待确认状态（如有）
        if pending_state:
            packets.append(ContextPacket(
                content=f"[待确认状态]\n{pending_state}",
                metadata={"type": "pending_state"}
            ))
        
        # 直接结构化，不做相关性过滤（保底上下文全部保留）
        structured_context = self._structure_base(packets, user_query)
        
        # 压缩（如果超预算）
        final_context = self._compress(structured_context)
        log_event(
            "context_base",
            {
                "tokens": count_tokens(final_context),
                "history_turns": len(conversation_history or []),
                "tool_summaries": len(tool_summaries or []),
                "lazy_fetch": self.config.lazy_fetch,
            },
        )
        return final_context
    
    def _structure_base(
        self,
        packets: List[ContextPacket],
        user_query: str,
    ) -> str:
        """为保底上下文构建结构化模板"""
        sections = []
        
        # [Role & Policies]
        instructions = [p for p in packets if p.metadata.get("type") == "instructions"]
        if instructions:
            sections.append("[Role & Policies]\n" + "\n".join([p.content for p in instructions]))
        
        # [Context] - 对话历史
        history = [p for p in packets if p.metadata.get("type") == "history"]
        if history:
            sections.append("[Context]\n以下是最近的对话记录：\n" + "\n".join([p.content for p in history]))
        
        # [Evidence] - 工具摘要
        tool_summary = [p for p in packets if p.metadata.get("type") == "tool_summary"]
        if tool_summary:
            sections.append("[Evidence]\n" + "\n".join([p.content for p in tool_summary]))
        
        # [State] - 待确认状态
        pending = [p for p in packets if p.metadata.get("type") == "pending_state"]
        if pending:
            sections.append("[State]\n" + "\n".join([p.content for p in pending]))
        
        # [Task]
        sections.append(f"[Task]\n{user_query}")
        
        return "\n\n".join(sections)
    
    def build(
        self,
        user_query: str,
        conversation_history: Optional[List[Message]] = None,
        system_instructions: Optional[str] = None,
        additional_packets: Optional[List[ContextPacket]] = None
    ) -> str:
        """构建完整上下文
        
        Args:
            user_query: 用户查询
            conversation_history: 对话历史
            system_instructions: 系统指令
            additional_packets: 额外的上下文包
            
        Returns:
            结构化上下文字符串
        """
        # 1. Gather: 收集候选信息
        packets = self._gather(
            user_query=user_query,
            conversation_history=conversation_history or [],
            system_instructions=system_instructions,
            additional_packets=additional_packets or []
        )
        
        # 2. Select: 筛选与排序
        selected_packets = self._select(packets, user_query)
        
        # 3. Structure: 组织成结构化模板
        structured_context = self._structure(
            selected_packets=selected_packets,
            user_query=user_query,
            system_instructions=system_instructions
        )
        
        # 4. Compress: 压缩与规范化（如果超预算）
        final_context = self._compress(structured_context)
        
        return final_context
    
    def _gather(
        self,
        user_query: str,
        conversation_history: List[Message],
        system_instructions: Optional[str],
        additional_packets: List[ContextPacket]
    ) -> List[ContextPacket]:
        """Gather: 收集候选信息
        
        当 lazy_fetch=True 时，只收集保底上下文（系统指令+对话历史+额外包）。
        当 lazy_fetch=False 时，主动查询 memory/rag（传统模式）。
        """
        packets = []
        
        # P0: 系统指令（强约束，总是保留）
        if system_instructions:
            packets.append(ContextPacket(
                content=system_instructions,
                metadata={"type": "instructions"}
            ))
        
        # P1: 对话历史（基础上下文，总是保留）
        if conversation_history:
            recent_history = conversation_history[-self.config.max_history_turns:]
            history_text = "\n".join([
                f"[{msg.role}] {msg.content}"
                for msg in recent_history
            ])
            packets.append(ContextPacket(
                content=history_text,
                metadata={"type": "history", "count": len(recent_history)}
            ))
        
        # 以下为扩展上下文，仅在 lazy_fetch=False 时主动收集
        if not self.config.lazy_fetch:
            # P2: 从记忆中获取任务状态与关键结论
            if self.memory_tool:
                try:
                    # 搜索任务状态相关记忆
                    state_results = self.memory_tool.execute(
                        "search",
                        query="(任务状态 OR 子目标 OR 结论 OR 阻塞)",
                        min_importance=0.7,
                        limit=5
                    )
                    if state_results and "未找到" not in state_results:
                        packets.append(ContextPacket(
                            content=state_results,
                            metadata={"type": "task_state", "importance": "high"}
                        ))
                    
                    # 搜索与当前查询相关的记忆
                    related_results = self.memory_tool.execute(
                        "search",
                        query=user_query,
                        limit=5
                    )
                    if related_results and "未找到" not in related_results:
                        packets.append(ContextPacket(
                            content=related_results,
                            metadata={"type": "related_memory"}
                        ))
                except Exception as e:
                    print(f"⚠️ 记忆检索失败: {e}")
            
            # P3: 从RAG中获取事实证据
            if self.rag_tool:
                try:
                    rag_results = self.rag_tool.run({
                        "action": "search",
                        "query": user_query,
                        "top_k": 5
                    })
                    if rag_results and "未找到" not in rag_results and "错误" not in rag_results:
                        packets.append(ContextPacket(
                            content=rag_results,
                            metadata={"type": "knowledge_base"}
                        ))
                except Exception as e:
                    print(f"⚠️ RAG检索失败: {e}")
        
        # 添加额外包（如上次工具结果摘要）
        packets.extend(additional_packets)
        
        return packets
    
    def _select(
        self,
        packets: List[ContextPacket],
        user_query: str
    ) -> List[ContextPacket]:
        """Select: 基于分数与预算的筛选"""
        # 1) 计算相关性（关键词重叠）
        query_tokens = set(user_query.lower().split())
        for packet in packets:
            content_tokens = set(packet.content.lower().split())
            if len(query_tokens) > 0:
                overlap = len(query_tokens & content_tokens)
                packet.relevance_score = overlap / len(query_tokens)
            else:
                packet.relevance_score = 0.0
        
        # 2) 计算新近性（指数衰减）
        def recency_score(ts: datetime) -> float:
            delta = max((datetime.now() - ts).total_seconds(), 0)
            tau = 3600  # 1小时时间尺度，可暴露到配置
            return math.exp(-delta / tau)
        
        # 3) 计算复合分：0.7*相关性 + 0.3*新近性
        scored_packets: List[Tuple[float, ContextPacket]] = []
        for p in packets:
            rec = recency_score(p.timestamp)
            score = 0.7 * p.relevance_score + 0.3 * rec
            scored_packets.append((score, p))
        
        # 4) 系统指令和对话历史单独拿出，固定纳入（这两者是基础上下文，不应被过滤）
        must_keep_types = {"instructions", "history"}
        must_keep_packets = [p for (_, p) in scored_packets if p.metadata.get("type") in must_keep_types]
        remaining = [p for (s, p) in sorted(scored_packets, key=lambda x: x[0], reverse=True)
                     if p.metadata.get("type") not in must_keep_types]
        
        # 5) 依据 min_relevance 过滤（仅对扩展上下文：memory、RAG、notes 等）
        filtered = [p for p in remaining if p.relevance_score >= self.config.min_relevance]
        
        # 6) 按预算填充
        available_tokens = self.config.get_available_tokens()
        selected: List[ContextPacket] = []
        used_tokens = 0
        
        # 先放入必须保留的上下文（系统指令 + 对话历史）
        for p in must_keep_packets:
            if used_tokens + p.token_count <= available_tokens:
                selected.append(p)
                used_tokens += p.token_count
        
        # 再按分数加入其余
        for p in filtered:
            if used_tokens + p.token_count > available_tokens:
                continue
            selected.append(p)
            used_tokens += p.token_count
        
        return selected
    
    def _structure(
        self,
        selected_packets: List[ContextPacket],
        user_query: str,
        system_instructions: Optional[str]
    ) -> str:
        """Structure: 组织成结构化上下文模板"""
        sections = []
        
        # [Role & Policies] - 系统指令
        p0_packets = [p for p in selected_packets if p.metadata.get("type") == "instructions"]
        if p0_packets:
            role_section = "[Role & Policies]\n"
            role_section += "\n".join([p.content for p in p0_packets])
            sections.append(role_section)
        
        # [Task] - 当前任务
        sections.append(f"[Task]\n用户问题：{user_query}")
        
        # [State] - 任务状态
        p1_packets = [p for p in selected_packets if p.metadata.get("type") == "task_state"]
        if p1_packets:
            state_section = "[State]\n关键进展与未决问题：\n"
            state_section += "\n".join([p.content for p in p1_packets])
            sections.append(state_section)
        
        # [Evidence] - 事实证据
        p2_packets = [
            p for p in selected_packets
            if p.metadata.get("type") in {"related_memory", "knowledge_base", "retrieval", "tool_result"}
        ]
        if p2_packets:
            evidence_section = "[Evidence]\n事实与引用：\n"
            for p in p2_packets:
                evidence_section += f"\n{p.content}\n"
            sections.append(evidence_section)
        
        # [Recent Conversation] - 对话历史（明确标识）
        p3_packets = [p for p in selected_packets if p.metadata.get("type") == "history"]
        if p3_packets:
            context_section = "[Recent Conversation]\n以下是最近的对话记录。当用户询问之前的对话内容时，请参考此部分：\n"
            context_section += "\n".join([p.content for p in p3_packets])
            sections.append(context_section)
        
        # [Output] - 输出约束（可选）
        if self.config.include_output_format:
            output_section = """[Output]
请按以下格式回答：
1. 结论（简洁明确）
2. 依据（列出支撑证据及来源）
3. 风险与假设（如有）
4. 下一步行动建议（如适用）"""
            sections.append(output_section)
        
        return "\n\n".join(sections)
    
    def _compress(self, context: str) -> str:
        """Compress: 压缩与规范化"""
        if not self.config.enable_compression:
            return context
        
        current_tokens = count_tokens(context)
        available_tokens = self.config.get_available_tokens()
        
        if current_tokens <= available_tokens:
            return context

        # LLM 压缩（更保真）：仅在提供 llm 时启用
        if self.llm is not None:
            try:
                target = available_tokens
                # 尽量保留结构：Role/Task 原样，压缩 Evidence/Context
                sys = (
                    "你是一个上下文压缩器。将输入的多段上下文压缩到目标 token 预算内，"
                    "尽量保留：用户目标、关键约束、关键证据（文件路径/命令/错误/结论）。"
                    "不要编造。保持原有分段标题（[Role & Policies]/[Task]/[State]/[Evidence]/[Context] 等），"
                    "但可以大幅精简 [Evidence]/[Context] 内容。输出应尽量短。"
                )
                user = f"目标预算(约): {target} tokens\n\n原始上下文:\n{context}"
                compressed = self.llm.invoke(
                    [
                        {"role": "system", "content": sys},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=min(1200, int(self.config.max_tokens * 0.4)),
                )
                if compressed and isinstance(compressed, str) and count_tokens(compressed) <= target:
                    return compressed
            except Exception:
                pass
        
        # 简单截断策略（保留前N个token）
        # 实际应用中可用LLM做高保真摘要
        print(f"⚠️ 上下文超预算 ({current_tokens} > {available_tokens})，执行截断")
        
        # 按段落截断，保留结构
        lines = context.split("\n")
        compressed_lines = []
        used_tokens = 0
        
        for line in lines:
            line_tokens = count_tokens(line)
            if used_tokens + line_tokens > available_tokens:
                break
            compressed_lines.append(line)
            used_tokens += line_tokens
        
        return "\n".join(compressed_lines)


def count_tokens(text: str) -> int:
    """计算文本token数（使用tiktoken）"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # 降级方案：粗略估算（1 token ≈ 4 字符）
        return len(text) // 4

