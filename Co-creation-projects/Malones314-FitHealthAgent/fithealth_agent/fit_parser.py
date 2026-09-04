"""fit_parser.py  — 弹性多运动类型 FIT 解析器

设计原则：
  - 不写死任何运动类型：通过 session.sport 自动检测，路由到对应的解析策略
  - 所有策略都返回统一的 ParsedActivity 数据结构
  - 新增运动类型只需注册一个 SportParser 子类，无需改动主流程

支持的运动类型（自动扩展）：
  strength_training → 力量训练  → 解析 set 消息（active/rest）
  cycling           → 骑行      → 解析 record 流 + lap 分段
  running           → 跑步      → 解析 record 流 + lap 分段（按公里）
  数字84 / 自定义sport → 跳绳/其他 → 解析 record + lap，用 sport.name 命名
  未知               → 通用兜底  → record 流 + session 摘要
"""

from __future__ import annotations

import statistics
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import fitparse
except ImportError as exc:
    raise ImportError("请先安装 fitparse：pip install fitparse") from exc


# ══════════════════════════════════════════════════════════════════════════════
# 一、通用数据结构
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class HRRecord:
    """单条心率记录"""
    timestamp: datetime
    heart_rate: int


@dataclass
class ActivitySegment:
    """
    通用活动片段，既可表示：
      - 力量训练组（active/rest）
      - 有氧运动的一个 lap 分段
      - 跳绳的一轮
    """
    index: int
    segment_type: str           # 'set_active' | 'set_rest' | 'lap' | 'interval'
    start_time: datetime
    end_time: datetime
    duration_s: float

    # 力量训练专属
    category: str = ""          # 中文动作名
    category_raw: str = ""      # 英文枚举名
    repetitions: int = 0
    weight_kg: float = 0.0
    is_rest: bool = False

    # 有氧专属
    distance_m: float = 0.0
    avg_speed_mps: float = 0.0
    max_speed_mps: float = 0.0
    avg_cadence: int = 0
    avg_power_w: int = 0
    calories: int = 0
    lap_trigger: str = ""

    # 通用心率
    avg_hr: int | None = None
    max_hr: int | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "index":        self.index,
            "segment_type": self.segment_type,
            "start_time":   self.start_time.isoformat(),
            "end_time":     self.end_time.isoformat(),
            "duration_s":   round(self.duration_s, 1),
            "avg_hr":       self.avg_hr,
            "max_hr":       self.max_hr,
        }
        if self.segment_type in ("set_active", "set_rest"):
            d.update({
                "category":     self.category,
                "category_raw": self.category_raw,
                "repetitions":  self.repetitions,
                "weight_kg":    self.weight_kg,
                "is_rest":      self.is_rest,
            })
        else:
            d.update({
                "distance_m":     round(self.distance_m, 1),
                "avg_speed_mps":  round(self.avg_speed_mps, 3),
                "max_speed_mps":  round(self.max_speed_mps, 3),
                "avg_cadence":    self.avg_cadence,
                "avg_power_w":    self.avg_power_w,
                "calories":       self.calories,
                "lap_trigger":    self.lap_trigger,
            })
        if self.extra:
            d.update(self.extra)
        return d

    # 向后兼容：原来 WorkoutSet 的接口
    @property
    def weight_kg_compat(self): return self.weight_kg


# 向后兼容别名
WorkoutSet = ActivitySegment


@dataclass
class SessionSummary:
    """整个运动会话的摘要（来自 session 消息）"""
    sport: str                  # 规范化后的运动类型名（中文）
    sport_raw: str              # FIT 原始值
    sub_sport: str = ""
    start_time: datetime | None = None
    total_elapsed_s: float = 0.0
    total_timer_s: float = 0.0
    total_distance_m: float = 0.0
    total_calories: int = 0
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_speed_mps: float = 0.0
    max_speed_mps: float = 0.0
    avg_cadence: int = 0
    total_ascent_m: float = 0.0
    total_descent_m: float = 0.0
    avg_power_w: int = 0
    training_effect: float = 0.0
    anaerobic_effect: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sport":             self.sport,
            "sport_raw":         self.sport_raw,
            "sub_sport":         self.sub_sport,
            "start_time":        self.start_time.isoformat() if self.start_time else None,
            "total_elapsed_s":   round(self.total_elapsed_s, 1),
            "total_timer_s":     round(self.total_timer_s, 1),
            "total_distance_m":  round(self.total_distance_m, 1),
            "total_calories":    self.total_calories,
            "avg_hr":            self.avg_hr,
            "max_hr":            self.max_hr,
            "avg_speed_mps":     round(self.avg_speed_mps, 3),
            "max_speed_mps":     round(self.max_speed_mps, 3),
            "avg_cadence":       self.avg_cadence,
            "total_ascent_m":    self.total_ascent_m,
            "total_descent_m":   self.total_descent_m,
            "avg_power_w":       self.avg_power_w,
            "training_effect":   self.training_effect,
            "anaerobic_effect":  self.anaerobic_effect,
        }


