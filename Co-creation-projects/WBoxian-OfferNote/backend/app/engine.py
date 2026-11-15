import hashlib
import json
import re
import time

from pydantic import BaseModel, ValidationError

from . import demo
from .schemas import AnalysisOutput
from .config import config_values, public_settings
from .usage import CURRENT_CALL, begin_call, end_call, instrument, public_usage
from .store import now, uid


class ModelError(Exception):
    pass


def fingerprint(resume: str, job: str) -> str:
    return hashlib.sha256(
        json.dumps([resume, job], ensure_ascii=False).encode()
    ).hexdigest()


def settings() -> dict:
    return public_settings()


def is_timeout(exc):
    from httpx import TimeoutException

    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, (TimeoutError, TimeoutException)):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


class Engine:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def make_llm(timeout=120):
        from hello_agents import HelloAgentsLLM

        state = CURRENT_CALL.get()
        config = state["config"] if state else config_values()
        llm = HelloAgentsLLM(
            model=config["MODEL"],
            api_key=config["API_KEY"],
            base_url=config["BASE_URL"],
            provider="custom",
            temperature=0.2,
            max_tokens=int(config["MAX_TOKENS"] or 12000),
            timeout=timeout,
        )
        # 长推理的读超时不应被 SDK 隐式重发，避免重复生成与未知计费。
        llm._client.max_retries = 0
        return instrument(llm)

    @staticmethod
    def parse(output, schema):
        if not isinstance(output, str) or not output.strip():
            raise ValueError("模型未返回 JSON 正文。")
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", output.strip())
        return schema.model_validate_json(text).model_dump()

    def structured_run(self, agent, context, schema):
        prompt = json.dumps(context, ensure_ascii=False)
        for attempt in range(2):
            output = agent.run(prompt)
            try:
                return self.parse(output, schema)
            except (ValidationError, ValueError) as exc:
                errors = (
                    [
                        {"path": ".".join(map(str, e["loc"])), "type": e["type"]}
                        for e in exc.errors(include_input=False, include_url=False)
                    ][:8]
                    if isinstance(exc, ValidationError)
                    else [{"path": "", "type": "empty_output"}]
                )
                state = CURRENT_CALL.get()
                if state is not None:
                    state["validation_errors"] = errors
                if attempt:
                    fields = "、".join(e["path"] or "JSON 根对象" for e in errors)
                    raise ModelError(
                        f"模型结构校验失败，自动修正一次后仍未通过：{fields}。请重试；原有材料和记录已保留。"
                    ) from None
                if state is not None:
                    state["repairs"] += 1
                prompt = (
                    "上次输出未通过结构校验。请依据原始任务重新返回完整 JSON 对象，不要 Markdown 或说明文字。"
                    "不得猜测证据或修改原始 ID。错误字段与类型："
                    + json.dumps(errors, ensure_ascii=False)
                )

    def live(self, stage: str, context: dict, schema: type[BaseModel]) -> dict:
        if not settings()["configured"]:
            raise ModelError(
                "真实模型尚未配置。请在模型设置中填写 API Key、Base URL 和 Model 后重试。"
            )
        try:
            if stage == "interview":
                from .agent_tools import native_decision

                return native_decision(self, context["session"], schema)
            from hello_agents import SimpleAgent
            from .prompts import (
                ANALYSIS_PROMPT,
                DATA_RULES,
                JUDGE_PROMPT,
                REFERENCE_PROMPT,
                DEMONSTRATION_PROMPT,
            )

            instructions = {
                "analysis": ANALYSIS_PROMPT,
                "judge": JUDGE_PROMPT,
                "reference_answers": REFERENCE_PROMPT,
                "demonstration_answer": DEMONSTRATION_PROMPT,
            }
            system = (
                DATA_RULES
                + "\n"
                + instructions[stage]
                + "\n输出 Schema："
                + json.dumps(schema.model_json_schema(), ensure_ascii=False)
            )
            agent = SimpleAgent(
                name=stage,
                llm=self.make_llm(),
                system_prompt=system,
                enable_tool_calling=False,
            )
            return self.structured_run(agent, context, schema)
        except ModelError:
            raise
        except (ValidationError, ValueError, TypeError):
            raise ModelError(
                "模型输出不符合结构契约，本次结果未保存。请重试或检查 JSON 输出与原生工具调用能力。"
            ) from None
        except Exception as exc:
            state = CURRENT_CALL.get()
            if state and state["finish_reason"] == "length":
                raise ModelError(
                    "模型输出达到 Token 上限，结果被截断；请在模型设置中提高最大输出 Token 后重试。"
                ) from None
            if is_timeout(exc):
                raise ModelError(
                    "模型生成超时，本次结果未提交，已有回答和记录仍保留。请稍后重试；系统未自动重发生成请求。"
                ) from None
            raise ModelError(
                "模型请求失败，请检查配置、额度、网络与原生 tool_calls 支持；未自动切回演示模式。"
            ) from None

    def probe(self):
        if not settings()["configured"]:
            raise ModelError("请先保存模型配置，再测试连接。")
        from .agent_tools import probe_native_tools

        started = time.perf_counter()
        state, token = begin_call(config_values())
        try:
            return {
                **probe_native_tools(self),
                **public_usage(state),
                "duration_ms": round((time.perf_counter() - started) * 1000),
            }
        except ModelError:
            raise
        except Exception:
            raise ModelError(
                "连接或原生工具调用测试失败，请检查地址、模型、密钥、网络及 tool_calls 支持。"
            ) from None
        finally:
            end_call(state, token)

    def call(
        self, workspace_id: str, mode: str, stage: str, context: dict, schema, demo_fn
    ) -> dict:
        started = time.perf_counter()
        status = "success"
        state, token = begin_call(config_values())
        try:
            result = demo_fn() if mode == "demo" else self.live(stage, context, schema)
            return schema.model_validate(result).model_dump()
        except ValidationError:
            status = "error"
            raise ModelError("模型结果未通过结构校验，请重试对应生成步骤。") from None
        except Exception:
            status = "error"
            raise
        finally:
            try:
                self.store.event(
                    workspace_id,
                    {
                        "stage": stage,
                        "mode": mode,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000),
                        "model": "固定规则 / 演示"
                        if mode == "demo"
                        else state["config"]["MODEL"],
                        "input_chars": len(json.dumps(context, ensure_ascii=False)),
                        **public_usage(state),
                    },
                )
            finally:
                end_call(state, token)

    def analyze(self, workspace: dict, mode: str) -> dict:
        resume, job = workspace["resume"], workspace["job"]
        raw = self.call(
            workspace["id"],
            mode,
            "analysis",
            {"resume": resume, "job": job},
            AnalysisOutput,
            lambda: demo.analyze(resume, job),
        )
        warnings = []
        for item in raw["requirements"]:
            item["id"] = uid()
            requirement_valid = item["requirement_quote"] in job
            evidence_valid = (
                bool(item["evidence_quote"]) and item["evidence_quote"] in resume
            )
            item["requirement_verified"] = requirement_valid
            item["evidence_verified"] = evidence_valid
            if not requirement_valid or (item["evidence_quote"] and not evidence_valid):
                item["status"] = "needs_review"
                warnings.append("部分模型引文未能在原文逐字找到，已标记待核对。")
            elif item["status"] in ("supported", "partial") and not evidence_valid:
                item["status"] = "missing"
                item["reason"] = "模型未提供可核对的简历原文，不能作为已匹配证据。"
        valid_claims = []
        for claim in raw["claims"]:
            if claim["quote"] not in resume:
                warnings.append("已丢弃无法在简历中找到原文的经历主张。")
                continue
            claim.update(id=uid(), confirmed=False, quote_verified=True)
            valid_claims.append(claim)
        if not valid_claims:
            raise ModelError("未提取到带有效原文证据的经历主张，请补充项目材料后重试。")
        raw.update(
            id=uid(),
            created_at=now(),
            mode=mode,
            fingerprint=fingerprint(resume, job),
            claims=valid_claims,
            warnings=list(dict.fromkeys(warnings)),
        )
        return raw


def report(session: dict) -> dict:
    turns = session["turns"]
    groups = {"supported": [], "partial": [], "unverified": []}
    for turn in turns:
        groups[turn["feedback"]["verdict"]].append(turn["question"]["topic"])
    weak = [turn for turn in turns if turn["feedback"]["verdict"] != "supported"]
    actions = list(dict.fromkeys(turn["feedback"]["next_step"] for turn in weak))
    return {
        "answered": len(turns),
        "planned": len(session["questions"]),
        "groups": groups,
        "actions": actions,
        "weak_topics": list(dict.fromkeys(turn["question"]["topic"] for turn in weak)),
        "scope": "仅覆盖已作答的问题；引文核对只证明原文存在，不等于技术结论正确。",
        "demo_notice": "演示反馈来自固定规则，不代表真实面试能力或模型推理结果。"
        if session["mode"] == "demo"
        else "面试判断需结合实际代码、产物与人工复核。",
    }
