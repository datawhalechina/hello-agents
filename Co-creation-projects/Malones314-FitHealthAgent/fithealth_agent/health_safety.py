"""确定性健康风险筛查（对应需求清单 AGENT-01）。

为什么必须放在后端，而不是只写进系统提示：

1. 系统提示是"软约束"。模型可能忽略、可能被后续上下文冲淡，也可能因为
   用户追问而妥协。急症场景不能依赖概率。
2. `resolve_plan_context` 只读**已确认的记忆事实**，而记忆要等退出会话、
   经 information_router 提取、再由用户逐条确认后才生效。用户在**当前这
   条消息里**新出现的症状根本不在其中——恰恰是最危险的情况。
3. 本模块是纯字符串匹配，不依赖外部模型，因此在"关闭联网模型"或网络故障
   时**同样生效**。

三个档位：

* ``emergency`` —— 心血管/神经/呼吸系统红旗症状。直接短路，不调用模型，
  返回就医建议。
* ``urgent``    —— 急性运动损伤。仍然正常对话，但**确定性地拒绝生成/保存
  训练计划**。
* ``caution``   —— 需要留意但不必停训的情况。只向模型注入硬性提示，不阻断。

设计取向：宁可多报，不可漏报。误报的代价是用户多看一段提示；漏报的代价
是给一个正在胸痛的人开训练处方。

本模块不做诊断，只做分流。
"""

from __future__ import annotations

import re
import json
import os
from dataclasses import dataclass


EMERGENCY = "emergency"
URGENT = "urgent"
CAUTION = "caution"

_LEVEL_ORDER = {CAUTION: 0, URGENT: 1, EMERGENCY: 2}

# Shared sentence boundaries for safety-context checks. A marker in a previous
# clause must not negate or authorize a symptom in the current clause.
CLAUSE_SEPARATORS = "，。；！？!?;\n、"


