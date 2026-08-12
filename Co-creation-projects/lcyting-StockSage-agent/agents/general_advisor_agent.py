"""
智能股票分析助手 — 普通投资顾问Agent

基于 HelloAgents ReActAgent，根据提供的数据进行综合分析并给出投资建议。
允许协调者Agent调用，支持流式输出。
"""

import sys
import os
from pathlib import Path
from typing import Iterator

_PROJECT_ROOT = Path(__file__).parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
for p in [_HELLO_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.agents.react_agent import ReActAgent
from hello_agents.tools import ToolRegistry
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.core.stream import StreamEvent

GENERAL_ADVISOR_PROMPT = """你是一位专业的A股投资顾问，擅长综合技术和基本面分析。

## 你的职责
1. 根据提供的数据进行综合分析
2. 给出客观、专业的投资建议
3. 明确标注风险因素
4. 提供参考但不构成投资建议

## 分析维度
- **技术面**: 价格走势、成交量、技术指标
- **基本面**: 财务指标、估值水平、行业地位
- **市场情绪**: 舆情倾向、资金流向
- **风险提示**: 政策风险、市场风险、行业风险

## 输出格式
1. **核心观点**：一句话总结
2. **分析逻辑**：2-3个关键支撑论据
3. **风险提示**：最重要的风险因素
4. **免责声明**：以上分析仅供参考

## 重要提醒
- 保持客观中立，不夸大也不隐瞒风险
- 末尾必须标注免责声明
"""


def create_general_advisor_agent(
    llm: HelloAgentsLLM = None,
    system_prompt: str = None,
    max_steps: int = 5,
) -> ReActAgent:
    """创建普通投资顾问Agent

    Args:
        llm: HelloAgentsLLM实例
        system_prompt: 自定义系统提示词
        max_steps: 最大推理步数

    Returns:
        配置好的ReActAgent实例
    """
    if llm is None:
        llm = _create_default_llm()

    registry = ToolRegistry()

    prompt = system_prompt or GENERAL_ADVISOR_PROMPT

    agent = ReActAgent(
        name="投资顾问Agent",
        llm=llm,
        tool_registry=registry,
        system_prompt=prompt,
        config=Config(temperature=0.35, max_tokens=4096),
        max_steps=max_steps,
    )

    return agent


def advise_stream(
    agent: ReActAgent,
    task: str,
) -> Iterator[dict]:
    """流式投资建议 - 供协调者Agent调用

    Args:
        agent: 已配置的投资顾问Agent
        task: 分析任务和数据

    Yields:
        dict: {"type": "status"|"delta"|"done"|"error", "content": str}
    """
    if agent is None:
        yield {"type": "error", "content": "投资顾问Agent未初始化"}
        return

    yield {"type": "status", "content": "投资顾问正在分析..."}

    try:
        result = agent.run(task)
        yield {"type": "delta", "content": result}
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "error", "content": f"投资分析出错: {e}"}


def _create_default_llm() -> HelloAgentsLLM:
    model = os.getenv("LLM_MODEL_ID")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    provider = os.getenv("LLM_PROVIDER", "auto")

    if not api_key:
        raise RuntimeError("LLM_API_KEY 环境变量未设置")

    return HelloAgentsLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        temperature=0.35,
    )
