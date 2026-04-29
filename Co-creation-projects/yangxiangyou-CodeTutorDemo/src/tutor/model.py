"""封装真实模型与测试替身，避免业务逻辑直接依赖外部网络。"""

from __future__ import annotations

import os
from typing import Iterable, Protocol

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI


class LLMAdapter(Protocol):
    """统一业务层调用接口，便于在测试中替换实现。"""

    def invoke(self, messages: Iterable[BaseMessage]) -> str:
        """接收消息列表并返回模型原始文本输出。"""


class LangChainLLMAdapter:
    """生产环境适配器，负责调用真实大模型。"""

    def __init__(self, model: ChatOpenAI) -> None:
        self._model = model

    def invoke(self, messages: Iterable[BaseMessage]) -> str:
        response = self._model.invoke(list(messages))
        content = response.content
        if isinstance(content, str):
            return content
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))


class FakeLLMAdapter:
    """测试替身，按顺序吐出预设结果，保证测试稳定复现。"""

    def __init__(self, outputs: Iterable[str]) -> None:
        self._outputs = list(outputs)
        self._index = 0

    def invoke(self, messages: Iterable[BaseMessage]) -> str:
        if self._index >= len(self._outputs):
            raise IndexError("FakeLLMAdapter has no more outputs.")
        output = self._outputs[self._index]
        self._index += 1
        return output


def build_default_llm() -> LangChainLLMAdapter:
    """读取环境变量并构建默认模型。"""

    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("Missing API_KEY. Please configure it in your .env file.")

    model = ChatOpenAI(
        api_key=api_key,
        base_url=os.getenv("BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("MODEL_NAME", "deepseek-chat"),
        temperature=0.4,
        max_tokens=900,
    )
    return LangChainLLMAdapter(model)
