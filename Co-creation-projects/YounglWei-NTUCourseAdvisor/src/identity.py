"""身份识别（D3 Planner 结构化职责，纯代码查表，不靠模型联想）。

背景（D2 v9-v12 教训，2026-10-23）：glm-4-flash 对非官方项目缩写（如 CCA 新生）
的身份识别是概率性行为，7 轮提示词迭代实证与措辞无关（模型能力天花板）。
根治方案（用户拍板）：缩写/全称双源查表——
  源 1 静态映射表（人工整理，宁缺毋滥，只收已验证条目）
  源 2 库内 Programme 字段（course_cards.jsonl，如 "MSc Computer Control & Automation (CCA)"）
判定规则（优先级从高到低）：
  1. 学历词直判：研究生/硕士/Master/MSc/PhD/博士/graduate → graduate；
     本科/undergraduate → undergraduate（用户明说的学历词是最强信号）
  2. 项目词查表：唯一命中 → 直接确认；多命中 → 列候选让用户选；零命中 → 开放反问
  3. 身份声明句式兜底（D3 验收期修复 2026-10-23）：项目词零命中但句中含
     第一人称声明「我是 X 新生/学生/在读」→ unrecognized（未知项目声明），
     旧会话缓存不作数、推荐类必反问——防止"用户换专业（如 SPML）被静默
     沿用上一轮 CCA 缓存"（demo 实测缺陷）
已知取舍：CCA 在 NTU 本科语境 = Co-Curricular Activity（课外活动），本表按用户拍板
方案"唯一命中直接确认"处理为硕士项目；用户明说"本科"时学历词优先，不受影响。
"""

import json
import re
from dataclasses import dataclass, field

from src.config import COURSE_CARDS_PATH

# ---------- 源 1：静态映射表（人工整理；扩 MSc 项目时逐条补，未验证不入表） ----------
# 格式：缩写/惯称/中文名 → (官方全称, level)
STATIC_PROGRAMME_ALIASES = {
    "CCA": ("MSc Computer Control & Automation", "graduate"),
    "计算机控制与自动化": ("MSc Computer Control & Automation", "graduate"),  # 中文惯称（D3.5）
    # 本科：CCDS 学院 5 个专业。课程卡片的 source_categories 字段自带这些代码
    # （如 SC2001 → CSC/CE/DSAI/AISC），2026-10-24 实测覆盖率 156/156
    "CSC": ("Computer Science", "undergraduate"),
    "CS": ("Computer Science", "undergraduate"),
    "计算机科学": ("Computer Science", "undergraduate"),  # 中文惯称（D4 grounding 需要）
    "DSAI": ("Data Science and AI", "undergraduate"),
    "数据科学与人工智能": ("Data Science and AI", "undergraduate"),
    "CE": ("Computer Engineering", "undergraduate"),
    "计算机工程": ("Computer Engineering", "undergraduate"),
    "AISC": ("AI and Society", "undergraduate"),
    "人工智能与社会": ("AI and Society", "undergraduate"),
    "COMP": ("Computing", "undergraduate"),
}

# 项目名 → 检索过滤代码（与课程卡 Curricula / Programme 字段里的代码对齐）
_PROGRAMME_CODES = {
    "csc": "CSC", "cs": "CSC", "computer science": "CSC", "计算机科学": "CSC",
    "dsai": "DSAI", "data science and ai": "DSAI", "数据科学与人工智能": "DSAI",
    "ce": "CE", "computer engineering": "CE", "计算机工程": "CE",
    "aisc": "AISC", "ai and society": "AISC", "人工智能与社会": "AISC",
    "comp": "COMP", "computing": "COMP",
    "cca": "CCA", "computer control & automation": "CCA",
    "计算机控制与自动化": "CCA",
}


