"""Deterministic planning tools and their HelloAgents adapters.

The tools deliberately keep calculations and evidence handling out of the LLM.  A
model may explain a plan, but it cannot silently change guest counts, budgets, or
source provenance.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import BanquetRequest, Guest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ToolResult:
    data: Any
    warnings: list[str]


class VenueSearchService:
    """Find wedding-ready venue references before falling back to generic map POIs."""

    endpoint = "https://restapi.amap.com/v5/place/text"
    detail_endpoint = "https://restapi.amap.com/v5/place/detail"

    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or PROJECT_ROOT / "data" / "venue_catalog.json"
        self.wedding_catalog_path = PROJECT_ROOT / "data" / "catalogs" / "shenzhen_wedding_venues.json"

    def execute(self, payload: dict[str, Any]) -> ToolResult:
        city = str(payload["city"])
        keyword = str(payload.get("venue_keyword") or f"{payload.get('banquet_type', '')} 酒店")
        curated = self._wedding_catalog(city, payload)
        if curated:
            return ToolResult(
                curated,
                [
                    "候选优先来自公开婚宴目录或酒店官网，而不是泛酒店 POI；已按本次所需桌数排序。",
                    "目录起价、桌数和菜单套数为采集日的公开参考，不是实时库存或成交价。",
                    "地图查询只建议用于补充候选地址和电话，不能证明当前档期或婚宴套餐。",
                ],
            )
        api_key = os.getenv("AMAP_WEB_SERVICE_KEY")
        if api_key:
            try:
                venues = self._search_amap(city, keyword, api_key)
                if venues:
                    return ToolResult(
                        venues,
                        [
                            "高德仅用于核验场地的地图信息（名称、地址、电话等公开字段）；"
                            "它不能证明该场地有可订婚宴档期、满足桌数，或提供当前套餐价。",
                        ],
                    )
            except Exception as exc:  # Network data is helpful, never fatal.
                fallback = self._catalog(city)
                return ToolResult(
                    fallback,
                    [f"高德 POI 查询失败，已退回演示目录：{exc}"],
                )

        return ToolResult(
            self._catalog(city),
            ["未配置 AMAP_WEB_SERVICE_KEY，以下为演示场地目录，不是实时查询结果。"],
        )

    def _search_amap(self, city: str, keyword: str, api_key: str) -> list[dict[str, Any]]:
        params = {
            "key": api_key,
            "keywords": keyword,
            "region": city,
            "city_limit": "true",
            "page_size": 5,
            "show_fields": "business,children,photos,navi",
        }
        with urlopen(f"{self.endpoint}?{urlencode(params)}", timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
        if str(body.get("status")) != "1":
            raise RuntimeError(body.get("info", "未知高德错误"))

        details = self._amap_details(
            [str(poi["id"]) for poi in body.get("pois", []) if poi.get("id")], api_key
        )
        venues = []
        for poi in body.get("pois", []):
            detail = details.get(str(poi.get("id")), {})
            business = {
                **(poi.get("business", {}) or {}),
                **(detail.get("business", {}) or {}),
            }
            venues.append(
                {
                    "name": poi.get("name", "未命名场地"),
                    "address": detail.get("address") or poi.get("address", "地址待确认"),
                    "phone": detail.get("tel") or poi.get("tel") or business.get("tel") or "地图未公开",
                    "location": detail.get("location") or poi.get("location", ""),
                    "poi_id": poi.get("id", ""),
                    "price_from": None,
                    "capacity": "未提供（需向宴会销售确认）",
                    "source": "高德地图 Web 服务 POI 搜索 + 详情查询",
                    "source_date": "运行时查询",
                    "evidence_level": "POI 实时信息",
                    "rating": business.get("rating", "地图未提供"),
                }
            )
        return venues

    def _amap_details(self, poi_ids: list[str], api_key: str) -> dict[str, dict[str, Any]]:
        """Fetch public POI details in one batch; absent fields remain absent."""
        if not poi_ids:
            return {}
        params = {
            "key": api_key,
            "id": "|".join(poi_ids[:10]),
            "show_fields": "business,photos,navi",
        }
        try:
            with urlopen(f"{self.detail_endpoint}?{urlencode(params)}", timeout=8) as response:
                body = json.loads(response.read().decode("utf-8"))
            if str(body.get("status")) != "1":
                return {}
            return {str(poi["id"]): poi for poi in body.get("pois", []) if poi.get("id")}
        except Exception:
            # The text-search result is still usable even if enrichment is unavailable.
            return {}

    def _wedding_catalog(self, city: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Return locally cached, source-labelled wedding listings for supported cities.

        The cache is deliberately data, not invented LLM output: each record keeps
        its page URL and retrieval date.  It gives a useful first shortlist while
        an authorised partner feed is not available.
        """
        if not self.wedding_catalog_path.exists():
            return []
        with self.wedding_catalog_path.open(encoding="utf-8") as file:
            records = json.load(file)
        required_tables = 0
        try:
            required_tables = (int(payload["guest_count"]) + int(payload["seats_per_table"]) - 1) // int(payload["seats_per_table"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            pass
        matching_city = [item.copy() for item in records if item.get("city") == city]

        def rank(item: dict[str, Any]) -> tuple[int, int, str]:
            minimum, maximum = item.get("min_tables"), item.get("max_tables")
            fits = (
                minimum is None
                or maximum is None
                or (int(minimum) <= required_tables <= int(maximum))
            )
            # Exact/smaller rooms belong ahead of large venues for a small banquet.
            span = int(maximum) - int(minimum) if isinstance(minimum, int) and isinstance(maximum, int) else 10_000
            return (0 if fits else 1, span, str(item.get("name", "")))

        return sorted(matching_city, key=rank)[:5]

    def _catalog(self, city: str) -> list[dict[str, Any]]:
        with self.catalog_path.open(encoding="utf-8") as file:
            catalog = json.load(file)
        return [item for item in catalog if item["city"] == city][:5]


