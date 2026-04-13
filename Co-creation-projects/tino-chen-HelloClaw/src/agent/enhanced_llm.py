"""增强版 HelloAgentsLLM - 支持流式工具调用"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Union, Any, AsyncIterator

from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.exceptions import HelloAgentsException


# ==================== 流式工具调用数据结构 ====================

class StreamToolEventType(Enum):
    """流式工具调用事件类型"""
    CONTENT = "content"  # 文本内容增量
    TOOL_CALL_START = "tool_call_start"  # 工具调用开始（收到ID和名称）
    TOOL_CALL_DELTA = "tool_call_delta"  # 工具调用参数增量
    FINISH = "finish"  # 流结束


@dataclass
class StreamToolEvent:
    """流式工具调用事件

    封装流式响应中的不同类型数据，统一处理文本内容和工具调用。
    """
    event_type: StreamToolEventType
    # 文本内容
    content: Optional[str] = None
    # 工具调用
    tool_call_index: Optional[int] = None  # 工具调用索引（用于增量累积）
    tool_call_id: Optional[str] = None  # 工具调用ID
    tool_name: Optional[str] = None  # 工具名称
    tool_arguments_delta: Optional[str] = None  # 参数增量
    # 结束信息
    finish_reason: Optional[str] = None

    @property
    def is_content(self) -> bool:
        """是否为文本内容事件"""
        return self.event_type == StreamToolEventType.CONTENT

    @property
    def is_tool_call(self) -> bool:
        """是否为工具调用事件"""
        return self.event_type in (
            StreamToolEventType.TOOL_CALL_START,
            StreamToolEventType.TOOL_CALL_DELTA
        )

    @property
    def is_finish(self) -> bool:
        """是否为结束事件"""
        return self.event_type == StreamToolEventType.FINISH


@dataclass
class StreamToolCallResult:
    """流式工具调用完成后的结果

    包含累积的文本内容和工具调用列表。
    """
    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None

    def add_content(self, delta: str):
        """添加文本内容"""
        self.content += delta

    def add_tool_call_start(self, index: int, tool_id: str, tool_name: str):
        """添加工具调用开始"""
        # 确保列表足够长
        while len(self.tool_calls) <= index:
            self.tool_calls.append({"id": "", "name": "", "arguments": ""})
        self.tool_calls[index]["id"] = tool_id
        self.tool_calls[index]["name"] = tool_name

    def add_tool_call_delta(self, index: int, arguments_delta: str):
        """添加工具调用参数增量"""
        while len(self.tool_calls) <= index:
            self.tool_calls.append({"id": "", "name": "", "arguments": ""})
        self.tool_calls[index]["arguments"] += arguments_delta

    def get_complete_tool_calls(self) -> List[Dict[str, Any]]:
        """获取完整的工具调用列表（过滤不完整的）"""
        return [
            tc for tc in self.tool_calls
            if tc["id"] and tc["name"]
        ]

    def to_assistant_message(self) -> Dict[str, Any]:
        """转换为助手消息格式（用于追加到消息历史）"""
        message: Dict[str, Any] = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    }
                }
                for tc in self.get_complete_tool_calls()
            ]
        return message


# ==================== 增强版 LLM 类 ====================

class EnhancedHelloAgentsLLM(HelloAgentsLLM):
    """
    增强版 HelloAgentsLLM - 添加流式工具调用支持

    继承自 HelloAgentsLLM，新增以下方法：
    - astream_invoke_with_tools: 异步流式工具调用
    - get_last_stream_tool_result: 获取最后一次流式工具调用的累积结果
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_stream_tool_result: Optional[StreamToolCallResult] = None

    async def astream_invoke_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        tool_choice: Union[str, Dict] = "auto",
        **kwargs
    ) -> AsyncIterator[StreamToolEvent]:
        """
        异步流式调用 LLM 并支持工具调用（Function Calling）

        这是最优雅的流式工具调用方法，封装了所有流式处理的复杂逻辑。

        Args:
            messages: 消息列表
            tools: 工具 schema 列表
            tool_choice: 工具选择策略
            **kwargs: 其他参数（temperature, max_tokens 等）

        Yields:
            StreamToolEvent: 流式事件，可能是文本内容或工具调用增量

        Example:
            async for event in llm.astream_invoke_with_tools(messages, tools):
                if event.is_content:
                    print(event.content, end="")
                elif event.event_type == StreamToolEventType.TOOL_CALL_START:
                    print(f"\\n调用工具: {event.tool_name}")

            # 获取累积结果
            result = llm.get_last_stream_tool_result()
        """
        from openai import AsyncOpenAI

        # 创建异步客户端
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        # 构建请求参数
        request_params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "stream": True,
        }
        if kwargs.get("temperature") is not None:
            request_params["temperature"] = kwargs["temperature"]
        if self.max_tokens:
            request_params["max_tokens"] = self.max_tokens

        # 初始化累积结果
        result = StreamToolCallResult()

        try:
            response = await client.chat.completions.create(**request_params)

            async for chunk in response:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # 处理文本内容
                if delta.content:
                    result.add_content(delta.content)
                    yield StreamToolEvent(
                        event_type=StreamToolEventType.CONTENT,
                        content=delta.content
                    )

                # 处理工具调用增量
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index

                        # 工具调用开始（收到 ID 或名称）
                        if tc_delta.id or (tc_delta.function and tc_delta.function.name):
                            tool_id = tc_delta.id or ""
                            tool_name = tc_delta.function.name if tc_delta.function else ""
                            if tool_id or tool_name:
                                result.add_tool_call_start(idx, tool_id, tool_name)
                                yield StreamToolEvent(
                                    event_type=StreamToolEventType.TOOL_CALL_START,
                                    tool_call_index=idx,
                                    tool_call_id=tool_id,
                                    tool_name=tool_name
                                )

                        # 工具调用参数增量
                        if tc_delta.function and tc_delta.function.arguments:
                            args_delta = tc_delta.function.arguments
                            result.add_tool_call_delta(idx, args_delta)
                            yield StreamToolEvent(
                                event_type=StreamToolEventType.TOOL_CALL_DELTA,
                                tool_call_index=idx,
                                tool_arguments_delta=args_delta
                            )

                # 处理结束原因
                if choice.finish_reason:
                    result.finish_reason = choice.finish_reason
                    yield StreamToolEvent(
                        event_type=StreamToolEventType.FINISH,
                        finish_reason=choice.finish_reason
                    )

        except Exception as e:
            raise HelloAgentsException(f"流式工具调用失败: {str(e)}")

        # 保存累积结果供后续使用
        self._last_stream_tool_result = result

    def get_last_stream_tool_result(self) -> Optional[StreamToolCallResult]:
        """
        获取最后一次流式工具调用的累积结果

        Returns:
            StreamToolCallResult 或 None
        """
        return self._last_stream_tool_result
