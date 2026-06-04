"""Service responsible for converting the research topic into actionable tasks."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional

from tool_aware_agent import ToolAwareSimpleAgent

from models import SummaryState, TodoItem
from config import Configuration
from prompts import get_current_date, todo_planner_instructions
from utils import strip_thinking_tokens
from services.llm_resilience import run_with_llm_retry

logger = logging.getLogger(__name__)

TOOL_CALL_PATTERN = re.compile(
    r"\[TOOL_CALL:(?P<tool>[^:]+):(?P<body>[^\]]+)\]",
    re.IGNORECASE,
)


DEFAULT_TASK_SPECS = [
    (
        "岗位搜索",
        "搜索符合用户方向、城市、技术栈和时间要求的实习岗位与招聘线索。",
        "实习生 招聘 校招 投递 官网 BOSS直聘 实习僧 牛客 应届生求职网",
    ),
    (
        "JD要求分析",
        "总结目标岗位常见的技能、学历、项目经历和实习周期要求。",
        "实习生 招聘 JD 岗位要求 技能要求 项目经验",
    ),
    (
        "投递渠道梳理",
        "寻找公司官网、校招官网、内推、学校就业网、牛客等可追踪投递渠道。",
        "实习 投递 渠道 校招 官网 内推 牛客 实习僧 BOSS直聘",
    ),
    (
        "简历优化建议",
        "分析用户背景和岗位要求的匹配点，提出简历与项目经历优化方向。",
        "后端实习 简历优化 项目经历 技能关键词 JD匹配",
    ),
]


class PlanningService:
    """Wraps the planner agent to produce structured TODO items."""

    def __init__(self, planner_agent: ToolAwareSimpleAgent, config: Configuration) -> None:
        self._agent = planner_agent
        self._config = config

    def plan_todo_list(self, state: SummaryState) -> List[TodoItem]:
        """Ask the planner agent to break the topic into actionable tasks."""

        prompt = todo_planner_instructions.format(
            current_date=get_current_date(),
            user_needs=state.research_topic,
        )

        try:
            response = run_with_llm_retry(
                lambda: self._agent.run(prompt),
                self._config,
                operation="planner",
            )
        except Exception as exc:  # pragma: no cover - fallback is validated downstream
            logger.warning("Planner failed; using fallback tasks: %s", exc)
            state.todo_items = self.create_fallback_tasks(state)
            return state.todo_items
        finally:
            self._agent.clear_history()

        logger.info("Planner raw output (truncated): %s", response[:500])

        tasks_payload = self._normalize_tasks(self._extract_tasks(response), state)
        todo_items: List[TodoItem] = []

        for idx, item in enumerate(tasks_payload, start=1):
            task = TodoItem(
                id=idx,
                title=item["title"],
                intent=item["intent"],
                query=item["query"],
            )
            todo_items.append(task)

        state.todo_items = todo_items

        titles = [task.title for task in todo_items]
        logger.info("Planner produced %d tasks: %s", len(todo_items), titles)
        return todo_items

    @staticmethod
    def create_fallback_task(state: SummaryState) -> TodoItem:
        """Create a single fallback task for legacy callers."""

        return PlanningService.create_fallback_tasks(state)[0]

    @staticmethod
    def create_fallback_tasks(state: SummaryState) -> List[TodoItem]:
        """Create default internship-search tasks when planning failed."""

        tasks = PlanningService._default_task_payloads(state)
        return [
            TodoItem(
                id=idx,
                title=item["title"],
                intent=item["intent"],
                query=item["query"],
            )
            for idx, item in enumerate(tasks, start=1)
        ]

    @staticmethod
    def _default_task_payloads(state: SummaryState) -> List[dict[str, str]]:
        """Return default task dictionaries grounded in the user request."""

        user_needs = (state.research_topic or "").strip()
        prefix = f"{user_needs} " if user_needs else ""

        return [
            {
                "title": title,
                "intent": intent,
                "query": f"{prefix}{query}".strip(),
            }
            for title, intent, query in DEFAULT_TASK_SPECS
        ]

    def _normalize_tasks(
        self,
        tasks_payload: List[dict[str, Any]],
        state: SummaryState,
    ) -> List[dict[str, str]]:
        """Ensure planner output has 3-5 complete internship-search tasks."""

        normalized: List[dict[str, str]] = []
        defaults = self._default_task_payloads(state)
        user_needs = (state.research_topic or "").strip()

        if not tasks_payload:
            return defaults

        for idx, item in enumerate(tasks_payload[:5], start=1):
            default = defaults[(idx - 1) % len(defaults)]
            title = str(item.get("title") or default["title"] or f"任务{idx}").strip()
            intent = str(item.get("intent") or default["intent"]).strip()
            query = str(item.get("query") or "").strip()

            if not query:
                query = default["query"]
            elif user_needs and user_needs not in query:
                query = f"{user_needs} {query}".strip()

            query = self._enhance_query(title, intent, query)

            normalized.append(
                {
                    "title": title,
                    "intent": intent,
                    "query": query,
                }
            )

        for default in defaults:
            if len(normalized) >= 3:
                break
            if any(task["title"] == default["title"] for task in normalized):
                continue
            normalized.append(default)

        return normalized[:5]

    @staticmethod
    def _enhance_query(title: str, intent: str, query: str) -> str:
        """Append hiring-focused keywords to keep search results on target."""

        text = f"{title} {intent}"
        hints: list[str] = []

        if any(keyword in text for keyword in ("岗位", "搜索", "机会")):
            hints.extend(["实习生", "招聘", "校招", "投递", "官网", "BOSS直聘", "实习僧"])
        if any(keyword in text for keyword in ("JD", "要求", "技能")):
            hints.extend(["招聘JD", "岗位要求", "实习生"])
        if any(keyword in text for keyword in ("渠道", "投递", "内推")):
            hints.extend(["校招官网", "内推", "牛客", "学校就业网"])
        if any(keyword in text for keyword in ("简历", "项目", "优化", "匹配")):
            hints.extend(["简历优化", "项目经历", "JD匹配", "技能关键词"])

        for hint in hints:
            if hint not in query:
                query = f"{query} {hint}".strip()

        return query

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _extract_tasks(self, raw_response: str) -> List[dict[str, Any]]:
        """Parse planner output into a list of task dictionaries."""

        text = raw_response.strip()
        if self._config.strip_thinking_tokens:
            text = strip_thinking_tokens(text)

        json_payload = self._extract_json_payload(text)
        tasks: List[dict[str, Any]] = []

        if isinstance(json_payload, dict):
            candidate = json_payload.get("tasks")
            if isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, dict):
                        tasks.append(item)
        elif isinstance(json_payload, list):
            for item in json_payload:
                if isinstance(item, dict):
                    tasks.append(item)

        if not tasks:
            tool_payload = self._extract_tool_payload(text)
            if tool_payload and isinstance(tool_payload.get("tasks"), list):
                for item in tool_payload["tasks"]:
                    if isinstance(item, dict):
                        tasks.append(item)

        return tasks

    def _extract_json_payload(self, text: str) -> Optional[dict[str, Any] | list]:
        """Try to locate and parse a JSON object or array from the text."""

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None

        return None

    def _extract_tool_payload(self, text: str) -> Optional[dict[str, Any]]:
        """Parse the first TOOL_CALL expression in the output."""

        match = TOOL_CALL_PATTERN.search(text)
        if not match:
            return None

        body = match.group("body")

        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        parts = [segment.strip() for segment in body.split(",") if segment.strip()]
        payload: dict[str, Any] = {}
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            payload[key.strip()] = value.strip().strip('"').strip("'")

        return payload or None
