"""
阶段 3：从已落库 run 构建可观测性视图（timeline / 摘要），供 GET .../observability 使用。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_diet_observability(row: Dict[str, Any]) -> Dict[str, Any]:
    """`get_diet_run` 返回的 row。"""
    out = row.get("output") or {}
    steps: List[Dict[str, Any]] = row.get("steps_trace") or []
    timeline: List[Dict[str, Any]] = []

    for s in steps:
        ph = s.get("phase")
        if ph == "tool_prefetch":
            tools = s.get("tools") or []
            timeline.append(
                {
                    "phase": ph,
                    "tool_calls": len(tools),
                    "tools_ok": [bool(t.get("ok")) for t in tools],
                }
            )
        elif ph in ("nutritionist", "coach", "habit"):
            ats = s.get("attempts") or []
            timeline.append(
                {
                    "phase": ph,
                    "fallback_used": bool(s.get("fallback_used")),
                    "llm_attempts": len(ats),
                    "last_attempt_ok": any(a.get("ok") for a in ats) if ats else False,
                }
            )
        else:
            timeline.append({"phase": ph or "unknown", "raw_keys": list(s.keys())})

    mp = out.get("meal_plan") or {}
    items = mp.get("items") or []

    return {
        "kind": "diet",
        "run_id": row.get("run_id"),
        "user_id": row.get("user_id"),
        "created_at": row.get("created_at"),
        "replayed_from_run_id": row.get("replayed_from_run_id")
        or out.get("replayed_from"),
        "schema_version": out.get("schema_version"),
        "pipeline_mode": out.get("pipeline_mode"),
        "degraded": out.get("degraded"),
        "errors": out.get("errors") or [],
        "rag_debug": out.get("rag_debug") or {},
        "trace_timeline": timeline,
        "input_snapshot": row.get("input"),
        "meal_plan_item_count": len(items),
        "estimated_total_protein_g": mp.get("total_est_protein_g"),
        "replay": {
            "supported": True,
            "method": "POST",
            "path_template": "/api/diet/runs/{run_id}/replay",
            "note": "使用同一份 input 重新跑流水线，生成新 run_id；Mock 工具确定性较高，LLM 输出仍可能不同。",
        },
    }


def build_report_observability(
    row: Dict[str, Any], *, include_raw_trace: bool = False
) -> Dict[str, Any]:
    """`get_report_run` 返回的 row。默认只返回摘要，避免 trace 过大。"""
    trace = row.get("agent_trace")
    summary: Dict[str, Any] = {}
    if isinstance(trace, dict):
        for agent_name, events in trace.items():
            if isinstance(events, list):
                summary[agent_name] = {
                    "event_count": len(events),
                    "last_titles": [e.get("title") for e in events[-5:] if isinstance(e, dict)],
                }
            else:
                summary[agent_name] = {"event_count": 0}

    out: Dict[str, Any] = {
        "kind": "health_report",
        "task_id": row.get("task_id"),
        "user_id": row.get("user_id"),
        "created_at": row.get("created_at"),
        "summary_text_preview": (row.get("summary_text") or "")[:240] or None,
        "has_agent_trace": bool(trace),
        "agent_trace_summary": summary,
    }
    if include_raw_trace:
        out["agent_trace"] = trace
    return out