def programme_code(text: str) -> str | None:
    """用户说的项目名 → 检索过滤用的标准代码（CSC/CE/DSAI/AISC/COMP/CCA）。"""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t in _PROGRAMME_CODES:
        return _PROGRAMME_CODES[t]
    if len(t) <= 3:  # 短串只做精确匹配，避免 "ce" 误中任意英文子串
        return None
    for key, code in sorted(_PROGRAMME_CODES.items(),
                            key=lambda kv: len(kv[0]), reverse=True):
        if len(key) <= 3:
            # 短键只允许精确命中（上面已处理）。否则 "cs" 会命中 "robotics"
            # ——D4 Q08 实测：Robotics 项目被补成 programme=CSC，过滤后 0 条。
            continue
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(key)}(?![A-Za-z0-9])", t):
            return code
        if t in key or key in t:
            return code
    return None


# 学历词（与 D2 v12 提示词规则同源，代码层确定性执行）
GRADUATE_WORDS = ["研究生", "硕士", "博士生", "master", "msc", "phd", "graduate",
                  "postgraduate",
                  # 口语年级（方案 A 实测：「我今年研一」LLM 提取对了但词表没有）
                  "研一", "研二", "研三", "硕一", "硕二"]
UNDERGRADUATE_WORDS = ["本科生", "本科", "undergraduate", "bachelor", "beng",
                       "大一", "大二", "大三", "大四"]

# 英文核心词提取时忽略的学位/连接噪声词（避免 "msc xx" 与用户说的 "xx" 对不上）
_DEGREE_NOISE = {"msc", "meng", "beng", "ms", "ma", "phd", "master", "bachelor",
                 "of", "and", "in", "the", "programme", "program", "programmes",
                 "programs", "degree"}

# 第一人称身份声明句式：「我是 X 新生/学生/在读」或「我是 X 专业/项目」（D3.5 补后者：
# 复测「我是 AAI 专业」此前落 unknown）
_IDENTITY_CLAIM_RE = re.compile(
    r"我是\s*(?:一名|一个)?\s*"
    r"([A-Za-z0-9&\u4e00-\u9fa5][A-Za-z0-9&\u4e00-\u9fa5\s.]{0,39}?)"
    r"\s*(?:的)?\s*(?:专业|项目|新生|学生|在读)"
)

# 非第一人称的未收录项目提及：「AAI专业课程有哪些」
# 英文缩写（2-6 位大写字母）紧邻 专业/项目 —— 用户把它当项目问，但不在表内。
# 只认「专业/项目」不认「课程」："AI 课程有哪些"是真在找课，不是报身份。
_UNKNOWN_MAJOR_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z]{2,6})\s*(?:的)?\s*(?:专业|项目)")


def _core_words(text: str) -> list[str]:
    """提取英文实义词：小写、去标点、去学位噪声词、去 ≤2 字符的短词。"""
    return [w for w in re.findall(r"[a-z]+", text.lower())
            if w not in _DEGREE_NOISE and len(w) > 2]


def _core_phrase_hit(full_key: str, text_lower: str) -> bool:
    """表项全称的核心词连续片段（≥2 词）是否出现在用户输入中。

    英文口头简称兜底（D3.5）：用户说 "computer control" 时命中
    "msc computer control & automation"（核心词 computer/control/automation，
    片段 [computer, control] 命中）；只含单个核心词（如 "automation"）不命中，
    避免过度放宽。多项目命中时走 ambiguous 候选列表，安全。
    """
    key_words = _core_words(full_key)
    user_words = _core_words(text_lower)
    if len(key_words) < 2 or len(user_words) < 2:
        return False
    for size in range(len(key_words), 1, -1):
        for i in range(len(key_words) - size + 1):
            phrase = key_words[i:i + size]
            for j in range(len(user_words) - size + 1):
                if user_words[j:j + size] == phrase:
                    return True
    return False


