"""确定性护栏：机械审查、来源验真、字段核对、覆盖/身份文案。

从 src/team.py 拆出（2026-10-25）。本模块只做过滤/校验，不改写用户输入。
"""

import re

from src.identity import STATIC_PROGRAMME_ALIASES
from src.validators import CCA_PROGRAMME_URL, _cards

# ---------------------------------------------------------------------------
# 机械审查（确定性，D3 补丁 2026-10-23：Reviewer 纯提示词审查实测压不住坏草稿
# ——"无来源断言+虚构冲突检测结论"被误判 PASS，与 D2 v9-v12 教训同源。
# 四项审查中可机械化的部分下沉代码，LLM 审查保留语义项辅助，任一 FAIL 即 FAIL）
# ---------------------------------------------------------------------------

_CODE_RE = re.compile(r"\b([A-Z]{2}\d{4}[A-Z]?)\b")
# 学位规则/冲突结论词：草稿出现这些结论却无校验证据 → 机械 FAIL
# 学位规则/冲突结论词：草稿出现这些结论却无校验证据 → 机械 FAIL。
# 注意**不含"专选/通选/符合要求"**：它们是课程类别字段与推荐语里的正常表述
# （"EE6406 是专选课""这些课符合你的方向"），此前误判导致 3 轮空转。
_RULE_WORDS = ["option 1", "option 2", "专选门数", "au 上限", "上限", "下限",
               "学位合规", "不符合要求", "满足学位要求", "冲突", "conflict"]
# 校验证据特征：校验工具返回文本/规则来源 URL 的标志片段
_AUDIT_EVIDENCE = ["check_", "规则来源", "无课表数据", "课表数据范围",
                   "规则来源", CCA_PROGRAMME_URL]
# 学位合规判定特征（计划无 audit 步却出现 = 越权校验）。
# 只认**结构性合规判定**："专选/通选/符合要求"是类别字段与推荐语，不在此列。
_AUDIT_CLAIM_RE = re.compile(
    r"option\s*[12]|专选门数|au\s*上限|通选[^\n]{0,8}上限|不符合要求|满足学位要求",
    re.IGNORECASE)
# 示例占位符残留（few-shot 结构示例被整段照抄的痕迹，D3.5 实测：
# 输出写成"推荐 A、B、C 三门"却列了 5 门）
_PLACEHOLDER_RE = re.compile(
    r"推荐\s*[A-Z](?:[、,，]\s*[A-Z])+|[A-Z]\s*是\s*(?:专选|通选|必修)")
_RECOMMEND_WORDS = ["推荐", "建议我选", "建议选", "帮我选", "帮我挑", "选哪些",
                    "选什么课", "怎么选课", "recommend", "any suggestions",
                    # D3.5 补：列表类提问同样需要身份过滤。实测「我是AI专业的新生，
                    # 有哪些课程？」不在原词表 → 未确认身份时不反问 → 混入本科课
                    "有哪些课", "有哪些课程", "有什么课", "课程列表", "开设哪些"]
# 否定提及豁免：课码出现在这类短语附近 = 明说未查到，不需要来源
# 2026-10-25 补「未能找到/未找到/找不到」：notebook 的 CS1010S 回答用「未能找到」，
# 旧词表未豁免，机械审查误判缺来源并空转 3 轮。
_NEGATIVE_CTX = ["未查到", "未收录", "没有查到", "查不到", "未能找到", "未找到",
                 "找不到", "没有找到", "未检索到", "未获取", "不在", "not found",
                 "no course", "not available", "不在课程库"]
# 字段转述豁免：课码是"某门课的字段值"（先修/互斥/限修）而非被推荐的课，
# 不需要单独来源——它的依据就是那门主课的卡片（实测 SC1007 的"先修 SC1003"
# 被机械审查误判为缺来源，导致 3 轮空转）
_FIELD_CTX = ["先修", "prerequisite", "互斥", "mutually exclusive", "限修",
              "not available", "前提"]

_URL_RE = re.compile(r"https?://[^\s\]\"'<>，。；]+")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_ALLOWED_URLS: set[str] | None = None