@dataclass
class ParsedActivity:
    """完整解析结果——对所有运动类型统一"""
    session: SessionSummary
    segments: list[ActivitySegment]      # lap / set / interval
    hr_records: list[HRRecord]           # 心率时间序列（用于重算）
    source_file: str = ""
    source_sha256: str = ""
    parsed_at: str = ""
    note: str = ""

    # 向后兼容
    @property
    def sets(self) -> list[ActivitySegment]:
        return self.segments

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "parsed_at":   self.parsed_at,
            "note":        self.note,
            "session":     self.session.to_dict(),
            "sets":        [s.to_dict() for s in self.segments],
        }


# 向后兼容别名
ParsedWorkout = ParsedActivity


# ══════════════════════════════════════════════════════════════════════════════
# 二、力量训练：动作名解析
# ══════════════════════════════════════════════════════════════════════════════

_EXERCISE_CATEGORY: dict[int, str] = {
    0:  "bench_press",     1:  "calf_raise",       2:  "cardio",
    3:  "carry",           4:  "chop",             5:  "core",
    6:  "crunch",          7:  "curl",             8:  "deadlift",
    9:  "flye",            10: "hip_raise",        11: "hip_stability",
    12: "hip_swing",       13: "hyperextension",   14: "lateral_raise",
    15: "leg_curl",        16: "leg_raise",        17: "lunge",
    18: "olympic_lift",    19: "plank",            20: "plyo",
    21: "pull_up",         22: "push_up",          23: "row",
    24: "shoulder_press",  25: "shoulder_stability", 26: "shrug",
    27: "sit_up",          28: "squat",            29: "total_body",
    30: "tricep_extension", 31: "warm_up",         32: "run",
    33: "unknown",
}

_EXERCISE_SUBTYPE: dict[int, str] = {
    0:  "卧推",    1:  "上斜卧推",  2:  "下斜卧推",  3:  "史密斯卧推",
    5:  "哑铃卧推", 7:  "颈上卧推",
    19: "硬拉",    20: "罗马尼亚硬拉", 21: "相扑硬拉", 22: "直腿硬拉",
    29: "二头弯举", 30: "哑铃弯举", 31: "锤式弯举",  32: "坐姿弯举",
    33: "集中弯举", 34: "绳索弯举", 35: "反握弯举",
    36: "臀桥",    37: "单腿臀桥",
    38: "肩上推举", 39: "哑铃肩推", 40: "阿诺德推举", 42: "杠铃肩推",
    48: "侧平举",  49: "哑铃侧平举", 50: "绳索侧平举",
    51: "弓步蹲",  52: "哑铃弓步", 53: "反向弓步",  54: "行走弓步",
    57: "平板支撑", 58: "单臂平板", 59: "侧平板",
    63: "引体向上", 64: "正握引体向上", 65: "反握引体向上", 67: "辅助引体向上",
    72: "俯卧撑",  73: "宽距俯卧撑", 74: "窄距俯卧撑",
    79: "划船",    80: "坐姿绳索划船", 81: "俯身划船", 84: "高位下拉",
    89: "深蹲",    90: "杠铃背蹲", 91: "史密斯深蹲", 92: "前蹲",
    93: "哑铃深蹲", 94: "相扑深蹲", 95: "箱式深蹲",
    101: "三头伸展", 102: "三头下压", 103: "法式推举",
    255: "通用动作",
}

_CATEGORY_ZH: dict[str, str] = {
    "bench_press": "卧推",        "calf_raise": "提踵",
    "cardio": "有氧",             "carry": "农夫行走",
    "core": "核心训练",           "crunch": "卷腹",
    "curl": "弯举",               "deadlift": "硬拉",
    "flye": "飞鸟",               "hip_raise": "臀桥",
    "lateral_raise": "侧平举",    "leg_curl": "腿弯举",
    "leg_raise": "腿部上抬",      "lunge": "弓步蹲",
    "olympic_lift": "奥林匹克举重", "plank": "平板支撑",
    "plyo": "爆发训练",           "pull_up": "引体向上",
    "push_up": "俯卧撑",          "row": "划船",
    "shoulder_press": "肩上推举", "shrug": "耸肩",
    "sit_up": "仰卧起坐",         "squat": "深蹲",
    "total_body": "全身训练",     "tricep_extension": "三头伸展",
    "warm_up": "热身",            "run": "跑步",
    "unknown": "未识别",
}

_INVALID_CAT = {65534, 65535, None}