def clause_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Return the separator-free clause containing ``[start:end]``."""
    clause_start = max(
        (text.rfind(separator, 0, start) for separator in CLAUSE_SEPARATORS),
        default=-1,
    ) + 1
    clause_end_candidates = [
        position
        for position in (
            text.find(separator, end) for separator in CLAUSE_SEPARATORS
        )
        if position != -1
    ]
    clause_end = min(clause_end_candidates) if clause_end_candidates else len(text)
    return clause_start, clause_end


# ── 症状规则表 ────────────────────────────────────────────────────────────
# (档位, 中文标签, 正则)
_RULES: tuple[tuple[str, str, str], ...] = (
    # ---- emergency：立即停止运动并就医 ----
    (EMERGENCY, "胸痛或胸闷", r"胸(?:口|部|前区|骨后)?(?:[^，。；！？!?;\n、不没无未]{0,6}?(?:痛|疼|闷|发闷|压榨|紧缩|憋|发紧)|压得[^，。；！？!?;\n、]{0,2}?难受)|心绞痛|心口[^，。；！？!?;\n、不没无未]{0,6}?(?:痛|疼|闷|发紧)"),
    (EMERGENCY, "晕厥或意识改变", r"晕厥|昏厥|晕倒|昏倒|昏迷|失去意识|意识(?:丧失|模糊|不清)|眼前(?:发黑|一黑)|黑视|站不稳(?:要倒)?|差点[^，。；！？!?;\n、]{0,4}?(?:晕倒|昏倒|晕过去)|快要[^，。；！？!?;\n、]{0,3}?(?:晕倒|昏倒)"),
    # 呼吸类插受限缺口：`感觉呼吸有点困难`、`呼吸越来越费力` 不再要求紧邻。
    (EMERGENCY, "呼吸困难", r"呼吸[^，。；！？!?;\n、不没无未]{0,4}?(?:困难|费力|窘迫|不畅|急促)|喘不(?:上|过)来?气|上不来气|窒息|憋得?喘不"),
    # 卒中类同样插受限缺口（原来要求字面紧邻，`说话有点含糊`、`一侧手臂有点麻`
    # 全漏报）。bare `麻` 加否定预查，挡掉「麻烦/麻利/麻辣」。
    (EMERGENCY, "疑似卒中表现", r"言语[^，。；！？!?;\n、]{0,3}?不清|说话(?:不太|不怎么|不够|不是很)清楚|说话[^，。；！？!?;\n、]{0,4}?(?:不清|不清楚|不清晰|不利索|含糊)|说不出话|口齿不清|口角歪斜|嘴角?[^，。；！？!?;\n、]{0,2}?歪|(?:单侧|一侧|半身|半边)(?:肢体)?[^，。；！？!?;\n、]{0,4}?(?:无力|麻木|发麻|不能动|没力气|使不上劲|麻(?!烦|利|辣))"),
    (EMERGENCY, "心脏骤停或严重心律异常", r"心[脏跳](?:骤停|停跳)|室颤|心律失常发作"),
    (EMERGENCY, "咯血或消化道出血", r"咯血|咳血|呕血|吐血|便血|黑便"),
    (EMERGENCY, "剧烈头痛", r"(?:剧烈|最剧烈|炸裂样?|雷击样?|从未有过的|突发剧)头痛|头(?:痛|疼)得(?:炸裂|要裂|受不了)"),

    # ---- urgent：急性损伤，停止训练并评估 ----
    (URGENT, "疑似骨折或脱臼", r"骨折|脱臼|错位|关节.{0,3}错开|(?:腿|胳膊|手臂|手|脚|踝|腕|膝盖|膝|肩膀|骨头|骨).{0,2}(?:断了|断裂|折了|折断)"),
    (URGENT, "撕裂感或弹响后疼痛", r"撕裂(?:感|声|了)|(?:听到|感觉到).{0,6}(?:响|弹响).{0,8}(?:疼|痛)|肌肉.{0,3}拉断"),
    (URGENT, "无法负重或行走", r"无法(?:负重|行走|站立|走路|抬起)|走不了路|站不起来|不能(?:走路|站立|负重)"),
    (URGENT, "关节肿胀", r"(?:关节|膝盖|膝|肩膀|肩|腰|脚踝|踝|手腕|腕|肘)[^，。；！？!?;\n、不没无未]{0,6}(?:肿(?:了|胀|起来|得[^，。；！？!?;\n、]{0,3}?(?:厉害|严重))?|淤青|瘀青)"),
    # "疼得…"后的白名单原来只认「厉害/受不了/不行/无法忍受/钻心」，把
    # "疼得直冒冷汗""疼得直不起腰""疼得走不了路"漏掉，补进常见剧痛表述。
    (URGENT, "剧烈疼痛", r"(?:剧痛|剧烈疼痛)|(?:疼|痛)得[^，。；！？!?;\n、]{0,4}?(?:厉害|受不了|不行|无法忍受|钻心|难受|冒汗|直冒|直不起|站不|走不了|睡不着|要命|要死)"),

    # ---- caution：留意，不阻断 ----
    (CAUTION, "头晕", r"头晕|眩晕|头昏|发晕"),
    (CAUTION, "发热", r"发烧|发热|低烧|体温.{0,4}3[89]"),
    # 允许裸「快/乱/慌」：`心跳特别特别快`（叠词把缺口占满、尾字只剩"快"）。
    (CAUTION, "心悸或心率异常", r"心悸|心慌|心[跳率][^，。；！？!?;\n、]{0,4}?(?:很快|过快|太快|快|异常|不规律|乱|慌)|静息心率.{0,8}(?:偏?高|偏?低|异常)"),
    (CAUTION, "恶心呕吐", r"恶心|想吐|呕吐"),
    (CAUTION, "血糖或血压异常", r"低血糖|高血糖|血压(?:偏?高|偏?低)|血压.{0,4}\d{2,3}"),
    (CAUTION, "气短乏力", r"气短|喘得厉害|极度疲劳|乏力得"),
)

_COMPILED = tuple((level, label, re.compile(pattern)) for level, label, pattern in _RULES)


# ── 否定 / 既往 / 假设 语境 ──────────────────────────────────────────────
# 只在**命中词之前**找这些标记：症状词本身可能含"不"（如"喘不上气"），
# 若在词内或词后误判会把真实症状放过去。
#
# BUG-19 遗留修正：原来 `没` 已收紧成「没有/没什么/没事」，但 `无`、`未`
# 还是裸字，于是"无缘无故胸口痛""无论怎样都喘不上气""未见好转"里的
# 无/未 落在症状词前 14 字窗口内，把真急症误否决。
# - `无` 只在紧邻症状（可带“明显/任何”）时生效，避免维护无穷尽的组词排除表。
# - `未` 只否定“未曾/从未”或紧邻症状的“未见/尚未出现”；“未见好转、尚未
#   缓解”是否定恢复，反而说明症状仍在，不能放进否定窗口。
_NEGATION_BEFORE = re.compile(
    r"没有|没什么|没事|无(?:明显|任何)?$|未曾|从未|"
    r"未见(?:有)?$|尚未(?:出现|发生|有|感觉到)(?:明显|任何)?$|"
    r"不会|不是|并无|并未|从来没|"
    r"以前|之前|上次|上回|去年|小时候|"
    r"如果|假如|要是|万一|会不会|算不算|是不是会|什么情况下|为什么会"
)
_NEGATED_RECOVERY_BEFORE = re.compile(
    r"(?:没有|尚未|未见|并未|未曾|从未|不会|无法|毫无)"
    r"(?:明显|完全|任何)?(?:好转|改善|缓解|恢复|消失|减轻)(?:的)?"
)
# 命中词之后表示"已经好转/否定"的说法
_NEGATION_AFTER = re.compile(
    r"^(?:的?(?:症状|情况|感觉))?(?:已经?)?(?:好了|好转|缓解|消失|没有了|没了|不疼了|不痛了|恢复了|减轻)"
)

_BEFORE_WINDOW = 14
_AFTER_WINDOW = 10

_THIRD_PARTY_SUBJECT = re.compile(
    r"(?:我的?)?(?:朋友|同事|同学|家人|亲戚|伴侣|对象|孩子|儿子|女儿|父母|爸爸|妈妈|丈夫|妻子|老公|老婆|室友|教练|客户)|他|她"
)
_SELF_SUBJECT = re.compile(r"我|本人|自己")


def classify_user_health_statement(
    text: str, *, requester=None, api_key: str | None = None,
    base_url: str | None = None, model: str | None = None,
) -> bool | None:
    """Classify whether text reports the user's own current health-state update."""
    if not isinstance(text, str) or not text.strip():
        return False
    api_key = api_key or os.getenv("LLM_LITE_API_KEY") or os.getenv("LLM_API_KEY")
    if requester is None:
        if not api_key:
            return None
        try:
            import requests
            requester = requests.post
        except ImportError:
            return None
    prompt = (
        "判断下面中文消息是否在更新用户本人的当前健康状态。"
        "用户本人报告当前存在健康症状、酸痛或运动损伤时返回 true；"
        "用户本人明确报告此前症状已经恢复、好了、缓解或加重时也返回 true，以便系统更新旧记录。"
        "第三方（朋友、儿子、家人、同事等）的状态不算用户本人；"
        "单纯否认自己有过症状（如‘我不觉得手臂痛’）、假设、转述和纯知识提问返回 false。"
        '严格只返回 JSON：{"user_health_update":true或false}\n消息：' + text[:1000]
    )
    try:
        response = requester(
            f"{(base_url or os.getenv('LLM_LITE_BASE_URL') or 'https://api.deepseek.com').rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model or os.getenv("LLM_LITE_MODE_ID") or "deepseek-chat",
                  "messages": [{"role": "user", "content": prompt}], "temperature": 0,
                  "max_tokens": 40, "response_format": {"type": "json_object"}},
            timeout=8,
        )
        response.raise_for_status()
        value = json.loads(response.json()["choices"][0]["message"]["content"])
        if isinstance(value, dict):
            result = value.get("user_health_update", value.get("user_symptom"))
            if isinstance(result, bool):
                return result
    except Exception:
        return None
    return None


