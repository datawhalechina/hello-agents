"""
阶段 2：Nutritionist → Coach → Habit 三 Agent 串行流水线；
每阶段 LLM 输出经 Pydantic 校验，失败自动重试；统一错误码与降级。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, ValidationError

from core.llm_adapter import get_llm_adapter
from memory.store import format_reflect_memory_for_prompt, save_diet_run
from rag.indexers import index_diet_run
from rag.retriever import retrieve
from service.diet_errors import DietErrorCode, diet_error_record
from service.diet_schemas import (
    SCHEMA_VERSION,
    CoachOutput,
    FoodParseOutput,
    HabitOutput,
    MealPlan,
    MealPlanItem,
    NutritionistOutput,
    NutritionSummary,
)
from tools.diet_tools import dispatch_tool

logger = logging.getLogger(__name__)

DIET_STAGE_TIMEOUT_SEC = 95.0
MAX_STAGE_ATTEMPTS = 2


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i = t.find("{")
        j = t.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(t[i : j + 1])
            except json.JSONDecodeError:
                return None
    return None


def _goal_target_protein(context: Dict[str, Any]) -> float:
    goal = str(context.get("goal") or "maintain")
    if goal == "muscle_gain":
        return 130.0
    if goal == "fat_loss":
        return 95.0
    return 105.0


def _fallback_food_parse(context: Dict[str, Any]) -> FoodParseOutput:
    raw = str(context.get("today_food_log_text") or "")
    pieces = [p.strip(" ，。;；\n\t") for p in re.split(r"[，,;；。]\s*", raw) if p.strip()]
    items = []
    for p in pieces[:10]:
        items.append(
            {
                "meal_time": "",
                "food_name": p[:40],
                "portion_text": "未明确",
                "confidence": 0.45,
            }
        )
    return FoodParseOutput(
        items=items,
        nutrition_summary=NutritionSummary(),
        parse_notes="（降级）食物解析阶段失败，已按日志片段做粗略拆分；营养值未估算。",
    )


def _fallback_nutritionist(context: Dict[str, Any], nutrition_summary: NutritionSummary) -> NutritionistOutput:
    tgt = _goal_target_protein(context)
    cur = float(nutrition_summary.protein_g or 0)
    gap = max(0.0, tgt - cur)
    return NutritionistOutput(
        protein_gap_g=gap,
        rationale="（降级）根据目标与日志解析结果估算蛋白缺口；LLM 阶段未通过校验或超时。",
        suggested_lookup_queries=["鸡蛋,希腊酸奶,牛奶,豆浆,即食鸡胸肉"],
        candidate_focus=["便利店高蛋白", "训练后补充"],
    )


def _fallback_coach(context: Dict[str, Any]) -> CoachOutput:
    activity_text = str(context.get("activity_context") or "")
    train = any(k in activity_text for k in ["训练", "力量", "健身", "workout", "training"])
    return CoachOutput(
        training_recovery_note="（降级）晚间安排力量训练时需优先补充蛋白与适量碳水；具体强度以当日体感为准。"
        if train
        else "（降级）非训练日仍以均衡蛋白为主，避免睡前过饱。",
        timing_constraints="训练后 1～2 小时内尽量安排一餐；便利店即食优先选成分表蛋白较高的品类。"
        if train
        else "晚餐时间尽量规律，避免过晚大量进食。",
        energy_note="",
        coach_constraints_for_menu=["少油炸", "避免单次过量乳糖不耐受品类"],
    )


def _fallback_habit(
    context: Dict[str, Any], reflect_mem: str, nutrition_summary: NutritionSummary
) -> HabitOutput:
    tgt = _goal_target_protein(context)
    cur = float(nutrition_summary.protein_g or 0)
    gap = max(25.0, min(80.0, max(0.0, tgt - cur)))
    return HabitOutput(
        reflect_alignment="（降级）未能生成完整习惯层输出；已忽略部分 Reflect 细节，仅做安全兜底推荐。"
        + (" 近期有用户反馈记录，建议下次缩短决策链或检查模型输出格式。" if "暂无" not in reflect_mem else ""),
        execution_hints=["优先买得到、可立即食用的组合", "若仍失败请改选外卖蛋白套餐"],
        meal_plan=MealPlan(
            items=[
                MealPlanItem(
                    name="希腊酸奶",
                    portion="约 150g×1 杯",
                    est_protein_g=min(18.0, gap * 0.35),
                    why="便利店常见，蛋白密度较高",
                ),
                MealPlanItem(
                    name="水煮蛋",
                    portion="2 个",
                    est_protein_g=12.0,
                    why="易购买、蛋白稳定",
                ),
                MealPlanItem(
                    name="豆浆",
                    portion="300ml",
                    est_protein_g=min(12.0, gap * 0.2),
                    why="补充液体蛋白与水分",
                ),
            ],
            total_est_protein_g=round(min(gap, 45.0), 1),
            tips=["此为 schema/LLM 失败时的安全兜底菜单，建议重试或检查 API。"],
        ),
    )


async def _run_validated_stage(
    llm: Any,
    stage: str,
    prompt: str,
    model_cls: Type[BaseModel],
    errors: List[Dict[str, Any]],
    timeout_sec: float = DIET_STAGE_TIMEOUT_SEC,
) -> Tuple[Optional[BaseModel], List[Dict[str, Any]]]:
    attempts: List[Dict[str, Any]] = []
    repair_hint = ""
    for attempt in range(MAX_STAGE_ATTEMPTS):
        full_prompt = prompt
        if repair_hint:
            full_prompt += (
                "\n\n【修正要求】上一输出未通过 schema 校验或无法解析：\n"
                f"{repair_hint}\n请只输出 **一个** JSON 对象，字段齐全、类型正确，不要 Markdown。"
            )
        try:
            raw = await asyncio.wait_for(llm.ainvoke(full_prompt), timeout=timeout_sec)
        except asyncio.TimeoutError:
            errors.append(
                diet_error_record(
                    stage,
                    DietErrorCode.LLM_TIMEOUT,
                    "LLM 调用超时",
                    attempt=attempt,
                )
            )
            attempts.append(
                {"attempt": attempt, "ok": False, "error_code": DietErrorCode.LLM_TIMEOUT.value}
            )
            repair_hint = "上次超时；请输出更紧凑的 JSON，保留所有必填字段。"
            continue
        except Exception as e:
            # 上游模型网关 5xx / SDK 异常都归一为阶段中止错误，避免接口直接 500。
            errors.append(
                diet_error_record(
                    stage,
                    DietErrorCode.STAGE_ABORTED,
                    f"LLM 调用异常: {type(e).__name__}",
                    attempt=attempt,
                    detail=str(e)[:1200],
                )
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "ok": False,
                    "error_code": DietErrorCode.STAGE_ABORTED.value,
                    "exception": type(e).__name__,
                }
            )
            repair_hint = "上轮调用失败，请仅输出合法 JSON。"
            continue

        obj = _extract_json_object(raw)
        if obj is None:
            errors.append(
                diet_error_record(
                    stage,
                    DietErrorCode.LLM_PARSE_ERROR,
                    "无法从模型输出解析 JSON",
                    attempt=attempt,
                    detail=(raw[:1200] if raw else ""),
                )
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "ok": False,
                    "error_code": DietErrorCode.LLM_PARSE_ERROR.value,
                    "llm_preview": (raw[:1500] if raw else ""),
                }
            )
            repair_hint = "模型输出不是合法 JSON；请严格输出 JSON only。"
            continue

        try:
            validated = model_cls.model_validate(obj)
            attempts.append(
                {
                    "attempt": attempt,
                    "ok": True,
                    "error_code": None,
                    "llm_preview": raw[:2500] if raw else "",
                }
            )
            return validated, attempts
        except ValidationError as ve:
            err_text = ve.json()[:2000]
            errors.append(
                diet_error_record(
                    stage,
                    DietErrorCode.VALIDATION_FAILED,
                    "Pydantic 校验失败",
                    attempt=attempt,
                    detail=err_text,
                )
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "ok": False,
                    "error_code": DietErrorCode.VALIDATION_FAILED.value,
                    "validation_detail": err_text,
                    "parsed_shape": {k: type(v).__name__ for k, v in obj.items()}
                    if isinstance(obj, dict)
                    else None,
                }
            )
            repair_hint = err_text

    return None, attempts


def _prefetch_tools(user_id: str, context: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    trace_tools: List[Dict[str, Any]] = []
    activity: Dict[str, Any] = {}
    nutrition: Dict[str, Any] = {}
    try:
        activity = dispatch_tool(
            "activity_sleep_summary", {"user_id": user_id}, user_id
        )
    except Exception as e:
        trace_tools.append(
            {
                "tool": "activity_sleep_summary",
                "ok": False,
                "error": str(e),
            }
        )
    else:
        trace_tools.append({"tool": "activity_sleep_summary", "ok": True, "result": activity})

    default_q = "鸡蛋,希腊酸奶,牛奶,豆浆,即食鸡胸肉"
    try:
        nutrition = dispatch_tool(
            "nutrition_lookup",
            {"query": context.get("nutrition_prefetch_query") or default_q},
            user_id,
        )
    except Exception as e:
        trace_tools.append({"tool": "nutrition_lookup", "ok": False, "error": str(e)})
    else:
        trace_tools.append({"tool": "nutrition_lookup", "ok": True, "result": nutrition})

    return {"activity": activity, "nutrition": nutrition}, trace_tools


class DietMultiAgentPipeline:
    def __init__(self) -> None:
        self.llm = get_llm_adapter()

    async def run(
        self,
        user_id: str,
        context: Dict[str, Any],
        *,
        replayed_from_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        reflect_mem = format_reflect_memory_for_prompt(user_id, limit=8)
        errors: List[Dict[str, Any]] = []
        pipeline_trace: List[Dict[str, Any]] = []
        rag_result = await asyncio.to_thread(
            retrieve,
            user_id,
            {
                "scenario": "diet_recommendation",
                "goal": context.get("goal"),
                "free_notes": context.get("free_notes", ""),
                "today_food_log_text": str(context.get("today_food_log_text") or "")[:600],
                "query": "训练后蛋白补齐与执行阻碍规避",
            },
        )
        rag_summary = rag_result.get("summary", "（暂无召回记忆）")
        pipeline_trace.append({"phase": "rag_retrieve", "debug": rag_result.get("debug", {})})

        tool_bundle, tool_trace = _prefetch_tools(user_id, context)
        pipeline_trace.append({"phase": "tool_prefetch", "tools": tool_trace})

        degraded = False

        # ----- Food Parse (LLM) -----
        fp_prompt = f"""你是食物日志解析 Agent。请把用户自然语言饮食记录解析为 JSON。只输出一个 JSON 对象，不要 Markdown。