def _decode_exercise_name(
    category_tuple: Any,
    subtype_tuple: Any,
    unknown2_tuple: Any,
    weight_kg: float,
    reps: int,
    set_type: str,
) -> tuple[str, str]:
    """返回 (中文名, 英文raw名)"""
    if set_type == "rest":
        return "组间休息", "rest"
    # 兜底：重量和次数都为 0 时通常是手表记录的休息段。
    # 但 set_type == "active" 时**不能**套用这个兜底 —— 平板支撑、静力保持、
    # 悬垂等计时类动作，以及手表漏计次的自重动作，同样是 weight=0 / reps=0，
    # 一旦被误判为休息就会被 workout_store 过滤掉组数、并且前端不生成编辑器，
    # 用户没有任何修正入口，只能重新导入。
    # set_type 缺失（老文件为 ""）时保持原有兜底行为。
    if set_type != "active" and weight_kg == 0.0 and reps == 0:
        return "组间休息", "rest_fallback"

    cat_list = list(category_tuple) if isinstance(category_tuple, (tuple, list)) else []
    u2_list  = list(unknown2_tuple)  if isinstance(unknown2_tuple,  (tuple, list)) else []
    sub_list = list(subtype_tuple)   if isinstance(subtype_tuple,   (tuple, list)) else []

    main_num: int | None = None
    if cat_list and cat_list[0] is not None:
        try:
            main_num = int(cat_list[0])
        except (TypeError, ValueError):
            main_num = None

    main_en = _EXERCISE_CATEGORY.get(main_num, "unknown") if main_num is not None else "unknown"

    # 同位置 unknown_2 subtype（最精准）
    u2v = None

    # 同位置 category_subtype
    sv = None
    if sv is not None and sv not in _INVALID_CAT:
        try:
            if int(sv) in _EXERCISE_SUBTYPE:
                return _EXERCISE_SUBTYPE[int(sv)], main_en
        except (TypeError, ValueError):
            pass

    return _CATEGORY_ZH.get(main_en, main_en), main_en


# ══════════════════════════════════════════════════════════════════════════════
# 三、通用工具函数
# ══════════════════════════════════════════════════════════════════════════════

def _to_utc(ts: Any) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
    return None


def _fv(d: dict, *keys: str, default: Any = None) -> Any:
    """从字典中按优先级取第一个非 None 的值"""
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return default


def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


# fitparse 的 StandardUnitsDataProcessor 会把**所有**以 `_speed` 结尾的字段
# 从 m/s 换算成 km/h（factor = 60*60/1000 = 3.6，见 fitparse/processors.py
# 的 process_field_speed）。本项目内部一律以 m/s 存储、由展示层再乘 3.6，
# 因此读取时必须先还原，否则速度会被放大 3.6 倍。
#
# 注意：`total_distance` 不受影响 —— process_field_distance 只作用于字段名
# 恰好为 `distance` 的字段，所以 total_distance 仍是米，不要一起改。
_KMH_TO_MPS = 1000.0 / 3600.0


def _speed_mps(*values: Any) -> float:
    """把 fitparse 读到的 `*_speed`（km/h）还原成 m/s。

    按顺序取第一个非零值，语义等价于原来的 `a or b` 写法。
    """
    for value in values:
        speed = _float(value)
        if speed:
            return speed * _KMH_TO_MPS
    return 0.0


def compute_hr_in_window(
    hr_records: list[HRRecord],
    start: datetime,
    end: datetime,
    margin_s: float = 2.0,
) -> tuple[int | None, int | None]:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    lo = start - timedelta(seconds=margin_s)
    hi = end   + timedelta(seconds=margin_s)
    vals = [r.heart_rate for r in hr_records if lo <= r.timestamp <= hi and r.heart_rate > 0]
    if not vals:
        return None, None
    return round(statistics.mean(vals)), max(vals)


# ══════════════════════════════════════════════════════════════════════════════
# 四、SportParser 策略基类
# ══════════════════════════════════════════════════════════════════════════════

class SportParser(ABC):
    """
    每种运动类型对应一个 SportParser 子类。
    parse() 接收从 FIT 文件中提取的原始消息列表，返回 segments。
    """

    # 子类声明自己能处理哪些 sport 值（字符串 or 整数）
    SPORT_KEYS: set[str | int] = set()
    # 子类声明自己能处理哪些 sub_sport 值。**优先于 SPORT_KEYS**——因为
    # Garmin 的 sport=training / generic 是大类（HIIT、瑜伽、普拉提、有氧训练
    # 全都用它），真正的语义在 sub_sport 上（DATA-04）。
    SUB_SPORT_KEYS: set[str] = set()

    @classmethod
    def can_handle(cls, sport_raw: Any, sub_sport_raw: Any = None) -> bool:
        """路由的唯一入口。子类可覆写以表达更复杂的归属规则。

        注意这里**只看 sport**。`SUB_SPORT_KEYS` 的匹配由 `_pick_parser` 统一
        处理，且只在 sport 缺失或只是大类时生效——否则 `sport=cycling` 配上
        `sub_sport=hiit` 会被间歇解析器抢走。
        """
        return sport_raw in cls.SPORT_KEYS or _sport_key(sport_raw) in cls.SPORT_KEYS

    @abstractmethod
    def parse(
        self,
        raw_messages: dict[str, list[dict]],
        hr_records: list[HRRecord],
        session_summary: SessionSummary,
    ) -> list[ActivitySegment]:
        ...

    def sport_name_zh(self, session_summary: SessionSummary) -> str:
        return session_summary.sport


