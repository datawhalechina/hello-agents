"""Observable design → four roles → deterministic compiler → bounded repair."""

from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser
from typing import Any, Callable

from .agents import (
    AgentConfigurationError, AgentContractError, AgentInvocationError, HelloAgentsRoles, RoleRunner,
    TrackedRoles, iter_nodes, make_prompt, validate_analysis, validate_plan,
    validate_review,
)
from .compiler import compile_project
from .design import normalize_design


class PipelineError(RuntimeError):
    """A failed run keeps its trace; it is never replaced with a demo success."""

    def __init__(self, stage: str, message: str, events: list[dict], metrics: dict, error_code: str = "pipeline_error"):
        super().__init__(message)
        self.stage = stage
        self.events = events
        self.metrics = metrics
        self.error_code = error_code


class _NodeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.node_ids: list[str] = []
        self.node_tags: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == "data-node-id" and value is not None:
                self.node_ids.append(value)
                self.node_tags[value] = tag


def review_project(design: dict, files: dict[str, str], plan: dict) -> dict:
    """Static structure/semantics checks, explicitly not a visual fidelity score."""
    nodes = list(iter_nodes(design["root"]))
    ids = {node["id"] for node in nodes}
    parser = _NodeParser()
    parser.feed(files.get("preview.html", ""))
    rendered = set(parser.node_ids)
    missing = sorted(ids - rendered)
    unexpected = sorted(rendered - ids)
    duplicate_ids = sorted({node_id for node_id in rendered if parser.node_ids.count(node_id) > 1})
    required = {"src/App.tsx", "src/styles.css", "preview.html", "manifest.json"}
    absent = sorted(path for path in required if not isinstance(files.get(path), str) or not files[path].strip())
    issues: list[dict] = []
    checks = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    check("required_files", not absent, "必备文件齐全" if not absent else "缺少文件：" + ", ".join(absent))
    check("node_coverage", not missing and not unexpected and not duplicate_ids,
          f"设计节点 {len(ids)}；预览匹配 {len(ids & rendered)}；缺失 {len(missing)}；额外 {len(unexpected)}；重复 {len(duplicate_ids)}")
    try:
        manifest = json.loads(files.get("manifest.json", ""))
        manifest_valid = isinstance(manifest, dict)
    except (ValueError, TypeError):
        manifest_valid = False
    check("manifest_json", manifest_valid, "manifest 是有效 JSON 对象" if manifest_valid else "manifest 不是有效 JSON 对象")
    for node_id in missing:
        issues.append({"node_id": node_id, "severity": "error", "message": "预览缺失导入节点", "source": "static"})
    for node_id in duplicate_ids:
        issues.append({"node_id": node_id, "severity": "error", "message": "预览重复输出节点", "source": "static"})

    # Inspect emitted tags: the compiler may safely turn a button's children into
    # spans. A check against the proposed plan would misreport the actual DOM.
    tags = parser.node_tags
    semantic_issues = []
    for tag in ("main", "h1"):
        matching = [node_id for node_id, assigned in tags.items() if assigned == tag]
        if len(matching) > 1:
            semantic_issues.append({"node_id": matching[1], "severity": "error", "message": f"单页存在多个 {tag} 标签", "source": "static"})
    for node in nodes:
        if tags.get(node["id"]) == "button":
            descendants = list(iter_nodes(node))
            text = " ".join(str(item.get("text", "")) for item in descendants).strip()
            if not text:
                semantic_issues.append({"node_id": node["id"], "severity": "error", "message": "按钮缺少可访问文本名称", "source": "static"})
            if any(tags.get(child["id"]) == "button" for child in descendants[1:]):
                semantic_issues.append({"node_id": node["id"], "severity": "error", "message": "按钮不能嵌套按钮", "source": "static"})
    issues.extend(semantic_issues)
    check("basic_accessibility", not semantic_issues,
          "通过基础语义检查；不代表完整 WCAG 合规" if not semantic_issues else "发现按钮或标题语义问题")
    passed = all(item["passed"] for item in checks)
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "checks": checks,
        "issues": issues,
        "node_coverage_percent": round(100 * len(ids & rendered) / len(ids), 2) if ids else 0,
        "node_count": len(ids),
        "rendered_node_count": len(ids & rendered),
        "scope": "仅静态结构与基础语义校验；未执行生成代码，未进行截图比较，不是像素还原率。",
    }


def _demo_analysis(design: dict) -> dict:
    nodes = list(iter_nodes(design["root"]))
    text_count = sum(node.get("type") == "TEXT" for node in nodes)
    return {
        "summary": f"离线规则分析：{design.get('name', '设计')}，共 {len(nodes)} 个可编译节点。",
        "observations": [
            f"保留 {text_count} 个文本节点和 {len(nodes) - text_count} 个容器或图形节点。",
            "编译器根据设计模型生成 React、CSS 与独立 HTML 预览；组件计划只选择语义标签。",
        ],
        "warnings": ["demo 使用确定性规则，没有调用任何大模型。", *design.get("warnings", [])[:10]],
    }


