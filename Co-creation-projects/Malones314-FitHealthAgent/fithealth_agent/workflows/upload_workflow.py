"""Logout and upload workflows without HTTP response objects (stage 5)."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from starlette.concurrency import run_in_threadpool
from fithealth_agent.runtime import deps
from fithealth_agent.runtime.deps import (
    _sign_analysis_confidence,
    logger,
)
from fithealth_agent.runtime.upload_io import (
    FIT_FILE_MAX_BYTES, HEALTH_CSV_MAX_BYTES, HEALTH_UPLOAD_MAX_FILES,
    HEALTH_ZIP_MAX_BYTES, PLAN_FILE_CONFIRM_BYTES, PLAN_FILE_MAX_BYTES,
    read_upload_with_limit,
)
from fithealth_agent.daily_checkin import CHECKIN_CATEGORY
from fithealth_agent.backup_service import MAX_BACKUP_BYTES
from fithealth_agent.context_budget import ContextInputError
from fithealth_agent.food_analysis import FoodAnalysisError, MAX_IMAGE_BYTES
from fithealth_agent.health_importer import HealthImportError, extract_activity_fit
from fithealth_agent.plan_classifier import validate_training_plan
from fithealth_agent.domain.plan_validation import infer_training_subject
from fithealth_agent import workout_store

@dataclass(frozen=True)
class WorkflowResult:
    body: dict[str, object]
    status_code: int = 200

def result(*args: object, content: dict[str, object] | None = None, status_code: int = 200, **kwargs: object) -> WorkflowResult:
    body = content if content is not None else (args[0] if args else {})
    if not isinstance(body, dict):
        body = {"detail": body}
    return WorkflowResult(body=body, status_code=status_code)

async def analyze_food(file: Any, context: str = "") -> WorkflowResult:
    if not deps.external_model_settings_store.get()["external_models_enabled"]:
        return result(
            {"error": "外部模型已关闭，餐盘照片不会被发送到视觉服务。"},
            status_code=503,
        )
    content = await read_upload_with_limit(file, MAX_IMAGE_BYTES)
    if content is None:
        return result({"error": "餐盘照片不能超过 10 MiB"}, status_code=413)
    try:
        analysis = await run_in_threadpool(deps.analyze_food_image, content, file.content_type or "", context)
    except FoodAnalysisError as exc:
        return result({"error": str(exc)}, status_code=400)
    except Exception as exc:  # noqa: BLE001
        # BUG-46：以前只捕获 FoodAnalysisError，其他异常（网络超时、视觉服务返回
        # 非预期结构、JSON 解析炸掉）会变成 FastAPI 默认的 500 `{"detail": ...}`，
        # 而前端读 `data.error` 得到 undefined，用户看到的是一片空白。
        logger.exception("餐盘照片分析失败")
        return result(
            {"error": f"餐盘照片分析失败：{exc}"}, status_code=502
        )
    confidence = str(analysis.get("confidence") or "low")
    return result({
        **analysis,
        "analysis_token": _sign_analysis_confidence(confidence),
    })

def logout(payload: dict | None = None) -> WorkflowResult:
    """Handle logout: decide whether to save a partial summary of the conversation.

    Expected payload: { messages: [ { role: 'user'|'bot', text: '...'}, ... ] }

    Returns:
        {
            status: 'saved' | 'not_saved' | 'no_messages' | 'error',
            saved: bool,
            reason: str,
            summary: str,          # present when saved=True
            pipeline_stage: str,   # level1 / level2 / level3 / early
            expired_removed: int,  # number of expired entries cleaned up
        }
    """
    try:
        messages = (payload or {}).get("messages") if payload else None
        if not messages or not isinstance(messages, list):
            return result(
                {"status": "no_messages", "saved": False, "reason": "未提供消息", "summary": "", "expired_removed": 0}
            )

        # 运行三级信息路由
        decision = deps.route_information(
            messages,
            allow_external_models=deps.external_model_settings_store.get()[
                "external_models_enabled"
            ],
        )
        stage = decision.get("pipeline_stage", "unknown")

        if decision.get("save"):
            from datetime import datetime, timedelta, timezone

            summary: str = decision.get("summary") or ""
            facts = normalize_memory_facts(decision.get("facts"))
            if not facts:
                removed = deps.info_store.cleanup_expired()
                return result({
                    "status": "not_saved", "saved": False,
                    "reason": "没有通过校验的结构化事实，未保存记忆",
                    "summary": "", "pipeline_stage": stage,
                    "rejected_facts": decision.get("rejected_facts", 0),
                    "fact_validation": decision.get("fact_validation", ""),
                    "expired_removed": removed,
                })
            retention = memory_retention_class(str(decision.get("type", "training_feedback")), facts)
            expires = None if retention == "long_term" else datetime.now(timezone.utc) + timedelta(days=(30 if retention == "medium" else 7 if retention == "short" else 3))
            entry = deps.info_store.add_entry(
                summary=summary,
                metadata={
                    "reason": decision.get("reason", ""),
                    "pipeline_stage": stage,
                },
                expires_at=expires,
                memory_type=str(decision.get("type", "training_feedback")),
                importance=int(decision.get("importance", 1)),
                user_confirmed=False,
                facts=facts,
            )
            removed = deps.info_store.cleanup_expired()
            return result(
                {
                    "status": "saved",
                    "saved": True,
                    "reason": decision.get("reason", ""),
                    "summary": summary,
                    "pipeline_stage": stage,
                    "entry_id": entry["id"],
                    "memory_type": entry["type"],
                    "importance": entry["importance"],
                    "user_confirmed": entry["user_confirmed"],
                    "rejected_facts": decision.get("rejected_facts", 0),
                    "fact_validation": decision.get("fact_validation", ""),
                    "expired_removed": removed,
                }
            )

        removed = deps.info_store.cleanup_expired()
        return result(
            {
                "status": "not_saved",
                "saved": False,
                "reason": decision.get("reason", ""),
                "summary": "",
                "pipeline_stage": stage,
                "rejected_facts": decision.get("rejected_facts", 0),
                "fact_validation": decision.get("fact_validation", ""),
                "expired_removed": removed,
            }
        )
    except Exception as e:  # noqa: BLE001
        return result(
            {"status": "error", "saved": False, "reason": str(e), "summary": "", "expired_removed": 0},
            status_code=500,
        )

async def upload_fit(file: Any, overwrite_pending: bool = False) -> WorkflowResult:
    """接收 .fit 二进制文件，解析后返回训练展示 JSON。

    返回格式：
        {
            status: 'ok' | 'error',
            message: str,          # 给对话的提示文本
            workout: {...}         # to_public_dict() 结果
        }
    """
    if not file.filename or not file.filename.lower().endswith(".fit"):
        return result(
            {"status": "error", "message": "请上传 .fit 格式的文件"},
            status_code=400,
        )
    tmp_path: str | None = None
    try:
        content = await read_upload_with_limit(file, FIT_FILE_MAX_BYTES)
        if content is None:
            return result(
                {"status": "error", "message": "FIT 文件不能超过 50 MiB。"},
                status_code=413,
            )

        fit_source = await run_in_threadpool(deps.inspect_fit_source, file.filename, content)
        if fit_source.get("warnings") and fit_source.get("kind") == "fit_unknown":
            return result(
                {"status": "error", "message": fit_source["warnings"][0]}, status_code=400
            )
        if fit_source.get("kind") != "activity":
            imported = await run_in_threadpool(
                deps.health_import_service.import_file, file.filename, content
            )
            return result(
                {
                    "status": "ok",
                    "message": _health_import_message([imported], []),
                    "health_import": imported,
                    "workout": None,
                }
            )

        # 保存到临时文件
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        workout = deps.parse_fit_file(tmp_path)
        workout.source_file = Path(file.filename).name
        workout.source_sha256 = hashlib.sha256(content).hexdigest()

        if workout_store.get_current() is not None and not overwrite_pending:
            return result({"error": "已有待确认训练，请确认覆盖后再导入", "code": "PENDING_WORKOUT_EXISTS"}, status_code=409)
        # 将解析结果存入内存状态
        workout_store.set_current(workout)

        # ── 构建给 Agent 的提示文本（按运动类型自适应）────────────────────
        # BUG-10：这里原本写着 `sess.sport if sess else "未知运动"`，读起来像是
        # session 可能为 None。**它不可能为 None**——`parse_fit_file` 取的是
        # `raw_msgs.get("session", [{}])[0]`，缺 session 消息时得到的是一个字段
        # 全为默认值的 SessionSummary（sport="未知运动"）。那句空值保护是死代码，
        # 而且正是它让人以为"缺 session 会崩"，把注意力从真正的缺陷上引开：
        # 缺 session 时不会崩，而是路由拿不到 sport，整场训练被静默丢光。
        sess = workout.session
        segs = workout.segments
        sport = sess.sport

        def _fmt_dur(s: float) -> str:
            s = int(s)
            if s >= 3600:
                return f"{s//3600}h{(s%3600)//60}m{s%60}s"
            if s >= 60:
                return f"{s//60}m{s%60}s"
            return f"{s}s"

        def _fmt_spd(mps: float) -> str:
            if mps <= 0:
                return "--"
            kmh = mps * 3.6
            return f"{kmh:.1f} km/h"

        def _session_summary_line(sess) -> str:
            parts = [f"运动类型：{sess.sport}"]
            if sess.total_elapsed_s:
                parts.append(f"总时长：{_fmt_dur(sess.total_elapsed_s)}")
            if sess.total_distance_m:
                parts.append(f"总距离：{sess.total_distance_m/1000:.2f} km")
            if sess.total_calories:
                parts.append(f"卡路里：{sess.total_calories} kcal")
            if sess.avg_hr:
                parts.append(f"平均心率：{sess.avg_hr} bpm")
            if sess.max_hr:
                parts.append(f"最大心率：{sess.max_hr} bpm")
            if sess.avg_speed_mps:
                parts.append(f"均速：{_fmt_spd(sess.avg_speed_mps)}")
            if sess.total_ascent_m:
                parts.append(f"总爬升：{sess.total_ascent_m:.0f} m")
            if sess.training_effect:
                parts.append(f"训练效果：{sess.training_effect}")
            return "  ".join(parts)

        # 判断主要运动模式：以**实际解析出的分段类型**为准，而不是 sport_raw。
        # DATA-04：`sport=training` 是大类，有氧/HIIT/瑜伽都用它；这些活动现在
        # 会降级成 lap 分段，若仍按 sport_raw 走力量分支，就会把 lap 当成"动作组"
        # 渲染出一串重量 0、次数 0 的假数据。
        sport_raw_lower = (sess.sport_raw or "").lower()
        has_sets = any(s.segment_type in ("set_active", "set_rest") for s in segs)
        is_strength = has_sets or (
            not segs and sport_raw_lower in ("strength_training", "training")
        )

        if is_strength:
            # ── 力量训练：展示 set 表格 ──
            active_sets = [s for s in segs if not s.is_rest]
            if not segs:
                msg = f"[已解析 FIT 文件 {file.filename}，未找到任何训练组数据]"
            else:
                header = "序号 | 类型   | 动作名         | 重量(kg) | 次数 | 时长    | 均心率 | 峰心率"
                sep = "-" * 72
                rows = []
                for s in segs:
                    if s.is_rest:
                        dur = _fmt_dur(s.duration_s)
                        rows.append(f"{s.index:<4} | 休息   | 组间休息        | --       | --   | {dur:<7} | --     | --")
                    else:
                        avg = f"{s.avg_hr}" if s.avg_hr else "--"
                        mx  = f"{s.max_hr}" if s.max_hr else "--"
                        rows.append(
                            f"{s.index:<4} | 动作   | {s.category:<14} | {s.weight_kg:<8} | "
                            f"{s.repetitions:<4} | {_fmt_dur(s.duration_s):<7} | {avg:<6} | {mx}"
                        )
                table = "\n".join(rows)
                msg = (
                    f"[FIT 解析完成] {file.filename} | {sport}\n"
                    f"概况：{_session_summary_line(sess)}\n\n"
                    f"{header}\n{sep}\n{table}\n\n"
                    f"共 {len(active_sets)} 组动作、{len(segs)-len(active_sets)} 段休息。"
                    f"以上识别结果是否准确？如有动作识别错误或需要合并（手表自动暂停导致拆分），请告知我。"
                )
        else:
            # ── 有氧 / 间歇 / 自定义运动：展示 session 摘要 + lap 表格 ──
            summary_line = _session_summary_line(sess)
            if not segs:
                msg = f"[FIT 解析完成] {file.filename} | {sport}\n概况：{summary_line}"
            else:
                # 根据有无距离决定显示列
                has_dist = any(s.distance_m > 0 for s in segs)
                has_cad  = any(s.avg_cadence > 0 for s in segs)
                if has_dist:
                    header = "段  | 时长    | 距离(km) | 均速      | 均心率 | 峰心率"
                    rows = []
                    for s in segs:
                        avg = f"{s.avg_hr}" if s.avg_hr else "--"
                        mx  = f"{s.max_hr}" if s.max_hr else "--"
                        rows.append(
                            f"{s.index:<3} | {_fmt_dur(s.duration_s):<7} | {s.distance_m/1000:<8.2f} | "
                            f"{_fmt_spd(s.avg_speed_mps):<9} | {avg:<6} | {mx}"
                        )
                else:
                    header = "段  | 时长    | 节拍(rpm) | 均心率 | 峰心率 | 卡路里"
                    rows = []
                    for s in segs:
                        avg = f"{s.avg_hr}" if s.avg_hr else "--"
                        mx  = f"{s.max_hr}" if s.max_hr else "--"
                        cad = f"{s.avg_cadence}" if s.avg_cadence else "--"
                        cal = f"{s.calories}" if s.calories else "--"
                        rows.append(
                            f"{s.index:<3} | {_fmt_dur(s.duration_s):<7} | {cad:<9} | "
                            f"{avg:<6} | {mx:<6} | {cal}"
                        )
                sep = "-" * 60
                table = "\n".join(rows)
                msg = (
                    f"[FIT 解析完成] {file.filename} | {sport}\n"
                    f"概况：{summary_line}\n\n"
                    f"{header}\n{sep}\n{table}\n\n"
                    f"共 {len(segs)} 段记录。数据是否符合你的预期？"
                )

        # BUG-10：一段都没解析出来时**不能报告成功**。原实现无论如何都返回
        # `status: "ok"` + "[FIT 解析完成]"，于是"整场训练被丢光"和"一切正常"
        # 在用户眼里长得一模一样，而原始 FIT 通常已不在磁盘上——等发现时数据
        # 已经拿不回来了。这里也不返回 5xx：文件读得动、解析没报错，只是没有
        # 可用分段，把它说成服务器错误同样是误导。
        if not segs:
            logger.warning(
                "FIT 解析未产出任何分段: %s | sport_raw=%s sub_sport=%s hr=%d",
                file.filename, sess.sport_raw, sess.sub_sport, len(workout.hr_records),
            )
            workout_store.clear_current()
            return result(
                {
                    "status": "empty",
                    "message": (
                        f"[FIT 已读取，但没有解析出任何训练分段] {file.filename} | {sport}\n"
                        f"概况：{_session_summary_line(sess)}\n\n"
                        "文件本身可以读取，但里面既没有动作组也没有分段记录"
                        "（常见于中断或未正常结束的活动）。**请保留这个 FIT 文件**，"
                        "它没有被保存，重新导入同一份文件不会有不同结果。"
                    ),
                    "workout": None,
                }
            )

        return result(
            {
                "status": "ok",
                "message": msg,
                "workout": workout.to_public_dict(),
            }
        )
    except HealthImportError as exc:
        # BUG-10：原先只有下面那个 `except Exception`，它会把 HealthImportError
        # 一并吞掉——而这个异常带着精确的中文原因（"该 FIT 是设备监测文件，请从
        # Garmin Connect 导出全天健康数据 ZIP"）和自己的 status_code。吞掉之后
        # 用户看到的是一句"请确认文件完整"，于是去检查一个完好无损的文件。
        # `/upload_health` 一直是单独捕获它的，这里只是把两条路径对齐。
        logger.info("FIT 文件按健康数据导入失败: %s | %s", file.filename, exc)
        return result(
            {"status": "error", "message": str(exc)}, status_code=exc.status_code
        )
    except Exception:  # noqa: BLE001
        logger.exception("FIT 文件解析失败: %s", file.filename)
        return result(
            {
                "status": "error",
                # 不再断言"文件损坏"——走到这里说明是**未预期**的异常，代码 bug
                # 与坏文件同样可能，把后者说成唯一原因会让用户白白折腾文件。
                "message": "FIT 文件解析失败。若文件能在 Garmin Connect 正常打开，请把它保留下来并反馈，这可能是解析器的问题。",
            },
            status_code=500,
        )
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)

async def upload_plan(
    file: Any,
    confirm_large: bool = False,
) -> WorkflowResult:
    """
    处理上传的 .md / .txt 训练计划文件，并进行初步鉴定。
    如果是训练计划，则返回其内容；否则返回拦截原因。
    """
    if not file.filename or Path(file.filename).suffix.lower() not in {".md", ".txt"}:
        return result(
            {"status": "error", "message": "请上传 .md 或 .txt 格式的训练计划。"},
            status_code=400,
        )

    try:
        content_bytes = await read_upload_with_limit(file, PLAN_FILE_MAX_BYTES)
        if content_bytes is None:
            return result(
                {"status": "error", "message": "训练计划文件不能超过 1 MiB。"},
                status_code=413,
            )
        if len(content_bytes) > PLAN_FILE_CONFIRM_BYTES and not confirm_large:
            return result(
                {
                    "status": "confirmation_required",
                    "message": "该训练计划超过 256 KiB，需要确认后才能继续解析。",
                    "size_bytes": len(content_bytes),
                },
                status_code=409,
            )
        try:
            content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = content_bytes.decode('gbk', errors='ignore')
            
        validation_result = validate_training_plan(
            content,
            allow_external_models=deps.external_model_settings_store.get()[
                "external_models_enabled"
            ],
        )
        
        if validation_result["is_plan"]:
            subject = infer_training_subject(content)
            return result(
                content={
                    "status": "ok",
                    "valid": True,
                    "content": content,
                    "reason": validation_result["reason"],
                    "subject": subject,
                }
            )
        else:
            return result(
                content={
                    "status": "ok",
                    "valid": False,
                    "reason": validation_result["reason"]
                }
            )
    except Exception:  # noqa: BLE001
        logger.exception("训练计划解析失败: %s", file.filename)
        return result(
            content={"status": "error", "message": "训练计划解析失败，请检查文件编码和内容。"},
            status_code=500,
        )

def _health_import_message(results: list[dict], errors: list[dict]) -> str:
    lines = ["[健康数据导入完成]"]
    for item in results:
        state = "已存在，未重复导入" if item.get("duplicate") else "已保存"
        details: list[str] = []
        if item.get("heart_rate_count"):
            details.append(f"有效心率 {item['heart_rate_count']} 条")
        if item.get("metric_count"):
            details.append(f"健康指标 {item['metric_count']} 条")
        if item.get("sleep_stage_count"):
            details.append(f"睡眠阶段 {item['sleep_stage_count']} 段")
        if item.get("data_types"):
            details.append("数据类型 " + "/".join(item["data_types"]))
        if item.get("sleep_date"):
            details.append(f"睡眠日期 {item['sleep_date']}")
        if item.get("source_count"):
            details.append(f"FIT 文件 {item['source_count']} 个")
        suffix = f"（{'，'.join(details)}）" if details else ""
        lines.append(f"- {item['filename']}：{state}{suffix}")
        for warning in item.get("warnings", [])[:3]:
            lines.append(f"  - 提示：{warning}")
        for skipped in item.get("skipped_files", []):
            if not isinstance(skipped, dict):
                continue
            skipped_name = str(skipped.get("filename") or "未命名文件")
            reason = str(skipped.get("reason") or "格式不受支持")
            lines.append(f"  - 未处理：{skipped_name}（{reason}）")
    for error in errors:
        lines.append(f"- {error['filename']}：导入失败，{error['message']}")
    if any(item.get("data_types") or item.get("source_count") for item in results):
        lines.append("后续可以直接询问某天的心率、睡眠情况或一段日期内的趋势。")
    elif results:
        lines.append("该压缩包中没有识别出可导入的健康或训练数据。")
    return "\n".join(lines)

def select_autoload_activity(
    activities: list[tuple[str, str, bytes]]
) -> tuple[str, str, bytes] | None:
    """只有**全局恰好一个**活动时才自动载入训练编辑区（BUG-08）。

    原实现的判断是 `len(activities) == 1 and workout is None`，其中 activities
    是**单个 ZIP 内**的列表、workout 是整个循环共用的单变量。于是一次上传两个
    各含一个活动的 ZIP 时，第 1 个被载入，第 2 个只把名字塞进 activity_files
    就没了；而前端在 `data.workout` 非空时直接走第一分支，第 2 个既不进选择器
    也没有任何提示，用户以为两个都导入了。

    改成全局计数：多于一个就一律交给前端选择器逐个处理，不再自动挑一个。
    """
    return activities[0] if len(activities) == 1 else None

async def upload_health(files: list[Any]) -> WorkflowResult:
    if not files or len(files) > HEALTH_UPLOAD_MAX_FILES:
        return result(
            {"status": "error", "message": f"每次请上传 1-{HEALTH_UPLOAD_MAX_FILES} 个健康数据文件。"},
            status_code=400,
        )
    results: list[dict] = []
    errors: list[dict] = []
    # BUG-08：先把**所有** ZIP 里的活动收集齐，再决定是否自动载入。
    # 原实现的条件是 `len(activities) == 1 and workout is None`，而 workout 是
    # 整个循环共用的单变量：第 1 个 ZIP 载入后，后面 ZIP 的活动只把名字塞进
    # activity_files 就没了；前端又在 data.workout 非空时直接走第一分支，
    # 于是 ZIP#2 的训练既不进选择器也没有任何提示，用户以为两个都导入了。
    activity_files: list[str] = []
    activities_index: list[dict[str, str]] = []
    pending_activities: list[tuple[str, str, bytes]] = []
    for file in files:
        filename = Path(file.filename or "").name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".zip", ".csv"}:
            errors.append({"filename": filename or "未命名文件", "message": "只支持 .zip 或 .csv"})
            continue
        limit = HEALTH_ZIP_MAX_BYTES if suffix == ".zip" else HEALTH_CSV_MAX_BYTES
        content = await read_upload_with_limit(file, limit)
        if content is None:
            size_text = "50 MiB" if suffix == ".zip" else "2 MiB"
            errors.append({"filename": filename, "message": f"文件不能超过 {size_text}"})
            continue
        try:
            imported = await run_in_threadpool(deps.health_import_service.import_file, filename, content)
            results.append(imported)
            if suffix == ".zip":
                activities = await run_in_threadpool(deps.extract_activity_fits, content)
                for activity_name, activity_content in activities:
                    activity_files.append(activity_name)
                    # 带上来源 ZIP：选择器要重新上传对应的那个 ZIP 才能取到 FIT
                    activities_index.append({"zip": filename, "name": activity_name})
                    pending_activities.append((filename, activity_name, activity_content))
        except HealthImportError as exc:
            errors.append({"filename": filename, "message": str(exc), "status_code": exc.status_code})
        except Exception:  # noqa: BLE001
            logger.exception("健康数据导入失败: %s", filename)
            errors.append({"filename": filename, "message": "解析或保存失败"})

    # 只有全局恰好一个活动时才自动载入编辑区；多于一个一律交给前端选择器，
    # 免得静默丢掉除第一个以外的训练。
    workout = None
    autoload = select_autoload_activity(pending_activities)
    if autoload is not None:
        _, activity_name, activity_content = autoload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as temporary:
            temporary.write(activity_content)
            temporary_path = temporary.name
        try:
            workout = await run_in_threadpool(deps.parse_fit_file, temporary_path)
            workout.source_file = activity_name
            workout.source_sha256 = hashlib.sha256(activity_content).hexdigest()
            if workout_store.get_current() is not None:
                # Health data itself is still imported, but its optional FIT
                # must not silently replace the workout being edited.
                errors.append({
                    "filename": activity_name,
                    "message": "已有待确认训练，活动未自动载入；请在活动选择器中确认覆盖后载入",
                    "code": "PENDING_WORKOUT_EXISTS",
                })
                workout = None
            else:
                workout_store.set_current(workout)
        except Exception:  # noqa: BLE001
            # 单个活动解析失败不该让整次健康数据导入失败——导入本身已经成功了
            logger.exception("压缩包内活动 FIT 解析失败: %s", activity_name)
            workout = None
            errors.append({"filename": activity_name, "message": "活动 FIT 解析失败，其余健康数据已导入"})
        finally:
            Path(temporary_path).unlink(missing_ok=True)

    if not results:
        status_code = max((int(item.get("status_code", 400)) for item in errors), default=400)
        return result(
            {
                "status": "error",
                "message": _health_import_message([], errors),
                "results": [],
                "errors": errors,
                "unprocessed_files": [
                    {
                        "zip": "",
                        "filename": str(item.get("filename") or "未命名文件"),
                        "reason": str(item.get("message") or "导入失败"),
                    }
                    for item in errors
                ],
            },
            status_code=status_code,
        )
    status = "partial" if errors or any(item.get("status") == "partial" for item in results) else "ok"
    unprocessed_files = [
        {
            "zip": str(result.get("filename") or ""),
            "filename": str(skipped.get("filename") or "未命名文件"),
            "reason": str(skipped.get("reason") or "格式不受支持"),
        }
        for result in results
        for skipped in result.get("skipped_files", [])
        if isinstance(skipped, dict)
    ]
    unprocessed_files.extend({
        "zip": "",
        "filename": str(error.get("filename") or "未命名文件"),
        "reason": str(error.get("message") or "导入失败"),
    } for error in errors)
    return result(
        {
            "status": status,
            "message": _health_import_message(results, errors),
            "results": results,
            "errors": errors,
            "unprocessed_files": unprocessed_files,
            "activity_files": activity_files,
            # 富结构：每个活动带上来源 ZIP，让前端跨多个 ZIP 也能逐个处理
            "activities": activities_index,
            "workout": workout.to_public_dict() if workout else None,
        }
    )

async def upload_activity_from_health_zip(
    file: Any, activity_name: str, overwrite_pending: bool = False
) -> WorkflowResult:
    if not (file.filename or "").lower().endswith(".zip"):
        return result({"error": "请选择包含活动 FIT 的 ZIP 文件"}, status_code=400)
    content = await read_upload_with_limit(file, HEALTH_ZIP_MAX_BYTES)
    if content is None:
        return result({"error": "ZIP 文件不能超过 50 MiB"}, status_code=413)
    try:
        activity_content = await run_in_threadpool(extract_activity_fit, content, activity_name)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as temporary:
            temporary.write(activity_content)
            temporary_path = temporary.name
        try:
            workout = await run_in_threadpool(deps.parse_fit_file, temporary_path)
            workout.source_file = activity_name
            workout.source_sha256 = hashlib.sha256(activity_content).hexdigest()
            if workout_store.get_current() is not None and not overwrite_pending:
                return result({"error": "已有待确认训练，请确认覆盖后再载入", "code": "PENDING_WORKOUT_EXISTS"}, status_code=409)
            workout_store.set_current(workout)
        finally:
            Path(temporary_path).unlink(missing_ok=True)
        return result({"status": "ok", "workout": workout.to_public_dict(), "filename": activity_name})
    except HealthImportError as exc:
        return result({"error": str(exc)}, status_code=400)
    except Exception:  # noqa: BLE001
        logger.exception("压缩包活动 FIT 解析失败: %s", activity_name)
        return result({"error": "活动 FIT 解析失败，请确认文件完整"}, status_code=500)