def _sport_key(value: Any) -> str:
    """把 sport / sub_sport 归一成小写字符串键；None 与占位值统一成空串。"""
    if value is None:
        return ""
    key = str(value).strip().lower()
    return "" if key in {"none", "unknown", "invalid"} else key


# sport=training / generic 只是大类，不能据此判定解析策略（DATA-04）
BROAD_SPORT_KEYS = {"training", "generic"}

# 这些 sub_sport 在语义上就是"力量训练"，即使 sport 是大类也按 set 消息解析
STRENGTH_SUB_SPORTS = {"strength_training", "curated_workout"}


# ══════════════════════════════════════════════════════════════════════════════
# 五、各运动类型解析策略
# ══════════════════════════════════════════════════════════════════════════════

class StrengthTrainingParser(SportParser):
    """力量训练：解析 set 消息（active/rest）"""
    SPORT_KEYS = {"strength_training", "training"}
    SUB_SPORT_KEYS = set(STRENGTH_SUB_SPORTS)

    @classmethod
    def can_handle(cls, sport_raw: Any, sub_sport_raw: Any = None) -> bool:
        sport = _sport_key(sport_raw)
        sub = _sport_key(sub_sport_raw)
        if sport == "strength_training":
            return True
        if sport in BROAD_SPORT_KEYS:
            # sport=training 是大类。只有 sub_sport 明确指向力量、或压根没有
            # sub_sport（老文件/无从判断）时才按 set 解析；HIIT / 瑜伽 /
            # 有氧训练不该走这条路。
            # sport 完全缺失时不落到这里——那种情况下没有任何依据假定是力量
            # 训练，交给 FallbackParser 按 lap 解析更安全。
            return not sub or sub in STRENGTH_SUB_SPORTS
        return False

    def parse(self, raw_messages, hr_records, session_summary):
        segments: list[ActivitySegment] = []
        idx = 0
        for raw in raw_messages.get("set", []):
            start_ts = _to_utc(raw.get("start_time") or raw.get("timestamp"))
            if start_ts is None:
                continue
            duration_s = _float(raw.get("duration"))
            end_ts = start_ts + timedelta(seconds=duration_s)
            reps   = _int(raw.get("repetitions"))
            weight = _float(raw.get("weight"))
            stype  = str(raw.get("set_type") or "").lower()
            zh, en = _decode_exercise_name(
                raw.get("category", ()),
                raw.get("category_subtype", ()),
                raw.get("unknown_2", ()),
                weight, reps, stype,
            )
            is_rest = (zh == "组间休息")
            avg_hr, max_hr = None, None
            if not is_rest and hr_records:
                avg_hr, max_hr = compute_hr_in_window(hr_records, start_ts, end_ts)
            idx += 1
            segments.append(ActivitySegment(
                index=idx,
                segment_type="set_rest" if is_rest else "set_active",
                start_time=start_ts,
                end_time=end_ts,
                duration_s=duration_s,
                category=zh,
                category_raw=en,
                repetitions=reps,
                weight_kg=weight,
                is_rest=is_rest,
                avg_hr=avg_hr,
                max_hr=max_hr,
                extra={
                    "category_source": "unidentified" if en == "unknown" else "device_category",
                    "category_device_raw": raw.get("category"),
                    "category_subtype_raw": raw.get("category_subtype"),
                    "unknown_2_raw": raw.get("unknown_2"),
                },
            ))
        if not segments:
            # DATA-04：没有可用的 set 消息时降级到 lap 解析，绝不返回空。
            # 原实现直接 return []，于是 sport=training 的有氧/HIIT/瑜伽活动
            # 的 lap 与心率被整段丢弃，用户只看到"未找到任何训练组数据"，
            # 且这一段数据再也拿不回来（原始 FIT 通常已不在磁盘上）。
            return LapBasedParser().parse(raw_messages, hr_records, session_summary)
        return segments


