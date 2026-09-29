"""对话进入模型之前的确定性安全检查。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardResult:
    """allowed 为 False 时，message 是直接返回给用户的固定话术。"""

    allowed: bool
    category: str
    message: str = ""


_CRISIS_PHRASES = (
    "不想活",
    "活不下去",
    "不想活了",
    "自杀",
    "轻生",
    "结束生命",
    "自残",
    "割腕",
    "跳楼",
    "想死",
    "弄死",
    "杀了他",
    "杀了她",
    "伤害别人",
    "想伤害",
)

_MEDICAL_PHRASES = (
    "开药",
    "吃药",
    "处方",
    "诊断",
    "抑郁症",
    "焦虑症",
    "双相",
    "安眠药",
    "抗焦虑",
    "抗抑郁",
    "是不是病",
)

_ILLEGAL_PHRASES = (
    "制作炸弹",
    "爆炸物",
    "毒品",
    "入侵系统",
    "木马",
    "诈骗脚本",
)

_SEXUAL_PHRASES = (
    "色情",
    "裸聊",
    "约炮",
    "性爱",
    "淫秽",
)

_CRISIS_REPLY = """我听到你现在很痛苦。我是倾诉助理，不能替代危机干预或专业帮助。

请现在联系现实中的人：
- 全国心理援助热线：12356（24 小时）
- 若有立即的人身危险：120（急救）或 110（报警）
- 也可以马上告诉身边可信的成年人，例如家长、班主任或学校心理老师

在联系到真人帮助之前，请尽量不要一个人待着。如果你愿意，可以只告诉我：你现在是否安全、身边有没有人。"""

_MEDICAL_REPLY = """我不能做心理或医疗诊断，也不能建议用药。是否需要治疗，要由学校心理老师、医院或正规咨询机构来判断。

我可以继续听你说：最近最压着你的是哪一件事，以及你希望父母怎样理解你。"""

_ILLEGAL_REPLY = "这个请求超出了我能帮助的范围。我只能在合法合规的边界内，陪你梳理学业和沟通上的困扰。"

_SEXUAL_REPLY = "这类内容不在本助理的服务范围内。如果你愿意，我们可以回到学业压力，或和家人、同学相处这些话题。"


def _hit(text: str, phrases: tuple[str, ...]) -> bool:
    compact = text.replace(" ", "")
    return any(phrase in compact for phrase in phrases)


def check_message(text: str) -> GuardResult:
    """按危机、违法、色情、医疗越界的顺序检查。危机优先于其他类别。"""
    content = (text or "").strip()
    if not content:
        return GuardResult(False, "empty", "可以先说一件最近让你卡住的事，哪怕只有一两句。")
    if _hit(content, _CRISIS_PHRASES):
        return GuardResult(False, "crisis", _CRISIS_REPLY)
    if _hit(content, _ILLEGAL_PHRASES):
        return GuardResult(False, "illegal", _ILLEGAL_REPLY)
    if _hit(content, _SEXUAL_PHRASES):
        return GuardResult(False, "sexual", _SEXUAL_REPLY)
    if _hit(content, _MEDICAL_PHRASES):
        return GuardResult(False, "medical", _MEDICAL_REPLY)
    return GuardResult(True, "ok", "")