def _norm_url(url: str) -> str:
    return url.strip().rstrip("/.,;").lower()


def _extract_urls(text: str) -> list[str]:
    """从正文提取 URL，并去掉不属于 URL 的尾部括号/标点。

    动机（2026-10-24 D4 预检）：Robotics 项目的官方来源 URL 自带括号
    （...master-of-science-(robotics-and-intelligent-systems)），此前的
    URL 正则排除 `)`，会把合法 URL 截断成半截 → 白名单验真误判为编造来源。
    这里允许 URL 内含括号，只剥离**不配对**的尾部右括号与句末标点。
    """
    urls = []
    for raw in _URL_RE.findall(text):
        u = raw.rstrip(".,;，。；、）】")
        while u.endswith(")") and u.count("(") < u.count(")"):
            u = u[:-1].rstrip(".,;，。；、）】")
        urls.append(u)
    return urls


def _allowed_urls() -> set[str]:
    """合法来源 URL 白名单：库内课程卡片 source_url + 规则页。

    动因（2026-10-24 实测）：回答"没找到课程"时模型编造了
    https://www.ntu.edu.sg/education ——来源覆盖检查只在有课码时触发，
    编造链接完全漏检，直接违反"没有来源不许出现"红线。
    """
    global _ALLOWED_URLS
    if _ALLOWED_URLS is None:
        urls = {c.get("source_url") for c in _cards().values() if c.get("source_url")}
        urls.add(CCA_PROGRAMME_URL)
        _ALLOWED_URLS = {_norm_url(u) for u in urls if u}
    return _ALLOWED_URLS


def _sanitize_sources(draft: str) -> str:
    """放行前代码兜底：把非白名单 URL 替换/移除，确保来源真实。

    动机（D4 Q11/Q12 实测）：模型编造 ntu-course-search.com / course.ntu.edu.sg，
    机械审查 3 轮打回后模型仍继续编造，最终带假 URL 放行——红线不能只靠
    模型自觉。这里只改 URL，不改事实正文：能定位到课码就用该课卡片的官方
    source_url 替换；定位不到就删除该 URL；正文有课码但完全没有合法 URL 时
    补一份卡片来源清单。
    """
    allowed = _allowed_urls()
    cards = _cards()
    out = []
    for line in draft.splitlines():
        # 模型有时把链接目标写成占位文字：[链接](课程库链接)。按行内课码换成官方 URL。
        line_codes = _CODE_RE.findall(line.upper())
        line_src = next((cards[c]["source_url"] for c in line_codes
                         if c in cards and cards[c].get("source_url")), None)
        if line_src:
            def _fix_target(m):
                target = m.group(2).strip()
                if target.startswith(("http://", "https://")):
                    return m.group(0)
                return f"[{m.group(1)}]({line_src})"
            line = _MD_LINK_RE.sub(_fix_target, line)
        bad = [u for u in _extract_urls(line) if _norm_url(u) not in allowed]
        if bad:
            codes = _CODE_RE.findall(line.upper())
            replacement = next((cards[c]["source_url"] for c in codes
                                if c in cards and cards[c].get("source_url")), None)
            if replacement:
                for u in bad:
                    line = line.replace(u, replacement)
            else:
                for u in bad:
                    line = line.replace(u, "")
                line = re.sub(r"\[\s*[^\]]*\]\(\s*\)", "", line)
                line = re.sub(r"\(\s*\)", "", line)
        out.append(line)
    text = "\n".join(out)

    # 正文有课码但没有任何合法 URL：补一份只含卡片 source_url 的来源清单
    body = text.split("来源")[0] if "来源" in text else text
    codes = _codes_with_negative_exempt(body)
    if codes and not any(_norm_url(u) in allowed for u in _extract_urls(text)):
        src_lines = [f"- {c} {cards[c].get('title', '')} — {cards[c]['source_url']}"
                     for c in sorted(codes)
                     if c in cards and cards[c].get("source_url")]
        if src_lines:
            text = text.rstrip() + "\n\n来源：\n" + "\n".join(src_lines)
    return text