class LapBasedParser(SportParser):
    """
    基于 lap 的有氧运动解析器（骑行、跑步、游泳…）
    每个 lap 成为一个 ActivitySegment。
    """
    SPORT_KEYS = {"cycling", "running", "swimming", "walking", "hiking",
                  "transition", "fitness_equipment"}
    # sport=training 的大部分活动其实是这些（DATA-04）
    SUB_SPORT_KEYS = {
        "cardio_training", "yoga", "pilates", "breathing", "meditation",
        "flexibility_training", "stretching", "warm_up", "cool_down",
        "treadmill", "indoor_running", "track", "trail", "street",
        "indoor_cycling", "spin", "virtual_activity", "elliptical",
        "stair_climbing", "indoor_rowing", "rowing", "indoor_walking",
        "open_water", "lap_swimming",
    }

    def parse(self, raw_messages, hr_records, session_summary):
        segments: list[ActivitySegment] = []
        laps = raw_messages.get("lap", [])
        if not laps:
            # 无 lap 消息，用整段 record 流构建一个虚拟段
            return self._from_session(session_summary, hr_records)

        for i, lap in enumerate(laps):
            start_ts = _to_utc(lap.get("start_time"))
            end_ts = _to_utc(lap.get("timestamp"))
            elapsed = _float(lap.get("total_elapsed_time") or lap.get("total_timer_time"))
            if start_ts is None and end_ts is not None and elapsed > 0:
                start_ts = end_ts - timedelta(seconds=elapsed)
            if end_ts is None and start_ts is not None and elapsed > 0:
                end_ts = start_ts + timedelta(seconds=elapsed)
            if start_ts is None or end_ts is None:
                continue

            avg_hr = _int(lap.get("avg_heart_rate")) or None
            max_hr = _int(lap.get("max_heart_rate")) or None
            if hr_records and (avg_hr is None or max_hr is None):
                computed_avg, computed_max = compute_hr_in_window(
                    hr_records, start_ts, end_ts
                )
                if avg_hr is None:
                    avg_hr = computed_avg
                if max_hr is None:
                    max_hr = computed_max

            dist = _float(lap.get("total_distance"))
            avg_spd = _speed_mps(lap.get("enhanced_avg_speed"), lap.get("avg_speed"))
            max_spd = _speed_mps(lap.get("enhanced_max_speed"), lap.get("max_speed"))

            segments.append(ActivitySegment(
                index=i + 1,
                segment_type="lap",
                start_time=start_ts,
                end_time=end_ts,
                duration_s=elapsed or max(0.0, (end_ts - start_ts).total_seconds()),
                distance_m=dist,
                avg_speed_mps=avg_spd,
                max_speed_mps=max_spd,
                avg_cadence=_int(lap.get("avg_running_cadence") or lap.get("avg_cadence")),
                avg_power_w=_int(lap.get("avg_power")),
                calories=_int(lap.get("total_calories")),
                lap_trigger=str(lap.get("lap_trigger") or ""),
                avg_hr=avg_hr,
                max_hr=max_hr,
            ))
        return segments

    def _from_session(self, s: SessionSummary, hr_records: list[HRRecord]) -> list[ActivitySegment]:
        start, end, source = s.start_time, None, "session"
        if start is not None:
            end = start + timedelta(seconds=s.total_elapsed_s)
        elif hr_records:
            # BUG-10：没有 session 消息时原实现直接 `return []`，把整条心率流
            # 连同这次活动一起丢掉。但 record 流本身就带着时间窗——中断的活动
            # 往往正是"有 record、没写出 session"的形状，这时手上明明有数据。
            start, end = hr_records[0].timestamp, hr_records[-1].timestamp
            source = "records"
        if start is None or end is None:
            return []
        duration = (end - start).total_seconds() or s.total_elapsed_s
        avg_hr, max_hr = None, None
        if hr_records:
            avg_hr, max_hr = compute_hr_in_window(hr_records, start, end, margin_s=10)
        return [ActivitySegment(
            index=1,
            segment_type="lap",
            start_time=start,
            end_time=end,
            duration_s=duration,
            distance_m=s.total_distance_m,
            avg_speed_mps=s.avg_speed_mps,
            avg_cadence=s.avg_cadence,
            avg_power_w=s.avg_power_w,
            calories=s.total_calories,
            lap_trigger=source,
            avg_hr=avg_hr or s.avg_hr,
            max_hr=max_hr or s.max_hr,
        )]


class IntervalSportParser(SportParser):
    """
    间歇型运动（跳绳、HIIT…）：每个 lap 是一轮间歇
    sport 可以是任意整数（Garmin 自定义）或间歇类 sub_sport
    """
    SPORT_KEYS: set[str | int] = {"hiit"}
    SUB_SPORT_KEYS = {
        "hiit", "interval_training", "amrap", "emom", "tabata",
        "circuit_training", "functional_training", "jump_rope",
        "high_intensity_interval_training",
    }

    @classmethod
    def can_handle(cls, sport_raw: Any, sub_sport_raw: Any = None) -> bool:
        """整数 sport 值（自定义运动）或间歇类 sub_sport 视为间歇型。

        这个方法以前是死代码——`_pick_parser` 从不调用它，而是在函数末尾
        自己又写了一遍整数判断（DATA-04 附带项）。现在路由统一走 can_handle。
        """
        if super().can_handle(sport_raw, sub_sport_raw):
            return True
        if isinstance(sport_raw, bool):
            return False
        if isinstance(sport_raw, int):
            return True
        return _sport_key(sport_raw).isdigit()

    def parse(self, raw_messages, hr_records, session_summary):
        # 直接复用 LapBasedParser 的逻辑
        return LapBasedParser().parse(raw_messages, hr_records, session_summary)