@dataclass
class IdentityResult:
    """身份识别结果。

    status:
      confirmed     —— level 已确定（学历词直判或项目词唯一命中）
      ambiguous     —— 项目词多命中，candidates 非空，须让用户选
      unrecognized  —— 第一人称声明了未收录项目（"我是 SPML 新生"），claim 存词
      unknown       —— 无任何信号，开放反问
    """

    status: str
    level: str | None = None          # graduate / undergraduate / None
    programme: str | None = None      # 命中的项目官方全称
    matched_signal: str | None = None # 命中的信号词（学历词或项目词）
    claim: str | None = None          # unrecognized 时用户声明的未知项目词
    candidates: list = field(default_factory=list)  # ambiguous 时候选 [(显示名, level)]

    @property
    def needs_ask(self) -> bool:
        return self.status in ("ambiguous", "unknown", "unrecognized")

    def ask_message(self) -> str:
        if self.status == "unrecognized":
            known = "、".join(_known_programmes("graduate")) or "（暂无）"
            # D3.5：反问带路——说清覆盖边界 + 给可直接照抄的示例格式，
            # 降低"用户答了第二次仍答不中"的概率
            return (f"未能识别「{self.claim}」对应的项目。\n"
                    f"目前研究生侧课程数据仅覆盖：{known}（其他 MSc 项目暂未收录）；"
                    f"本科侧覆盖 NTU WIS 官方目录课程。\n"
                    f"可直接回复如「我是 CCA 研究生」，或回复“本科”/“研究生”按学历查询。")
        if self.status == "ambiguous":
            lines = "\n".join(f"  {i}. {name}（{lv}）"
                              for i, (name, lv) in enumerate(self.candidates, 1))
            return f"您提到的词可能对应多个项目，请回复编号确认：\n{lines}"
        return "请问您是本科生还是研究生？回复“本科”或“研究生”即可。"


def _load_programmes() -> dict:
    """源 2：从课程卡片提取 Programme 字段 → {小写关键词: (全称, level, 缩写)}。

    卡片 programme 形如 "MSc Computer Control & Automation (CCA)"，
    括号内即圈内惯称缩写，与全称一起注册为可匹配信号。
    """
    table = {}
    try:
        with open(COURSE_CARDS_PATH, encoding="utf-8") as f:
            for line in f:
                card = json.loads(line)
                prog = card.get("programme") or ""
                if not prog:
                    continue
                m = re.search(r"\(([^()]+)\)\s*$", prog)
                abbr = m.group(1).strip() if m else None
                full = re.sub(r"\s*\([^()]+\)\s*$", "", prog).strip()
                level = card.get("level") or "graduate"
                table[full.lower()] = (full, level, abbr)
                if abbr:
                    table[abbr.lower()] = (full, level, abbr)
    except FileNotFoundError:
        pass  # 库缺失时仅靠静态表 + 反问兜底
    return table


# 匹配信号 → (全称, level)：静态表优先（后加载会被静态表覆盖？不，静态表先写入，库内补充）
def _build_lookup() -> dict:
    lookup = {}
    for abbr, (full, level) in STATIC_PROGRAMME_ALIASES.items():
        lookup[abbr.lower()] = (full, level, abbr)
        lookup[full.lower()] = (full, level, abbr)
    # 库内 Programme 字段（与静态表冲突时静态表优先：已验证条目权威）
    for key, val in _load_programmes().items():
        lookup.setdefault(key, val)
    return lookup


_LOOKUP = _build_lookup()


def _known_programmes(level: str | None = None) -> list[str]:
    """当前双源查表覆盖的项目全称（去重保序），供反问时告知用户支持范围。

    level="graduate" 时只列研究生项目——反问文案里的“研究生侧覆盖”不能
    混入 CSC/CE 等本科专业（D4 预检发现的中文别名扩展后更明显）。
    """
    seen = []
    for full, lv, _abbr in _LOOKUP.values():
        if level and lv != level:
            continue
        if full not in seen:
            seen.append(full)
    return seen


