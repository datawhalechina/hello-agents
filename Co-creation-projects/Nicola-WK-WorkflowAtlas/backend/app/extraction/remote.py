"""Explicitly authorized HelloAgents reasoning; no automatic remote fallback."""
from __future__ import annotations

import json
import time
from typing import Any, Callable
from urllib.parse import urlparse

from hello_agents import Config, HelloAgentsLLM, SimpleAgent
from hello_agents.core.budget import RunBudget
from openai import APIConnectionError, APITimeoutError, AuthenticationError, PermissionDeniedError, RateLimitError

from ..agents.prompts import BATCH_EXTRACTION_PROMPT, EXTRACTION_PROMPT, FILTER_PROMPT
from ..schemas import EvidenceReference, FactKind, StandardMessage, WorkFact
from .local import stable_fact_id


def external_authorized(external_llm_enabled: bool = False, external_data_authorized: bool = False) -> bool:
    """Explicit booleans only; environment variables cannot grant permission."""
    return external_llm_enabled is True and external_data_authorized is True


class ModelAnalysisCancelled(RuntimeError):
    """Cooperative cancellation checked before a transmission, without retry."""


class ModelResponseError(RuntimeError):
    def __init__(self, message: str, public_detail: str):
        super().__init__(message)
        self.public_detail = public_detail


class _BatchOutputLimit(RuntimeError):
    """Split a multi-segment input instead of increasing output tokens."""


def _connection_error_detail(error: Exception) -> str:
    # HelloAgents may wrap SDK errors. Inspect only their types/numeric status,
    # following the bounded exception chain without ever reading body text.
    seen: set[int] = set()
    current: BaseException | None = error
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        status = getattr(current, "status_code", None)
        if isinstance(current, (AuthenticationError, PermissionDeniedError)) or status in (401, 403):
            return "模型服务认证失败，请检查 API Key 及模型访问权限。"
        if isinstance(current, RateLimitError) or status == 429:
            return "模型服务限流或额度不足，请检查配额并稍后重试。"
        if isinstance(current, (APITimeoutError, TimeoutError)):
            return "模型连接超时，请检查服务地址或稍后重试。"
        if isinstance(current, (APIConnectionError, ConnectionError)):
            return "无法连接模型服务，请检查服务地址和网络。"
        if status == 404:
            return "模型或接口不存在，请检查模型名称及接口根地址。"
        current = current.__cause__ or current.__context__
    return "模型连接失败，请检查服务地址、模型名称和接口兼容性。"


def test_model_connection(model: str, api_key: str, base_url: str) -> dict[str, Any]:
    """One fixed synthetic request; never sends imported data or returns secrets.

    URL validation and user-triggered access are owned by the settings service.
    Keep response/error bodies private even if an upstream service echoes keys.
    """
    started = time.perf_counter()
    llm = None
    ok = False
    detail = "模型连接失败，请检查服务地址和模型名称。"
    try:
        if not model.strip() or not api_key.strip() or not base_url.strip():
            return {"ok": False, "detail": "请填写模型名称、服务地址和 API Key。", "latency_ms": 0}
        llm = HelloAgentsLLM(model=model, api_key=api_key, base_url=base_url,
                             provider="openai", temperature=0, max_tokens=16, timeout=10,
                             budget=RunBudget(max_calls=1, max_seconds=30))
        llm._adapter._get_client().max_retries = 0
        options = {}
        if urlparse(base_url).hostname == 'api.deepseek.com' and (model == 'deepseek-flash' or model.startswith('deepseek-v4')):
            options['extra_body'] = {'thinking': {'type': 'disabled'}}
        result = llm.invoke([
            {"role": "system", "content": "This is a connection test. Reply only OK."},
            {"role": "user", "content": "请回复 OK。"},
        ], **options)
        if isinstance(result.content, str) and result.content.strip():
            ok = True
            detail = "连接成功，模型已返回有效响应。"
        else:
            detail = "模型服务未返回有效文本，请确认接口类型和模型名称。"
    except (AuthenticationError, PermissionDeniedError):
        detail = "模型服务认证失败，请检查 API Key 及模型访问权限。"
    except RateLimitError:
        detail = "模型服务限流或额度不足，请检查配额并稍后重试。"
    except (APITimeoutError, TimeoutError):
        detail = "模型连接超时，请检查服务地址或稍后重试。"
    except (APIConnectionError, ConnectionError):
        detail = "无法连接模型服务，请检查服务地址和网络。"
    except Exception as exc:
        detail = _connection_error_detail(exc)
    finally:
        if llm is not None:
            try:
                llm.close()
            except Exception:
                # Cleanup failures must not turn a sanitized result into a raw
                # provider exception containing credentials or request bodies.
                pass
    return {"ok": ok, "detail": detail, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}