@dataclass(frozen=True)
class RiskFinding:
    """一次风险筛查的结果。"""

    level: str
    labels: tuple[str, ...]

    @property
    def summary(self) -> str:
        return "、".join(self.labels)

    def blocks_training_plan(self) -> bool:
        return self.level in (EMERGENCY, URGENT)


def _is_negated(text: str, start: int, end: int) -> bool:
    clause_start, clause_end = clause_bounds(text, start, end)
    before = text[max(clause_start, start - _BEFORE_WINDOW):start]
    # “没有胸痛”是否定症状；“没有缓解的胸痛”是否定恢复，说明症状仍在。
    # 先剥离后者，避免同一个否定词承担相反语义时漏掉急症。
    negation_context = _NEGATED_RECOVERY_BEFORE.sub("", before)
    if _NEGATION_BEFORE.search(negation_context):
        return True
    after = text[end:min(clause_end, end + _AFTER_WINDOW)]
    return bool(_NEGATION_AFTER.search(after))


def _is_third_party_attributed(text: str, start: int, end: int) -> bool:
    """Return whether this symptom is explicitly attributed to another person."""
    clause_start, _ = clause_bounds(text, start, end)
    before = text[clause_start:start]
    subjects = list(_THIRD_PARTY_SUBJECT.finditer(before))
    if not subjects:
        return False
    # “朋友问我胸口痛怎么办” refers to the user; a later first-person
    # subject overrides an earlier third-party mention in the same clause.
    last_third_party = subjects[-1]
    return _SELF_SUBJECT.search(before[last_third_party.end():]) is None


