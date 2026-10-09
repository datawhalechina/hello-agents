"""共享单例与可替换的外部依赖引用（main.py 拆分：阶段 1）。

拆分之后 routes / workflows 各层都要用到同一批 store 实例。如果每个模块各自
`import main`，立刻形成循环导入；如果各自再 new 一个 store，那就是两份状态互相覆盖。
所以这里做**单一持有点**。

## 为什么调用方必须写 `deps.X` 而不是 `from deps import X`

`from x import f` 会在调用方模块里绑一个**新名字**。测试替换 `deps.soreness_store`
时，那个副本还指向旧实例——测试变绿但桩根本没生效。这是本次拆分里最危险的一类回归
（拆分计划里的"约束 A"），因为它不报错、不留痕，只是让一整组用例失去意义。
属性访问在调用时才解析，所以凡是**可能被整体替换**的东西都必须写 `deps.X`：

- 11 个 store / service 实例；
- 10 个被测试打桩的外部依赖函数（下面第二组）。

反过来，**不会被替换**的东西按名字导入就好，没有"副本指向旧对象"的问题：上传体积
上限（见 `upload_io.py`）、`logger`、两个签名辅助函数。

## 为什么不能在 `runtime/__init__.py` 里 eager import 本模块

见 `runtime/__init__.py` 的说明：store 实例化必须晚于 `FITHEALTH_DATA_DIR` 设值。
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fithealth_agent.backup_service import LocalBackupService
from fithealth_agent.external_model_settings import ExternalModelSettingsStore
from fithealth_agent.health_importer import HealthImportService
from fithealth_agent.health_store import HealthStore
from fithealth_agent.hr_stream_store import HRStreamStore
from fithealth_agent.info_store import InfoStore
from fithealth_agent.maintenance import MAINTENANCE
from fithealth_agent.plan_draft_cache import PlanDraftCache
from fithealth_agent.plan_store import TrainingPlanStore
from fithealth_agent.soreness_store import SorenessStore
from fithealth_agent.storage import DailyRecordStore, UserProfileStore

# ── 被测试打桩的外部依赖 ────────────────────────────────────────────────
# 这些名字在本模块里"未被使用"是故意的：它们就是为了让调用方走
# `deps.route_chat_intent(...)`，从而使 `monkeypatch.setattr(deps, ...)` 生效。
# 不要因为静态检查报"unused import"就删掉，也不要改成 `import ... as _...`。
from fithealth_agent import create_fithealth_agent  # noqa: F401
from fithealth_agent.chat_intent_router import route_chat_intent  # noqa: F401
from fithealth_agent.fit_parser import parse_fit_file  # noqa: F401
from fithealth_agent.food_analysis import analyze_food_image  # noqa: F401
from fithealth_agent.health_importer import (  # noqa: F401
    extract_activity_fits,
    inspect_fit_source,
)
from fithealth_agent.health_safety import classify_user_health_statement  # noqa: F401
from fithealth_agent.information_router import route_information  # noqa: F401
from fithealth_agent.muscle_recovery import parse_soreness_reply  # noqa: F401
from fithealth_agent.plan_goal_validator import validate_plan_goal_alignment  # noqa: F401
from fithealth_agent.weekly_summary import build_current_week_reply  # noqa: F401


#: 全局共享的日志器。用固定名字而不是 `__name__`：拆分后 routes / workflows 各层
#: 都从这里取 logger，用 `__name__` 的话日志里会出现一串
#: `fithealth_agent.runtime.deps`，反而看不出是哪一层打的。
logger = logging.getLogger("fithealth")


# ── 共享单例 ────────────────────────────────────────────────────────────
profile_store = UserProfileStore()
daily_record_store = DailyRecordStore()
info_store = InfoStore()
external_model_settings_store = ExternalModelSettingsStore()
soreness_store = SorenessStore()
plan_store = TrainingPlanStore()
# 生成计划时在服务端留一份完整正文，避免"保存刚才的计划"回捞被截断的
# 聊天历史（BUG-05）。进程内短期缓存，不持久化。
plan_draft_cache = PlanDraftCache()
health_store = HealthStore()
# 已保存训练的 1Hz 心率流旁挂存储（DATA-05）：训练记录里只留摘要，
# 原始流不进 daily_records.json（会撑爆 ReAct 观察）也不进 health.db
# 的 heart_rate_samples（会把日均心率按采样点等权算歪）。
hr_stream_store = HRStreamStore()
health_import_service = HealthImportService(health_store)
# DATA-12：恢复备份要同时换掉 4 个 JSON 与 health.db，所以把维护开关和
# HealthStore 都交给备份服务——它需要竖开关、排空在飞请求、独占数据库。
backup_service = LocalBackupService(
    daily_record_store.db_path.parent,
    gate=MAINTENANCE,
    database=health_store,
    on_restored=[info_store.revalidate],
)


# ── 餐盘分析置信度的签名状态 ────────────────────────────────────────────
# 餐盘分析签发 token、营养保存校验 token，两条路径必须用**同一把**密钥。所以密钥和
# 两个辅助函数一起放在这唯一的持有点：拆分后如果 routes/uploads.py 和
# routes/records.py 各自 `os.urandom(32)`，签出来的 token 永远验不过，
# 而症状只是"保存营养记录时置信度被静默降级"。
_configured_analysis_secret = (
    os.getenv("FITHEALTH_SIGNING_KEY")
    or os.getenv("VISION_API_KEY")
    or os.getenv("LLM_API_KEY")
)
_analysis_signing_key = (
    _configured_analysis_secret.encode("utf-8")
    if _configured_analysis_secret
    else os.urandom(32)
)


def _sign_analysis_confidence(confidence: str) -> str:
    signature = hmac.new(
        _analysis_signing_key, confidence.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{confidence}.{signature}"


def _verified_analysis_confidence(token: str) -> str | None:
    try:
        confidence, signature = token.split(".", 1)
    except ValueError:
        return None
    if confidence not in {"low", "medium", "high"}:
        return None
    expected = _sign_analysis_confidence(confidence).split(".", 1)[1]
    return confidence if hmac.compare_digest(signature, expected) else None
