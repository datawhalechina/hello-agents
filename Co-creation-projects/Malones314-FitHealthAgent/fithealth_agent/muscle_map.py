"""Training-action to muscle mapping used by the recovery planner.

The deterministic rules in this module are deliberately conservative.  They
operate on the saved/displayed action name (which may be user edited) and do
not access a store.  An optional Lite-model fallback is available for action
names that the local rules cannot identify; the fallback is strictly
validated and can never replace a local match.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Iterable
from threading import RLock


REGION_LEXICON: dict[str, tuple[tuple[str, str], ...]] = {
    "胸部": (("胸部", "primary"),), "胸": (("胸部", "primary"),),
    "背部": (("背部", "primary"),), "背": (("背部", "primary"),),
    "后背": (("背部", "primary"),),
    "腿部": (("腿部", "primary"),), "腿": (("腿部", "primary"),),
    "下肢": (("腿部", "primary"),),
    "肩部": (("肩部", "primary"),), "肩膀": (("肩部", "primary"),),
    "肩": (("肩部", "primary"),),
    "手臂": (("手臂", "primary"),), "胳膊": (("手臂", "primary"),),
    "上臂": (("手臂", "primary"),), "前臂": (("手臂", "primary"),),
    "核心": (("核心", "primary"),), "腹部": (("核心", "primary"),),
    "腹": (("核心", "primary"),),
    "腰": (("核心", "primary"), ("背部", "secondary")),
    "腰部": (("核心", "primary"), ("背部", "secondary")),
    "下背": (("核心", "primary"), ("背部", "secondary")),
    "后腰": (("核心", "primary"), ("背部", "secondary")),
    "腰椎": (("核心", "primary"), ("背部", "secondary")),
    "颈部": (("颈部", "primary"), ("背部", "secondary")),
    "脖子": (("颈部", "primary"), ("背部", "secondary")),
    "颈椎": (("颈部", "primary"), ("背部", "secondary")),
    "后颈": (("颈部", "primary"), ("背部", "secondary")),
    "颈项": (("颈部", "primary"), ("背部", "secondary")),
    "落枕": (("颈部", "primary"), ("背部", "secondary")),
    "髋部": (("髋部", "primary"), ("腿部", "secondary")),
    "髋关节": (("髋部", "primary"), ("腿部", "secondary")),
    "胯部": (("髋部", "primary"), ("腿部", "secondary")),
    "胯": (("髋部", "primary"), ("腿部", "secondary")),
    "臀部": (("臀部", "primary"), ("腿部", "secondary")),
    "臀肌": (("臀部", "primary"), ("腿部", "secondary")),
    "屁股": (("臀部", "primary"), ("腿部", "secondary")),
    "肘部": (("肘部", "primary"), ("手臂", "secondary")),
    "肘关节": (("肘部", "primary"), ("手臂", "secondary")),
    "手肘": (("肘部", "primary"), ("手臂", "secondary")),
    "胳膊肘": (("肘部", "primary"), ("手臂", "secondary")),
    "手腕": (("手腕", "primary"), ("手臂", "secondary")),
    "腕部": (("手腕", "primary"), ("手臂", "secondary")),
    "腕关节": (("手腕", "primary"), ("手臂", "secondary")),
    "手部": (("手部", "primary"), ("手臂", "secondary")),
    "手掌": (("手部", "primary"), ("手臂", "secondary")),
    "手指": (("手部", "primary"), ("手臂", "secondary")),
    "膝部": (("膝部", "primary"), ("腿部", "secondary")),
    "膝盖": (("膝部", "primary"), ("腿部", "secondary")),
    "膝关节": (("膝部", "primary"), ("腿部", "secondary")),
    "脚踝": (("脚踝", "primary"), ("腿部", "secondary")),
    "踝部": (("脚踝", "primary"), ("腿部", "secondary")),
    "踝关节": (("脚踝", "primary"), ("腿部", "secondary")),
    "足部": (("足部", "primary"), ("腿部", "secondary")),
    "脚掌": (("足部", "primary"), ("腿部", "secondary")),
    "脚背": (("足部", "primary"), ("腿部", "secondary")),
    "脚趾": (("足部", "primary"), ("腿部", "secondary")),
    "头部": (("头部", "primary"),), "头顶": (("头部", "primary"),),
    "后脑": (("头部", "primary"),), "额头": (("头部", "primary"),),
}

REGIONS = frozenset(
    region for mappings in REGION_LEXICON.values() for region, _role in mappings
)
ROLES = frozenset({"primary", "secondary"})


# ── 肌群元数据（BUG-26 问题 3）────────────────────────────────────────────────
#
# 每个 `muscle_id` 的中文名与所属区域**只在这里定义一次**。原先它们写在每一条
# `MuscleRule` 上，同一个 id 可以有多条规则，于是同一块肌肉会因为命中的是哪条规则
# 而拿到不同的名字和角色：`calves` 在"提踵"下叫"小腿"、在"跑步"下叫"小腿肌群"，
# `hamstrings` 在"硬拉"下叫"股二头肌"、在"深蹲"下叫"腘绳肌"。更糟的是
# `_RULES_BY_ID` 用 dict 推导建表、同 id **后写覆盖**，而 `calves`/`hamstrings`
# 的最后一条恰好是 `role="secondary"`，于是 `muscles_for_sport("跳绳")` 返回的小腿
# 是次要、权重 0.4——与文档 §2.3 的意图正好相反。
#
# 规则表现在只管"什么关键词命中什么 id、以什么角色命中"，名字和区域一律来自这里。
MUSCLE_META: dict[str, tuple[str, str]] = {
    # muscle_id: (中文名, 区域)
    "chest": ("胸大肌", "胸部"),
    "upper_chest": ("胸大肌上束", "胸部"),
    "lower_chest": ("胸大肌下束", "胸部"),
    "serratus_anterior": ("前锯肌", "胸部"),
    "latissimus": ("背阔肌", "背部"),
    "rhomboids": ("斜方肌·菱形肌", "背部"),
    "erector_spinae": ("竖脊肌", "背部"),
    "trapezius": ("斜方肌", "背部"),
    "trapezius_upper": ("斜方肌上束", "背部"),
    "front_deltoid": ("三角肌前束", "肩部"),
    "lateral_deltoid": ("三角肌中束", "肩部"),
    "rear_deltoid": ("三角肌后束", "肩部"),
    "biceps": ("肱二头肌", "手臂"),
    "triceps": ("肱三头肌", "手臂"),
    "brachioradialis": ("肱桡肌", "手臂"),
    "forearms": ("小臂肌群", "手臂"),
    "quadriceps": ("股四头肌", "腿部"),
    # 取解剖学上覆盖整组的名字，与 id 一致；旧规则表里"股二头肌"只是其中一条肌腹
    "hamstrings": ("腘绳肌", "腿部"),
    "gluteus_maximus": ("臀大肌", "腿部"),
    "calves": ("小腿", "腿部"),
    "adductors": ("大腿内收肌", "腿部"),
    "abductors": ("大腿外展肌", "腿部"),
    "core": ("核心", "核心"),
    "obliques": ("腹内外斜肌", "核心"),
}

_unknown_meta_regions = {
    region for _zh, region in MUSCLE_META.values() if region not in REGIONS
}
if _unknown_meta_regions:  # pragma: no cover - 建表期不变量
    raise ValueError(f"MUSCLE_META 引用了未知区域：{sorted(_unknown_meta_regions)}")


def regions_for_text(text: str, *, include_secondary: bool) -> set[str]:
    normalized = re.sub(r"\s+", "", str(text or "")).casefold()
    roles = ROLES if include_secondary else {"primary"}
    return {
        region
        for term, mappings in REGION_LEXICON.items()
        if term.casefold() in normalized
        for region, role in mappings
        if role in roles
    }


REGION_ALIASES = MappingProxyType({
    region: tuple(dict.fromkeys(
        term
        for term, mappings in REGION_LEXICON.items()
        if (region, "primary") in mappings
    ))
    for region in REGIONS
})


MUSCLE_DETAIL_LEXICON: dict[str, tuple[str, ...]] = {
    "大腿内侧": ("adductors",),
    "大腿内收肌": ("adductors",),
    "内收肌": ("adductors",),
}


def muscle_ids_for_region(region: str) -> tuple[str, ...]:
    """区域 → 该区域全部肌群 id。真值来自 `MUSCLE_META`，不再扫规则表。"""

    return tuple(
        muscle_id
        for muscle_id, (_zh, meta_region) in MUSCLE_META.items()
        if meta_region == region
    )


def muscle_ids_for_text(region: str, text: str) -> tuple[str, ...]:
    """Return explicitly named muscles, falling back to the whole region."""

    all_region_ids = muscle_ids_for_region(region)
    region_ids = set(all_region_ids)
    normalized = re.sub(r"\s+", "", str(text or ""))
    detailed = tuple(dict.fromkeys(
        muscle_id
        for term, muscle_ids in MUSCLE_DETAIL_LEXICON.items()
        if term in normalized
        for muscle_id in muscle_ids
        if muscle_id in region_ids
    ))
    return detailed or all_region_ids


@dataclass(frozen=True)
class MuscleRule:
    """一条"关键词 → 肌群 id + 角色"的规则。

    **不带中文名和区域**——那两项是 `MUSCLE_META` 的职责（BUG-26 问题 3）。
    `zh` / `region` 保留为属性，这样既保证同一个 id 在任何规则下名字都一样，
    又不用改动既有调用方。
    """

    muscle_id: str
    keywords: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    role: str = "primary"

    def __post_init__(self) -> None:
        if self.muscle_id not in MUSCLE_META:
            raise ValueError(f"unknown muscle id: {self.muscle_id}")
        if self.role not in ROLES:
            raise ValueError(f"unknown muscle role: {self.role}")
        if not self.keywords:
            raise ValueError("a muscle rule needs at least one keyword")

    @property
    def zh(self) -> str:
        return MUSCLE_META[self.muscle_id][0]

    @property
    def region(self) -> str:
        return MUSCLE_META[self.muscle_id][1]


@dataclass(frozen=True)
class MuscleHit:
    muscle_id: str
    zh: str
    region: str
    role: str = "primary"
    weight: float = 1.0

    @classmethod
    def for_muscle(cls, muscle_id: str, role: str = "primary") -> "MuscleHit":
        """按 id 直接造一条命中；名字/区域/权重全部由元数据与角色决定。"""

        zh, region = MUSCLE_META[muscle_id]
        return cls(
            muscle_id=muscle_id,
            zh=zh,
            region=region,
            role=role,
            weight=1.0 if role == "primary" else 0.4,
        )

    @classmethod
    def from_rule(cls, rule: MuscleRule) -> "MuscleHit":
        return cls.for_muscle(rule.muscle_id, rule.role)


# Keep the ids stable: recovery snapshots and future plans refer to these ids.
# 只写"关键词 → id + 角色"；中文名与区域见 `MUSCLE_META`。
MUSCLE_RULES: tuple[MuscleRule, ...] = (
    MuscleRule("chest", ("平板卧推", "卧推", "上斜卧推", "下斜卧推", "飞鸟", "俯卧撑")),
    MuscleRule("triceps", ("臂屈伸", "三头伸展", "三头下压", "法式推举")),
    MuscleRule("triceps", ("卧推", "俯卧撑", "肩上推举", "肩推"), role="secondary"),
    MuscleRule("latissimus", ("划船", "下拉", "引体向上")),
    MuscleRule("rhomboids", ("划船", "引体向上"), role="secondary"),
    MuscleRule("biceps", ("弯举", "二头")),
    MuscleRule("biceps", ("划船", "下拉", "引体向上"), role="secondary"),
    MuscleRule("front_deltoid", ("肩上推举", "肩推", "前平举")),
    MuscleRule("lateral_deltoid", ("侧平举",)),
    MuscleRule("rear_deltoid", ("反向飞鸟", "俯身飞鸟")),
    MuscleRule("quadriceps", ("深蹲", "弓步", "腿举")),
    MuscleRule("gluteus_maximus", ("臀桥", "臀推", "髋推")),
    MuscleRule("gluteus_maximus", ("深蹲", "弓步"), role="secondary"),
    MuscleRule("hamstrings", ("罗马尼亚硬拉", "硬拉", "腿弯举")),
    MuscleRule("erector_spinae", ("罗马尼亚硬拉", "硬拉")),
    MuscleRule("calves", ("提踵", "小腿")),
    MuscleRule("core", ("卷腹", "仰卧起坐", "平板支撑", "核心"), exclude=("卧推", "推举")),
    # === 胸部与肩部补充 ===
    MuscleRule("upper_chest", ("上斜卧推", "低位夹胸", "上斜飞鸟")),
    MuscleRule("lower_chest", ("双杠臂屈伸", "下斜卧推", "高位夹胸")),
    MuscleRule("front_deltoid", ("平板卧推", "上斜卧推", "俯卧撑", "双杠臂屈伸"), role="secondary"),
    MuscleRule("serratus_anterior", ("哑铃直臂上拉", "前锯肌推举", "健腹轮")),

    # === 背部与核心补充 ===
    MuscleRule("trapezius_upper", ("耸肩", "农夫行走")),
    MuscleRule("trapezius", ("侧平举", "肩上推举", "硬拉"), role="secondary"),
    MuscleRule("erector_spinae", ("山羊挺身", "背屈伸", "早安式屈体")),  # 竖脊肌作为主要发力
    MuscleRule("obliques", ("俄罗斯转体", "侧卷腹", "伐木", "侧平板支撑")),

    # === 手臂补充 ===
    MuscleRule("brachioradialis", ("锤式弯举", "反握弯举")),
    MuscleRule("forearms", ("腕弯举", "农夫行走", "悬垂")),
    MuscleRule("forearms", ("硬拉", "划船", "引体向上"), role="secondary"),
    MuscleRule("triceps", ("双杠臂屈伸", "窄距卧推")),

    # === 腿部与臀部补充 ===
    MuscleRule("gluteus_maximus", ("臀推", "臀桥", "后踢腿")),  # 臀大肌作为主要发力
    MuscleRule("adductors", ("坐姿夹腿", "相扑硬拉", "宽距深蹲")),
    MuscleRule("abductors", ("坐姿分腿", "蚌式开合", "侧卧抬腿")),
    MuscleRule("hamstrings", ("深蹲", "腿举", "弓步"), role="secondary"),
    MuscleRule("calves", ("跑步", "跳绳", "深蹲"), role="secondary"),
)


TRAINING_SUBJECT_RULES: dict[str, tuple[str, ...]] = {
    region: tuple(dict.fromkeys((region, region.removesuffix("部"), *(
        keyword
        for rule in MUSCLE_RULES
        if rule.region == region and rule.role == "primary"
        for keyword in rule.keywords
    ))))
    for region in sorted({rule.region for rule in MUSCLE_RULES})
}


# Rules are checked longest-first and then in declaration order.  This makes
# "罗马尼亚硬拉" win over the more general "硬拉" rule and prevents a short
# word such as "平板" from becoming a false core hit.
#
# BUG-26 问题 3：这里**不再**建 `id -> rule` 的表。原先那张表用 dict 推导、同 id
# 后写覆盖，而 `calves`/`hamstrings`/`forearms`/`front_deltoid` 的最后一条恰好是
# secondary，于是"按 id 取一条代表规则"这个动作会静默降级它们的角色。需要按 id
# 拿名字/区域的地方一律走 `MUSCLE_META`，需要角色的地方由调用方显式给出。
_SORTED_RULES = tuple(
    sorted(enumerate(MUSCLE_RULES), key=lambda item: (-max(map(len, item[1].keywords)), item[0]))
)


SPORT_RULES: dict[str, tuple[str, ...]] = {
    "跳绳": ("calves", "quadriceps"),
    "跑步": ("quadriceps", "hamstrings", "calves"),
    "骑行": ("quadriceps",),
    "有氧运动": (),
    "有氧": (),
}


def _normalise(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _rule_matches(rule: MuscleRule, text: str) -> bool:
    return any(_normalise(keyword) in text for keyword in rule.keywords) and not any(
        _normalise(word) in text for word in rule.exclude
    )


def muscles_for_exercise(name: str) -> list[MuscleHit]:
    """Return deterministic local hits for one saved action name.

    A rule with the same muscle id is emitted once; if a primary rule and a
    secondary rule both match, the primary role wins.
    """

    text = _normalise(name)
    if not text:
        return []
    selected: dict[str, MuscleHit] = {}
    for _, rule in _SORTED_RULES:
        if not _rule_matches(rule, text):
            continue
        hit = MuscleHit.from_rule(rule)
        previous = selected.get(hit.muscle_id)
        if previous is None or (previous.role == "secondary" and hit.role == "primary"):
            selected[hit.muscle_id] = hit
    return sorted(selected.values(), key=lambda hit: (hit.role != "primary", hit.muscle_id))


def muscles_for_sport(sport: str) -> list[MuscleHit]:
    """Return sport-level fallback hits; unknown/general aerobic sports return [].

    BUG-26 问题 3：运动项目展开出来的肌群**一律按主项计**。这里列的是这项运动的
    主要发力肌群（"跳绳"→小腿+股四头），跟规则表里某条以 secondary 角色命中同一
    id 的规则无关；原实现按 id 取"最后一条规则"的角色，把小腿降成了 0.4 权重。
    """

    key = str(sport or "").strip()
    return [
        MuscleHit.for_muscle(muscle_id, "primary")
        for muscle_id in SPORT_RULES.get(key, ())
        if muscle_id in MUSCLE_META
    ]


def _extract_json(text: str) -> dict[str, Any] | None:
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text or "")
    if fenced:
        candidates.insert(0, fenced.group(1))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _validate_model_hits(value: Any) -> list[MuscleHit]:
    if isinstance(value, dict):
        value = value.get("muscles", value.get("hits"))
    if not isinstance(value, list):
        return []
    valid: list[MuscleHit] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, MuscleHit):
            item = {"muscle_id": item.muscle_id, "role": item.role}
        if not isinstance(item, dict):
            continue
        muscle_id = str(item.get("muscle_id") or "").strip()
        if muscle_id not in MUSCLE_META or muscle_id in seen:
            continue
        role = str(item.get("role") or "primary").strip().lower()
        if role not in ROLES:
            continue
        # The model may select a known id, but cannot invent its Chinese name
        # or region.  Those are always taken from our metadata table.
        valid.append(MuscleHit.for_muscle(muscle_id, role))
        seen.add(muscle_id)
    return sorted(valid, key=lambda hit: (hit.role != "primary", hit.muscle_id))


def query_muscles_with_lite_model(
    name: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    requester: Callable[..., Any] | None = None,
) -> list[MuscleHit]:
    """Ask the configured Lite model for a structured fallback result.

    ``requester`` is injectable for tests and follows ``requests.post``'s
    calling convention.  Only the action name and allowed ids are sent.
    """

    name = str(name or "").strip()
    api_key = api_key or os.getenv("LLM_LITE_API_KEY") or os.getenv("LLM_API_KEY")
    if not name or not api_key:
        return []
    model = model or os.getenv("LLM_LITE_MODE_ID") or "deepseek-chat"
    base_url = (base_url or os.getenv("LLM_LITE_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    if requester is None:
        try:
            import requests
            requester = requests.post
        except ImportError:
            return []
    prompt = (
        "只根据动作名判断主要使用的训练肌群。严格返回 JSON："
        '{"muscles":[{"muscle_id":"...","role":"primary|secondary"}]}。'
        f"允许的 muscle_id：{', '.join(sorted(MUSCLE_META))}。动作名：{name[:200]}"
    )
    try:
        response = requester(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
            timeout=10,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        return []
    return _validate_model_hits(_extract_json(content))


_MODEL_RESOLUTION_CACHE: dict[tuple[str, int, str], tuple[MuscleHit, ...]] = {}
_MODEL_RESOLUTION_LOCK = RLock()


def _records_mtime_ns() -> int:
    try:
        from .settings import data_path
        return data_path("daily_records.json").stat().st_mtime_ns
    except OSError:
        return 0


def cached_model_muscle_resolution(name: str) -> list[MuscleHit]:
    """Cache Lite-model mappings until the training-record source changes."""
    normalized = " ".join(str(name or "").casefold().split())
    model = os.getenv("LLM_LITE_MODE_ID") or "deepseek-chat"
    key = (normalized, _records_mtime_ns(), model)
    with _MODEL_RESOLUTION_LOCK:
        cached = _MODEL_RESOLUTION_CACHE.get(key)
        if cached is not None:
            return list(cached)
        # Keep the lock through the request: unknown exercises are resolved
        # serially anyway, and this prevents concurrent /chat requests from
        # issuing the same expensive model call twice.
        resolved = tuple(query_muscles_with_lite_model(name))
        if len(_MODEL_RESOLUTION_CACHE) >= 256:
            _MODEL_RESOLUTION_CACHE.pop(next(iter(_MODEL_RESOLUTION_CACHE)))
        _MODEL_RESOLUTION_CACHE[key] = resolved
    return list(resolved)


def resolve_muscles_for_exercise(
    name: str,
    *,
    allow_external_models: bool = False,
    model_resolver: Callable[[str], Iterable[MuscleHit] | list[dict[str, Any]]] | None = None,
) -> list[MuscleHit]:
    """Local-first resolution with an optional, validated model fallback."""

    local = muscles_for_exercise(name)
    if local or not allow_external_models:
        return local
    if model_resolver is not None:
        try:
            return _validate_model_hits(list(model_resolver(name)))
        except Exception:
            return []
    return cached_model_muscle_resolution(name)


__all__ = [
    "REGION_LEXICON", "REGION_ALIASES", "REGIONS", "ROLES", "TRAINING_SUBJECT_RULES",
    "MUSCLE_DETAIL_LEXICON",
    "regions_for_text", "MuscleRule", "MuscleHit", "MUSCLE_RULES", "SPORT_RULES",
    "muscles_for_exercise", "muscles_for_sport", "query_muscles_with_lite_model",
    "resolve_muscles_for_exercise", "muscle_ids_for_region", "muscle_ids_for_text",
    "cached_model_muscle_resolution",
]