结构：
{{
  "items": [
    {{
      "meal_time": string,      // breakfast/lunch/dinner/snack 或空字符串
      "food_name": string,
      "portion_text": string,
      "confidence": number      // 0~1
    }}
  ],
  "nutrition_summary": {{
    "protein_g": number,
    "carb_g": number,
    "fat_g": number,
    "fiber_g": number,
    "sodium_mg": number,
    "calories_kcal": number
  }},
  "parse_notes": string
}}

要求：
- 从 today_food_log_text 中尽可能提取食物与份量；没有明确份量可写“未明确”。
- nutrition_summary 给出粗略估计值；无法判断可填 0。
- 字段齐全且类型正确。

用户场景：
{json.dumps(context, ensure_ascii=False, indent=2)}
"""
        fp, fp_attempts = await _run_validated_stage(
            self.llm, "food_parse", fp_prompt, FoodParseOutput, errors
        )
        fp_fb = False
        if fp is None:
            fp = _fallback_food_parse(context)
            fp_fb = True
            degraded = True
            errors.append(
                diet_error_record(
                    "food_parse",
                    DietErrorCode.DEGRADED_FALLBACK,
                    "食物解析阶段失败，已使用规则降级输出",
                )
            )
        pipeline_trace.append(
            {
                "phase": "food_parse",
                "fallback_used": fp_fb,
                "attempts": fp_attempts,
                "output": fp.model_dump(),
            }
        )

        # ----- Nutritionist -----
        n_prompt = f"""你是 **Nutritionist（营养师）Agent**。只输出 **一个 JSON**，不要其它文字。