class TavilyEvidenceSearchService:
    """Search public web evidence; it never turns a snippet into a fact itself."""

    endpoint = "https://api.tavily.com/search"

    def execute(self, payload: dict[str, Any]) -> ToolResult:
        query = str(payload.get("query", "")).strip()
        if not query:
            return ToolResult({"query": "", "sources": []}, ["网络证据搜索缺少 query。"])
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return ToolResult(
                {"query": query, "sources": []},
                ["未配置 TAVILY_API_KEY，跳过公开网络证据检索。"],
            )
        request_body = json.dumps(
            {
                "query": query,
                "search_depth": "basic",
                "max_results": min(max(int(payload.get("max_results", 3)), 1), 5),
                "include_answer": False,
                "include_raw_content": False,
                "topic": "general",
            }
        ).encode("utf-8")
        request = Request(
            self.endpoint,
            data=request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return ToolResult(
                {"query": query, "sources": []},
                [f"Tavily 证据搜索失败：{exc}"],
            )
        sources = [
            {
                "title": str(item.get("title", "未命名页面")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("content", "")),
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
            for item in body.get("results", [])
            if item.get("url")
        ]
        return ToolResult(
            {"query": query, "sources": sources},
            ["搜索结果是待审校的公开网页证据；只有审校通过且保留来源链接的字段才能进入方案。"],
        )


class PublishedMenuExampleService:
    """Return source-labelled local menus as examples, never as regional rules."""

    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or PROJECT_ROOT / "data" / "catalogs" / "shenzhen_published_menu_examples.json"

    def execute(self, payload: dict[str, Any]) -> ToolResult:
        if not self.catalog_path.exists():
            return ToolResult([], ["尚未建立该城市的公开菜单样本库。"])
        with self.catalog_path.open(encoding="utf-8") as file:
            examples = json.load(file)
        city = str(payload.get("city", ""))
        banquet_type = str(payload.get("banquet_type", ""))
        matched = [
            item for item in examples
            if item.get("city") == city and item.get("banquet_type") == banquet_type
        ]
        return ToolResult(
            matched[:3],
            ["公开菜单样本用于帮助比较菜品构成；不能当作其他场地的报价或强制菜单模板。"],
        )


class SeatingPlanService:
    """Create a role-oriented seating list; physical chair orientation is on-site."""

    _priority_keywords = {
        0: ("主办", "宴请方", "董事长", "总经理"),
        1: ("主宾", "客户", "嘉宾", "贵宾", "领导", "父亲", "母亲", "父", "母"),
        2: ("陪", "舅", "叔", "伯", "姨", "长辈"),
        3: ("同事", "朋友", "同学", "亲友"),
    }

    def execute(self, payload: dict[str, Any]) -> ToolResult:
        request = BanquetRequest.from_dict(payload)
        grouped_guests = self._group_guests(request)
        target_sizes = self._target_table_sizes(request)
        assigned_tables: list[list[Guest]] = [[] for _ in target_sizes]
        for group in grouped_guests:
            table_index = self._find_table_for_group(assigned_tables, target_sizes, group)
            assigned_tables[table_index].extend(group)
        tables: list[dict[str, Any]] = []
        for index, people in enumerate(assigned_tables):
            table_name = "主桌" if index == 0 else f"宾客桌 {index}"
            tables.append(
                {
                    "name": table_name,
                    "capacity": request.seats_per_table,
                    "guests": [self._seat_entry(guest, seat_no, index, request) for seat_no, guest in enumerate(people, 1)],
                }
            )

        warnings = [
            "“主位/主宾位”是角色标记；现场的具体朝向应由主办方结合入口、舞台和当地习惯确认。",
        ]
        assigned = {entry["name"] for table in tables for entry in table["guests"]}
        if len(assigned) != request.guest_count:
            warnings.append("存在未分配或重复宾客，请检查名单。")
        warnings.extend(self._relationship_warnings(request.guests, tables))
        return ToolResult(tables, warnings)

    def _group_guests(self, request: BanquetRequest) -> list[list[Guest]]:
        """Keep explicitly linked guests together while preserving role priority."""
        pinned_names = list(request.seat_overrides.values())
        by_name = {guest.name: guest for guest in request.guests}
        pinned = [by_name[name] for name in pinned_names]
        remaining_names = set(by_name) - set(pinned_names)
        groups: list[list[Guest]] = [[guest] for guest in pinned]
        while remaining_names:
            seed = remaining_names.pop()
            connected = {seed}
            frontier = [seed]
            while frontier:
                current = frontier.pop()
                for candidate in by_name.values():
                    linked = current in candidate.must_with or candidate.name in by_name[current].must_with
                    if linked and candidate.name in remaining_names:
                        remaining_names.remove(candidate.name)
                        connected.add(candidate.name)
                        frontier.append(candidate.name)
            groups.append(sorted((by_name[name] for name in connected), key=self._priority))

        pinned_count = len(pinned)
        return groups[:pinned_count] + sorted(
            groups[pinned_count:],
            key=lambda group: (min(self._priority(guest) for guest in group), group[0].name),
        )

    @staticmethod
    def _target_table_sizes(request: BanquetRequest) -> list[int]:
        """Spread guests evenly among the minimum feasible number of tables."""
        base, remainder = divmod(request.guest_count, request.table_count)
        return [base + (1 if index < remainder else 0) for index in range(request.table_count)]

    @staticmethod
    def _find_table_for_group(
        tables: list[list[Guest]], target_sizes: list[int], group: list[Guest]
    ) -> int:
        for index, table in enumerate(tables):
            if len(table) + len(group) <= target_sizes[index]:
                return index
        # A relationship group can exceed the ideal balanced size. Put it in the
        # least-populated table rather than silently splitting the group.
        return min(range(len(tables)), key=lambda index: len(tables[index]))

    def _priority(self, guest: Guest) -> tuple[int, str]:
        role = guest.role
        if role in {"新郎", "新娘"}:
            return 0, guest.name
        for priority, words in self._priority_keywords.items():
            if any(word in role for word in words):
                return priority, guest.name
        return 4, guest.name

    def _seat_entry(
        self, guest: Guest, seat_no: int, table_index: int, request: BanquetRequest
    ) -> dict[str, str | int]:
        if table_index == 0:
            labels = {1: "主位", 2: "主宾位", 3: "主陪位", 4: "次主宾位"}
            label = labels.get(seat_no, "主桌宾客位")
        else:
            label = "桌长位" if seat_no == 1 else "宾客位"
        return {
            "seat_no": seat_no,
            "seat_role": label,
            "name": guest.name,
            "guest_role": guest.role,
            "reason": self._reason(guest, label, request),
        }

    @staticmethod
    def _reason(guest: Guest, label: str, request: BanquetRequest) -> str:
        if request.seat_overrides.get(label) == guest.name:
            return f"由主办方明确指定为{label}。"
        if label == "主位":
            return f"{guest.role}，优先安排为主桌接待与统筹角色。"
        if label in {"主宾位", "次主宾位"}:
            return f"{guest.role}，按重要宾客/核心长辈优先级安排。"
        if label == "主陪位":
            return f"{guest.role}，便于协助主位接待本桌宾客。"
        if label == "桌长位":
            return f"{guest.role}，作为本桌照应与沟通的优先人选。"
        return f"{guest.role}，按关系亲近度与分桌均衡安排。"

    @staticmethod
    def _relationship_warnings(guests: list[Guest], tables: list[dict[str, Any]]) -> list[str]:
        table_by_name = {
            entry["name"]: table["name"]
            for table in tables
            for entry in table["guests"]
        }
        warnings: list[str] = []
        for guest in guests:
            for target in guest.must_with:
                if target in table_by_name and table_by_name.get(guest.name) != table_by_name[target]:
                    warnings.append(f"{guest.name} 希望与 {target} 同桌，但当前未满足，请人工调整。")
            for target in guest.avoid_with:
                if target in table_by_name and table_by_name.get(guest.name) == table_by_name[target]:
                    warnings.append(f"{guest.name} 希望避免与 {target} 同桌，但当前未满足，请人工调整。")
        return warnings


class RegionalEtiquetteService:
    """Retrieve regional references without presenting them as universal rules."""

    def __init__(self, profile_path: Path | None = None) -> None:
        self.profile_path = profile_path or PROJECT_ROOT / "data" / "etiquette" / "regional_profiles.json"

    def execute(self, payload: dict[str, Any]) -> ToolResult:
        request = BanquetRequest.from_dict(payload)
        research = payload.get("research", {}) or {}
        researched_menu = research.get("menu", {}) if isinstance(research, dict) else {}
        source_urls = researched_menu.get("source_urls", []) if isinstance(researched_menu, dict) else []
        if source_urls:
            notes = researched_menu.get("notes", [])
            return ToolResult(
                {
                    "profile": f"{request.city}公开资料检索并经审校",
                    "seating_focus": "先明确主办方、核心长辈与主宾，再由主办方根据现场入口、舞台和家庭习惯确认实体朝向。",
                    "menu_focus": "；".join(notes) if notes else "菜单依据报告中的公开来源建议，仍以所选酒店当期套餐为准。",
                    "beverage_focus": "同时准备酒精与非酒精饮品；开瓶费和服务费以酒店书面答复为准。",
                    "source_urls": source_urls,
                },
                ["地域菜单建议来自本次网络检索并经审校的来源；它不是对全城宴席习惯的绝对断言。"],
            )
        with self.profile_path.open(encoding="utf-8") as file:
            profiles = json.load(file)
        profile = profiles["通用"]
        return ToolResult(
            {
                "profile": "未取得经审校的本地菜单证据",
                **profile,
                "menu_focus": "未取得经审校的本地菜单资料，不套用其他城市或地区的菜品结构。",
                "source_urls": [],
            },
            [
                "未取得经审校的本地菜单证据：报告不会套用其他城市或地区的菜品结构。",
                "地域礼俗用于生成可讨论的建议，不替代双方家庭、主办方或酒店礼宾的最终决定。",
                *profile.get("confirmation_points", []),
            ],
        )


class MenuBudgetService:
    """Build an explicitly estimated menu and budget; it never claims a venue quote."""

    def execute(self, payload: dict[str, Any]) -> ToolResult:
        request = BanquetRequest.from_dict(payload)
        tables = request.table_count
        per_table_cap = request.budget / tables
        food_ratio = 0.68
        beverage_ratio = 0.16
        service_ratio = 0.08
        reserve_ratio = 0.08
        estimated = {
            "餐费": round(request.budget * food_ratio),
            "酒水饮料": round(request.budget * beverage_ratio),
            "服务费与杂费预留": round(request.budget * service_ratio),
            "应急备用金": request.budget - round(request.budget * (food_ratio + beverage_ratio + service_ratio)),
        }
        research = payload.get("research", {}) or {}
        researched_menu = research.get("menu", {}) if isinstance(research, dict) else {}
        source_urls = researched_menu.get("source_urls", []) if isinstance(researched_menu, dict) else []
        has_verified_local_menu = bool(
            source_urls
            and (
                researched_menu.get("structure", [])
                or researched_menu.get("main_dishes", [])
            )
        )
        if has_verified_local_menu:
            structure = researched_menu.get("structure", [])
            main_dishes = researched_menu.get("main_dishes", [])
            structure_note = "本节仅采用本次检索后、经证据审校保留的本地菜单建议；最终菜单以酒店书面套餐为准。"
        else:
            structure = ["尚未取得经审校的当地婚宴菜单证据；请先选择场地或补充酒店套餐链接。"]
            main_dishes = []
            structure_note = "不会套用广东、河南或其他城市的菜单模板。取得本地公开套餐或礼俗资料后，Agent 才会生成当地化菜品建议。"
        menu = {
            "每桌菜品结构": structure,
            "结构说明": structure_note,
            "主菜建议": main_dishes,
            "菜单来源": source_urls,
            "忌口处理": request.dietary_constraints or ["未提供忌口信息；下单前请再次与宾客和酒店确认。"],
            "酒水建议": [
                f"白酒：每桌约 1/3 瓶起，根据饮酒宾客比例调整（总预算内预留 {estimated['酒水饮料']} 元）。",
                "红酒、啤酒、饮料和茶水由酒店最终套餐与开瓶费规则确认。",
            ],
            "预算": estimated,
            "每桌可用餐饮预算": round((estimated["餐费"] + estimated["酒水饮料"]) / tables),
            "每桌总预算上限": round(per_table_cap),
        }
        return ToolResult(
            menu,
            [
                "菜品和酒水为预算方案，不等于酒店最终菜单；请向商家确认食材、份量、服务费和开瓶费。",
                *([] if has_verified_local_menu else ["本地菜单证据不足，已停止使用静态地域菜单模板。"]),
            ],
        )


# HelloAgents integration ---------------------------------------------------

try:
    from hello_agents import ToolRegistry
    from hello_agents.tools import Tool, ToolParameter, ToolResponse

    HELLO_AGENTS_AVAILABLE = True
except ImportError:  # Makes `python main.py` explain the setup error cleanly.
    HELLO_AGENTS_AVAILABLE = False
    ToolRegistry = Any  # type: ignore[misc,assignment]


if HELLO_AGENTS_AVAILABLE:

    class ServiceToolAdapter(Tool):
        """Adapt a deterministic service to a real HelloAgents Tool."""

        def __init__(self, name: str, description: str, service: Any) -> None:
            super().__init__(name=name, description=description)
            self.service = service

        def run(self, parameters: dict[str, Any]) -> ToolResponse:
            result = self.service.execute(parameters)
            envelope = {"data": result.data, "warnings": result.warnings}
            return ToolResponse.success(text=json.dumps(envelope, ensure_ascii=False))

        def get_parameters(self) -> list[ToolParameter]:
            return [
                ToolParameter(
                    name="city",
                    type="string",
                    description="举办宴席的城市；工作流会同时传入完整宴席需求。",
                    required=True,
                ),
                ToolParameter(
                    name="banquet_type",
                    type="string",
                    description="宴请类型，例如婚宴或商务宴。",
                    required=False,
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="公开网页证据搜索词，仅 web_evidence_search 使用。",
                    required=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="公开网页证据最多返回条数，仅 web_evidence_search 使用。",
                    required=False,
                ),
            ]


class HelloAgentsToolRuntime:
    """Registers project tools in HelloAgents ToolRegistry and invokes adapters."""

    def __init__(self) -> None:
        if not HELLO_AGENTS_AVAILABLE:
            raise RuntimeError("未安装 hello-agents。请先执行 pip install -r requirements.txt。")
        self.registry = ToolRegistry()
        self.adapters: dict[str, ServiceToolAdapter] = {}
        self._register("venue_search", "查询真实 POI 或演示场地目录", VenueSearchService())
        self._register("web_evidence_search", "通过 Tavily 搜索公开网页证据，不直接将摘要当作事实", TavilyEvidenceSearchService())
        self._register("published_menu_examples", "读取带来源的本地酒店公开菜单样本", PublishedMenuExampleService())
        self._register("seating_plan", "根据身份关系生成分桌与座次", SeatingPlanService())
        self._register("regional_etiquette", "检索地域礼俗参考与待确认项", RegionalEtiquetteService())
        self._register("menu_budget", "生成地域化菜单、酒水与预算建议", MenuBudgetService())

    def _register(self, name: str, description: str, service: Any) -> None:
        adapter = ServiceToolAdapter(name, description, service)
        self.registry.register_tool(adapter)
        self.adapters[name] = adapter

    def invoke(self, name: str, request: BanquetRequest, extra_payload: dict[str, Any] | None = None) -> ToolResult:
        # Go through ToolRegistry rather than calling the service directly.  This
        # gives every tool call the framework's validation, timing and traceable
        # context, which is important for later observability work.
        payload = asdict(request)
        payload.update(extra_payload or {})
        response = self.registry.execute_tool(name, payload)
        payload = json.loads(response.text)
        return ToolResult(payload["data"], payload["warnings"])

    def invoke_payload(self, name: str, payload: dict[str, Any]) -> ToolResult:
        """Invoke a registered tool with non-request research parameters."""
        response = self.registry.execute_tool(name, payload)
        result = json.loads(response.text)
        return ToolResult(result["data"], result["warnings"])
