"""Notebook-oriented presentation helpers for analysis results."""

from __future__ import annotations

import html
from typing import Iterable

from .agent_runner import AgentStepTrace, AnalysisRunResult


def _tool_label(tool_name: str | None) -> str:
    if tool_name == "PythonInterpreterTool":
        return "本地 Python 分析"
    if tool_name == "TavilySearchTool":
        return "联网背景检索"
    if tool_name:
        return tool_name
    return "报告收敛"


def _status_label(status: str) -> str:
    mapping = {
        "success": "成功",
        "partial": "部分完成",
        "error": "失败",
        "unknown": "未知",
    }
    return mapping.get(status, status)


def _escape(value: object) -> str:
    return html.escape(str(value))


def _trace_short_observation(trace: AgentStepTrace) -> str:
    if trace.observation_preview:
        return trace.observation_preview
    if trace.observation:
        return " ".join(trace.observation.split())[:220]
    return ""


def _iter_failed_traces(step_traces: Iterable[AgentStepTrace]) -> list[AgentStepTrace]:
    failed = []
    for trace in step_traces:
        observation = trace.observation or ""
        if trace.tool_status == "error" or "Traceback" in observation:
            failed.append(trace)
    return failed


def render_trace_table(result: AnalysisRunResult):
    """Render the agent reasoning trace as notebook-friendly HTML."""

    from IPython.display import HTML

    rows = []
    for trace in result.step_traces:
        if trace.action == "call_tool":
            stage = f"{_tool_label(trace.tool_name)} ({trace.tool_name})"
        else:
            stage = "最终报告"
        rows.append(
            """
            <tr>
              <td style="border:1px solid #d1d5db; padding:8px; vertical-align:top;">{step}</td>
              <td style="border:1px solid #d1d5db; padding:8px; vertical-align:top;">{stage}</td>
              <td style="border:1px solid #d1d5db; padding:8px; vertical-align:top;">{decision}</td>
              <td style="border:1px solid #d1d5db; padding:8px; vertical-align:top;">{status}</td>
              <td style="border:1px solid #d1d5db; padding:8px; vertical-align:top;">{observation}</td>
              <td style="border:1px solid #d1d5db; padding:8px; vertical-align:top;">{notes}</td>
            </tr>
            """.format(
                step=_escape(trace.step_index),
                stage=_escape(stage),
                decision=_escape(trace.decision or trace.action),
                status=_escape(_status_label(trace.tool_status)),
                observation=_escape(_trace_short_observation(trace) or "无"),
                notes=_escape(trace.summary or trace.parse_error or "无"),
            )
        )

    html_content = """
    <h2>Agent 推理轨迹表</h2>
    <table style="width:100%; border-collapse:collapse; font-size:14px;">
      <thead>
        <tr style="background:#f3f4f6;">
          <th style="border:1px solid #d1d5db; padding:8px;">Step</th>
          <th style="border:1px solid #d1d5db; padding:8px;">Stage / Tool</th>
          <th style="border:1px solid #d1d5db; padding:8px;">Decision</th>
          <th style="border:1px solid #d1d5db; padding:8px;">Status</th>
          <th style="border:1px solid #d1d5db; padding:8px;">Short Observation</th>
          <th style="border:1px solid #d1d5db; padding:8px;">Notes</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
    """.format(rows="".join(rows))
    return HTML(html_content)


def render_full_report(result: AnalysisRunResult):
    """Render the full Markdown report without relying on plain print()."""

    from IPython.display import Markdown

    return Markdown("## 完整报告正文\n\n" + result.report_markdown)


def render_diagnostics(result: AnalysisRunResult):
    """Render expandable diagnostics with full observations and tracebacks."""

    from IPython.display import HTML

    failed_traces = _iter_failed_traces(result.step_traces)
    if not failed_traces:
        return HTML("<h2>错误与诊断详情</h2><p>本次运行无工具级异常。</p>")

    details_blocks = []
    for trace in failed_traces:
        title = f"Step {trace.step_index} Traceback"
        body = _escape(trace.observation or trace.parse_error or "No diagnostic text available.")
        details_blocks.append(
            f"""
            <details style="margin-bottom:12px;">
              <summary style="cursor:pointer; font-weight:600;">{_escape(title)}</summary>
              <pre style="white-space:pre-wrap; background:#111827; color:#f9fafb; padding:12px; border-radius:8px; margin-top:8px;">{body}</pre>
            </details>
            """
        )

    return HTML("<h2>错误与诊断详情</h2>" + "".join(details_blocks))
