"""agent.py — FitHealthAgent 主体工厂函数

职责：
    组装并返回一个配置完毕的 ReActAgent 实例，包括：
    - LLM 后端（HelloAgentsLLM）
    - 内置工具：数据存取、FIT 文件组编辑（更新/合并）
    - YouTube 视频搜索工具（原生 Tool 子类，无需任何 MCP 客户端扩展）

设计说明：
    YouTube 搜索直接通过 ``YouTubeSearchTool`` 实现，该类继承自
    ``hello_agents.tools.Tool``，与框架 1.0.0 完全兼容，不依赖
    ``MCPTool`` 或任何框架扩展特性。
    MCP Server（``mcp_servers/youtube_server.py``）保留用于将来
    若需要以 MCP 协议对外暴露该能力时使用。
"""

from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from hello_agents import HelloAgentsLLM, ReActAgent, ToolRegistry

from .fit_tools import (
    DeleteSetTool,
    MergeSetsTool,
    RestoreParsedSourceTool,
    UndoLastEditTool,
    UpdateSetTool,
)
from .health_store import HealthStore
from .health_tools import (
    QueryDailyHealthTool,
    QueryHealthRangeTool,
    QueryHeartRateWindowTool,
    QuerySleepTool,
)
from .prompts import SYSTEM_PROMPT
from .storage import DailyRecordStore
from .tools import QueryDailyRecordsTool, SaveDailyRecordTool
from .youtube_tool import YouTubeSearchTool


def create_fithealth_agent(
    *, avoid_youtube_channels: Iterable[str] | None = None
) -> ReActAgent:
    """创建并返回配置完毕的 FitHealthAgent 实例。

    该函数执行以下步骤：
    1. 初始化 LLM 后端与数据存储层。
    2. 注册所有内置工具（数据存取 + FIT 文件编辑）。
    3. 注册 YouTubeSearchTool（原生 Tool 子类，直接调用 YouTube Data API v3）。
    4. 组装并返回 ReActAgent。

    Returns:
        已完成初始化的 ReActAgent 实例，可直接调用 .run() 处理用户消息。
    """
    llm = HelloAgentsLLM(
        model=os.getenv("LLM_MODEL_ID") or "deepseek-chat",
        base_url=os.getenv("LLM_BASE_URL") or "https://api.deepseek.com",
    )
    store = DailyRecordStore()
    health_store = HealthStore()

    registry = ToolRegistry()

    # ── 内置工具：数据存取 ────────────────────────────────────────────────
    # hello-agents 1.0.0 prints an emoji for every registration. Redirecting
    # library noise also avoids UnicodeEncodeError on Windows GBK consoles.
    with redirect_stdout(io.StringIO()):
        registry.register_tool(SaveDailyRecordTool(store))
        registry.register_tool(QueryDailyRecordsTool(store))

        # ── 全天健康与睡眠查询（SQLite 汇总，不向模型暴露原始时间序列） ───
        registry.register_tool(QueryDailyHealthTool(health_store))
        registry.register_tool(QueryHealthRangeTool(health_store))
        registry.register_tool(QuerySleepTool(health_store))
        registry.register_tool(QueryHeartRateWindowTool(health_store))

        # ── 内置工具：FIT 文件组编辑 ─────────────────────────────────────
        registry.register_tool(UpdateSetTool())
        registry.register_tool(MergeSetsTool())
        registry.register_tool(DeleteSetTool())
        registry.register_tool(UndoLastEditTool())
        registry.register_tool(RestoreParsedSourceTool())

        # ── YouTube 视频搜索（原生 Tool，无需 MCPTool）────────────────────
        registry.register_tool(YouTubeSearchTool(avoid_channels=avoid_youtube_channels))

    with redirect_stdout(io.StringIO()):
        current_time = datetime.now(ZoneInfo("Asia/Shanghai"))
        runtime_system_prompt = (
            SYSTEM_PROMPT
            + "\n\n## Current time\n"
            + f"Current date: {current_time.date().isoformat()}\n"
            + f"Current time: {current_time.isoformat(timespec='seconds')} (Asia/Shanghai)\n"
            + "Resolve relative dates such as today/now/this week using this anchor unless the user explicitly provides a date."
        )
        return ReActAgent(
            name="FitHealthAgent",
            llm=llm,
            tool_registry=registry,
            system_prompt=runtime_system_prompt,
            max_steps=15,
        )