字段与类型必须完全一致：
{{
  "protein_gap_g": number,
  "rationale": string,
  "suggested_lookup_queries": string[],
  "candidate_focus": string[]
}}

用户场景：
{json.dumps(context, ensure_ascii=False, indent=2)}

食物解析结果（LLM）：
{json.dumps(fp.model_dump(), ensure_ascii=False, indent=2)}

Reflect 记忆（调整推荐策略）：
{reflect_mem}

历史记忆召回（RAG）：
{rag_summary}

Mock 营养表检索结果（供参考）：
{json.dumps(tool_bundle.get("nutrition", {}), ensure_ascii=False, indent=2)}
"""
        nu, nu_attempts = await _run_validated_stage(
            self.llm, "nutritionist", n_prompt, NutritionistOutput, errors
        )
        nu_fb = False
        if nu is None:
            nu = _fallback_nutritionist(context, fp.nutrition_summary)
            nu_fb = True
            degraded = True
            errors.append(
                diet_error_record(
                    "nutritionist",
                    DietErrorCode.DEGRADED_FALLBACK,
                    "营养师阶段失败，已使用规则降级输出",
                )
            )
        pipeline_trace.append(
            {
                "phase": "nutritionist",
                "fallback_used": nu_fb,
                "attempts": nu_attempts,
                "output": nu.model_dump(),
            }
        )

        # 按营养师建议追加一次营养查询（可选）
        extra_nutrition: Dict[str, Any] = {}
        if nu.suggested_lookup_queries:
            q = ",".join(nu.suggested_lookup_queries[:3])
            try:
                extra_nutrition = dispatch_tool(
                    "nutrition_lookup", {"query": q[:200]}, user_id
                )
            except Exception as e:
                errors.append(
                    diet_error_record(
                        "tool",
                        DietErrorCode.TOOL_ERROR,
                        f"nutrition_lookup 追加查询失败: {e}",
                    )
                )
                extra_nutrition = {"error": str(e)}
        tool_bundle["nutrition_extra"] = extra_nutrition

        # ----- Coach -----
        c_prompt = f"""你是 **Coach（运动恢复）Agent**。只输出 **一个 JSON**。