def _demo_plan(design: dict) -> dict:
    nodes = list(iter_nodes(design["root"]))
    components = []
    heading_assigned = False
    button_descendants: set[str] = set()
    for index, node in enumerate(nodes):
        if len(components) >= 40:
            break
        # Preorder traversal sees a button before its children. Let the compiler
        # render its entire subtree as safe inline content; no heading or landmark
        # heuristic should override that inherited content model.
        if node["id"] in button_descendants:
            continue
        node_type = node.get("type")
        name = str(node.get("name", "")).lower()
        tag = None
        if index == 0 and node_type != "TEXT":
            tag = "main"
        elif node_type == "TEXT":
            size = node.get("style", {}).get("fontSize", 0)
            try:
                is_title = float(str(size).removesuffix("px")) >= 28
            except ValueError:
                is_title = False
            if not heading_assigned and (is_title or re.search(r"(^|[ _-])(title|headline)([ _-]|$)|标题", name)):
                tag, heading_assigned = "h1", True
        elif "button" in name or "按钮" in name or name == "cta":
            # Button placeholders remain disabled; no invented business actions.
            descendants = list(iter_nodes(node))
            if any(item.get("text", "").strip() for item in descendants):
                tag = "button"
                button_descendants.update(item["id"] for item in descendants[1:])
        elif "header" in name or "导航栏" in name:
            tag = "header"
        elif "footer" in name or "页脚" in name:
            tag = "footer"
        elif name in ("nav", "navigation", "导航"):
            tag = "nav"
        if tag:
            components.append({"node_id": node["id"], "name": f"Node{index + 1}", "tag": tag})
    return {
        "components": components,
        "notes": ["离线演示只做有限的名称与字号规则推断；未识别业务逻辑。", "未列入计划的节点仍由编译器完整保留。"],
    }