def _codes_with_negative_exempt(text: str) -> set[str]:
    """提取正文课程码，豁免否定提及与字段转述（先修/互斥/限修）。"""
    codes = set()
    for m in _CODE_RE.finditer(text):
        ctx = text[max(0, m.start() - 25):m.end() + 25]
        if any(w in ctx for w in _NEGATIVE_CTX):
            continue
        if any(w in ctx for w in _FIELD_CTX):
            continue
        codes.add(m.group(1))
    return codes


def _has_inline_source(body: str, code: str, expected_url: str | None = None,
                       window: int = 250) -> bool:
    """课码所在条目块内是否含来源链接；给定 expected_url 时必须是该课卡片 URL。

    补强（2026-10-25）：此前只查 "http" 任意 URL，模型引用另一门课的合法 URL
    也会通过；现在来源段/条目块必须出现该课卡片的 source_url（本科同为 WIS
    入口页，研究生可区分 CCA / Robotics）。
    """
    marks = list(_CODE_RE.finditer(body))
    for idx, m in enumerate(marks):
        if m.group(1) != code:
            continue
        start = body.rfind("\n", 0, m.start()) + 1
        end = len(body)
        if idx + 1 < len(marks):
            nl = body.rfind("\n", 0, marks[idx + 1].start())
            end = nl if nl > start else marks[idx + 1].start()
        block = body[start:end]
        before = body[max(0, m.start() - window):start]
        if expected_url:
            expected = _norm_url(expected_url)
            if expected in {_norm_url(u) for u in _extract_urls(block)}:
                return True
            if expected in {_norm_url(u) for u in _extract_urls(before)}:
                return True
        elif "http" in block or "http" in before:
            return True
    return False


def _has_source_for_code(code: str, body: str, source_urls: set[str]) -> bool:
    """该课码是否有“对得上号”的来源：来源清单或条目块含其卡片 source_url。"""
    card = _cards().get(code)
    if not card or not card.get("source_url"):
        return False
    expected = _norm_url(card["source_url"])
    return expected in source_urls or _has_inline_source(body, code, expected)


# 组合逻辑总述特征词（推荐类精炼稿的代码护栏判定；只查开头段，属性罗列不误伤）
_SYNTHESIS_WORDS = ["搭配", "互补", "计入", "进阶", "循序渐进", "由浅入深",
                    "打基础", "打.*基础", "先修链"]


def _has_synthesis(text: str) -> bool:
    """精炼稿是否含组合逻辑总述（推荐类问题的 polish 结果判定）。

    检查全文而非仅开头：模型自然行为是把总述放结尾（收尾总结式），
    强制位置属过度约束（体验迭代目标就是反死板），存在即可。
    """
    return any(re.search(w, text) for w in _SYNTHESIS_WORDS)


# ReAct 内部思考泄漏（实测修订轮输出过 `Thought {"reasoning": ...}` 前缀）
_REACT_LEAK_RE = re.compile(
    r"^\s*(?:<)?Thought(?:>)?\s*\{.*?\}\s*", re.DOTALL | re.IGNORECASE)


def _clean_answer(text: str) -> str:
    """去掉模型泄漏到正文里的 ReAct 思考块（Thought {...}）。"""
    return _REACT_LEAK_RE.sub("", text, count=1).lstrip()


def _programme_known(name: str) -> bool:
    """模型提到的项目是否真在课程库里（卡片 programme 字段或静态别名表）。"""
    n = (name or "").strip().lower()
    if not n:
        return False
    for c in _cards().values():
        p = (c.get("programme") or "").lower()
        if p and (n in p or p in n):
            return True
    for alias, (full, _lv) in STATIC_PROGRAMME_ALIASES.items():
        if n == alias.lower() or n in full.lower():
            return True
    return False


