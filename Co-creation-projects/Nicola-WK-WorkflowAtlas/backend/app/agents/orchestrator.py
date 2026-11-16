"""A deterministic main coordinator with six bounded HelloAgents tools.

Remote mode delegates only classification and extraction to isolated
SimpleAgent subagents. Project resolution, explicit-relation checking, graph
construction and literal evidence verification are deterministic boundaries.
"""
from __future__ import annotations

from collections import Counter
from time import perf_counter
from typing import Any, Callable

import hello_agents
from hello_agents import ToolRegistry
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse, ToolStatus

from ..extraction.local import explicit_relations
from ..extraction.contextual import classify_local_message, extract_messages
from ..extraction.remote import ModelResponseError, RemoteReasoner, external_authorized
from ..resolution.projects import resolve_projects
from ..schemas import AgentTaskResult, AnalysisResult, Project, StandardMessage, WorkFact, WorkflowUpdateProposal
from ..workflow.builder import build_workflow
from ..workflow.verifier import fact_verification_errors, message_index, verify_references

AGENT_NAMES = ["Information Filter", "Fact Extractor", "Project Resolver", "Relation Reasoner", "Workflow Reconstructor", "Evidence Verifier"]


class AnalysisError(RuntimeError):
    def __init__(self, stage: str, results: list[AgentTaskResult], public_detail: str | None = None):
        super().__init__(f"Analysis failed at {stage}; no update proposal was committed")
        self.stage = stage
        self.agent_results = results
        self.public_detail = public_detail


class SpecialistTool(Tool):
    """Actual framework Tool: registered/executed with timing and circuit breaker."""
    def __init__(self, name: str, callback: Callable[[dict], dict]):
        super().__init__(name=name.replace(" ", "_"), description=f"Bounded read-only workflow specialist: {name}")
        self.callback = callback

    def get_parameters(self) -> list[ToolParameter]:
        return [ToolParameter(name="payload", type="object", description="Only this stage's required structured data")]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        if set(parameters) != {"payload"} or not isinstance(parameters["payload"], dict):
            return ToolResponse.error("INVALID_PARAM", "Expected a bounded payload object")
        try:
            result = self.callback(parameters["payload"])
        except ModelResponseError as error:
            return ToolResponse.error("MODEL_RESPONSE", error.public_detail)
        return ToolResponse.success(text="Specialist stage completed", data=result)