def claimed_programme(text: str) -> str | None:
    """用户原话里声明的项目名（字面提取，不做身份判定）。

    只用于 D4 Q14 的 grounding 失败场景：模型把库内项目安到用户没说的身份
    上时，用用户原话（如“机械工程”）进入覆盖说明，而不是沿用模型猜的 CCA。
    """
    text = text or ""
    m = _IDENTITY_CLAIM_RE.search(text)
    if m:
        return m.group(1).strip()
    m = _UNKNOWN_MAJOR_RE.search(text)
    return m.group(1).strip() if m else None


def programme_mentioned(text: str, programme: str) -> bool:
    """模型理解出的项目是否真的出现在用户话里（grounding 校验，确定性）。

    D4 Q14 实测：用户说“机械工程专业”，Planner 把 assumed_identity.programme
    填成 CCA 且 confidence=certain，代码只校验“CCA 在不在库内”就放行，
    结果推荐了 5 门 CCA 课。这里只做一件过滤：项目名必须能在用户原话
    （或允许的历史上下文）里找到证据，否则视为模型臆断。
    """
    t = (text or "").lower()
    p = (programme or "").strip().lower()
    if not t or not p:
        return False
    candidates: set[str] = {p}

    # 同一项目的静态别名/全称（CSC ↔ CS ↔ Computer Science；
    # CCA ↔ 计算机控制与自动化 ↔ MSc Computer Control & Automation）
    target_full = None
    for alias, (full, _lv) in STATIC_PROGRAMME_ALIASES.items():
        if p == alias.lower() or p == full.lower():
            target_full = full.lower()
            break
    if target_full:
        for alias, (full, _lv) in STATIC_PROGRAMME_ALIASES.items():
            if full.lower() == target_full:
                candidates.add(alias.lower())
                candidates.add(full.lower())

    # 库内 Programme 全称/缩写（如 MSc Robotics and Intelligent Systems）
    for key, (full, _lv, abbr) in _LOOKUP.items():
        if p == key or p in full.lower() or full.lower() in p:
            candidates.add(key)
            candidates.add(full.lower())
            if abbr:
                candidates.add(abbr.lower())

    for c in candidates:
        if not c:
            continue
        if len(c) <= 3:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(c)}(?![A-Za-z0-9])", t):
                return True
        elif c in t:
            return True

    # 口头简称：computer control / robotics 这类片段
    for key, (full, _lv, _abbr) in _LOOKUP.items():
        if p == key or p in full.lower() or full.lower() in p:
            if _core_phrase_hit(full, t):
                return True
            for word in _core_words(full):
                if len(word) >= 6 and word in t:
                    return True
    return False


def explicit_level(text: str) -> str | None:
    """用户原话中**明说**的学历层次（graduate / undergraduate / None）。

    出路 1（2026-10-24）：模型做身份理解时会臆断库外项目的层次
    （实测把 SPML 说成"本科生 certain"）。用这个函数区分「用户明说的」
    与「模型猜的」——只有用户明说层次时，才允许库外项目继续检索。
    """
    return _match_level_word(text)


def _match_level_word(text: str) -> str | None:
    """学历词直判（大小写不敏感）。返回 graduate / undergraduate / None。"""
    lower = text.lower()
    for w in GRADUATE_WORDS:
        if w in lower:
            return "graduate"
    for w in UNDERGRADUATE_WORDS:
        if w in lower:
            return "undergraduate"
    return None


