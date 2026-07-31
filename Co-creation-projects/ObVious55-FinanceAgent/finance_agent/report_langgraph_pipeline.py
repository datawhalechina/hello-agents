from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.types import Command, interrupt

from finance_agent.report_agents import (
    AcceptanceReviewAgent,
    AgentNode,
    BudgetVarianceAgent,
    ExpenseInsightAgent,
    FinalReportAgent,
)
from finance_agent.report_constants import DEFAULT_AGENT_RUN_DIR
from finance_agent.report_io import camel_to_snake
from finance_agent.report_llm import LLMClient, OpenAICompatibleLLMClient
from finance_agent.report_models import ReportPipelineState, StatePatch
from finance_agent.report_models import (
    HUMAN_FEEDBACK,
    HUMAN_REVIEW_STATUSES,
    PIPELINE_COMPLETED,
    PIPELINE_STOPPED,
    PIPELINE_WAITING_HUMAN,
)
from finance_agent.report_observability import (
    apply_state_patch,
    flush_observability,
    save_failure_debug_bundle,
    save_state_snapshot,
    serialize_runtime_state,
    trace_event,
    to_jsonable,
)
from finance_agent.report_state_pipeline import (
    MAX_ERROR_HISTORY_ITEMS,
    MAX_AGENT_SCHEMA_ATTEMPTS,
    build_agent_input,
    build_agent_run_record,
    build_failed_agent_run_record,
    build_schema_retry_input,
    build_shared_state,
    call_agent_llm,
    build_rerun_context,
    build_human_review_package,
    human_review_gate,
    record_agent_error,
    rerun_router,
    run_final_report_agent,
    route_after_human_review,
    restore_runtime_state,
    validate_json_agent_output,
    validate_report,
    write_outputs,
)
from finance_agent.report_state_store import TRUE_VALUES, MySQLStateStore
from finance_agent.report_state_store import load_project_env as load_state_store_env


def append_lists(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    return (left or []) + (right or [])


class LangGraphReportState(TypedDict, total=False):
    runtime_state: dict[str, Any] | ReportPipelineState
    output_payload: dict[str, Any]
    report: str


class AnalysisGraphState(TypedDict, total=False):
    runtime_state: ReportPipelineState
    analysis_patches: Annotated[list[StatePatch], append_lists]
    parallel_trace_events: Annotated[list[dict[str, Any]], append_lists]
    error_history: Annotated[list[dict[str, Any]], append_lists]


class JsonAgentGraphState(TypedDict, total=False):
    runtime_state: ReportPipelineState
    input_json: dict[str, Any]
    attempt_input: dict[str, Any]
    raw_output: str
    parsed_output: dict[str, Any]
    patch: StatePatch
    attempt: int
    status: str
    last_error: str


def route_json_agent_after_validation(graph_state: JsonAgentGraphState) -> str:
    status = graph_state.get("status")
    if status == "valid":
        return "done"
    if status == "retry":
        return "retry"
    return "fail"


def route_json_agent_after_build_input(graph_state: JsonAgentGraphState) -> str:
    return "fail" if graph_state.get("status") == "failed" else "prepare"


def route_json_agent_after_prepare_attempt(graph_state: JsonAgentGraphState) -> str:
    return "fail" if graph_state.get("status") == "failed" else "call"


def route_json_agent_after_call_llm(graph_state: JsonAgentGraphState) -> str:
    return "fail" if graph_state.get("status") == "failed" else "validate"


def route_after_human_review_graph(graph_state: LangGraphReportState) -> str:
    return route_after_human_review(require_runtime_state(graph_state))


def route_after_rerun_router_graph(graph_state: LangGraphReportState) -> str:
    return rerun_router(require_runtime_state(graph_state))


def default_checkpointer(enabled: bool) -> tuple[Any | None, Any | None]:
    if not enabled:
        return None, None
    load_state_store_env()
    backend = os.getenv("REPORT_CHECKPOINT_BACKEND", "").strip().lower()
    if not backend:
        backend = "mysql" if os.getenv("REPORT_STATE_MYSQL_ENABLED", "").lower() in TRUE_VALUES else "memory"
    if backend == "none":
        return None, None
    if backend == "mysql":
        return build_mysql_checkpointer()
    if backend != "memory":
        raise RuntimeError(
            "REPORT_CHECKPOINT_BACKEND must be one of mysql, memory, or none."
        )
    try:
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError as exc:
        raise RuntimeError("Missing LangGraph MemorySaver checkpointer.") from exc
    return MemorySaver(), None


def build_mysql_checkpointer() -> tuple[Any, Any]:
    try:
        import pymysql
        from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: install langgraph-checkpoint-mysql[pymysql] "
            "or set REPORT_CHECKPOINT_BACKEND=memory."
        ) from exc

    store = MySQLStateStore.from_env()
    if store is None:
        raise RuntimeError(
            "REPORT_CHECKPOINT_BACKEND=mysql requires REPORT_STATE_MYSQL_ENABLED=1 "
            "and MySQL connection settings."
        )
    conn = pymysql.connect(
        host=store.host,
        port=store.port,
        user=store.user,
        password=store.password,
        database=store.database,
        charset="utf8mb4",
        init_command="SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci",
        autocommit=True,
    )
    with conn.cursor() as cur:
        cur.execute("SET collation_connection = 'utf8mb4_0900_ai_ci'")
    saver = PyMySQLSaver(conn)
    saver.setup()
    ensure_mysql_checkpoint_collation(conn)
    return saver, conn