结构：
{{
  "training_recovery_note": string,
  "timing_constraints": string,
  "energy_note": string,
  "coach_constraints_for_menu": string[]
}}

用户场景：
{json.dumps(context, ensure_ascii=False, indent=2)}

食物解析（营养汇总）：
{json.dumps(fp.nutrition_summary.model_dump(), ensure_ascii=False, indent=2)}

营养师结论：
{json.dumps(nu.model_dump(), ensure_ascii=False, indent=2)}

活动/睡眠摘要：
{json.dumps(tool_bundle.get("activity", {}), ensure_ascii=False, indent=2)}

历史记忆召回（RAG）：
{rag_summary}
"""
        co, co_attempts = await _run_validated_stage(
            self.llm, "coach", c_prompt, CoachOutput, errors
        )
        co_fb = False
        if co is None:
            co = _fallback_coach(context)
            co_fb = True
            degraded = True
            errors.append(
                diet_error_record(
                    "coach",
                    DietErrorCode.DEGRADED_FALLBACK,
                    "Coach 阶段失败，已使用模板降级输出",
                )
            )
        pipeline_trace.append(
            {
                "phase": "coach",
                "fallback_used": co_fb,
                "attempts": co_attempts,
                "output": co.model_dump(),
            }
        )

        # ----- Habit -----
        h_prompt = f"""你是 **Habit（习惯养成）Agent**。只输出 **一个 JSON**。