def run_pipeline(
    payload: dict, *, node_id: str | None = None, mode: str = "demo", brief: str = "",
    on_event: Callable[[dict], None] | None = None,
    role_runner: RoleRunner | None = None,
) -> dict:
    """Run synchronously; ``role_runner`` is an internal offline test seam.

    Live mode requires real credentials unless a caller explicitly injects a test
    runner. The web API never accepts a runner from request data. No mode fallback
    is performed on configuration, network, schema, compiler or review failures.
    """
    if mode not in ("demo", "live"):
        raise ValueError("mode 只能是 demo 或 live")
    if not isinstance(brief, str) or len(brief) > 4_000:
        raise ValueError("brief 必须是最多 4000 字符的字符串")
    started = time.perf_counter()
    events: list[dict] = []
    tracked: TrackedRoles | None = None
    design: dict = {}
    files: dict = {}
    review: dict = {}

    def metrics() -> dict:
        calls = tracked.calls if tracked else []
        return {
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "llm_calls": len(calls),
            "llm_latency_ms": round(sum(call.get("duration_ms", 0) for call in calls), 2),
            "input_chars": sum(call.get("input_chars", 0) for call in calls),
            "output_chars": sum(call.get("output_chars", 0) for call in calls),
            "input_chars_note": "输入字符数统计摘要 JSON，不含角色系统提示词。",
            "context_omitted_nodes": max((call.get("omitted_nodes", 0) for call in calls), default=0),
            "truncated_context_calls": sum(bool(call.get("context_truncated")) or bool(call.get("omitted_nodes")) for call in calls),
            "token_usage": None if calls else {"input": 0, "output": 0},
            "estimated_cost_usd": None if calls else 0,
            "cost_note": "HelloAgents 0.2.2 不暴露 usage；未估算 token 或费用，请以供应商账单为准。" if calls else "离线运行，无 LLM 请求与 LLM 费用。",
            "files_count": len(files),
            "node_count": design.get("stats", {}).get("node_count", 0),
            "node_coverage_percent": review.get("node_coverage_percent", 0),
            "coverage_note": "节点覆盖率仅表示导入节点出现在预览 DOM 中，不是视觉还原率。",
            "calls": [dict(call) for call in calls],
            "runner": "injected_test_runner" if role_runner is not None and mode == "live" else ("hello_agents.SimpleAgent" if mode == "live" else "deterministic_demo"),
        }

    def emit(stage: str, status: str, message: str, duration_ms: float | None = None, error_code: str | None = None) -> None:
        event = {"stage": stage, "status": status, "message": message}
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if error_code is not None:
            event["error_code"] = error_code
        events.append(event)
        if on_event:
            on_event(dict(event))

    def execute(stage: str, message: str, action: Callable[[], Any]) -> Any:
        step_started = time.perf_counter()
        emit(stage, "running", message)
        try:
            value = action()
        except Exception as exc:
            # Provider errors can contain URLs/request details: do not expose them.
            if isinstance(exc, (AgentConfigurationError, AgentContractError, AgentInvocationError, ValueError)):
                detail = str(exc)[:600]
            else:
                detail = f"{type(exc).__name__}：执行失败，请检查服务配置与连接；详细原因见服务端日志。"
            if isinstance(exc, AgentInvocationError):
                error_code = exc.error_code
            elif isinstance(exc, AgentConfigurationError):
                error_code = "configuration"
            elif isinstance(exc, AgentContractError):
                error_code = "model_invalid_output"
            elif stage == "import":
                error_code = "invalid_input"
            elif stage in ("generate", "repair"):
                error_code = "compilation_failed"
            else:
                error_code = "pipeline_error"
            elapsed = round((time.perf_counter() - step_started) * 1000, 2)
            emit(stage, "failed", detail, elapsed, error_code)
            raise PipelineError(stage, detail, list(events), metrics(), error_code) from exc
        emit(stage, "completed", message + " · 完成", round((time.perf_counter() - step_started) * 1000, 2))
        return value

    design = execute("import", "导入并规范化选中设计节点", lambda: normalize_design(payload, node_id=node_id))
    node_ids = {node["id"] for node in iter_nodes(design["root"])}
    node_types = {node["id"]: node.get("type", "") for node in iter_nodes(design["root"])}

    def analyze() -> dict:
        nonlocal tracked
        if mode == "demo":
            return _demo_analysis(design)
        tracked = TrackedRoles(role_runner if role_runner is not None else HelloAgentsRoles())
        return validate_analysis(tracked.run("DesignAnalyst", make_prompt(design, brief)))

    analysis = execute("analyze", "离线规则分析" if mode == "demo" else "DesignAnalyst 分析设计", analyze)

    def plan_components() -> dict:
        if mode == "demo":
            return validate_plan(_demo_plan(design), node_ids, node_types)
        assert tracked is not None
        return validate_plan(tracked.run("ComponentPlanner", make_prompt(design, brief, analysis=analysis)), node_ids, node_types)

    candidate = execute("plan", "规划已有节点的语义组件", plan_components)

    def generate() -> tuple[dict, dict]:
        if mode == "demo":
            final_plan = candidate
        else:
            assert tracked is not None
            final_plan = validate_plan(tracked.run("CodeEngineer", make_prompt(design, brief, candidate=candidate)), node_ids, node_types)
        return final_plan, compile_project(design, final_plan)

    plan, files = execute("generate", "生成受约束的 React 与 CSS 项目", generate)

    def review_output() -> tuple[dict, dict | None]:
        static = review_project(design, files, plan)
        if mode == "demo":
            return static, None
        assert tracked is not None
        model_review = validate_review(tracked.run("Reviewer", make_prompt(
            design, brief, plan=plan,
            static_review={"status": static["status"], "checks": static["checks"], "issues": static["issues"][:10]},
        )), node_ids, node_types)
        return static, model_review

    review, model_review = execute("review", "校验节点覆盖与基础可访问性", review_output)
    repair_applied = False
    if model_review and model_review["plan"] is not None and model_review["plan"] != plan:
        replacement = model_review["plan"]

        def repair() -> tuple[dict, dict]:
            revised_files = compile_project(design, replacement)
            return revised_files, review_project(design, revised_files, replacement)

        files, review = execute("repair", "按 Reviewer 计划执行唯一一次修复并重新静态校验", repair)
        plan = replacement
        repair_applied = True
    review["repair_applied"] = repair_applied
    review["repair_count"] = int(repair_applied)
    review["model_review"] = model_review
    if tracked and any(call.get("omitted_nodes") or call.get("context_truncated") for call in tracked.calls):
        omitted = max(call.get("omitted_nodes", 0) for call in tracked.calls)
        analysis["warnings"].append(
            f"为限制模型上下文，部分角色只收到设计摘要（单次最多省略 {omitted} 个节点），或收到截短的上游结果；全部导入节点仍由确定性编译器保留。详情见 metrics.calls。"
        )
    if model_review and model_review["issues"]:
        # Preserve original reviewer feedback. A repaired plan has only been
        # statically rechecked; it must not be portrayed as a second LLM review.
        review["issues"].extend({**issue, "source": "model_before_repair" if repair_applied else "model"} for issue in model_review["issues"])
        if review["status"] == "passed":
            review["status"] = "passed_with_advisories"
        review["model_review_note"] = "模型建议供人工复核；修复后仅重新进行了静态检查，没有再次调用 Reviewer。" if repair_applied else "模型建议供人工复核，不是视觉检测结论。"
    return {
        "design": design, "analysis": analysis, "plan": plan, "files": files,
        "review": review, "events": events, "mode": mode, "metrics": metrics(),
    }