def _scope_notice(programme: str) -> str:
    """库外专业的覆盖说明（方案 C：明确边界，不硬答、不检索）。"""
    return (f"「{programme}」目前不在课程库覆盖范围内。\n"
            "当前覆盖：\n"
            "· 本科：CCDS 学院 5 个专业（CSC 计算机科学、CE 计算机工程、"
            "DSAI 数据科学与人工智能、AISC 人工智能与社会、COMP 计算）\n"
            "· 研究生：MSc Computer Control & Automation（CCA）、"
            "MSc Robotics and Intelligent Systems\n"
            "其他学院的专业暂未收录。可以直接问具体课程代码，或换成本库覆盖的专业。")


def _identity_ask(programme: str = "") -> str:
    """反问文案：说清覆盖边界 + 给可照抄示例（用户可见的兜底）。

    出路 1（2026-10-24）：这是编排层唯一的身份相关拦截——模型自己说
    confidence != certain 且检索需要身份时才触发，不替模型做判断。
    """
    if programme:  # 用户提到了库外项目 → 直接给覆盖清单（与 _scope_notice 一致）
        return _scope_notice(programme)
    facts = ("当前课程库覆盖：研究生侧 MSc Computer Control & Automation（CCA）、"
             "MSc Robotics and Intelligent Systems；"
             "本科侧 CCDS 学院 5 个专业（CSC / CE / DSAI / AISC / COMP）。")
    return (f"要推荐或列出课程，我需要先知道你的身份。\n"
            f"{facts}\n"
            f"请回复「本科」或「研究生」；如果是 CCA 学生，回复「我是 CCA 研究生」更准确。")


# 先修/互斥字段核对（D4 Q04）：草稿里的先修/互斥结论必须能在目标课程卡片
# 对应字段里找到依据，不能把检索结果中相近课的字段搬过来。
_PREREQ_WORDS = ("先修", "prerequisite")
_MUTEX_WORDS = ("互斥", "mutually exclusive")
_PREREQ_NEGATIVE = ("无先修", "没有先修", "未列出", "未标注", "不需要先修",
                    "no prerequisite", "not listed")
_MUTEX_NEGATIVE = ("无互斥", "没有互斥", "未列出", "未标注", "无冲突",
                   "no mutual")
# 空描述防编造（D4 Q16）：卡片 Description 为空时，出现这些内容性词即视为编造。
_DESC_MISSING_WORDS = ("未提供", "未收录", "未标注", "暂无", "没有描述",
                       "无描述", "未列出", "not provided", "no description",
                       "not available")
_DESC_CLAIM_WORDS = ("包括", "涵盖", "涉及", "旨在", "讲授", "学习",
                     "控制", "感知", "规划", "内容", "主题")
# 用户明确问“讲什么/内容/简介”时，空描述课程必须明说“简介未收录”；
# 列表类问题（有哪些课程）不强制每门都写，避免把列表回答逼长（Q08 实测）。
_DESC_INTENT_WORDS = ("讲什么", "什么内容", "内容", "简介", "介绍",
                      "about", "what is")


def _block_of(text: str, code: str) -> str:
    """课码所在条目块：本课行首 → 下一课行首（或文末）。"""
    marks = list(_CODE_RE.finditer(text))
    for idx, m in enumerate(marks):
        if m.group(1) != code:
            continue
        start = text.rfind("\n", 0, m.start()) + 1
        end = len(text)
        if idx + 1 < len(marks):
            nl = text.rfind("\n", 0, marks[idx + 1].start())
            end = nl if nl > start else marks[idx + 1].start()
        return text[start:end]
    return ""