class FallbackParser(SportParser):
    """兜底：按**消息证据**依次尝试 set → lap → session 整段。

    BUG-10：原实现直接走 lap 解析，于是"有 set 消息但 sport 缺失"的文件
    （中断的活动、session 消息未写出的文件）会一路落到 `_from_session()`，
    而那里因 `session.start_time is None` 返回 `[]`——**整场训练被静默丢光**，
    用户看到的却是一句"[FIT 解析完成]"。

    走到这里就意味着 sport 没能给出裁决，那就该问文件里到底有什么，而不是
    假定它是有氧。set 消息的存在本身就是"这是力量训练"的确凿证据。
    """
    SPORT_KEYS: set[str | int] = set()

    @classmethod
    def can_handle(cls, sport_raw: Any, sub_sport_raw: Any = None) -> bool:
        return True

    def parse(self, raw_messages, hr_records, session_summary):
        if raw_messages.get("set"):
            return StrengthTrainingParser().parse(raw_messages, hr_records, session_summary)
        return LapBasedParser().parse(raw_messages, hr_records, session_summary)


# ══════════════════════════════════════════════════════════════════════════════
# 六、SportParser 注册表
# ══════════════════════════════════════════════════════════════════════════════

# 顺序即优先级：越具体的解析器越靠前，FallbackParser 必须最后（它 can_handle 恒真）
_REGISTERED_PARSERS: list[SportParser] = [
    StrengthTrainingParser(),
    IntervalSportParser(),
    LapBasedParser(),
    FallbackParser(),
]


def _pick_parser(sport_raw: Any, sub_sport_raw: Any = None) -> SportParser:
    """根据 session.sport 与 sub_sport 选择合适的解析器。

    DATA-04：sub_sport 必须参与路由。Garmin 的 `sport=training(10)` 是大类，
    HIIT、瑜伽、普拉提、有氧训练全都用它，只靠 sub_sport 区分；原实现只看
    sport，把它们统统交给 StrengthTrainingParser，而后者只读 set 消息。
    """
    sport = _sport_key(sport_raw)
    sub = _sport_key(sub_sport_raw)
    # sub_sport 只在 sport 缺失或只是大类时才有裁决权——sport 已经写明
    # cycling / strength_training 之类的具体值时，不该被 sub_sport 推翻。
    if sub and (not sport or sport in BROAD_SPORT_KEYS):
        for parser in _REGISTERED_PARSERS:
            if sub in parser.SUB_SPORT_KEYS:
                return parser
    for parser in _REGISTERED_PARSERS:
        if parser.can_handle(sport_raw, sub_sport_raw):
            return parser
    return FallbackParser()


# ══════════════════════════════════════════════════════════════════════════════
# 七、运动名称中文化
# ══════════════════════════════════════════════════════════════════════════════

# Garmin FIT sport 枚举 → 中文
_SPORT_ZH: dict[str, str] = {
    "generic":              "通用运动",
    "running":              "跑步",
    "cycling":              "骑行",
    "transition":           "转换",
    "fitness_equipment":    "健身器械",
    "swimming":             "游泳",
    "basketball":           "篮球",
    "soccer":               "足球",
    "tennis":               "网球",
    "american_football":    "美式橄榄球",
    "training":             "训练",
    "walking":              "步行",
    "cross_country_skiing": "越野滑雪",
    "alpine_skiing":        "高山滑雪",
    "snowboarding":         "单板滑雪",
    "rowing":               "划船",
    "mountaineering":       "登山",
    "hiking":               "徒步",
    "multisport":           "多运动",
    "paddling":             "划桨",
    "flying":               "飞行",
    "e_biking":             "电动车骑行",
    "motorcycling":         "摩托",
    "boating":              "划船",
    "driving":              "驾车",
    "golf":                 "高尔夫",
    "hang_gliding":         "悬挂式滑翔",
    "horseback_riding":     "骑马",
    "hunting":              "打猎",
    "fishing":              "钓鱼",
    "inline_skating":       "轮滑",
    "rock_climbing":        "攀岩",
    "sailing":              "帆船",
    "ice_skating":          "溜冰",
    "sky_diving":           "跳伞",
    "snowshoeing":          "雪鞋",
    "snowmobiling":         "雪地摩托",
    "stand_up_paddleboarding": "站立划桨",
    "surfing":              "冲浪",
    "wakeboarding":         "尾流板",
    "water_skiing":         "水上滑雪",
    "kayaking":             "皮划艇",
    "rafting":              "漂流",
    "windsurfing":          "风帆冲浪",
    "kitesurfing":          "风筝冲浪",
    "tactical":             "战术",
    "jumpmaster":           "跳伞主",
    "boxing":               "拳击",
    "floor_climbing":       "楼梯攀登",
    "baseball":             "棒球",
    "diving":               "潜水",
    "hiit":                 "高强度间歇",
    "racket":               "球拍运动",
    "wheelchair_push_walk": "轮椅步行",
    "wheelchair_push_run":  "轮椅跑步",
    "strength_training":    "力量训练",
    "cardio_training":      "有氧训练",
    "yoga":                 "瑜伽",
    "pilates":              "普拉提",
    "meditation":           "冥想",
}