class WorkflowOrchestrator:
    """Coordinates tools; never synthesizes project facts itself."""
    agent_names = AGENT_NAMES

    def __init__(self, provider: str = "local-demo", *, external_llm_enabled: bool = False,
                 external_data_authorized: bool = False, llm_model: str = "", llm_api_key: str = "",
                 llm_base_url: str = "", remote_max_seconds: float = 180,
                 cancel_check: Callable[[], bool] | None = None, economy_mode: bool = False):
        self.provider = provider
        self.economy_mode = economy_mode
        if self.provider not in {"local-demo", "helloagents-llm"}:
            raise ValueError("WORKFLOW_PROVIDER must be local-demo or helloagents-llm")
        self.external_llm_enabled = external_llm_enabled
        self.external_data_authorized = external_data_authorized
        self.remote_config = {"external_llm_enabled": external_llm_enabled,
                              "external_data_authorized": external_data_authorized,
                              "model": llm_model, "api_key": llm_api_key, "base_url": llm_base_url,
                              "max_seconds": remote_max_seconds, "cancel_check": cancel_check}
        if self.provider == "helloagents-llm" and not external_authorized(external_llm_enabled, external_data_authorized):
            raise PermissionError("External reasoning requires both model enablement and enterprise data authorization")
        self.framework_version = hello_agents.__version__
        self.last_results: list[AgentTaskResult] = []

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "framework": {"name": "HelloAgents", "version": self.framework_version,
                          "components": ["Tool", "ToolRegistry", "ToolResponse", "SimpleAgent.run_as_subagent (remote only)"]},
            "agents": [{"name": name, "mode": "llm" if self.provider == "helloagents-llm" and index < 2 and not (self.economy_mode and index == 0) else "deterministic"}
                       for index, name in enumerate(AGENT_NAMES)],
            "external_llm_enabled": self.provider == "helloagents-llm" and external_authorized(self.external_llm_enabled, self.external_data_authorized),
            "limitations": ["Local demo uses conservative rules, not LLM inference.",
                            "Evidence verification checks literal support, not semantic truth; human review is required.",
                            "Local project attribution uses literal natural names, explicit sections and unique recorded reply ancestors; ambiguity stays unassigned.",
                            "Remote calls require two explicit authorization flags and finite context/call budgets; economy mode combines filtering/extraction for up to five bounded segments."],
            "latest_results": [result.model_dump(mode="json") for result in self.last_results],
        }

    def analyze(self, messages: list[StandardMessage], existing_projects: list[Project] | None = None) -> AnalysisResult:
        if len(messages) > 100000:
            raise ValueError("Local job limit is 100000 messages; process a smaller source")
        remote = None
        results: list[AgentTaskResult] = []
        registry = ToolRegistry()

        def filter_stage(payload):
            checked = [StandardMessage.model_validate(item) for item in payload["messages"]]
            classified = []
            for message in checked:
                if remote and self.economy_mode and callable(getattr(remote, "extract_many", None)):
                    category = "work" if message.text.strip() else "background"
                else:
                    category = remote.classify(message) if remote else classify_local_message(message)
                classified.append({"source_id": message.source_id, "message_id": message.id, "classification": category})
            return {"classifications": classified, "messages": [message.model_dump(mode="json") for message, item in zip(checked, classified) if item["classification"] == "work"]}

        def extract_stage(payload):
            if remote is None:
                selected = [StandardMessage.model_validate(item) for item in payload["messages"]]
                context = [StandardMessage.model_validate(item) for item in payload.get("context_messages", payload["messages"])]
                facts = extract_messages(context, selected_messages=selected)
                return {"facts": [fact.model_dump(mode="json") for fact in facts]}
            facts = []
            if self.economy_mode and callable(getattr(remote, "extract_many", None)):
                facts = remote.extract_many([StandardMessage.model_validate(item) for item in payload["messages"]])
                return {"facts": [fact.model_dump(mode="json") for fact in facts]}
            for item in payload["messages"]:
                message = StandardMessage.model_validate(item)
                facts.extend(remote.extract(message))
            return {"facts": [fact.model_dump(mode="json") for fact in facts]}

        def resolve_stage(payload):
            facts = [WorkFact.model_validate(item) for item in payload["facts"]]
            projects = [Project.model_validate(item) for item in payload["projects"]]
            evidence_index = message_index([StandardMessage.model_validate(item) for item in payload["messages"]])
            valid, invalid, warnings = [], [], []
            for fact in facts:
                errors = fact_verification_errors(fact, evidence_index)
                if errors:
                    fact.project_id = None
                    invalid.append(fact)
                    warnings.append(f"Fact {fact.id}: project discovery skipped because source evidence failed verification")
                else:
                    valid.append(fact)
            resolved, discovered, resolution_warnings = resolve_projects(valid, projects)
            resolved.extend(invalid)
            warnings.extend(resolution_warnings)
            return {"facts": [fact.model_dump(mode="json") for fact in resolved],
                    "projects": [project.model_dump(mode="json") for project in discovered], "warnings": warnings}

        def relation_stage(payload):
            facts = [WorkFact.model_validate(item) for item in payload["facts"]]
            candidates = 0
            for fact in facts:
                # Additional references may justify project/assignee context.
                # Their predicates belong to the ancestor observation, not to
                # this fact. Only its primary observation can propose a link.
                observations = fact.evidence[:1]
                explicit = []
                for evidence in observations:
                    explicit.extend(explicit_relations(evidence.quote))
                # A remote interpretation remains a proposal; graph builder
                # checks explicit markers, target identity and source support.
                proposed = fact.attributes.get("relations", [])
                if not isinstance(proposed, list):
                    proposed = []
                unique = {}
                for item in [*proposed, *explicit]:
                    if not isinstance(item, dict):
                        continue
                    quote = item.get("quote")
                    if not isinstance(quote, str) or not quote.strip() or not any(quote in evidence.quote for evidence in observations):
                        continue
                    key = (item.get("relation"), item.get("target_entity_key"), item.get("target_fact_id"), quote)
                    if not all(value is None or isinstance(value, str) for value in key):
                        continue
                    unique[key] = item
                relations = list(unique.values())[:20]
                fact.attributes["relations"] = relations
                candidates += len(relations)
            return {"facts": [fact.model_dump(mode="json") for fact in facts], "candidate_count": candidates}

        def reconstruct_stage(payload):
            proposal = build_workflow([WorkFact.model_validate(item) for item in payload["facts"]],
                                      [StandardMessage.model_validate(item) for item in payload["messages"]],
                                      [Project.model_validate(item) for item in payload["projects"]])
            return {"proposal": proposal.model_dump(mode="json")}

        def verify_stage(payload):
            proposal = WorkflowUpdateProposal.model_validate(payload["proposal"])
            originals = [StandardMessage.model_validate(item) for item in payload["messages"]]
            evidence_index = message_index(originals)
            node_ids = {node.id for node in proposal.nodes}
            for fact in proposal.facts:
                supported = verify_references(fact.evidence, evidence_index)
                if fact.verified and not supported:
                    raise ValueError("Graph builder returned a fact with unsupported evidence")
            for node in proposal.nodes:
                if not node.verified or not verify_references(node.evidence, evidence_index):
                    raise ValueError("Graph node evidence did not pass final verification")
            for edge in proposal.edges:
                if edge.source not in node_ids or edge.target not in node_ids or not edge.verified or not verify_references(edge.evidence, evidence_index):
                    raise ValueError("Graph edge did not pass final source/endpoint verification")
            return {"proposal": proposal.model_dump(mode="json"), "verified_count": sum(fact.verified for fact in proposal.facts)}

        callbacks = [filter_stage, extract_stage, resolve_stage, relation_stage, reconstruct_stage, verify_stage]
        for name, callback in zip(AGENT_NAMES, callbacks):
            tool = SpecialistTool(name, callback)
            try:
                registry.register_tool(tool)
            except UnicodeEncodeError:
                # Upstream prints an emoji after successful registration. GBK
                # Windows consoles cannot encode it; do not undo actual work.
                if registry.get_tool(tool.name) is not tool:
                    raise

        def execute(name: str, payload: dict, input_count: int, count_output: Callable[[dict], int], detail: str) -> dict:
            started = perf_counter()
            tool_name = name.replace(" ", "_")
            # Each role sees only its own registered tool and required payload.
            scoped = registry.fork([tool_name])
            response = scoped.execute_tool(tool_name, {"payload": payload})
            elapsed = (perf_counter() - started) * 1000
            if response.status != ToolStatus.SUCCESS:
                results.append(AgentTaskResult(agent=name, status="failed", input_count=input_count,
                                               detail="Stage failed; proposal rejected atomically", duration_ms=elapsed))
                self.last_results = results
                detail = response.text if response.error_info and response.error_info.get("code") == "MODEL_RESPONSE" else None
                raise AnalysisError(name, results, detail)
            results.append(AgentTaskResult(agent=name, status="completed", input_count=input_count,
                                           output_count=count_output(response.data), detail=detail, duration_ms=elapsed))
            return response.data

        encoded_messages = [message.model_dump(mode="json") for message in sorted(messages, key=lambda message: (message.timestamp, message.source_id, message.id))]
        try:
            if self.provider == "helloagents-llm":
                remote = RemoteReasoner(**self.remote_config)
            filtered = execute(AGENT_NAMES[0], {"messages": encoded_messages}, len(messages), lambda result: len(result["messages"]),
                               ("Nonempty messages queued for combined model filtering/extraction" if remote and self.economy_mode and callable(getattr(remote, "extract_many", None)) else
                                "One-message classification: " + ("authorized isolated HelloAgents subagents" if remote else "local deterministic rules")))
            categories = Counter(item["classification"] for item in filtered["classifications"])
            results[-1].detail += "; " + ", ".join(f"{name}={count}" for name, count in sorted(categories.items()))
            extracted = execute(AGENT_NAMES[1], {"messages": filtered["messages"], "context_messages": encoded_messages if remote is None else []}, len(filtered["messages"]), lambda result: len(result["facts"]),
                                "Atomic observations bound to literal source quotes; pending human review")
            resolved = execute(AGENT_NAMES[2], {"facts": extracted["facts"], "projects": [project.model_dump(mode="json") for project in existing_projects or []], "messages": encoded_messages},
                               len(extracted["facts"]), lambda result: sum(item["project_id"] is not None for item in result["facts"]),
                               "Deterministic explicit project/alias matching; unresolved information retained")
            reasoned = execute(AGENT_NAMES[3], {"facts": resolved["facts"]}, len(resolved["facts"]), lambda result: result["candidate_count"],
                               "Bounded explicit relation proposals; chronology alone never creates causation")
            reconstructed = execute(AGENT_NAMES[4], {"facts": reasoned["facts"], "messages": encoded_messages, "projects": [project.model_dump(mode="json") for project in existing_projects or []]},
                                    len(reasoned["facts"]), lambda result: len(result["proposal"]["nodes"]),
                                    "Deterministic temporal graph, branches and source-supported cycles")
            verified = execute(AGENT_NAMES[5], {"proposal": reconstructed["proposal"], "messages": encoded_messages},
                               len(reconstructed["proposal"]["facts"]), lambda result: result["verified_count"],
                               "Literal source identity, nonempty quotes and graph endpoints checked; semantic review remains pending")
            proposal = WorkflowUpdateProposal.model_validate(verified["proposal"])
            proposal.warnings = list(dict.fromkeys([*resolved["warnings"], *proposal.warnings]))
            self.last_results = results
            return AnalysisResult(proposal=proposal, agent_results=results, provider=self.provider)
        finally:
            if remote is not None:
                remote.close()