def ensure_mysql_checkpoint_collation(conn: Any) -> None:
    target = os.getenv("REPORT_CHECKPOINT_MYSQL_COLLATION", "utf8mb4_0900_ai_ci")
    tables = [
        "checkpoints",
        "checkpoint_blobs",
        "checkpoint_writes",
        "checkpoint_migrations",
    ]
    with conn.cursor() as cur:
        cur.execute("SELECT DATABASE()")
        database = cur.fetchone()[0]
        for table in tables:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                  AND TABLE_COLLATION <> %s
                """,
                (database, table, target),
            )
            needs_convert = cur.fetchone()[0] > 0
            if needs_convert:
                cur.execute(
                    f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE {target}"
                )


def human_review_gate_with_interrupt(state: ReportPipelineState) -> None:
    trace_event(state, "node_started", "human_review_gate")
    state.human_review_package = build_human_review_package(state)
    state.pipeline_status = PIPELINE_WAITING_HUMAN
    state.human_review = None
    save_state_snapshot(
        state,
        "03_human_review_gate",
        status=PIPELINE_WAITING_HUMAN,
        current_node="human_review_gate",
        next_node=None,
    )
    human_review = interrupt(state.human_review_package)
    normalized_review = normalize_interrupt_human_review(human_review)
    state.human_review = normalized_review
    state.pipeline_status = normalized_review["status"]
    if normalized_review["status"] == HUMAN_FEEDBACK and normalized_review["rerun_required"]:
        state.rerun_context = build_rerun_context(state)
    else:
        state.rerun_context = None
    next_node = route_after_human_review(state)
    save_state_snapshot(
        state,
        "04_after_human_review",
        status=state.pipeline_status,
        current_node="human_review_gate",
        next_node=None if next_node == "stop_pipeline" else next_node,
    )
    trace_event(
        state,
        "node_completed",
        "human_review_gate",
        writes=["human_review_package", "pipeline_status", "human_review", "rerun_context"],
    )


def normalize_interrupt_human_review(human_review: Any) -> dict[str, Any]:
    if not isinstance(human_review, dict):
        raise ValueError("Human review resume payload must be a JSON object.")
    status = human_review.get("status")
    if status not in HUMAN_REVIEW_STATUSES:
        raise ValueError(
            "human_review.status must be one of "
            f"{', '.join(sorted(HUMAN_REVIEW_STATUSES))}."
        )
    normalized = {
        "status": status,
        "reviewer": human_review.get("reviewer", "human"),
        "review_notes": list(human_review.get("review_notes") or []),
        "overrides": human_review.get("overrides", {}),
        "rerun_required": bool(human_review.get("rerun_required", False)),
        "rerun_targets": list(human_review.get("rerun_targets") or []),
        "supplemental_inputs": human_review.get("supplemental_inputs", {}),
    }
    if status != HUMAN_FEEDBACK:
        normalized["rerun_required"] = False
        normalized["rerun_targets"] = []
    return normalized


def interrupt_payload(result: dict[str, Any]) -> dict[str, Any]:
    interrupts = result.get("__interrupt__", [])
    if not interrupts:
        return {}
    first = interrupts[0]
    return getattr(first, "value", first)


def ensure_human_review_resume_allowed(run_id: str) -> None:
    store = MySQLStateStore.from_env()
    if store is None:
        return
    latest = store.latest_snapshot_header_by_run_id(run_id)
    if latest is None:
        return
    status = latest.get("status")
    if status == PIPELINE_WAITING_HUMAN:
        return
    raise RuntimeError(
        "Human review has already been submitted or the run is no longer waiting. "
        f"run_id={run_id}, latest_status={status}, latest_node={latest.get('current_node')}"
    )


class ReportPipeline:
    """LangGraph-backed runtime for the finance report multi-agent workflow."""

    def __init__(
        self,
        budget_payload: dict[str, Any] | None = None,
        llm_client: LLMClient | None = None,
        agent_run_dir: Path = DEFAULT_AGENT_RUN_DIR,
        checkpointer: Any | None = None,
        review_mode: str = "interactive",
        use_langgraph_interrupt: bool | None = None,
    ) -> None:
        self.budget_payload = budget_payload
        self.llm_client = llm_client or OpenAICompatibleLLMClient()
        self.agent_run_dir = agent_run_dir
        self.review_mode = review_mode
        self.use_langgraph_interrupt = review_mode == "interactive" if use_langgraph_interrupt is None else use_langgraph_interrupt
        if checkpointer is None:
            self.checkpointer, self._checkpoint_connection = default_checkpointer(self.use_langgraph_interrupt)
        else:
            self.checkpointer = checkpointer
            self._checkpoint_connection = None
        self.agents: list[AgentNode] = [
            ExpenseInsightAgent(self.llm_client),
            BudgetVarianceAgent(self.llm_client),
            AcceptanceReviewAgent(self.llm_client),
            FinalReportAgent(self.llm_client),
        ]
        self._graph: Any | None = None
        self._analysis_graph: Any | None = None
        self._json_agent_graphs: dict[str, Any] = {}

    def close(self) -> None:
        if self._checkpoint_connection is not None:
            self._checkpoint_connection.close()
            self._checkpoint_connection = None

    def run(self, classification: dict[str, Any]) -> tuple[dict[str, Any], str]:
        records = classification.get("records", [])
        state = ReportPipelineState(
            classification=classification,
            records=records,
            budget_payload=self.budget_payload,
            agent_run_dir=self.agent_run_dir,
            review_mode=self.review_mode,
        )
        state.thread_id = state.run_id
        try:
            trace_event(
                state,
                "pipeline_started",
                "LangGraphReportPipeline",
                run_id=state.run_id,
                thread_id=state.thread_id,
                record_count=len(records),
            )
            save_state_snapshot(
                state,
                "00_initial_state",
                current_node="LangGraphReportPipeline",
                next_node="build_shared_state",
            )
            result = self._compiled_graph().invoke(
                {
                    "runtime_state": export_runtime_state(state),
                },
                config={"configurable": {"thread_id": state.thread_id}},
            )
            if "__interrupt__" in result:
                package = interrupt_payload(result)
                interrupted_state = require_runtime_state(result)
                trace_event(interrupted_state, "pipeline_interrupted", "LangGraphReportPipeline", run_id=interrupted_state.run_id)
                flush_observability(interrupted_state)
                return build_interrupt_payload(interrupted_state, package), ""
            final_state = require_runtime_state(result)
            trace_event(final_state, "pipeline_completed", "LangGraphReportPipeline")
            flush_observability(final_state)
            return result.get("output_payload") or build_terminal_payload(final_state), result.get("report", final_state.final_report)
        except Exception as exc:
            trace_event(state, "pipeline_failed", "LangGraphReportPipeline", error_type=type(exc).__name__, error=str(exc))
            try:
                save_state_snapshot(
                    state,
                    "99_failure",
                    status="FAILED",
                    current_node="LangGraphReportPipeline",
                    next_node=None,
                    error_message=str(exc),
                )
            except Exception as snapshot_exc:
                trace_event(
                    state,
                    "failure_snapshot_failed",
                    "LangGraphReportPipeline",
                    error_type=type(snapshot_exc).__name__,
                    error=str(snapshot_exc),
                )
            save_failure_debug_bundle(state, exc)
            flush_observability(state)
            raise

    def resume_from_state(self, state: ReportPipelineState) -> tuple[dict[str, Any], str]:
        try:
            result = self._run_after_human_review(state)
            flush_observability(state)
            return result
        except Exception as exc:
            trace_event(state, "pipeline_failed", "LangGraphReportPipeline", error_type=type(exc).__name__, error=str(exc))
            save_failure_debug_bundle(state, exc)
            flush_observability(state)
            raise

    def resume_with_human_review(self, run_id: str, human_review: dict[str, Any]) -> tuple[dict[str, Any], str]:
        try:
            ensure_human_review_resume_allowed(run_id)
            result = self._compiled_graph().invoke(
                Command(resume=human_review),
                config={"configurable": {"thread_id": run_id}},
            )
            if "__interrupt__" in result:
                state = require_runtime_state(result)
                package = interrupt_payload(result)
                trace_event(state, "pipeline_interrupted", "LangGraphReportPipeline", run_id=state.run_id)
                flush_observability(state)
                return build_interrupt_payload(state, package), ""
            final_state = require_runtime_state(result)
            trace_event(final_state, "pipeline_completed", "LangGraphReportPipeline")
            flush_observability(final_state)
            return result.get("output_payload") or build_terminal_payload(final_state), result.get("report", final_state.final_report)
        except Exception as exc:
            raise RuntimeError(f"LangGraph checkpoint resume failed for run_id={run_id}: {exc}") from exc

    def _run_after_human_review(self, state: ReportPipelineState) -> tuple[dict[str, Any], str]:
        route = route_after_human_review(state)
        while route == "rerun_router":
            self._rerun_router_node({"runtime_state": state})
            rerun_route = rerun_router(state)
            if rerun_route == "analysis_subgraph":
                self._analysis_subgraph_node({"runtime_state": state})
            elif rerun_route == "rerun_expense_agent":
                self._rerun_expense_agent_node({"runtime_state": state})
            elif rerun_route == "rerun_budget_agent":
                self._rerun_budget_agent_node({"runtime_state": state})
            elif rerun_route == "rerun_acceptance_agent":
                self._rerun_acceptance_agent_node({"runtime_state": state})
            else:
                state.pipeline_status = PIPELINE_STOPPED
                return build_terminal_payload(state), state.final_report
            human_review_gate(state)
            route = route_after_human_review(state)

        if route == "stop_pipeline":
            return build_terminal_payload(state), state.final_report

        self._final_report_agent_node({"runtime_state": state})
        self._validate_report_node({"runtime_state": state})
        result = self._write_outputs_node({"runtime_state": state})
        return result["output_payload"], result["report"]

    def _compiled_graph(self) -> Any:
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    def _build_graph(self) -> Any:
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: install langgraph with `python -m pip install -r requirements.txt`."
            ) from exc

        graph = StateGraph(LangGraphReportState)
        graph.add_node("build_shared_state", self._build_shared_state_node)
        graph.add_node("analysis_subgraph", self._analysis_subgraph_node)
        graph.add_node("human_review_gate", self._human_review_gate_node)
        graph.add_node("rerun_router", self._rerun_router_node)
        graph.add_node("rerun_expense_agent", self._rerun_expense_agent_node)
        graph.add_node("rerun_budget_agent", self._rerun_budget_agent_node)
        graph.add_node("rerun_acceptance_agent", self._rerun_acceptance_agent_node)
        graph.add_node("stop_pipeline", self._stop_pipeline_node)
        graph.add_node("final_report_agent", self._final_report_agent_node)
        graph.add_node("validate_report", self._validate_report_node)
        graph.add_node("write_outputs", self._write_outputs_node)

        graph.add_edge(START, "build_shared_state")
        graph.add_edge("build_shared_state", "analysis_subgraph")
        graph.add_edge("analysis_subgraph", "human_review_gate")
        graph.add_conditional_edges(
            "human_review_gate",
            route_after_human_review_graph,
            {
                "final_report_agent": "final_report_agent",
                "rerun_router": "rerun_router",
                "stop_pipeline": "stop_pipeline",
            },
        )
        graph.add_conditional_edges(
            "rerun_router",
            route_after_rerun_router_graph,
            {
                "analysis_subgraph": "analysis_subgraph",
                "rerun_expense_agent": "rerun_expense_agent",
                "rerun_budget_agent": "rerun_budget_agent",
                "rerun_acceptance_agent": "rerun_acceptance_agent",
                "stop_pipeline": "stop_pipeline",
            },
        )
        graph.add_edge("rerun_expense_agent", "human_review_gate")
        graph.add_edge("rerun_budget_agent", "human_review_gate")
        graph.add_edge("rerun_acceptance_agent", "human_review_gate")
        graph.add_edge("stop_pipeline", END)
        graph.add_edge("final_report_agent", "validate_report")
        graph.add_edge("validate_report", "write_outputs")
        graph.add_edge("write_outputs", END)

        if self.checkpointer is not None:
            return graph.compile(checkpointer=self.checkpointer)
        return graph.compile()

    def _build_shared_state_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        build_shared_state(state)
        save_state_snapshot(state, "01_shared_state")
        return {"runtime_state": export_runtime_state(state)}

    def _analysis_subgraph_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        trace_event(state, "node_started", "analysis_subgraph")
        result = self._compiled_analysis_graph().invoke(
            {
                "runtime_state": state,
                "analysis_patches": [],
                "parallel_trace_events": [],
                "error_history": [],
            },
            config={"configurable": {"thread_id": state.thread_id}},
        )
        final_state = result["runtime_state"]
        trace_event(final_state, "node_completed", "analysis_subgraph", writes=["expense_output", "budget_output", "acceptance_output"])
        return {"runtime_state": export_runtime_state(final_state)}

    def _human_review_gate_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        if self.use_langgraph_interrupt:
            human_review_gate_with_interrupt(state)
        else:
            human_review_gate(state)
        return {"runtime_state": export_runtime_state(state)}

    def _rerun_router_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        state.rerun_context = build_rerun_context(state)
        state.rerun_count += 1
        save_state_snapshot(
            state,
            "04_rerun_router",
            status="RERUN_REQUESTED",
            current_node="rerun_router",
            next_node=rerun_router(state),
        )
        return {"runtime_state": export_runtime_state(state)}

    def _rerun_expense_agent_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        return self._run_single_analysis_agent_node(graph_state, self.agents[0], index=1, output_key="expense_output")

    def _rerun_budget_agent_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        return self._run_single_analysis_agent_node(graph_state, self.agents[1], index=2, output_key="budget_output")

    def _rerun_acceptance_agent_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        return self._run_single_analysis_agent_node(graph_state, self.agents[2], index=3, output_key="acceptance_output")

    def _run_single_analysis_agent_node(
        self,
        graph_state: LangGraphReportState,
        agent: AgentNode,
        index: int,
        output_key: str,
    ) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        result = self._compiled_json_agent_graph(agent, index, output_key).invoke(
            {
                "runtime_state": clone_state_for_parallel_node(state),
                "attempt": 1,
                "status": "running",
            },
            config={"configurable": {"thread_id": state.thread_id}},
        )
        patch = result["patch"]
        apply_state_patch(state, patch)
        save_state_snapshot(state, f"04_after_rerun_{camel_to_snake(agent.name)}")
        return {"runtime_state": export_runtime_state(state)}

    def _stop_pipeline_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        if state.pipeline_status != PIPELINE_WAITING_HUMAN:
            state.pipeline_status = PIPELINE_STOPPED
            save_state_snapshot(
                state,
                "98_stopped",
                status=PIPELINE_STOPPED,
                current_node="stop_pipeline",
                next_node=None,
            )
        return {"runtime_state": export_runtime_state(state), "output_payload": build_terminal_payload(state), "report": state.final_report}

    def _compiled_analysis_graph(self) -> Any:
        if self._analysis_graph is None:
            self._analysis_graph = self._build_analysis_graph()
        return self._analysis_graph

    def _build_analysis_graph(self) -> Any:
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: install langgraph with `python -m pip install -r requirements.txt`."
            ) from exc

        graph = StateGraph(AnalysisGraphState)
        graph.add_node("expense_agent", self._expense_agent_subgraph_node)
        graph.add_node("budget_agent", self._budget_agent_subgraph_node)
        graph.add_node("acceptance_agent", self._acceptance_agent_subgraph_node)
        graph.add_node("merge_analysis_patches", self._merge_analysis_patches_node)

        graph.add_edge(START, "expense_agent")
        graph.add_edge(START, "budget_agent")
        graph.add_edge(START, "acceptance_agent")
        graph.add_edge(["expense_agent", "budget_agent", "acceptance_agent"], "merge_analysis_patches")
        graph.add_edge("merge_analysis_patches", END)
        return graph.compile()

    def _expense_agent_subgraph_node(self, graph_state: AnalysisGraphState) -> dict[str, Any]:
        return self._run_json_agent_subgraph_node(graph_state, self.agents[0], index=1, output_key="expense_output")

    def _budget_agent_subgraph_node(self, graph_state: AnalysisGraphState) -> dict[str, Any]:
        return self._run_json_agent_subgraph_node(graph_state, self.agents[1], index=2, output_key="budget_output")

    def _acceptance_agent_subgraph_node(self, graph_state: AnalysisGraphState) -> dict[str, Any]:
        return self._run_json_agent_subgraph_node(graph_state, self.agents[2], index=3, output_key="acceptance_output")

    def _run_json_agent_subgraph_node(
        self,
        graph_state: AnalysisGraphState,
        agent: AgentNode,
        index: int,
        output_key: str,
    ) -> dict[str, Any]:
        parent_state = require_runtime_state(graph_state)
        node_state = clone_state_for_parallel_node(parent_state)
        result = self._compiled_json_agent_graph(agent, index, output_key).invoke(
            {
                "runtime_state": node_state,
                "attempt": 1,
                "status": "running",
            },
            config={"configurable": {"thread_id": node_state.thread_id}},
        )
        patch = result["patch"]
        return {
            "analysis_patches": [patch],
            "parallel_trace_events": node_state.trace_events,
            "error_history": node_state.error_history,
        }

    def _compiled_json_agent_graph(self, agent: AgentNode, index: int, output_key: str) -> Any:
        key = agent.name
        if key not in self._json_agent_graphs:
            self._json_agent_graphs[key] = self._build_json_agent_graph(agent, index, output_key)
        return self._json_agent_graphs[key]

    def _build_json_agent_graph(self, agent: AgentNode, index: int, output_key: str) -> Any:
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: install langgraph with `python -m pip install -r requirements.txt`."
            ) from exc

        graph = StateGraph(JsonAgentGraphState)
        graph.add_node("build_input", self._json_agent_build_input_node(agent))
        graph.add_node("prepare_attempt", self._json_agent_prepare_attempt_node(agent))
        graph.add_node("call_llm", self._json_agent_call_llm_node(agent))
        graph.add_node("validate_output", self._json_agent_validate_output_node(agent))
        graph.add_node("build_patch", self._json_agent_build_patch_node(agent, index, output_key))
        graph.add_node("fail_agent", self._json_agent_fail_node(agent, index))

        graph.add_edge(START, "build_input")
        graph.add_conditional_edges(
            "build_input",
            route_json_agent_after_build_input,
            {
                "prepare": "prepare_attempt",
                "fail": "fail_agent",
            },
        )
        graph.add_conditional_edges(
            "prepare_attempt",
            route_json_agent_after_prepare_attempt,
            {
                "call": "call_llm",
                "fail": "fail_agent",
            },
        )
        graph.add_conditional_edges(
            "call_llm",
            route_json_agent_after_call_llm,
            {
                "validate": "validate_output",
                "fail": "fail_agent",
            },
        )
        graph.add_conditional_edges(
            "validate_output",
            route_json_agent_after_validation,
            {
                "retry": "prepare_attempt",
                "done": "build_patch",
                "fail": "fail_agent",
            },
        )
        graph.add_edge("build_patch", END)
        graph.add_edge("fail_agent", END)
        return graph.compile()

    def _json_agent_build_input_node(self, agent: AgentNode) -> Any:
        def node(graph_state: JsonAgentGraphState) -> dict[str, Any]:
            state = require_runtime_state(graph_state)
            trace_event(state, "node_started", agent.name)
            try:
                input_json = build_agent_input(agent, state, previous_outputs={})
                return {"input_json": input_json, "status": "running"}
            except Exception as exc:
                record_agent_error(state, agent.name, graph_state.get("attempt", 1), exc)
                trace_event(state, "node_failed", agent.name, error_type=type(exc).__name__, error=str(exc))
                return {"status": "failed", "last_error": str(exc)}

        return node

    def _json_agent_prepare_attempt_node(self, agent: AgentNode) -> Any:
        def node(graph_state: JsonAgentGraphState) -> dict[str, Any]:
            state = require_runtime_state(graph_state)
            input_json = graph_state.get("input_json", {})
            attempt = graph_state.get("attempt", 1)
            try:
                if attempt <= 1:
                    return {"attempt_input": input_json, "status": "running"}
                trace_event(
                    state,
                    "llm_output_schema_retry",
                    agent.name,
                    attempt=attempt,
                    error=graph_state.get("last_error", ""),
                )
                return {
                    "attempt_input": build_schema_retry_input(input_json, agent.name, state.error_history),
                    "status": "running",
                }
            except Exception as exc:
                record_agent_error(state, agent.name, attempt, exc)
                trace_event(state, "node_failed", agent.name, error_type=type(exc).__name__, error=str(exc))
                return {"status": "failed", "last_error": str(exc)}

        return node

    def _json_agent_call_llm_node(self, agent: AgentNode) -> Any:
        def node(graph_state: JsonAgentGraphState) -> dict[str, Any]:
            state = require_runtime_state(graph_state)
            attempt = graph_state.get("attempt", 1)
            try:
                raw_output = call_agent_llm(
                    agent,
                    state,
                    graph_state.get("input_json", {}),
                    graph_state.get("attempt_input", {}),
                    attempt,
                )
                return {"raw_output": raw_output, "status": "running"}
            except Exception as exc:
                record_agent_error(state, agent.name, attempt, exc)
                trace_event(state, "node_failed", agent.name, error_type=type(exc).__name__, error=str(exc))
                return {"status": "failed", "last_error": str(exc)}

        return node

    def _json_agent_validate_output_node(self, agent: AgentNode) -> Any:
        def node(graph_state: JsonAgentGraphState) -> dict[str, Any]:
            state = require_runtime_state(graph_state)
            attempt = graph_state.get("attempt", 1)
            try:
                parsed_output = validate_json_agent_output(agent, graph_state.get("raw_output", ""), graph_state.get("input_json", {}))
                return {"parsed_output": parsed_output, "status": "valid"}
            except ValueError as exc:
                record_agent_error(state, agent.name, attempt, exc)
                next_status = "retry" if attempt < MAX_AGENT_SCHEMA_ATTEMPTS else "failed"
                return {
                    "attempt": attempt + 1,
                    "status": next_status,
                    "last_error": str(exc),
                }

        return node

    def _json_agent_build_patch_node(self, agent: AgentNode, index: int, output_key: str) -> Any:
        def node(graph_state: JsonAgentGraphState) -> dict[str, Any]:
            state = require_runtime_state(graph_state)
            record = build_agent_run_record(
                index,
                agent,
                graph_state["input_json"],
                graph_state.get("raw_output", ""),
                graph_state["parsed_output"],
            )
            patch = StatePatch(node=agent.name, writes={output_key: graph_state["parsed_output"]}, run_record=record)
            trace_event(state, "node_completed", agent.name, writes=[output_key])
            return {"patch": patch}

        return node

    def _json_agent_fail_node(self, agent: AgentNode, index: int) -> Any:
        def node(graph_state: JsonAgentGraphState) -> dict[str, Any]:
            state = require_runtime_state(graph_state)
            error = ValueError(graph_state.get("last_error") or f"{agent.name} failed to produce valid JSON.")
            record = build_failed_agent_run_record(
                index,
                agent,
                graph_state.get("input_json", {}),
                graph_state.get("raw_output", ""),
                error,
            )
            trace_event(state, "node_failed", agent.name, error_type=type(error).__name__, error=str(error))
            return {"patch": StatePatch(node=agent.name, writes={}, run_record=record), "status": "failed"}

        return node

    def _merge_analysis_patches_node(self, graph_state: AnalysisGraphState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        for event in sorted(graph_state.get("parallel_trace_events", []), key=lambda item: item.get("time", "")):
            state.trace_events.append(event)
        state.error_history.extend(graph_state.get("error_history", []))
        state.error_history = state.error_history[-MAX_ERROR_HISTORY_ITEMS:]

        patches = sorted(
            graph_state.get("analysis_patches", []),
            key=lambda patch: patch.run_record.index if patch.run_record is not None else 0,
        )
        failed_patches = [
            patch
            for patch in patches
            if patch.run_record is not None
            and isinstance(patch.run_record.parsed_output, dict)
            and patch.run_record.parsed_output.get("status") == "agent_failed"
        ]
        if failed_patches:
            state.agent_runs.extend(
                patch.run_record
                for patch in patches
                if patch.run_record is not None
            )
            failed_agents = ", ".join(patch.node for patch in failed_patches)
            trace_event(state, "node_failed", "analysis_subgraph", failed_agents=failed_agents)
            raise ValueError(f"Analysis subgraph failed: {failed_agents}")

        for patch in patches:
            apply_state_patch(state, patch)
            save_state_snapshot(state, f"02_after_{camel_to_snake(patch.node)}")
        return {"runtime_state": state}

    def _final_report_agent_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        if state.final_report.strip():
            trace_event(state, "node_skipped", "FinalReportAgent", reason="final_report_already_exists")
            return {"runtime_state": export_runtime_state(state)}
        run_final_report_agent(state, self.agents[3])
        save_state_snapshot(state, "05_after_final_report")
        return {"runtime_state": export_runtime_state(state)}

    def _validate_report_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        validate_report(state)
        save_state_snapshot(state, "06_after_validation")
        return {"runtime_state": export_runtime_state(state)}

    def _write_outputs_node(self, graph_state: LangGraphReportState) -> dict[str, Any]:
        state = require_runtime_state(graph_state)
        if state.output_payload is not None and state.outputs_written_at:
            trace_event(state, "node_skipped", "write_outputs", reason="output_payload_already_exists")
            state.pipeline_status = PIPELINE_COMPLETED
            return {
                "runtime_state": export_runtime_state(state),
                "output_payload": state.output_payload,
                "report": state.final_report,
            }
        payload, report = write_outputs(state)
        state.pipeline_status = PIPELINE_COMPLETED
        save_state_snapshot(state, "07_after_write_outputs")
        return {
            "runtime_state": export_runtime_state(state),
            "output_payload": payload,
            "report": report,
        }


def require_runtime_state(graph_state: LangGraphReportState) -> ReportPipelineState:
    state = graph_state.get("runtime_state")
    if state is None:
        raise RuntimeError("LangGraph runtime state is missing.")
    if isinstance(state, dict):
        return restore_runtime_state(state)
    if isinstance(state, ReportPipelineState):
        return state
    raise RuntimeError("LangGraph runtime state has an unsupported type.")


def export_runtime_state(state: ReportPipelineState) -> dict[str, Any]:
    return to_jsonable(serialize_runtime_state(state))


def clone_state_for_parallel_node(state: ReportPipelineState) -> ReportPipelineState:
    return ReportPipelineState(
        classification=state.classification,
        records=state.records,
        budget_payload=state.budget_payload,
        agent_run_dir=state.agent_run_dir,
        run_id=state.run_id,
        thread_id=state.thread_id,
        business_task=state.business_task,
        schema_version=state.schema_version,
        step_no=state.step_no,
        parent_snapshot_id=state.parent_snapshot_id,
        shared=copy.deepcopy(state.shared),
        expense_output=state.expense_output,
        budget_output=state.budget_output,
        acceptance_output=state.acceptance_output,
        final_report=state.final_report,
        final_report_generated_at=state.final_report_generated_at,
        outputs_written_at=state.outputs_written_at,
        agent_runs=list(state.agent_runs),
        validation_checks=list(state.validation_checks),
        output_payload=state.output_payload,
        error_history=[],
        trace_events=[],
        state_diffs=[],
        pipeline_status=state.pipeline_status,
        human_review_package=copy.deepcopy(state.human_review_package),
        human_review=copy.deepcopy(state.human_review),
        rerun_context=copy.deepcopy(state.rerun_context),
        review_mode=state.review_mode,
        rerun_count=state.rerun_count,
        max_rerun_count=state.max_rerun_count,
    )


def build_terminal_payload(state: ReportPipelineState) -> dict[str, Any]:
    return {
        "schema": "ResearchFinanceReportAgentOutputs",
        "schema_version": "2.0",
        "run_id": state.run_id,
        "thread_id": state.thread_id,
        "pipeline_status": state.pipeline_status,
        "human_review_package": state.human_review_package,
        "human_review": state.human_review,
        "rerun_context": state.rerun_context,
        "final_report_generated_at": state.final_report_generated_at,
        "outputs_written_at": state.outputs_written_at,
        "final_report": {
            "agent": "FinalReportAgent",
            "generated": bool(state.final_report),
        },
    }


def build_interrupt_payload(state: ReportPipelineState, package: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ResearchFinanceReportAgentOutputs",
        "schema_version": "2.0",
        "run_id": state.run_id,
        "thread_id": state.thread_id,
        "pipeline_status": PIPELINE_WAITING_HUMAN,
        "human_review_package": package,
        "human_review": None,
        "rerun_context": state.rerun_context,
        "checkpoint": {
            "resume": "Command(resume=human_review)",
            "thread_id": state.thread_id,
        },
        "final_report": {
            "agent": "FinalReportAgent",
            "generated": False,
        },
    }