class RemoteReasoner:
    """One fresh, tool-less subagent per call, max two attempts, bounded evidence."""
    max_input_chars = 16000
    max_output_chars = 32000

    def __init__(self, *, external_llm_enabled: bool = False, external_data_authorized: bool = False,
                 model: str = "", api_key: str = "", base_url: str = "",
                 max_calls: int = 60, max_seconds: float = 180,
                 cancel_check: Callable[[], bool] | None = None):
        self.external_llm_enabled = external_llm_enabled
        self.external_data_authorized = external_data_authorized
        self.cancel_check = cancel_check
        self._economy_calls = 0
        self._economy_max_calls = min(60, max_calls)
        if not external_authorized(external_llm_enabled, external_data_authorized):
            raise PermissionError("Remote analysis requires explicit model enablement and enterprise data authorization")
        if not model.strip() or not api_key.strip() or not base_url.strip():
            raise ValueError("Explicit model, API key and base URL are required; ambient credentials are not used")
        endpoint = urlparse(base_url)
        if endpoint.scheme not in {"http", "https"} or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.fragment:
            raise ValueError("Model endpoint must be an explicit HTTP(S) URL without embedded credentials or fragment")
        self.budget = RunBudget(max_calls=max_calls, max_seconds=max_seconds)
        self.llm = HelloAgentsLLM(model=model, api_key=api_key, base_url=base_url,
                                  provider="openai", temperature=0, max_tokens=3000, timeout=120, budget=self.budget)

    def close(self) -> None:
        self.llm.close()

    def _json(self, name: str, prompt: str, message: StandardMessage, validator) -> Any:
        # Send only this source's necessary fields, never metadata or full history.
        payload = json.dumps({"message_id": message.id, "source_id": message.source_id,
                              "sender": message.sender, "timestamp": message.timestamp.isoformat(),
                              "text": message.text}, ensure_ascii=False)
        if len(payload) > self.max_input_chars:
            raise ValueError("Message exceeds remote context budget (16000 characters); split the source before analysis")
        last_error = None
        token_budget = original_tokens = getattr(self.llm, "max_tokens", 3000)
        public_detail = "模型返回的结构化数据或原文引文未通过校验，请重试或更换模型。"
        for attempt in range(2):
            # Re-check authorization at every transmission boundary.
            if self.cancel_check is not None and self.cancel_check():
                raise ModelAnalysisCancelled("Analysis cancellation requested before model transmission")
            if not external_authorized(self.external_llm_enabled, self.external_data_authorized):
                raise PermissionError("External data authorization was revoked")
            try:
                self.llm.max_tokens = token_budget
                agent = SimpleAgent(name, self.llm, system_prompt=prompt,
                                    config=Config(context_window=12000, skills_enabled=False,
                                                  session_enabled=False, trace_enabled=False,
                                                  subagent_enabled=False),
                                    enable_tool_calling=False)
                receipt = agent.run_as_subagent(payload, return_summary=False, max_steps_override=1)
                if not receipt["success"]:
                    # Read only a fixed framework status, never raw provider errors.
                    if receipt.get("metadata", {}).get("error") == "子任务未完成：output_limit":
                        public_detail = "模型输出达到长度上限，增加预算重试后仍被截断；请更换模型或拆分较长消息。"
                        token_budget = 12000
                    raise ValueError("HelloAgents subagent did not complete")
                raw = receipt["result"]
                if not isinstance(raw, str) or len(raw) > self.max_output_chars:
                    raise ValueError("Model output violates response size/type budget")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError("Model JSON must be an object")
                return validator(result)
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.1)
            finally:
                self.llm.max_tokens = original_tokens
        # Upstream error text may echo keys or request data. Keep the safe type
        # for diagnostics while preventing raw provider cause chains in logs.
        raise ModelResponseError(f"{name} failed structured output validation after two attempts ({type(last_error).__name__})", public_detail) from None

    def classify(self, message: StandardMessage) -> str:
        def validate(result):
            if set(result) != {"classification"} or result["classification"] not in {"work", "chitchat", "background", "uncertain"}:
                raise ValueError("Invalid classification schema")
            return result["classification"]
        return self._json("Information Filter", FILTER_PROMPT, message, validate)

    def extract(self, message: StandardMessage) -> list[WorkFact]:
        return self._json("Fact Extractor", EXTRACTION_PROMPT, message,
                          lambda result: self._validate_facts(result, message))

    @staticmethod
    def _segments(message: StandardMessage) -> list[StandardMessage]:
        # splitlines keeps every original newline; slicing never discards a tail.
        pieces: list[str] = []
        current = ""
        for paragraph in message.text.splitlines(keepends=True):
            while paragraph:
                if current and len(current) + len(paragraph) > 800:
                    pieces.append(current)
                    current = ""
                take = paragraph[:800]
                paragraph = paragraph[800:]
                current += take
                if len(current) == 800:
                    pieces.append(current)
                    current = ""
        if current:
            pieces.append(current)
        assert "".join(pieces) == message.text
        return [message.model_copy(update={"text": piece}) for piece in pieces]

    def extract_many(self, messages: list[StandardMessage]) -> list[WorkFact]:
        """One combined filter/extract call per five small, independent segments.

        Matching is source-scoped and complete. Segments retain original IDs;
        repeated IDs never occur within one request. Facts are deduplicated by
        stable identity only after strict validation against the supplied segment.
        """
        originals: dict[str, StandardMessage] = {}
        sources = {message.source_id for message in messages}
        if len(sources) > 1:
            raise ValueError("Batch extraction requires exactly one source")
        for message in messages:
            previous = originals.get(message.id)
            if previous is not None and previous != message:
                raise ValueError("Conflicting duplicate message ID")
            originals[message.id] = message
        batches: list[list[StandardMessage]] = []
        pending: list[StandardMessage] = []
        chars = 0
        for message in originals.values():
            if not message.text.strip():
                continue
            for segment in self._segments(message):
                if pending and (len(pending) == 5 or chars + len(segment.text) > 1800
                                or any(item.id == segment.id for item in pending)):
                    batches.append(pending)
                    pending, chars = [], 0
                pending.append(segment)
                chars += len(segment.text)
        if pending:
            batches.append(pending)
        unique: dict[str, WorkFact] = {}
        for batch in batches:
            for fact in self._extract_batch(batch):
                # Source identity/actor/timestamp and fact ID derive from the
                # immutable original; segments only constrain admissible quotes.
                original = originals[fact.evidence[0].message_id]
                fact.id = stable_fact_id(original, fact.kind.value, fact.evidence[0].quote, fact.summary)
                unique[fact.id] = fact
        return list(unique.values())

    def _extract_batch(self, messages: list[StandardMessage]) -> list[WorkFact]:
        expected = {message.id: message for message in messages}

        def validate(result):
            if set(result) != {"messages"} or not isinstance(result["messages"], list):
                raise ValueError("Invalid batch envelope")
            seen: set[str] = set()
            facts = []
            for item in result["messages"]:
                if not isinstance(item, dict) or set(item) != {"message_id", "facts"}:
                    raise ValueError("Invalid batch message")
                identity = item["message_id"]
                if not isinstance(identity, str) or identity not in expected or identity in seen:
                    raise ValueError("Unknown or duplicate output message ID")
                seen.add(identity)
                compact = item["facts"]
                if isinstance(compact, list):
                    compact = [dict(fact, summary=fact["quote"][:2000])
                               if isinstance(fact, dict) and "summary" not in fact and isinstance(fact.get("quote"), str)
                               else fact for fact in compact]
                facts.extend(self._validate_facts({"facts": compact}, expected[identity]))
            if seen != set(expected):
                raise ValueError("Model omitted an input message")
            return facts

        try:
            return self._economy_json(messages, validate)
        except _BatchOutputLimit:
            if len(messages) == 1:
                message = messages[0]
                if len(message.text) <= 200:
                    raise ModelResponseError("Single segment reached output limit",
                                             "短消息分段的模型输出仍达到长度上限；本批次未提交，请更换模型后重试。") from None
                middle = len(message.text) // 2
                # Prefer a nearby exact paragraph boundary; both slices always
                # shrink, preserving every character and the original identity.
                newline = message.text.rfind("\n", len(message.text) // 3, 2 * len(message.text) // 3)
                if newline >= 0:
                    middle = newline + 1
                left = message.model_copy(update={"text": message.text[:middle]})
                right = message.model_copy(update={"text": message.text[middle:]})
                return self._extract_batch([left]) + self._extract_batch([right])
            middle = len(messages) // 2
            return self._extract_batch(messages[:middle]) + self._extract_batch(messages[middle:])

    def _economy_json(self, messages: list[StandardMessage], validator) -> list[WorkFact]:
        payload = json.dumps({"messages": [
            {"message_id": message.id, "source_id": message.source_id,
             "sender": message.sender, "timestamp": message.timestamp.isoformat(), "text": message.text}
            for message in messages]}, ensure_ascii=False)
        if len(payload) > self.max_input_chars:
            raise ModelResponseError("Batch identity fields exceed input limit", "消息标识等字段超过模型输入限制，本批次未提交。")
        original_tokens = getattr(self.llm, "max_tokens", 3000)
        last_error = None
        for _ in range(2):
            if self.cancel_check is not None and self.cancel_check():
                raise ModelAnalysisCancelled("Analysis cancellation requested before model transmission")
            if not external_authorized(self.external_llm_enabled, self.external_data_authorized):
                raise PermissionError("External data authorization was revoked")
            if self._economy_calls >= self._economy_max_calls:
                raise ModelResponseError("Batch call budget exhausted", "本批次已达到模型调用上限，未提交结果；请减小批次后重试。")
            self._economy_calls += 1
            try:
                self.llm.max_tokens = 3000
                agent = SimpleAgent("Batch Fact Extractor", self.llm, system_prompt=BATCH_EXTRACTION_PROMPT,
                                    config=Config(context_window=12000, skills_enabled=False,
                                                  session_enabled=False, trace_enabled=False,
                                                  subagent_enabled=False), enable_tool_calling=False)
                receipt = agent.run_as_subagent(payload, return_summary=False, max_steps_override=1)
                if not receipt["success"]:
                    if receipt.get("metadata", {}).get("error") == "子任务未完成：output_limit":
                        raise _BatchOutputLimit()
                    raise ValueError("HelloAgents subagent did not complete")
                raw = receipt["result"]
                if not isinstance(raw, str):
                    raise ValueError("Invalid response type")
                if len(raw) > self.max_output_chars:
                    raise _BatchOutputLimit()
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError("Model JSON must be an object")
                return validator(result)
            except _BatchOutputLimit:
                raise
            except Exception as error:
                last_error = error
            finally:
                self.llm.max_tokens = original_tokens
        raise ModelResponseError(f"Batch extraction failed validation after two attempts ({type(last_error).__name__})",
                                 "模型返回的消息标识、结构或原文引文未通过校验，本批次未提交。") from None

    def _validate_facts(self, result: dict, message: StandardMessage) -> list[WorkFact]:
        if set(result) != {"facts"} or not isinstance(result["facts"], list) or len(result["facts"]) > 30:
            raise ValueError("Invalid fact envelope")
        facts = []
        allowed = {"kind", "summary", "quote", "project_hint", "entity_key", "status", "relations"}
        for item in result["facts"]:
            if not isinstance(item, dict) or set(item) - allowed:
                raise ValueError("Invalid fact fields")
            quote = item.get("quote")
            summary = item.get("summary")
            if not isinstance(quote, str) or not quote.strip() or quote not in message.text:
                raise ValueError("Model evidence is not a literal source substring")
            if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000 or summary not in quote:
                raise ValueError("Summary must be a literal substring of its own evidence")
            kind = FactKind(item["kind"])
            relations = item.get("relations", [])
            if not isinstance(relations, list) or len(relations) > 20:
                raise ValueError("Invalid relations")
            for relation in relations:
                if not isinstance(relation, dict) or set(relation) != {"relation", "target_entity_key", "quote"}:
                    raise ValueError("Invalid relation schema")
                if relation["relation"] not in {"depends_on", "blocks", "resolves", "produces", "revises", "branches_to", "parallel_with"}:
                    raise ValueError("Invalid relation kind")
                if not isinstance(relation["quote"], str) or not relation["quote"] or relation["quote"] not in quote:
                    raise ValueError("Invalid relation evidence")
                target = relation["target_entity_key"]
                if not isinstance(target, str) or not target or target not in relation["quote"]:
                    raise ValueError("Invalid relation target")
            project_hint, entity_key = item.get("project_hint"), item.get("entity_key")
            for value in (project_hint, entity_key):
                if value is not None and (not isinstance(value, str) or not value.strip() or value not in quote):
                    raise ValueError("Entity/project must occur explicitly in source")
            status = item.get("status", "observed")
            if status not in {"observed", "pending", "planned", "in_progress", "blocked", "completed", "cancelled", "rework"}:
                raise ValueError("Invalid observation status")
            facts.append(WorkFact(id=stable_fact_id(message, kind.value, quote, summary), kind=kind,
                                  summary=summary, project_hint=project_hint, entity_key=entity_key,
                                  actor=message.sender, status=status, occurred_at=message.timestamp,
                                  evidence=[EvidenceReference(message_id=message.id, source_id=message.source_id, quote=quote)],
                                  confidence=0.65, attributes={"provider": "helloagents-llm", "relations": relations}))
        return facts