def _match_programme(text: str) -> list[tuple[str, str, str]]:
    """项目词查表（D3.5 加模糊匹配）。

    三类信号按 key 形态分流：
      - 中文别名：直接子串匹配（中文无词边界）
      - 英文全称：完整子串匹配，或核心词连续片段匹配（"computer control" 命中）
      - 缩写：词边界匹配（避免 OCCASION 误中 CCA）
    """
    hits = {}
    lower = text.lower()
    for key, (full, level, abbr) in _LOOKUP.items():
        if re.search(r"[\u4e00-\u9fa5]", key):
            if key in lower:
                hits.setdefault(full, (key, full, level))
        elif re.fullmatch(r"[a-z&\s]+", key) and len(key) > 4:
            if key in lower or _core_phrase_hit(key, lower):
                hits.setdefault(full, (key, full, level))
        else:
            # 缩写：ASCII 字母数字边界。不能用 \b——中文字符在 Unicode 下也算 \w，
            # 「CCA专业」的 CCA 后不是边界，曾漏匹配（D3.5 二轮实测）
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(key)}(?![A-Za-z0-9])", lower):
                hits.setdefault(full, (key, full, level))
    return list(hits.values())


def identify(question: str) -> IdentityResult:
    """身份识别主入口（确定性，无 LLM 参与 judgement）。"""
    # 1. 学历词直判（最强信号）
    level = _match_level_word(question)
    if level:
        # 学历词出现时不做项目词消歧：用户明说的层次优先
        # （如"本科 CCA 学生"= 本科生提到课外活动，不应被项目表带偏）
        return IdentityResult(status="confirmed", level=level,
                              matched_signal=f"学历词→{level}")

    # 2. 项目词查表
    hits = _match_programme(question)
    if len(hits) == 1:
        _, full, lv = hits[0]
        return IdentityResult(status="confirmed", level=lv, programme=full,
                              matched_signal=f"项目词→{full}")
    if len(hits) > 1:
        cands = [(full, lv) for _, full, lv in hits]
        return IdentityResult(status="ambiguous", candidates=cands,
                              matched_signal="项目词多命中")

    # 3. 身份声明句式兜底：「我是 X 新生/学生/在读」但 X 不在表内
    #    （用户明确声明了身份，即使会话已有缓存也不能沿用——换专业场景）
    m = _IDENTITY_CLAIM_RE.search(question)
    if m:
        claim = m.group(1).strip()
        return IdentityResult(status="unrecognized", claim=claim,
                              matched_signal=f"未知项目声明→{claim}")

    # 3b. 非第一人称的项目提及：「AAI 专业课程有哪些」——没有「我是」句式，
    #     但用户显然把 X 当作项目在问。若 X 是英文缩写且紧邻 专业/项目/课程，
    #     视为未收录项目（宁可反问，不把它当普通关键词检索出一堆无关课）。
    m = _UNKNOWN_MAJOR_RE.search(question)
    if m:
        claim = m.group(1)
        return IdentityResult(status="unrecognized", claim=claim,
                              matched_signal=f"未收录项目提及→{claim}")
    return IdentityResult(status="unknown")


def _normalize_level(value: str) -> str | None:
    """LLM 归一化后的学历值 → 内部两档（graduate / undergraduate）。

    D3.5 实测：「研究生一年级」「博一」这类口语年级用词表穷举不完，
    改为由 LLM 提取时归一化为三档标准值（graduate / undergraduate / 博士→graduate），
    代码只认标准值，不再追着口语变体扩词表。
    """
    v = (value or "").strip().lower()
    if v in ("graduate", "undergraduate"):
        return v
    if v in ("doctor", "doctoral", "phd", "博士", "博士生"):
        return "graduate"  # 博士属研究生院，内部两档归 graduate
    return _match_level_word(v) if v else None


