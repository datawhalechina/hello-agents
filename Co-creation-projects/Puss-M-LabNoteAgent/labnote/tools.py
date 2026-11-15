# -*- coding: utf-8 -*-
"""LabNoteAgent 的四个自定义工具（继承 hello_agents 的 Tool 基类，新工具协议）

工具设计原则（对齐课程第四章工具系统）：
- 每个工具职责单一，结构化参数 + ToolResponse 标准返回
- 参数定义用 get_parameters() 显式声明，减少模型出错空间
"""
import json
import re
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse

from .storage import NoteStore


def _parse_params(text: str) -> dict:
    """从自由文本里抽取 key=value / key:value 对（支持中文冒号与单位后缀）。"""
    params = {}
    for m in re.finditer(r"([\w\u4e00-\u9fa5]+)\s*[=:：]\s*([0-9.]+[a-zA-Z%]*|[\w\u4e00-\u9fa5\-]+)", text):
        k, v = m.group(1), m.group(2)
        try:
            v = float(v) if re.fullmatch(r"[0-9.]+", v) else v
        except ValueError:
            pass
        params[k] = v
    return params


def _payload(parameters: Dict[str, Any], fallback_keys=("payload", "query", "input")):
    """工具入参兼容：直接结构化调用原样返回；字符串型参数尝试 JSON 解析。"""
    for k in fallback_keys:
        if k in parameters and parameters[k] not in (None, ""):
            v = parameters[k]
            if isinstance(v, dict):
                return v
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {"__raw__": str(v)}
    # 直接结构化传参（字段名与 get_parameters 声明一致）
    if any(k not in fallback_keys for k in parameters):
        return dict(parameters)
    return {}


class SaveNoteTool(Tool):
    """保存实验记录：LLM 负责从对话中提炼标题/参数/结果/标签，本工具负责落盘。"""

    def __init__(self, store: NoteStore):
        super().__init__(
            name="save_note",
            description="保存一条实验记录到笔记库。需要 title；params 放参数键值对、results 放结果指标、tags 放英文小写标签。",
        )
        self.store = store

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="title", type="string", description="实验简短标题"),
            ToolParameter(name="date", type="string", description="日期 YYYY-MM-DD，缺省为今天", required=False),
            ToolParameter(name="params", type="object", description="实验参数键值对，数值保留单位含义", required=False),
            ToolParameter(name="results", type="object", description="结果指标键值对", required=False),
            ToolParameter(name="tags", type="array", description="1-3个英文小写标签", required=False),
            ToolParameter(name="raw", type="string", description="用户原话（可选存档）", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        payload = _payload(parameters)
        if "__raw__" in payload and "title" not in payload:
            raw = payload["__raw__"]
            rec = self.store.add(title=raw[:40], params=_parse_params(raw), raw=raw)
            return ToolResponse.success(
                text=f"已保存（宽松模式，未能解析JSON）：{rec['id']} {rec['title']}",
                data={"id": rec["id"]},
            )
        if not payload.get("title"):
            return ToolResponse.error(code="MISSING_TITLE", message="缺少 title 字段，无法保存")
        rec = self.store.add(
            title=str(payload.get("title"))[:80],
            date=payload.get("date"),
            params=payload.get("params") or {},
            results=payload.get("results") or {},
            tags=payload.get("tags") or [],
            raw=payload.get("raw", ""),
        )
        return ToolResponse.success(
            text=f"已保存：[{rec['id']}] {rec['title']}（参数{len(rec['params'])}项，结果{len(rec['results'])}项，标签{rec['tags']}）",
            data={"id": rec["id"], "record": rec},
        )


class SearchNotesTool(Tool):
    """检索实验记录：关键词 / 标签 / 日期前缀。"""

    def __init__(self, store: NoteStore):
        super().__init__(
            name="search_notes",
            description="检索历史实验记录。可按关键词、标签、日期前缀过滤，最新记录优先。",
        )
        self.store = store

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="keyword", type="string", description="关键词（标题/参数/结果/原文模糊匹配）", required=False),
            ToolParameter(name="tag", type="string", description="标签过滤", required=False),
            ToolParameter(name="date", type="string", description="日期前缀 YYYY-MM 或 YYYY-MM-DD", required=False),
            ToolParameter(name="limit", type="integer", description="返回条数，默认5", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        payload = _payload(parameters)
        hits = self.store.search(
            keyword=payload.get("keyword"), tag=payload.get("tag"),
            date=payload.get("date"), limit=int(payload.get("limit", 5) or 5),
        )
        if not hits:
            return ToolResponse.success(text="没有找到匹配的实验记录。", data={"count": 0})
        lines = [
            f"[{h['id']}] {h['date']} {h['title']} | 参数:{h['params']} | 结果:{h['results']} | 标签:{h['tags']}"
            for h in hits
        ]
        return ToolResponse.success(
            text="找到 {} 条：\n{}".format(len(hits), "\n".join(lines)),
            data={"count": len(hits), "ids": [h["id"] for h in hits]},
        )


class CompareExperimentsTool(Tool):
    """对比两次实验的参数与结果差异。"""

    def __init__(self, store: NoteStore):
        super().__init__(
            name="compare_experiments",
            description="对比两次实验的参数/结果差异。a、b 可传记录 ID 或关键词（先用 search_notes 确认最准确）。",
        )
        self.store = store

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="a", type="string", description="第一条记录的 ID 或关键词"),
            ToolParameter(name="b", type="string", description="第二条记录的 ID 或关键词"),
        ]

    def _resolve(self, key: str) -> dict:
        rec = self.store.get(key)
        if rec:
            return rec
        hits = self.store.search(keyword=key, limit=1)
        return hits[0] if hits else {}

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        payload = _payload(parameters)
        a_key, b_key = str(payload.get("a", "")), str(payload.get("b", ""))
        a, b = self._resolve(a_key), self._resolve(b_key)
        if not a or not b:
            return ToolResponse.error(
                code="NOT_FOUND",
                message=f"找不到记录：a={bool(a)}, b={bool(b)}，请先用 search_notes 确认。",
            )
        diff = self.store.diff(a, b)
        out = [f"对比 [{a['id']}] {a['title']}  vs  [{b['id']}] {b['title']}"]
        for k, v in diff["params_diff"].items():
            out.append(f"  参数 {k}: {v['a']} -> {v['b']}")
        for k, v in diff["results_diff"].items():
            out.append(f"  结果 {k}: {v['a']} -> {v['b']}")
        if len(out) == 1:
            out.append("  两次实验参数与结果完全一致。")
        return ToolResponse.success(text="\n".join(out), data={"diff": diff})


class StatsTool(Tool):
    """笔记库统计：总数、最近实验日期、高频标签。"""

    def __init__(self, store: NoteStore):
        super().__init__(
            name="note_stats",
            description="查看实验笔记库统计（总条数、最近实验日期、高频标签）。",
        )
        self.store = store

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        s = self.store.stats()
        return ToolResponse.success(
            text=f"共 {s['total']} 条记录；最近日期：{s['dates'][:5]}；高频标签：{s['top_tags']}",
            data=s,
        )