def _field_claim_issues(draft: str) -> list[str]:
    """先修/互斥结论必须与目标课程卡片字段一致（确定性）。"""
    cards = _cards()
    issues: list[str] = []
    lines = draft.splitlines()
    for i, line in enumerate(lines):
        low = line.lower()

        def subject_before(pos: int) -> str | None:
            before = _CODE_RE.findall(line[:pos].upper())
            if before:
                return before[-1]
            for prev in reversed(lines[:i]):
                stripped = prev.strip().lstrip("-*0123456789.、) ")
                if stripped.startswith(("先修", "互斥", "限修", "来源", "Prerequisite",
                                        "Mutually", "Not available", "Source")):
                    continue
                pc = _CODE_RE.findall(prev.upper())
                if pc:
                    return pc[0]  # 块内第一课码是主课（避免把先修课当成主课）
            return None

        # ---- 先修 ----
        hits = [low.find(w.lower()) for w in _PREREQ_WORDS if w.lower() in low]
        if hits and not any(w in low for w in _PREREQ_NEGATIVE):
            pos = min(hits)
            subject = subject_before(pos)
            card = cards.get(subject) if subject else None
            if card:
                refs = [c for c in _CODE_RE.findall(line[pos:].upper())
                        if c != subject]
                field = (card.get("prerequisite") or "").strip()
                field_codes = set(_CODE_RE.findall(field.upper()))
                if not field:
                    issues.append(f"先修字段为空：{subject} 的卡片没有先修字段，"
                                  f"草稿却给出先修结论——删除或明说未列出")
                elif refs and not (set(refs) & field_codes):
                    issues.append(f"先修字段不符：{subject} 卡片未包含 "
                                  f"{', '.join(refs)}——只可转述卡片原文")

        # ---- 互斥 ----
        hits = [low.find(w.lower()) for w in _MUTEX_WORDS if w.lower() in low]
        if hits and not any(w in low for w in _MUTEX_NEGATIVE):
            pos = min(hits)
            before = _CODE_RE.findall(line[:pos].upper())
            after = _CODE_RE.findall(line[pos:].upper())
            codes = list(dict.fromkeys(before + after))
            subject = before[-1] if before else subject_before(pos)
            refs = [c for c in codes if c != subject] if subject else codes
            if subject and subject in cards and refs:
                field = set(_CODE_RE.findall(
                    (cards[subject].get("mutually_exclusive") or "").upper()))
                if not any(r in field for r in refs):
                    reverse = any(subject in set(_CODE_RE.findall(
                        (cards.get(r, {}).get("mutually_exclusive") or "").upper()))
                        for r in refs)
                    if not reverse:
                        issues.append(f"互斥字段不符：{subject} 与 "
                                      f"{', '.join(refs)} 的卡片互斥字段未包含对方"
                                      f"——只可转述卡片原文")
            elif len(codes) >= 2:
                ok = any(
                    b in set(_CODE_RE.findall(
                        (cards.get(a, {}).get("mutually_exclusive") or "").upper()))
                    or a in set(_CODE_RE.findall(
                        (cards.get(b, {}).get("mutually_exclusive") or "").upper()))
                    for a in codes for b in codes if a != b
                )
                if not ok:
                    issues.append(f"互斥字段不符：{', '.join(codes)} 的卡片互斥字段"
                                  f"未包含彼此——只可转述卡片原文")
    return issues


def _empty_description_issues(draft: str, question: str = "") -> list[str]:
    """卡片 Description 为空时：问内容必须明说未收录，其余不得编造内容。"""
    cards = _cards()
    issues: list[str] = []
    wants_desc = any(w in (question or "").lower() for w in _DESC_INTENT_WORDS)
    for code in sorted(_codes_with_negative_exempt(draft)):
        card = cards.get(code)
        if not card or (card.get("description") or "").strip():
            continue
        block = _block_of(draft, code).lower()
        has_missing = any(w in block for w in _DESC_MISSING_WORDS)
        if wants_desc and not has_missing:
            issues.append(f"空描述：{code} 卡片 Description 为空，用户问课程内容，"
                          f"草稿却未明说——必须写“课程简介未收录”")
        elif any(w in block for w in _DESC_CLAIM_WORDS) and not has_missing:
            issues.append(f"空描述：{code} 卡片 Description 为空，草稿却展开"
                          f"课程内容——只可给标题/AU/项目并明说简介未收录")
    return issues


# 用户点名的字段必须逐项回答（D4.1 Q01 复跑实测：问了“哪些学期”但回答漏了学期）。
_FIELD_INTENT_TERMS = {
    "AU": ("au", "学分"),
    "学期": ("semester", "学期", "sem ", "2026_1", "2026_2"),
    "先修": ("先修", "prerequisite"),
    "互斥": ("互斥", "mutually exclusive"),
}


