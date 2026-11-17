"""Evidence-first multi-agent research for venues and local banquet menus.

Search results are deliberately separated from accepted facts.  Two specialist
agents extract only explicit claims, then a ReflectionAgent audits them against
the original source URLs before the planner can use them.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from hello_agents import Config, HelloAgentsLLM, ReflectionAgent, SimpleAgent

from .models import BanquetRequest
from .tools import HelloAgentsToolRuntime


class BanquetResearchTeam:
    """Coordinate specialised HelloAgents roles around the shared ToolRegistry."""

    def __init__(self, runtime: HelloAgentsToolRuntime) -> None:
        self.runtime = runtime
        config = Config(
            trace_enabled=True,
            trace_dir="outputs/traces",
            trace_sanitize=True,
            session_enabled=False,
            subagent_enabled=True,
            max_concurrent_tools=3,
        )
        # Some reasoning models spend tokens before emitting the JSON.  Keep the
        # evidence packet compact and leave enough room for an actual response.
        self.venue_researcher = SimpleAgent(
            "venue_evidence_researcher",
            HelloAgentsLLM(temperature=0, max_tokens=3200),
            system_prompt=(
                "你是场地公开信息研究员。只可根据给出的网页标题、URL 与摘要提取内容。"
                "绝不猜测、补全、换算或将搜索排名当作事实。只输出合法 JSON。"
            ),
            config=config,
            enable_tool_calling=False,
        )
        self.menu_researcher = SimpleAgent(
            "local_menu_researcher",
            HelloAgentsLLM(temperature=0, max_tokens=3200),
            system_prompt=(
                "你是本地宴席菜单研究员。只可根据给出的网页标题、URL 与摘要提出建议。"
                "没有充分本地证据时必须返回空列表；不可套用其他地区经验。只输出合法 JSON。"
            ),
            config=config,
            enable_tool_calling=False,
        )
        self.evidence_reviewer = ReflectionAgent(
            "evidence_reviewer",
            HelloAgentsLLM(temperature=0, max_tokens=3200),
            system_prompt=(
                "你是严格的证据审校员。审校场地与菜单研究结果时，只允许保留带有原始 URL 且"
                "能在摘要中找到明确支持的内容。无法支持、来源不明或只是推断的内容必须剔除。"
                "你的最终回答必须是合法 JSON，不能使用 Markdown 代码块。"
            ),
            config=config,
            # The deterministic URL whitelist below is the second audit layer;
            # avoid an additional free-form rewrite turn for every CLI run.
            max_iterations=0,
            enable_tool_calling=False,
        )

    def research(self, request: BanquetRequest, venues: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
        """Search, extract, then audit.  Any failure degrades to an empty result."""
        warnings: list[str] = []
        venue_evidence: list[dict[str, Any]] = []
        for venue in venues[:2]:
            name = str(venue.get("name", ""))
            query = f"{name} {request.city} 婚宴 套餐 价格 联系方式 官网"
            result = self.runtime.invoke_payload(
                "web_evidence_search",
                {"city": request.city, "banquet_type": request.banquet_type, "query": query, "max_results": 2},
            )
            warnings.extend(result.warnings)
            venue_evidence.append({"venue": name, **result.data})

        menu_query = f"{request.city} {request.banquet_type} 酒店 宴席菜单 头盘 热菜 汤品 当地习俗"
        menu_search = self.runtime.invoke_payload(
            "web_evidence_search",
            {"city": request.city, "banquet_type": request.banquet_type, "query": menu_query, "max_results": 3},
        )
        warnings.extend(menu_search.warnings)
        raw_evidence = {"venue_evidence": venue_evidence, "menu_evidence": menu_search.data}
        compact_evidence = self._compact_evidence(raw_evidence)
        allowed_urls = self._source_urls(raw_evidence)
        if not allowed_urls:
            return self._empty_result(raw_evidence), warnings

        try:
            venue_prompt = (
                "从以下证据中提取场地信息。只保留摘要明确写出的套餐价格、公开电话或厅容量；"
                "一个字段没有明确证据就留空；没有可用声明时返回空数组。只输出 JSON："
                '{"claims":[{"venue":"","package_price":"","phone":"","capacity":"","source_url":"","evidence":""}]}'
                "\n证据：" + json.dumps(compact_evidence["venue_evidence"], ensure_ascii=False)
            )
            menu_prompt = (
                "从以下本地资料中提取婚宴菜单建议。仅当摘要明确支持时才写入。不要从其他城市迁移规则。只输出 JSON："
                '{"structure":[""],"main_dishes":[""],"notes":[""],"source_urls":[""]}'
                "\n证据：" + json.dumps(compact_evidence["menu_evidence"], ensure_ascii=False)
            )
            # 两项研究没有前后依赖，使用独立 HelloAgents 客户端并行执行。
            with ThreadPoolExecutor(max_workers=2) as pool:
                venue_future = pool.submit(self._ask_json, self.venue_researcher, venue_prompt)
                menu_future = pool.submit(self._ask_json, self.menu_researcher, menu_prompt)
                venue_draft = venue_future.result()
                menu_draft = menu_future.result()
            reviewed = self._ask_json(
                self.evidence_reviewer,
                """审校下列草稿。原始证据 URL 白名单如下；草稿中的 source_url/source_urls 不在白名单内即删除。
                只有 evidence 能在给定摘要中得到支持才批准。输出：
                {"approved_venue_claims":[{"venue":"","package_price":"","phone":"","capacity":"","source_url":"","evidence":""}],"menu":{"structure":[""],"main_dishes":[""],"notes":[""],"source_urls":[""]},"rejected":[""]}

                URL 白名单：""" + json.dumps(sorted(allowed_urls), ensure_ascii=False)
                + "\n场地草稿：" + json.dumps(venue_draft, ensure_ascii=False)
                + "\n菜单草稿：" + json.dumps(menu_draft, ensure_ascii=False)
                + "\n原始证据：" + json.dumps(compact_evidence, ensure_ascii=False),
            )
        except Exception as exc:
            warnings.append(f"多智能体证据审校未完成，已停止使用网络结论：{exc}")
            return self._empty_result(raw_evidence), warnings

        result = self._sanitize_review(
            reviewed,
            allowed_urls,
            raw_evidence,
            {str(venue.get("name", "")) for venue in venues},
        )
        if not result["menu"]["source_urls"]:
            warnings.append("本地菜单研究未获得可复核结论；报告不会套用其他地区的菜单模板。")
        return result, warnings

    @staticmethod
    def _ask_json(agent: SimpleAgent, prompt: str) -> dict[str, Any]:
        answer = agent.run(prompt)
        return BanquetResearchTeam._parse_json(answer)

    @staticmethod
    def _parse_json(answer: str) -> dict[str, Any]:
        text = (answer or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.endswith("```"):
                text = text[:-3]
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("智能体未返回 JSON 对象")
        value = json.loads(text[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("智能体 JSON 顶层必须是对象")
        return value

    @staticmethod
    def _source_urls(raw_evidence: dict[str, Any]) -> set[str]:
        urls: set[str] = set()
        for venue in raw_evidence.get("venue_evidence", []):
            urls.update(str(item.get("url")) for item in venue.get("sources", []) if item.get("url"))
        urls.update(
            str(item.get("url"))
            for item in raw_evidence.get("menu_evidence", {}).get("sources", [])
            if item.get("url")
        )
        return urls

    @staticmethod
    def _compact_evidence(raw_evidence: dict[str, Any]) -> dict[str, Any]:
        """Keep bounded evidence excerpts so structured output is not starved."""
        def compact_source(source: dict[str, Any]) -> dict[str, Any]:
            return {
                "title": str(source.get("title", ""))[:160],
                "url": str(source.get("url", "")),
                "snippet": str(source.get("snippet", ""))[:600],
            }

        return {
            "venue_evidence": [
                {
                    "venue": venue.get("venue", ""),
                    "sources": [compact_source(item) for item in venue.get("sources", [])[:2]],
                }
                for venue in raw_evidence.get("venue_evidence", [])
            ],
            "menu_evidence": {
                "query": raw_evidence.get("menu_evidence", {}).get("query", ""),
                "sources": [
                    compact_source(item)
                    for item in raw_evidence.get("menu_evidence", {}).get("sources", [])[:3]
                ],
            },
        }

    def _empty_result(self, raw_evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "证据不足",
            "venue_claims": [],
            "menu": {"structure": [], "main_dishes": [], "notes": [], "source_urls": []},
            "rejected": ["未取得经多智能体审校的可用结论。"],
            "raw_evidence": raw_evidence,
        }

    def _sanitize_review(
        self,
        reviewed: dict[str, Any],
        allowed_urls: set[str],
        raw_evidence: dict[str, Any],
        candidate_names: set[str],
    ) -> dict[str, Any]:
        claims = []
        for claim in reviewed.get("approved_venue_claims", []):
            if (
                not isinstance(claim, dict)
                or claim.get("source_url") not in allowed_urls
                or str(claim.get("venue", "")) not in candidate_names
            ):
                continue
            claims.append(
                {
                    key: str(claim.get(key, ""))
                    for key in ("venue", "package_price", "phone", "capacity", "source_url", "evidence")
                }
            )
        raw_menu = reviewed.get("menu", {}) if isinstance(reviewed.get("menu"), dict) else {}
        menu_urls = [str(url) for url in raw_menu.get("source_urls", []) if str(url) in allowed_urls]
        menu = {
            "structure": self._string_list(raw_menu.get("structure")) if menu_urls else [],
            "main_dishes": self._string_list(raw_menu.get("main_dishes")) if menu_urls else [],
            "notes": self._string_list(raw_menu.get("notes")) if menu_urls else [],
            "source_urls": menu_urls,
        }
        return {
            "status": "已审校" if claims or menu_urls else "证据不足",
            "venue_claims": claims,
            "menu": menu,
            "rejected": self._string_list(reviewed.get("rejected")),
            "raw_evidence": raw_evidence,
        }

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:8]