def judge_programme(programme_text: str, level: str = "") -> IdentityResult:
    """对 LLM 提取出的项目/学历**原文**做确定性裁决（提取归模型，裁决归代码）。

    方案 A（2026-10-24，用户拍板）：代码识别不出时，让 LLM 理解"用户说了什么"，
    这里仍用查表决定"那是什么项目"——查不到就 unrecognized（反问）。
    危害不对称保持不变：提取错了最坏是反问，不会静默给出错误推荐。
    """
    programme_text = (programme_text or "").strip()
    if not programme_text:
        lv = _normalize_level(level)
        if lv:
            return IdentityResult("confirmed", level=lv,
                                  matched_signal=f"LLM提取学历→{lv}")
        return IdentityResult("unknown")
    hits = _match_programme(programme_text)
    if len(hits) == 1:
        _, full, lv = hits[0]
        return IdentityResult("confirmed", level=lv, programme=full,
                              matched_signal=f"LLM提取项目→{full}")
    if len(hits) > 1:
        cands = [(full, lv) for _, full, lv in hits]
        return IdentityResult("ambiguous", candidates=cands,
                              matched_signal="LLM提取项目多命中")
    return IdentityResult("unrecognized", claim=programme_text,
                          matched_signal=f"LLM提取未收录→{programme_text}")


def resolve_reply(reply_text: str, pending: IdentityResult) -> IdentityResult:
    """用户对反问的答复 → 身份确定（交互层调用）。

    支持：直接学历词（"研究生"/"本科"）、候选编号（"1"/"2"）。
    """
    level = _match_level_word(reply_text)
    if level:
        return IdentityResult(status="confirmed", level=level,
                              matched_signal=f"用户答复→{level}")
    if pending.status == "ambiguous":
        m = re.search(r"[12]", reply_text.strip())
        if m:
            idx = int(m.group()) - 1
            if 0 <= idx < len(pending.candidates):
                name, lv = pending.candidates[idx]
                return IdentityResult(status="confirmed", level=lv, programme=name,
                                      matched_signal=f"用户选候选→{name}")
    # 答复里出现项目词也接受
    hits = _match_programme(reply_text)
    if len(hits) == 1:
        _, full, lv = hits[0]
        return IdentityResult(status="confirmed", level=lv, programme=full,
                              matched_signal=f"答复项目词→{full}")
    return IdentityResult(status="unknown")


if __name__ == "__main__":
    # 冒烟：python -m src.identity
    cases = [
        "我是 CCA 2027 春入学的新生，想选机器学习方向的课",   # 项目词唯一命中 → graduate
        "我是研究生，推荐几门课",                              # 学历词直判
        "我是本科生，SC2001 怎么样",                           # 学历词直判 → undergraduate
        "OCCASIONALLY 我想知道 SC2001 的先修",                # 缩写词边界：不误中 CCA → unknown
        "推荐一些好课",                                        # 零命中 → unknown
        "我是 SPML 新生，推荐几门机器学习相关的课",            # 未知项目声明 → unrecognized
        "我是 CCA 新生",                                       # 已知项目声明 → confirmed
        "我是新生，推荐几门课",                                # 声明句式无项目词 → unknown
        # ---- D3.5 新增：模糊匹配与「专业」句式 ----
        "我是 AAI 专业",                                       # 未知项目 + 专业句式 → unrecognized
        "我是计算机控制与自动化专业",                          # 中文别名 → confirmed
        "我是 computer control 专业，推荐几门课",              # 英文不完整短语 → confirmed
        "我是 CCA 专业",                                       # 缩写 + 专业句式 → confirmed
        # ---- D3.5 二轮：非第一人称的项目提及 ----
        "AAI专业课程有哪些？",                                 # 无"我是"，但 AAI 作项目问 → unrecognized
        "AI 课程有哪些",                                       # 紧邻"课程"非"专业"，不算项目 → 不触发
        "EE6407 几 AU",                                        # 课码属性查询 → unknown（不需身份）
        "CCA专业课程有哪些？",                                 # 表内项目 → confirmed
    ]
    for q in cases:
        r = identify(q)
        print(f"{q!r:55s} → status={r.status:14s} level={r.level} "
              f"claim={r.claim} signal={r.matched_signal}")
    print("\n--- 反问文案（unrecognized） ---")
    print(identify("我是 AAI 专业").ask_message())