def _missing_field_intents(question: str, draft: str) -> list[str]:
    """用户明确问到的字段是否在草稿中出现（确定性完整性检查）。"""
    q = (question or "").lower()
    d = (draft or "").lower()
    missing = []
    if "au" in q or "学分" in q:
        if not any(w in d for w in _FIELD_INTENT_TERMS["AU"]):
            missing.append("AU")
    if "学期" in q or "semester" in q:
        if not any(w in d for w in _FIELD_INTENT_TERMS["学期"]):
            missing.append("学期")
    if "先修" in q or "prerequisite" in q:
        if not any(w in d for w in _FIELD_INTENT_TERMS["先修"]):
            missing.append("先修")
    if "互斥" in q or "mutually exclusive" in q:
        if not any(w in d for w in _FIELD_INTENT_TERMS["互斥"]):
            missing.append("互斥")
    return missing


def _only_empty_field_complaint(review: str, draft: str) -> bool:
    """LLM Reviewer 的已知假阳性：草稿明说“未列出/未收录”，却要求补全/猜测。

    D4 复跑实测：Q04/Q16 的机械审查已通过（无编造），LLM Reviewer 仍把
    “先修要求：未列出”“课程描述未收录”当成缺失信息，要求补猜测——这正好
    违反反幻觉红线。只在**机械审查无问题**且抱怨仅围绕空字段时放行。
    """
    r = (review or "").lower()
    if not any(w in draft for w in ("未列出", "未收录", "未提供", "暂无")):
        return False
    if not any(w in r for w in ("先修", "描述", "简介", "字段",
                                "prerequisite", "description")):
        return False
    if any(w in r for w in ("来源", "编造", "事实", "错误", "冲突",
                            "au", "身份", "课程码")):
        return False
    return True


