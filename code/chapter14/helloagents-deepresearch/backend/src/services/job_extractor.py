"""Structured job extraction and first-pass matching."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from config import Configuration
from models import JobItem, SummaryState, TodoItem
from tool_aware_agent import ToolAwareSimpleAgent
from utils import strip_thinking_tokens
from services.llm_resilience import run_with_llm_retry
from services.search import is_reliable_job_source
from services.text_processing import strip_tool_calls

logger = logging.getLogger(__name__)

MAX_JOB_ITEMS = 8
UNKNOWN = "未确认"


class JobExtractionService:
    """Extract structured internship/job items from search context."""

    def __init__(
        self,
        extractor_factory: Callable[[], ToolAwareSimpleAgent],
        config: Configuration,
    ) -> None:
        self._agent_factory = extractor_factory
        self._config = config

    def extract_jobs(
        self,
        state: SummaryState,
        task: TodoItem,
        search_result: dict[str, Any] | None,
        context: str,
    ) -> list[JobItem]:
        """Return structured jobs, falling back to source-only items on failure."""

        prompt = self.build_prompt(state, task, context)
        agent = self._agent_factory()
        try:
            response = run_with_llm_retry(
                lambda: agent.run(prompt),
                self._config,
                operation="job extraction",
            )
            jobs = self._parse_response(response)
        except Exception as exc:  # pragma: no cover - defensive guardrail
            logger.warning("Job extraction failed; using fallback sources: %s", exc)
            jobs = []
        finally:
            agent.clear_history()

        if not jobs:
            jobs = self._fallback_from_sources(search_result)

        return self._dedupe_and_sort(jobs)[:MAX_JOB_ITEMS]

    def build_prompt(self, state: SummaryState, task: TodoItem, context: str) -> str:
        """Build the extraction prompt sent to the job extraction LLM."""

        return (
            "<用户求职目标>\n"
            f"{state.research_topic}\n"
            "</用户求职目标>\n\n"
            "<当前任务>\n"
            f"任务名称：{task.title}\n"
            f"任务目标：{task.intent}\n"
            f"检索 query：{task.query}\n"
            "</当前任务>\n\n"
            "<搜索来源上下文>\n"
            f"{context}\n"
            "</搜索来源上下文>\n\n"
            "请抽取真实岗位/JD条目并输出严格 JSON。"
            "不要编造岗位、公司、城市、截止日期、薪资或链接；"
            "信息不足时 match_score 使用 null；"
            "如果没有可靠招聘/JD/投递来源，请返回空 jobs 数组。"
        )

    def _build_prompt(self, state: SummaryState, task: TodoItem, context: str) -> str:
        """Backward-compatible alias for older tests and callers."""

        return self.build_prompt(state, task, context)

    def _parse_response(self, response: str) -> list[JobItem]:
        text = response.strip()
        if self._config.strip_thinking_tokens:
            text = strip_thinking_tokens(text)
        text = strip_tool_calls(text).strip()
        payload = self._extract_json(text)
        if payload is None:
            return []

        raw_jobs: Any
        if isinstance(payload, dict):
            raw_jobs = payload.get("jobs", [])
        else:
            raw_jobs = payload

        if not isinstance(raw_jobs, list):
            return []

        jobs: list[JobItem] = []
        for index, raw in enumerate(raw_jobs, start=1):
            if not isinstance(raw, dict):
                continue
            job = self._normalize_job(raw, index)
            if self._looks_like_job(job) and self._is_reliable_job(job):
                jobs.append(job)

        return jobs

    def _extract_json(self, text: str) -> Any | None:
        if not text:
            return None

        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        candidates = [fenced.group(1)] if fenced else []
        candidates.append(text)

        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

            start_obj = candidate.find("{")
            end_obj = candidate.rfind("}")
            if start_obj != -1 and end_obj > start_obj:
                try:
                    return json.loads(candidate[start_obj : end_obj + 1])
                except json.JSONDecodeError:
                    pass

            start_list = candidate.find("[")
            end_list = candidate.rfind("]")
            if start_list != -1 and end_list > start_list:
                try:
                    return json.loads(candidate[start_list : end_list + 1])
                except json.JSONDecodeError:
                    pass

        return None

    def _normalize_job(self, raw: dict[str, Any], index: int) -> JobItem:
        company = self._string(raw.get("company"))
        title = self._string(raw.get("title"))
        source_url = self._string(raw.get("source_url"))
        source_title = self._string(raw.get("source_title"))
        if source_title == UNKNOWN and title != UNKNOWN:
            source_title = title

        return JobItem(
            id=self._make_id(company, title, source_url, index),
            company=company,
            title=title,
            location=self._string(raw.get("location")),
            source_url=source_url,
            source_title=source_title,
            requirements=self._string_list(raw.get("requirements")),
            responsibilities=self._string_list(raw.get("responsibilities")),
            tech_stack=self._string_list(raw.get("tech_stack")),
            duration=self._string(raw.get("duration")),
            deadline=self._string(raw.get("deadline")),
            match_score=self._score(raw.get("match_score")),
            match_reason=self._string(
                raw.get("match_reason"),
                default="信息不足，需点开来源确认",
            ),
            resume_advice=self._string_list(raw.get("resume_advice")),
            risks=self._string_list(raw.get("risks")),
        )

    def _fallback_from_sources(self, search_result: dict[str, Any] | None) -> list[JobItem]:
        if not search_result:
            return []

        results = search_result.get("results")
        if not isinstance(results, list):
            return []

        jobs: list[JobItem] = []
        for index, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue
            if not is_reliable_job_source(item):
                continue

            title = self._string(item.get("title"))
            url = self._string(item.get("url"))
            source_title = title if title != UNKNOWN else url
            jobs.append(
                JobItem(
                    id=self._make_id(UNKNOWN, title, url, index),
                    company=UNKNOWN,
                    title=title,
                    location=UNKNOWN,
                    source_url=url,
                    source_title=source_title,
                    match_score=None,
                    match_reason="信息不足，需点开来源确认",
                    resume_advice=["点开来源核对岗位 JD 后，再补充简历关键词。"],
                    risks=["岗位信息不足，需点开来源确认"],
                )
            )

        return jobs

    def _dedupe_and_sort(self, jobs: list[JobItem]) -> list[JobItem]:
        seen: set[str] = set()
        unique: list[JobItem] = []

        for job in jobs:
            key = self._dedupe_key(job)
            if key in seen:
                continue
            seen.add(key)
            unique.append(job)

        return sorted(
            unique,
            key=lambda item: (
                item.match_score is not None,
                item.match_score or -1,
                self._completeness(item),
            ),
            reverse=True,
        )

    def _dedupe_key(self, job: JobItem) -> str:
        url = job.source_url.strip().lower()
        if url and url != UNKNOWN:
            return f"url:{url}"
        return f"text:{job.company.strip().lower()}|{job.title.strip().lower()}"

    def _completeness(self, job: JobItem) -> int:
        score = 0
        for value in (
            job.company,
            job.title,
            job.location,
            job.source_url,
            job.source_title,
            job.duration,
            job.deadline,
        ):
            if value and value != UNKNOWN:
                score += 1
        score += min(len(job.requirements), 3)
        score += min(len(job.responsibilities), 2)
        score += min(len(job.tech_stack), 3)
        return score

    def _looks_like_job(self, job: JobItem) -> bool:
        text = " ".join([job.title, job.source_title, job.source_url]).lower()
        if not text or text == UNKNOWN.lower():
            return False
        negative_terms = ("面经", "面试题", "教程", "学习资源", "开源项目")
        return not any(term.lower() in text for term in negative_terms)

    def _is_reliable_job(self, job: JobItem) -> bool:
        return is_reliable_job_source(
            {
                "title": job.title,
                "url": job.source_url,
                "content": " ".join(
                    [
                        job.source_title,
                        job.match_reason,
                        " ".join(job.requirements),
                        " ".join(job.responsibilities),
                        " ".join(job.tech_stack),
                    ]
                ),
            }
        )

    def _make_id(self, company: str, title: str, source_url: str, index: int) -> str:
        material = f"{company}|{title}|{source_url}|{index}"
        digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:12]
        return f"job_{digest}"

    def _string(self, value: Any, *, default: str = UNKNOWN) -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = value
        else:
            return []

        items: list[str] = []
        for item in candidates:
            text = str(item).strip()
            if text and text != UNKNOWN and text not in items:
                items.append(text)
        return items

    def _score(self, value: Any) -> int | None:
        if value in (None, "", UNKNOWN):
            return None
        try:
            score = int(float(str(value)))
        except (TypeError, ValueError):
            return None
        return max(0, min(100, score))