def _sport_to_zh(sport_raw: Any, sport_name_from_file: str = "", sub_sport_raw: Any = None) -> str:
    """
    将 sport 字段（字符串枚举或整数）转成中文。
    优先使用 FIT 文件里的 sport.name 字段（用户自定义名称最准确）。
    """
    if sport_name_from_file:
        return sport_name_from_file
    if sport_raw is None:
        return "未知运动"
    key = _sport_key(sport_raw)
    # DATA-04：sport=training/generic 只是大类，单看它只能得到"训练"这种
    # 没有信息量的名字。sub_sport 能说清是有氧/HIIT/瑜伽时就用它。
    if key in BROAD_SPORT_KEYS:
        sub_key = _sport_key(sub_sport_raw)
        if sub_key in _SPORT_ZH:
            return _SPORT_ZH[sub_key]
    if key in _SPORT_ZH:
        return _SPORT_ZH[key]
    # 整数型：Garmin 未在 SDK 枚举中定义的自定义运动
    return f"自定义运动({sport_raw})"


def _in_window(item: dict, start: datetime | None, end: datetime | None) -> bool:
    """
    判断一条原始消息（lap / set / record）是否属于时间窗 `[start, end)`。

    契约（DATA-34 与 BUG-10 是同一类教训，改动前务必先读）：
    - `start is None` 表示**不过滤**，无条件收下。子会话缺 `start_time`
      是中断活动最常见的形状，这时若判为窗外，它的 lap 与 set 会被一条不剩
      地丢光——原缺陷正是把这一支写成了恒 False。
    - `end is None` 表示右边界开放（最后一个子会话且推不出结束时间），
      只要不早于 `start` 就收下。
    - 消息自身取不到时间戳时算窗外；只有在不过滤的情况下才会被收下。
    """
    if start is None:
        return True
    timestamp = _to_utc(item.get("start_time") or item.get("timestamp"))
    if timestamp is None or timestamp < start:
        return False
    return end is None or timestamp < end


def _parse_multisport(
    raw_msgs: dict[str, list[dict]],
    hr_records: list[HRRecord],
    summaries: list[SessionSummary],
) -> tuple[SessionSummary, list[ActivitySegment], str]:
    """Assign raw messages once and aggregate all child session summaries."""
    ordered = sorted(
        summaries,
        key=lambda item: item.start_time or datetime.max.replace(tzinfo=timezone.utc),
    )
    segments: list[ActivitySegment] = []
    claimed: dict[str, set[int]] = {"record": set(), "lap": set(), "set": set()}

    for pos, summary in enumerate(ordered):
        start_bound = summary.start_time
        next_start = ordered[pos + 1].start_time if pos + 1 < len(ordered) else None
        end_bound = next_start
        if end_bound is None and start_bound and summary.total_elapsed_s > 0:
            end_bound = start_bound + timedelta(seconds=summary.total_elapsed_s)

        local = dict(raw_msgs)
        for kind in claimed:
            selected: list[dict] = []
            for index, item in enumerate(raw_msgs.get(kind, [])):
                if index in claimed[kind]:
                    continue
                if _in_window(item, start_bound, end_bound):
                    selected.append(item)
                    claimed[kind].add(index)
            local[kind] = selected

        local_segments = _pick_parser(summary.sport_raw, summary.sub_sport).parse(
            local, hr_records, summary
        )
        for segment in local_segments:
            segment.extra.update({
                "sport": summary.sport,
                "sport_raw": summary.sport_raw,
                "sub_sport": summary.sub_sport,
            })
        segments.extend(local_segments)

    segments.sort(key=lambda item: item.start_time)
    for index, segment in enumerate(segments, start=1):
        segment.index = index

    def weighted(field: str) -> float:
        weighted_total = sum(
            float(getattr(item, field) or 0) * max(item.total_elapsed_s, 0)
            for item in ordered
        )
        duration = sum(
            max(item.total_elapsed_s, 0)
            for item in ordered
            if getattr(item, field)
        )
        return weighted_total / duration if duration else 0.0

    sport_names = list(dict.fromkeys(item.sport for item in ordered if item.sport))
    session = SessionSummary(
        sport="多运动（" + "+".join(sport_names) + "）",
        sport_raw="multisport",
        start_time=min(
            (item.start_time for item in ordered if item.start_time), default=None
        ),
        total_elapsed_s=sum(item.total_elapsed_s for item in ordered),
        total_timer_s=sum(item.total_timer_s for item in ordered),
        total_distance_m=sum(item.total_distance_m for item in ordered),
        total_calories=sum(item.total_calories for item in ordered),
        avg_hr=round(weighted("avg_hr")) or None,
        max_hr=max((item.max_hr or 0 for item in ordered), default=0) or None,
        avg_speed_mps=weighted("avg_speed_mps"),
        max_speed_mps=max((item.max_speed_mps or 0 for item in ordered), default=0),
        avg_cadence=round(weighted("avg_cadence")),
        total_ascent_m=sum(item.total_ascent_m for item in ordered),
        total_descent_m=sum(item.total_descent_m for item in ordered),
        avg_power_w=round(weighted("avg_power_w")),
        training_effect=max(
            (item.training_effect or 0 for item in ordered), default=0
        ),
        anaerobic_effect=max(
            (item.anaerobic_effect or 0 for item in ordered), default=0
        ),
    )

    unassigned = {
        kind: len(raw_msgs.get(kind, [])) - len(indices)
        for kind, indices in claimed.items()
        if len(raw_msgs.get(kind, [])) > len(indices)
    }
    notes: list[str] = []
    if unassigned:
        detail = "、".join(f"{kind} {count} 条" for kind, count in unassigned.items())
        notes.append(f"多运动中有未能归属到子会话的数据：{detail}")
    missing_start_count = sum(item.start_time is None for item in ordered)
    if missing_start_count > 1:
        notes.append(
            f"有 {missing_start_count} 个子会话缺少开始时间，未定时数据只能归入首个缺失时间的会话"
        )
    return session, segments, "；".join(notes)