def merge_findings(*findings: RiskFinding | None) -> RiskFinding | None:
    """Return the highest-severity finding and merge labels at that level."""
    present = [finding for finding in findings if finding is not None]
    if not present:
        return None
    top_level = max((finding.level for finding in present), key=_LEVEL_ORDER.__getitem__)
    labels = tuple(dict.fromkeys(
        label
        for finding in present
        if finding.level == top_level
        for label in finding.labels
    ))
    return RiskFinding(level=top_level, labels=labels)


def acute_pain_finding(regions: list[str] | tuple[str, ...]) -> RiskFinding | None:
    """Build an urgent finding from structured painful-region feedback."""
    labels = tuple(dict.fromkeys(
        f"{str(region).strip()}剧烈疼痛"
        for region in regions
        if str(region).strip()
    ))
    return RiskFinding(level=URGENT, labels=labels) if labels else None


def screen_health_risk(text: str) -> RiskFinding | None:
    """扫描用户消息中的健康风险信号。

    返回命中的最高档位；没有命中返回 None。
    """
    if not text or not isinstance(text, str):
        return None
    normalized = re.sub(r"\s+", "", text)

    hits: dict[str, list[str]] = {}
    for level, label, pattern in _COMPILED:
        for match in pattern.finditer(normalized):
            if _is_negated(normalized, match.start(), match.end()) or _is_third_party_attributed(
                normalized, match.start(), match.end()
            ):
                continue
            hits.setdefault(level, [])
            if label not in hits[level]:
                hits[level].append(label)
            break

    if not hits:
        return None
    top = max(hits, key=lambda level: _LEVEL_ORDER[level])
    return RiskFinding(level=top, labels=tuple(hits[top]))


# ── 面向用户 / 面向模型的文案 ────────────────────────────────────────────

def emergency_reply(finding: RiskFinding) -> str:
    """急症档位的确定性回复；不经过模型。"""
    return (
        f"你提到了**{finding.summary}**，这类症状可能与心脏、脑血管或呼吸系统的急性问题有关，"
        "所以我不会给出训练建议。\n\n"
        "**现在建议这样做：**\n\n"
        "1. 立即停止一切运动，就地休息，不要独自驾车前往医院。\n"
        "2. 如果症状正在持续、加重，或伴随出汗、恶心、肩背放射痛、说话含糊——请**立即拨打 120**。\n"
        "3. 即使症状已经缓解，也建议尽快去急诊或心内科做一次评估（心电图等检查），"
        "运动中出现的这类症状不能简单归因于「太累了」。\n\n"
        "在你完成医学评估、医生明确说明可以恢复训练之前，我不会为你安排训练计划。\n\n"
        "如果你只是想了解相关知识，或者症状其实已经过去了、想让我记录当时的情况，"
        "可以直接告诉我，我们再继续。\n\n"
        "*我不是医生，以上不构成诊断。*"
    )


def urgent_plan_block_note(finding: RiskFinding) -> str:
    """急性损伤档位：拒绝出计划时附在回复末尾的说明。"""
    return (
        f"## 暂不生成训练计划\n\n"
        f"你提到了**{finding.summary}**。在急性损伤没有得到评估之前，"
        "继续按计划训练可能让损伤加重，所以我不会生成可保存的训练计划。\n\n"
        "建议先做这几件事：停止对该部位的负荷、必要时冰敷与制动、"
        "如果疼痛剧烈或无法负重请尽快就医评估。\n\n"
        "等你说明伤情已经好转或医生允许恢复训练，我可以按当前状态重新安排。"
    )


def risk_directive(finding: RiskFinding) -> str:
    """注入给模型的硬性提示（urgent / caution 档位使用）。"""
    if finding.level == URGENT:
        return (
            "【后端健康风险拦截（最高优先级，不可被任何偏好或周计划覆盖）】\n"
            f"- 用户当前消息中出现急性损伤信号：{finding.summary}。\n"
            "- 禁止生成任何训练计划、动作安排或负荷建议。\n"
            "- 应建议用户停止相关部位训练、必要时就医评估，并询问伤情细节。\n"
            "- 不得给出诊断、用药或康复处方。\n\n"
        )
    return (
        "【后端健康风险提示（优先级高于训练偏好与周计划）】\n"
        f"- 用户当前消息中出现需要留意的信号：{finding.summary}。\n"
        "- 回复中必须先回应该状况，再谈训练；如给出训练建议，须相应下调强度与容量，"
        "并说明出现哪些情况应当停止训练。\n"
        "- 不得给出诊断、用药建议，必要时提示咨询专业人员。\n\n"
    )