def mechanical_review(question: str, identity, draft: str, steps: list[dict]) -> list[str]:
    """代码层确定性审查（四项中的三项机械化），返回问题清单（空 = 通过）。

    ① 来源覆盖：正文断言性提及的课码必须出现在来源清单段
    ③ 学位规则引用：规则/冲突结论必须有校验工具证据特征
    ④ 身份一致性：推荐类检索（计划含 level 步）时草稿不应混入不符身份的课
    （② 查不到明说/猜测兜底为语义判断，由 Reviewer LLM 审查承担）
    """
    issues = []
    # 来源段起点：最后一处独立的"来源/来源清单/Sources"标题行。
    # 排除"来源 URL/来源链接"行（它们是清单内的字段，不是标题，会把清单截断）。
    src_matches = list(re.finditer(
        r"(?:^|\n)\s*(?:[-*]\s*)?(?:课程来源|来源清单|来源(?! ?URL| ?链接)|"
        r"Sources?|References?)[^\n]*\n", draft))
    src_match = src_matches[-1] if src_matches else None
    source_part = draft[src_match.start():] if src_match else ""
    source_urls = {_norm_url(u) for u in _extract_urls(source_part)}

    body = draft[:src_match.start()] if src_match else draft
    body_codes = _codes_with_negative_exempt(body)
    # 来源覆盖判定：
    # a) 纯 audit 计划（无 search 步）：校验工具返回只附规则来源 URL，无逐课卡片
    #    source，逐课要求超出工具能力（场景 11 曾 3 轮空转实证）——有 http 来源
    #    且有校验证据即可，校验结论完整性由下方"学位规则引用"项独立保证
    # b) 其余：每个课码的来源必须是该课卡片的 source_url（来源清单或条目块），
    #    不能只满足"URL 在白名单里"——否则引用另一门课的合法 URL 也会通过。
    pure_audit = steps and not any(s.get("action") == "search" for s in steps)
    if (pure_audit and "http" in source_part
            and any(e.lower() in draft.lower() for e in _AUDIT_EVIDENCE)):
        missing_src = []
    else:
        missing_src = sorted(
            c for c in body_codes
            if not _has_source_for_code(c, body, source_urls))
    if missing_src:
        issues.append(f"来源覆盖：以下课程的来源不是该课卡片的官方 source_url，"
                      f"或既不在来源清单、邻近也无该课来源链接——"
                      f"{', '.join(missing_src)}（补该课卡片 source_url，或删除相关断言）")

    if (any(w in draft.lower() for w in _RULE_WORDS)
            and not any(e.lower() in draft.lower() for e in _AUDIT_EVIDENCE)):
        issues.append("学位规则：草稿含学位规则/冲突结论，但未见校验工具返回"
                      "（check_* 输出/规则来源 URL）——调用校验工具并引用其返回")

    # 越权校验（D3.5 实测）：计划无 audit 步，草稿却给出学位合规判定——
    # 「我是AI专业的新生，有哪些课程？」Retrieval 自行调校验工具输出
    # Option 1 判定，Reviewer 3 轮 FAIL 空转 167s。代码护栏独立拦一道。
    if not any(s.get("action") == "audit" for s in steps) \
            and _AUDIT_CLAIM_RE.search(draft):
        issues.append("越权校验：计划中没有 audit（学位校验）步，草稿却给出学位合规"
                      "结论（Option 1/2、专选门数、AU 上限等）——删除该段，"
                      "学位合规须由用户明确要求并走校验工具")

    if _PLACEHOLDER_RE.search(draft):
        issues.append("占位符残留：草稿出现「推荐 A、B、C」类示例占位符——"
                      "必须替换为真实课程代码与实际门数")

    # 来源真实性（2026-10-24 新增）：正文 URL 必须来自课程库 source_url 或规则页。
    # 实测「没找到课程」时模型编造 https://www.ntu.edu.sg/education 且无人拦截。
    bad_urls = sorted({u for u in _extract_urls(draft)
                       if _norm_url(u) not in _allowed_urls()})
    if bad_urls:
        issues.append(f"来源真实性：以下 URL 不属于课程库或规则页——"
                      f"{', '.join(bad_urls)}（删除编造来源，只引用工具返回的 "
                      f"source 字段；确实查不到就明说，不要附通用官网链接）")

    # 先修/互斥字段核对（D4 Q04）：不得把相近课字段搬到所问课程
    issues.extend(_field_claim_issues(draft))
    # 空描述防编造（D4 Q16）：Description 为空时不得展开内容
    issues.extend(_empty_description_issues(draft, question))
    # 字段完整性（D4.1 Q01）：用户点名的 AU/学期/先修/互斥必须逐项回答
    missing_fields = _missing_field_intents(question, draft)
    if missing_fields:
        issues.append(f"字段遗漏：用户问到的 {'、'.join(missing_fields)} 未在草稿中回答"
                      f"——逐项补全（卡片没有就写未列出）")

    # 身份一致性：身份已确认（且非属性查询）时，草稿不应混入不符层次的课。
    # 不再要求"计划里必须有 level 步"——实测 Planner 对推荐类常不标 level，
    # 旧条件会让这项审查整体失效（建议课混本科课也放行）。
    if identity and identity.status == "confirmed" and identity.level:
        cards = _cards()
        wrong_level = sorted(
            c for c in body_codes
            if c in cards and cards[c].get("level") != identity.level)
        if wrong_level:
            issues.append(f"身份一致性：用户身份 level={identity.level}，但草稿涉及"
                          f"{'本科' if identity.level == 'graduate' else '研究生'}"
                          f"课程——{', '.join(wrong_level)}（不符课程不得作为主推荐，"
                          f"如需提及必须标注其卡片 Level 字段值）")

    # 注：曾尝试机械审查强制"推荐类组合逻辑总述"→ 3 轮 FAIL 空转，已撤。
    # 归因经 A/B 判别实验修正：不是模型上限，是 ReAct 循环内信息流压制；
    # 现由 _polish_draft 单轮精炼 + _has_synthesis 重试护栏负责，不放机械审查。
    return issues