# ══════════════════════════════════════════════════════════════════════════════
# 八、主解析函数
# ══════════════════════════════════════════════════════════════════════════════

def parse_fit_file(path: str | Path) -> ParsedActivity:
    """
    解析任意 Garmin .fit 文件。

    1. 遍历所有消息，按类型归类
    2. 从 sport/session 消息确定运动类型
    3. 路由到对应的 SportParser
    4. 返回统一的 ParsedActivity
    """
    path = Path(path)
    ff = fitparse.FitFile(
        str(path),
        data_processor=fitparse.StandardUnitsDataProcessor(),
    )

    # 按消息类型收集原始数据
    raw_msgs: dict[str, list[dict]] = defaultdict(list)
    hr_records: list[HRRecord] = []

    for msg in ff.get_messages():
        d = {f.name: f.value for f in msg.fields}
        raw_msgs[msg.name].append(d)

        if msg.name == "record":
            ts = _to_utc(d.get("timestamp"))
            hr = d.get("heart_rate")
            if ts is not None and hr is not None:
                try:
                    hr_records.append(HRRecord(timestamp=ts, heart_rate=int(hr)))
                except (TypeError, ValueError):
                    pass

    hr_records.sort(key=lambda r: r.timestamp)

    # 解析 sport 消息（获取用户自定义名称）
    sport_name_from_file = ""
    sport_raw: Any = None
    sub_sport_raw: Any = None
    for s in raw_msgs.get("sport", []):
        sport_name_from_file = str(s.get("name") or "").strip()
        sport_raw = s.get("sport")
        sub_sport_raw = s.get("sub_sport")
        break

    session_dicts = raw_msgs.get("session", []) or [{}]

    def build_session(data: dict, sport_value: Any, sub_value: Any) -> SessionSummary:
        return SessionSummary(
            sport=_sport_to_zh(sport_value, sport_name_from_file, sub_value),
            sport_raw=str(sport_value) if sport_value is not None else "unknown",
            sub_sport=str(sub_value) if sub_value is not None else "",
            start_time=_to_utc(data.get("start_time") or data.get("timestamp")),
            total_elapsed_s=_float(data.get("total_elapsed_time")),
            total_timer_s=_float(data.get("total_timer_time")),
            total_distance_m=_float(data.get("total_distance")),
            total_calories=_int(data.get("total_calories")),
            avg_hr=_int(data.get("avg_heart_rate")) or None,
            max_hr=_int(data.get("max_heart_rate")) or None,
            avg_speed_mps=_speed_mps(data.get("enhanced_avg_speed"), data.get("avg_speed")),
            max_speed_mps=_speed_mps(data.get("enhanced_max_speed"), data.get("max_speed")),
            avg_cadence=_int(data.get("avg_running_cadence") or data.get("avg_cadence")),
            total_ascent_m=_float(data.get("total_ascent")),
            total_descent_m=_float(data.get("total_descent")),
            avg_power_w=_int(data.get("avg_power")),
            training_effect=_float(data.get("total_training_effect")),
            anaerobic_effect=_float(data.get("total_anaerobic_training_effect")),
        )

    first = session_dicts[0]
    if sport_raw is None:
        sport_raw = first.get("sport")
    if sub_sport_raw is None:
        sub_sport_raw = first.get("sub_sport")
    session = build_session(first, sport_raw, sub_sport_raw)

    note = ""
    if len(session_dicts) > 1:
        summaries = [
            build_session(
                item,
                item.get("sport", sport_raw),
                item.get("sub_sport", sub_sport_raw),
            )
            for item in session_dicts
        ]
        session, segments, note = _parse_multisport(raw_msgs, hr_records, summaries)
    else:
        segments = _pick_parser(sport_raw, sub_sport_raw).parse(dict(raw_msgs), hr_records, session)

    return ParsedActivity(
        session=session,
        segments=segments,
        hr_records=hr_records,
        source_file=path.name,
        parsed_at=datetime.now(timezone.utc).isoformat(),
        note=note,
    )
