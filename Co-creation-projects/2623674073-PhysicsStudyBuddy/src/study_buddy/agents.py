"""HelloAgents roles for question writing, grading, planning and tutoring."""

from __future__ import annotations

import json
import os
import re
from contextlib import redirect_stdout
from io import StringIO
from typing import Any
from urllib.parse import urlparse

from .core import validate_plan, validate_quiz


def _read_json(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("模型返回空内容")
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("智能体未返回 JSON 对象")
    return value


def _normalize_quiz(questions: Any) -> None:
    """Accept the model's four-item list as well as the documented A-D mapping."""
    if not isinstance(questions, list):
        raise ValueError("questions 必须是列表")
    for question in questions:
        if not isinstance(question, dict) or question.get("type") != "choice":
            continue
        options = question.get("options")
        if isinstance(options, list):
            if len(options) != 4 or any(not isinstance(item, str) or not item.strip() for item in options):
                raise ValueError(f"题目 {question.get('id', '?')} 的选项不完整")
            labeled = [re.match(r"^\s*([A-Da-d])[.．、:：)）]\s*(.+)$", item) for item in options]
            if any(labeled):
                if not all(labeled) or {match.group(1).upper() for match in labeled} != set("ABCD"):
                    raise ValueError(f"题目 {question.get('id', '?')} 的选项标签不完整或重复")
                question["options"] = {match.group(1).upper(): match.group(2).strip() for match in labeled}
            else:
                question["options"] = dict(zip("ABCD", (item.strip() for item in options)))
        answer = question.get("correct_answer")
        if isinstance(answer, str):
            question["correct_answer"] = answer.strip().upper()
    validate_quiz(questions)


def _validate_grading(grading: Any) -> None:
    if not isinstance(grading, dict):
        raise ValueError("评分必须为对象")
    if type(grading.get("score")) is not int or grading["score"] not in (0, 1, 2):
        raise ValueError("简答分数必须是 0、1 或 2")
    if not isinstance(grading.get("feedback"), str) or not grading["feedback"].strip():
        raise ValueError("简答反馈不能为空")


class HelloAgentsBackend:
    """Separate agents share one model client but have distinct responsibilities."""

    def __init__(self) -> None:
        missing = [key for key in ("LLM_MODEL_ID", "LLM_BASE_URL", "LLM_API_KEY") if not os.getenv(key)]
        if missing:
            raise RuntimeError("请在 .env 中配置：" + "、".join(missing))
        from hello_agents import HelloAgentsLLM, SimpleAgent
        from hello_agents.tools import SearchTool

        llm = HelloAgentsLLM(provider="custom", temperature=0.2, max_tokens=3500)
        self.diagnostic = SimpleAgent(
            name="物理诊断智能体", llm=llm,
            system_prompt="你是严谨的高中物理出题与评分教师。题目必须物理正确、条件充分；不确定时明确失败，不编造定律。仅返回指定 JSON。",
            enable_tool_calling=False,
        )
        self.planner = SimpleAgent(
            name="学习规划智能体", llm=llm,
            system_prompt="你根据测验逐能力点证据制定短期高中物理学习计划。先补必要前置知识，再练习和复测。不把一次答题当作长期能力证明。仅返回指定 JSON。",
            enable_tool_calling=False,
        )
        self.tutor = SimpleAgent(
            name="学习辅导智能体", llm=llm,
            system_prompt="你是耐心的高中物理导师。结合当前学习任务，引导学生理解概念与解题思路。计算时写清单位；不确定时说明。不要捏造资源链接。",
            enable_tool_calling=False,
        )
        # SearchTool prints warnings for unrelated optional backends at construction.
        with redirect_stdout(StringIO()):
            self.search_tool = SearchTool(backend="duckduckgo")

    def _json_call(self, agent: Any, prompt: str, field: str, checker: Any = None) -> Any:
        host = (urlparse(os.getenv("LLM_BASE_URL", "")).hostname or "").lower()
        call_kwargs: dict[str, Any] = {}
        if host == "deepseek.com" or host.endswith(".deepseek.com"):
            call_kwargs = {"response_format": {"type": "json_object"}, "max_tokens": 8000,
                           "extra_body": {"reasoning_effort": "low"}}
        error = ""
        for _ in range(2):
            agent.clear_history()
            request = prompt if not error else prompt + "\n上次输出不合规，请修正：" + error
            try:
                raw = agent.run(request, **call_kwargs)
            except Exception as exc:
                raise RuntimeError("模型调用失败，请检查服务地址、模型、密钥和网络") from exc
            try:
                data = _read_json(raw)
                value = data[field]
                if checker:
                    checker(value)
                return value
            except (KeyError, ValueError, TypeError, IndexError) as exc:
                error = str(exc)
        raise ValueError(f"{agent.name} 两次未返回合规的 {field}：{error}")

    def make_quiz(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        prompt = (
            "为下面的高中物理主题生成一轮诊断题，只返回 JSON 对象 {\"questions\": [...]}。\n"
            "必须恰好 5 题，顺序为 3 道选择题和 2 道简答题。每题字段："
            "id (q1...q5), type (choice 或 short), skill (能力点), stem, explanation。"
            "选择题另含 options（必须为 JSON 对象，如 {\"A\":\"选项一\",\"B\":\"选项二\",\"C\":\"选项三\",\"D\":\"选项四\"}）"
            "和 correct_answer (A/B/C/D)；"
            "简答题另含 rubric (两个可独立核对的评分要点，每点 1 分)。"
            "题干不得透露答案；数值、单位、方向与物理条件必须自洽。"
            "覆盖至少两个能力点；若给出前置知识，至少有一题检查相关基础。"
            "复测不得重复先前题干，应针对薄弱点改变情境。\n"
            + json.dumps(context, ensure_ascii=False)
        )
        return self._json_call(self.diagnostic, prompt, "questions", _normalize_quiz)

    def grade_short(self, question: dict[str, Any], answer: str) -> dict[str, Any]:
        prompt = (
            "按两个评分要点分别给分，每个满足得 1 分。只返回 JSON 对象："
            "{\"grading\": {\"score\": 0到2的整数, \"feedback\": \"简要指出满足的要点、欠缺之处和改进建议\"}}。"
            "接受语义等价表述；不能因措辞不同扣分；不得把学生没有写出的推理算作正确。\n"
            + json.dumps({"question": question, "student_answer": answer}, ensure_ascii=False)
        )
        return self._json_call(self.diagnostic, prompt, "grading", _validate_grading)

    def make_plan(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        prompt = (
            "根据逐题诊断结果制定当前主题的分阶段学习计划，只返回 JSON 对象 {\"tasks\": [...]}。"
            "包含 3 到 6 项按学习顺序排列的任务：必要前置知识、薄弱能力讲解、针对性练习、复习与最后复测。"
            "已完成任务不应原样重复，除非复测仍显示不足。每项字段：id (本轮唯一短字符串), title, why "
            "(联系实际错题或得分), minutes (5到120的整数), done_when (可观察完成条件), "
            "resource_query (适合搜索教学资源的中文关键词或空字符串)。"
            "不输出未经证实的学习资源链接。\n" + json.dumps(context, ensure_ascii=False)
        )
        return self._json_call(self.planner, prompt, "tasks", validate_plan)

    def answer(self, context: dict[str, Any], question: str) -> str:
        try:
            return self.tutor.run(
                "当前学习资料：" + json.dumps(context, ensure_ascii=False)
                + "\n学生的问题：" + question + "\n请先给出针对性的提示，再解释关键概念；如果学生需要完整解答则给出步骤。"
            ).strip()
        except Exception as exc:
            raise RuntimeError("模型调用失败，请检查服务地址、模型、密钥和网络") from exc

    def search(self, query: str) -> list[dict[str, str]]:
        payload = self.search_tool.run({"input": query, "backend": "duckduckgo",
                                        "mode": "structured", "max_results": 5,
                                        "fetch_full_page": False})
        if not isinstance(payload, dict):
            return []
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in payload.get("results", []):
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            if urlparse(url).scheme not in ("http", "https") or not title or url in seen:
                continue
            results.append({"title": title, "url": url})
            seen.add(url)
        return results
