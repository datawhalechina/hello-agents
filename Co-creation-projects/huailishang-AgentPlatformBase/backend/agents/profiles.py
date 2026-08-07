from __future__ import annotations

from backend.models import AgentKind, AgentProfile


def default_profiles() -> list[AgentProfile]:
    return [
        AgentProfile(
            agent_id="deep_research",
            name="搜索员",
            kind=AgentKind.research,
            description="自动搜索互联网结果并生成研究报告。",
            system_prompt="Coordinate research tasks and produce a report.",
            tools=["web_search", "notes", "summarizer"],
            enabled=True,
        ),
        AgentProfile(
            agent_id="rss_digest",
            name="资讯员",
            kind=AgentKind.research,
            description="拉取 RSS 源并生成中文资讯简报。",
            system_prompt="Collect RSS updates, summarize them in Chinese, and return a daily digest.",
            tools=["rss", "article_extractor", "translator", "html_digest"],
            enabled=True,
        ),
    ]
