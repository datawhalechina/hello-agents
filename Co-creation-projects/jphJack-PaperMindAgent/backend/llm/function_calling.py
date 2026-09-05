"""Function Calling 工具调用循环：调用模型→执行工具→回填结果→继续调用"""
import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional, Union

from backend.config import settings
from backend.llm.client import DeepSeekClient
from backend.models.schemas import ToolCallRecord

logger = logging.getLogger(__name__)

# 工具可调用对象类型：同步或异步函数均可
ToolCallable = Union[Callable[..., Any], Callable[..., Awaitable[Any]]]


def _message_to_dict(message: Any) -> dict:
    """把 OpenAI 返回的 message 对象转为可序列化的 dict，便于回填到 messages"""
    msg: dict = {"role": message.role, "content": message.content or ""}
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    return msg


class ToolLoop:
    """工具调用循环

    循环逻辑：调用模型 → 若返回 tool_calls 则执行对应工具 →
    把工具结果以 role=tool 回填 → 继续调用，直到模型无 tool_calls 返回最终文本。
    """

    def __init__(
        self,
        client: DeepSeekClient,
        tool_registry: dict[str, ToolCallable],
    ) -> None:
        self.client = client
        self.tool_registry = tool_registry
        self.tool_calls: list[ToolCallRecord] = []

    async def run(
        self,
        messages: list[dict],
        tools_schema: list[dict],
        max_iterations: int = 10,
    ) -> str:
        """运行工具调用循环，返回模型最终文本回复"""
        # 复制一份消息，避免修改入参
        working_messages = list(messages)
        final_content = ""

        for iteration in range(max_iterations):
            response = await self.client.chat(
                messages=working_messages,
                tools=tools_schema,
                tool_choice="auto",
            )

            choice = response.choices[0]
            message = choice.message
            final_content = message.content or ""

            # 把模型消息追加到对话上下文
            working_messages.append(_message_to_dict(message))

            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                # 模型未请求工具，返回最终文本
                return final_content

            # 依次执行每个工具调用并回填结果
            for tool_call in tool_calls:
                record, content = await self._execute_tool_call(tool_call)
                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content,
                    }
                )

        # 达到最大迭代次数仍未结束，降级返回最后一次内容
        logger.warning("工具调用循环达到最大迭代次数 %d", max_iterations)
        return final_content

    async def _invoke(self, tool_fn: ToolCallable, args: dict) -> Any:
        """调用工具，自动区分同步/异步函数

        同步工具用 asyncio.to_thread 包装，避免阻塞事件循环；
        异步工具直接 await。
        """
        if asyncio.iscoroutinefunction(tool_fn):
            return await tool_fn(**args)
        return await asyncio.to_thread(tool_fn, **args)

    async def _execute_tool_call(self, tool_call: Any) -> tuple[ToolCallRecord, str]:
        """执行单个工具调用，返回 (调用记录, 回填结果文本)

        工具执行失败时重试 TOOL_MAX_RETRIES 次，仍失败则记录错误并继续（降级不崩溃）。
        """
        tool_name = tool_call.function.name
        # 解析工具参数
        try:
            args = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        args_summary = json.dumps(args, ensure_ascii=False)[:200]

        # 查找工具
        tool_fn = self.tool_registry.get(tool_name)
        if tool_fn is None:
            record = ToolCallRecord(
                tool_name=tool_name,
                args_summary=args_summary,
                success=False,
                duration_sec=0.0,
                error=f"未注册的工具: {tool_name}",
            )
            self.tool_calls.append(record)
            return record, f"工具执行失败: 未注册的工具 {tool_name}"

        # 执行工具（带重试）
        start = time.perf_counter()
        last_error: Optional[str] = None
        result: Any = None
        success = False
        total_attempts = settings.TOOL_MAX_RETRIES + 1  # 初次 + 重试次数
        for attempt in range(total_attempts):
            try:
                result = await self._invoke(tool_fn, args)
                success = True
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "工具 %s 执行失败 (attempt=%d/%d): %s",
                    tool_name,
                    attempt + 1,
                    total_attempts,
                    exc,
                )
        duration = time.perf_counter() - start

        record = ToolCallRecord(
            tool_name=tool_name,
            args_summary=args_summary,
            success=success,
            duration_sec=round(duration, 3),
            error=None if success else last_error,
            result=result if success else None,  # 持久化工具返回值，供 ReportAgent 整合
        )
        self.tool_calls.append(record)

        # 构造回填内容：成功则序列化结果，失败则回填错误信息（降级继续）
        if success:
            if isinstance(result, str):
                content = result
            else:
                content = json.dumps(result, ensure_ascii=False, default=str)
        else:
            content = f"工具执行失败: {last_error}"
        return record, content

    def get_tool_records(self) -> list[ToolCallRecord]:
        """返回所有工具调用记录"""
        return list(self.tool_calls)