结构：
{{
  "reflect_alignment": string,
  "execution_hints": string[],
  "meal_plan": {{
    "items": [{{ "name": string, "portion": string, "est_protein_g": number, "why": string }}],
    "total_est_protein_g": number,
    "tips": string[]
  }}
}}

要求：
- meal_plan.items 至少 1 条；份量具体、可执行；适合便利店/外卖。
- 结合 Reflect 记忆，说明本次如何规避上次失败原因。
- est_protein_g 为粗略估计。

用户场景：
{json.dumps(context, ensure_ascii=False, indent=2)}

食物解析结果：
{json.dumps(fp.model_dump(), ensure_ascii=False, indent=2)}

Reflect 记忆：
{reflect_mem}

历史记忆召回（RAG）：
{rag_summary}

营养师：
{json.dumps(nu.model_dump(), ensure_ascii=False, indent=2)}

Coach：
{json.dumps(co.model_dump(), ensure_ascii=False, indent=2)}

营养数据（含追加查询）：
{json.dumps(tool_bundle, ensure_ascii=False, indent=2)[:12000]}
"""
        ha, ha_attempts = await _run_validated_stage(
            self.llm, "habit", h_prompt, HabitOutput, errors
        )
        ha_fb = False
        if ha is None:
            ha = _fallback_habit(context, reflect_mem, fp.nutrition_summary)
            ha_fb = True
            degraded = True
            errors.append(
                diet_error_record(
                    "habit",
                    DietErrorCode.DEGRADED_FALLBACK,
                    "Habit 阶段失败，已使用安全兜底菜单",
                )
            )
        pipeline_trace.append(
            {
                "phase": "habit",
                "fallback_used": ha_fb,
                "attempts": ha_attempts,
                "output": ha.model_dump(),
            }
        )

        meal_plan = ha.meal_plan.model_dump()

        planning = {
            "reasoning": nu.rationale,
            "plan_steps": [
                "FoodParse：从饮食日志抽取食物与份量并估算营养",
                f"Nutritionist：缺口约 {nu.protein_gap_g:.1f}g 蛋白",
                "Coach：训练/进食窗口与恢复约束",
                "Habit：对齐 Reflect 的可执行菜单",
            ],
            "agent_pipeline": [
                "FoodParseAgent",
                "NutritionistAgent",
                "CoachAgent",
                "HabitAgent",
            ],
        }

        output: Dict[str, Any] = {
            "run_id": run_id,
            "user_id": user_id,
            "schema_version": SCHEMA_VERSION,
            "pipeline_mode": "multi_agent",
            "replayed_from": replayed_from_run_id,
            "degraded": degraded,
            "errors": errors,
            "planning": planning,
            "stages": {
                "nutritionist": {
                    "ok": not nu_fb,
                    "fallback_used": nu_fb,
                    "output": nu.model_dump(),
                },
                "coach": {
                    "ok": not co_fb,
                    "fallback_used": co_fb,
                    "output": co.model_dump(),
                },
                "habit": {
                    "ok": not ha_fb,
                    "fallback_used": ha_fb,
                    "output": ha.model_dump(),
                },
            },
            "meal_plan": meal_plan,
            "food_parse": fp.model_dump(),
            "nutrition_summary": fp.nutrition_summary.model_dump(),
            "habit_extras": {
                "reflect_alignment": ha.reflect_alignment,
                "execution_hints": ha.execution_hints,
            },
            "react_trace": pipeline_trace,
            "reflect_memory_used": reflect_mem,
            "retrieved_memory": rag_summary,
            "rag_debug": rag_result.get("debug", {}),
        }

        try:
            save_diet_run(
                user_id=user_id,
                run_id=run_id,
                input_payload=context,
                steps_trace=pipeline_trace,
                output_payload=output,
                replayed_from_run_id=replayed_from_run_id,
            )
        except Exception as e:
            logger.exception("diet_runs 落库失败: %s", e)
        try:
            # 最佳努力索引，不影响主流程
            await asyncio.to_thread(index_diet_run, run_id)
        except Exception as e:
            logger.warning("diet run 向量索引失败（不影响返回）: %s", e)

        return output
        
