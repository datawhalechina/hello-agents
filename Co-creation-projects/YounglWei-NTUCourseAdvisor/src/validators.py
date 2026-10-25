"""学位规则校验工具（D3，requirements Must 第 5 条）。

4 项检查，做成一个可展开工具（框架 RAGTool 同款 expandable + @tool_action 模式），
注册后自动展开为 4 个子工具：
  1. check_schedule_conflict  课表时间冲突检测（仅有课表数据的课；研究生课表官方不公开，如实告知）
  2. check_specialized_electives  专选门数 ≥4（CCA Option1/Option2 均要求）
  3. check_au_limit  AU 上限校验（Option1 通选 ≤18AU / Option2 通选 ≤12AU；Option1 专选 ≥12AU）
  4. check_prerequisites  先修/互斥/限修提示（转述卡片字段，不推断）

学位规则来源（可溯源）：NTU 官网 CCA 项目页 Programme Structure
https://www.ntu.edu.sg/education/graduate-programme/master-of-science-in-computer-control-automation
规则拍板记录：decisions.md 2026-10-22 行（Option1 = 10 门 30AU：专选≥4 门/≥12AU +
通选 6 门/≤18AU；Option2 = 8 门 + 论文 6AU：专选≥4 + 通选 4 门/≤12AU；每门 3AU、39 学时）。
"""

import json
import re
from pathlib import Path

from hello_agents.tools.base import Tool, ToolParameter, tool_action
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.response import ToolResponse

from src.config import COURSE_CARDS_PATH, DATA_DIR

CCA_PROGRAMME_URL = (
    "https://www.ntu.edu.sg/education/graduate-programme/"
    "master-of-science-in-computer-control-automation"
)
# 课程卡片 programme 字段里 CCA 的标识（Robotics 等研究生课不得计入 CCA 规则）
CCA_PROGRAMME_MARK = "Computer Control & Automation"

# CCA 学位规则（官网 Programme Structure，decisions.md 2026-10-22 拍板）
CCA_OPTIONS = {
    1: {"name": "Option 1（10 门课 30 AU，无论文）",
        "total_courses": 10, "specialized_min_count": 4, "specialized_min_au": 12.0,
        "general_courses": 6, "general_max_au": 18.0},
    2: {"name": "Option 2（8 门课 + 论文 6 AU）",
        "total_courses": 8, "specialized_min_count": 4,
        "general_courses": 4, "general_max_au": 12.0},
}

SCHEDULE_FILES = ["schedule_csc_y1_2026_1.jsonl"]  # 课表数据覆盖范围（如实告知边界）

_COURSE_CODE_RE = re.compile(r"\b([A-Z]{2}\d{4}[A-Z]?)\b")


def _load_cards() -> dict:
    """course_code → 卡片 dict（模块级缓存）。"""
    cards = {}
    if COURSE_CARDS_PATH.exists():
        with open(COURSE_CARDS_PATH, encoding="utf-8") as f:
            for line in f:
                card = json.loads(line)
                cards[card["course_code"].upper()] = card
    return cards


def _load_schedule() -> list:
    """全部课表记录（course_code, day, time, index...）。"""
    rows = []
    for name in SCHEDULE_FILES:
        p = DATA_DIR / name
        if p.exists():
            with open(p, encoding="utf-8") as f:
                rows.extend(json.loads(line) for line in f if line.strip())
    return rows


_CARDS = None
_SCHEDULE = None


def _cards():
    global _CARDS
    if _CARDS is None:
        _CARDS = _load_cards()
    return _CARDS


def _schedule():
    global _SCHEDULE
    if _SCHEDULE is None:
        _SCHEDULE = _load_schedule()
    return _SCHEDULE


def _normalize_codes(course_codes: list) -> list[str]:
    """课码规范化为大写去空格；也接受整段文本（从中提取课码）。"""
    if isinstance(course_codes, str):
        return _COURSE_CODE_RE.findall(course_codes.upper())
    codes = []
    for c in course_codes:
        codes.extend(_COURSE_CODE_RE.findall(str(c).upper()))
    # 去重保序
    return list(dict.fromkeys(codes))


def _parse_au(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time_range(t: str):
    """'1030-1220' → (630, 740) 分钟数；异常返回 None。"""
    m = re.match(r"^(\d{2})(\d{2})-(\d{2})(\d{2})$", t.strip())
    if not m:
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    return h1 * 60 + m1, h2 * 60 + m2


class DegreeAuditTool(Tool):
    """CCA 学位规则与选课校验（4 个子工具）。数据：课程卡片 + CSC 本科课表。"""

    def __init__(self):
        super().__init__(
            name="degree_audit",
            description="NTU 选课校验：课表冲突/专选门数/AU上限/先修互斥（学位规则以官网 Programme Structure 为准）",
            expandable=True,
        )

    def get_parameters(self) -> list[ToolParameter]:
        return []  # expandable：参数由各 @tool_action 方法定义

    def run(self, parameters):
        return ToolResponse.error(ToolErrorCode.INVALID_PARAM,
                                  "请使用展开后的子工具（check_schedule_conflict 等）")

    # ---------- 1. 课表时间冲突检测 ----------
    @tool_action("check_schedule_conflict", "检测所选课程之间的课表时间冲突（仅有课表数据的课程可检测）")
    def check_schedule_conflict(self, course_codes: list) -> ToolResponse:
        """检测课程之间的时间冲突。

        Args:
            course_codes: 课程代码列表，如 ["SC1003", "SC1005"]
        """
        codes = _normalize_codes(course_codes)
        if not codes:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "未识别到课程代码")

        # 按课码收集团组时段（同门课的 LEC/TUT 组件不算冲突，跨课才算）
        slots = {}  # code -> [(day, (start, end), index, type)]
        missing = []
        for code in codes:
            rows = [r for r in _schedule() if r["course_code"].upper() == code]
            if not rows:
                missing.append(code)
                continue
            slots[code] = []
            for r in rows:
                tr = _parse_time_range(r.get("time", ""))
                if r.get("day") and tr:
                    slots[code].append((r["day"], tr, r.get("index"), r.get("type")))

        # 冲突聚合到课程对级别：每门课的多个 index 是平行班（学生只注册一个），
        # index 级全量两两比对会产生组合爆炸，如实输出"课程对 + 重叠 index 组合数"
        pair_hits = {}
        checked = list(slots)
        for i, a in enumerate(checked):
            for b in checked[i + 1:]:
                n = 0
                sample = None
                for (da, ta, ia, ya) in slots[a]:
                    for (db, tb, ib, yb) in slots[b]:
                        if da == db and ta[0] < tb[1] and tb[0] < ta[1]:
                            n += 1
                            if sample is None:
                                sample = {"day": da,
                                          "time": f"{ta[0]//60:02d}{ta[0]%60:02d}-{ta[1]//60:02d}{ta[1]%60:02d}"}
                if n:
                    pair = tuple(sorted((a, b)))
                    pair_hits.setdefault(pair, {"count": 0, "sample": sample})
                    pair_hits[pair]["count"] += n

        lines = []
        if pair_hits:
            lines.append(f"检出 {len(pair_hits)} 对课程存在时段重叠：")
            for (a, b), info in pair_hits.items():
                lines.append(f"  {a} 与 {b}：{info['count']} 个班次组合重叠"
                             f"（示例时段 {info['sample']['day']} {info['sample']['time']}）")
            lines.append("注：每门课的多个 index 为平行班，实际是否冲突取决于注册的 index，"
                         "请选课时错开时段。")
        else:
            lines.append("有课表数据的课程之间未检出时间冲突。")
        if missing:
            lines.append(f"以下课程无课表数据（研究生课表官方不公开/课表库未覆盖），无法检测冲突，"
                         f"请以学校发布的时间安排为准：{', '.join(missing)}")
        lines.append(f"课表数据范围：CSC 本科 2026 学年第 1 学期（{len(_schedule())} 条时段记录）。")

        return ToolResponse.success(
            text="\n".join(lines),
            data={"conflict_pairs": {f"{a}x{b}": info for (a, b), info in pair_hits.items()},
                  "no_schedule_data": missing,
                  "checked_with_data": checked},
        )

    # ---------- 2. 专选门数 ≥4 ----------
    @tool_action("check_specialized_electives", "检查所选课程中 CCA 专选（specialised elective）门数是否 ≥4")
    def check_specialized_electives(self, course_codes: list) -> ToolResponse:
        """检查专选门数是否满足 CCA 要求（Option1/Option2 均要求专选 ≥4 门）。

        Args:
            course_codes: 课程代码列表
        """
        codes = _normalize_codes(course_codes)
        if not codes:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "未识别到课程代码")

        cards = _cards()
        specialized, general, not_in_cca, unknown = [], [], [], []
        for code in codes:
            card = cards.get(code)
            if card is None:
                unknown.append(code)
            elif card.get("level") != "graduate":
                not_in_cca.append(code)
            elif card.get("category") == "specialized_elective":
                specialized.append(code)
            elif card.get("category") == "general_elective":
                general.append(code)
            else:
                not_in_cca.append(code)

        ok = len(specialized) >= 4
        lines = [f"专选门数：{len(specialized)} 门"
                 f"（{', '.join(specialized) if specialized else '无'}）",
                 f"CCA 要求：专选 ≥4 门（Option 1 与 Option 2 相同）",
                 "结论：" + ("满足 ≥4 门要求。" if ok else "未满足 ≥4 门要求，还需 "
                             f"{max(0, 4 - len(specialized))} 门专选。")]
        if general:
            lines.append(f"另识别到通选 {len(general)} 门：{', '.join(general)}")
        if not_in_cca:
            lines.append(f"以下课程不在 CCA 研究生课库内（本科课或非本项目课），"
                         f"是否计入学位请以项目页/学院规定为准：{', '.join(not_in_cca)}")
        if unknown:
            lines.append(f"以下课程码在课程库中未查到，无法判断类别：{', '.join(unknown)}")
        lines.append(f"规则来源：{CCA_PROGRAMME_URL}")

        return ToolResponse.success(
            text="\n".join(lines),
            data={"specialized": specialized, "general": general,
                  "not_in_cca": not_in_cca, "unknown": unknown,
                  "meets_minimum": ok, "rule_source": CCA_PROGRAMME_URL},
        )

    # ---------- 3. AU 上限 ----------
    @tool_action("check_au_limit", "按 CCA Option 1/2 校验所选课程的 AU 分布（通选上限/专选下限）")
    def check_au_limit(self, course_codes: list, option: int = 1) -> ToolResponse:
        """按指定 Option 校验 AU 上限/下限。

        Args:
            course_codes: 课程代码列表
            option: 1 = Option 1（10 门 30AU，通选 ≤18AU，专选 ≥12AU）；
                    2 = Option 2（8 门 + 论文，通选 ≤12AU）
        """
        if option not in CCA_OPTIONS:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "option 只支持 1 或 2")
        codes = _normalize_codes(course_codes)
        if not codes:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "未识别到课程代码")

        rule = CCA_OPTIONS[option]
        cards = _cards()
        spec_au = gen_au = 0.0
        spec_cnt = gen_cnt = 0
        no_au, no_credit_ruling, non_rule_category = [], [], []
        for code in codes:
            card = cards.get(code)
            if card is None:
                no_credit_ruling.append(code)
                continue
            # 只认 CCA 研究生课：Robotics 等其他项目的研究生课不得计入 CCA 规则
            if (card.get("level") != "graduate"
                    or CCA_PROGRAMME_MARK not in (card.get("programme") or "")):
                no_credit_ruling.append(code)
                continue
            au = _parse_au(card.get("au"))
            if au is None:
                no_au.append(code)
                continue
            if card.get("category") == "specialized_elective":
                spec_au += au; spec_cnt += 1
            elif card.get("category") == "general_elective":
                gen_au += au; gen_cnt += 1
            else:
                # 核心课/其他类别不属于 Option 1/2 的专选/通选统计口径
                non_rule_category.append(code)

        lines = [f"按 {rule['name']} 校验："]
        checks = []
        if "general_max_au" in rule:
            ok_g = gen_au <= rule["general_max_au"]
            checks.append(ok_g)
            lines.append(f"  通选：{gen_cnt} 门 {gen_au:g} AU（上限 {rule['general_max_au']:g} AU）——"
                         + ("符合" if ok_g else "超出上限"))
        if "specialized_min_au" in rule:
            ok_s = spec_au >= rule["specialized_min_au"]
            checks.append(ok_s)
            lines.append(f"  专选：{spec_cnt} 门 {spec_au:g} AU（下限 {rule['specialized_min_au']:g} AU）——"
                         + ("符合" if ok_s else "不足"))
        lines.append(f"  专选门数：{spec_cnt} 门（要求 ≥{rule['specialized_min_count']} 门）——"
                     + ("符合" if spec_cnt >= rule["specialized_min_count"] else "不足"))
        lines.append("总体结论：" + ("当前选课组合符合该 Option 的 AU 约束。" if all(checks)
                     else "存在不满足项，见上。"))
        if no_au:
            lines.append(f"注意：{', '.join(no_au)} 的课程卡片未标注 AU，未计入统计，请以项目页为准。")
        if no_credit_ruling:
            lines.append(f"以下课程不在 CCA 研究生课库内（本科课或其他项目课），是否可计入学位请以项目页/学院规定为准："
                         f"{', '.join(no_credit_ruling)}")
        if non_rule_category:
            lines.append(f"以下 CCA 课程的类别不是专选/通选（核心课或其他），未计入本工具统计，"
                         f"请以项目页为准：{', '.join(non_rule_category)}")
        lines.append("注：本工具只校验专选门数与 AU 分布，不校验总门数"
                     "（Option 1 需 10 门；Option 2 需 8 门 + 论文 6 AU）与论文要求；"
                     "完整学位合规请以项目页为准。")
        lines.append(f"规则来源：{CCA_PROGRAMME_URL}")

        return ToolResponse.success(
            text="\n".join(lines),
            data={"option": option, "specialized_au": spec_au, "general_au": gen_au,
                  "specialized_count": spec_cnt, "general_count": gen_cnt,
                  "no_au": no_au, "not_ruled": no_credit_ruling,
                  "non_rule_category": non_rule_category,
                  "rule_source": CCA_PROGRAMME_URL},
        )

    # ---------- 4. 先修/互斥/限修 ----------
    @tool_action("check_prerequisites", "检查所选课程的先修要求、互斥课程与限修提示（转述课程卡片字段）")
    def check_prerequisites(self, course_codes: list) -> ToolResponse:
        """检查先修是否满足、互斥是否同选、限修提示（依据课程卡片字段，如实转述）。

        Args:
            course_codes: 课程代码列表（当前已选/计划选修的课程）
        """
        codes = _normalize_codes(course_codes)
        if not codes:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "未识别到课程代码")
        selected = set(codes)
        cards = _cards()

        lines, missing, no_prereq_info = [], [], []
        for code in codes:
            card = cards.get(code)
            if card is None:
                missing.append(code)
                continue
            prereq = (card.get("prerequisite") or "").strip()
            mutex = (card.get("mutually_exclusive") or "").strip()
            na = (card.get("not_available_to") or "").strip()
            if card.get("level") == "graduate" and not (prereq or mutex or na):
                no_prereq_info.append(code)
                continue
            if prereq:
                req_codes = set(_COURSE_CODE_RE.findall(prereq.upper()))
                satisfied = bool(req_codes & selected) if req_codes else None
                note = ("已满足（所选列表含先修课）" if satisfied
                        else "未满足——所选列表中未见先修课" if satisfied is False
                        else "卡片未解析出课码，原文如下")
                lines.append(f"{code} 先修要求：{prereq!r} → {note}")
            if mutex:
                clash = set(_COURSE_CODE_RE.findall(mutex.upper())) & selected - {code}
                if clash:
                    lines.append(f"{code} 互斥警告：与所选 {', '.join(sorted(clash))} 互斥，不可同选！"
                                 f"（卡片原文：{mutex}）")
                else:
                    lines.append(f"{code} 互斥课程：{mutex}（当前所选未包含，无冲突）")
            if na:
                lines.append(f"{code} 限修提示：不开放给 {na}")
        if no_prereq_info:
            lines.append(f"以下研究生课程卡片未列先修/互斥/限修信息（以 CCA 项目页为准）："
                         f"{', '.join(no_prereq_info)}")
        if missing:
            lines.append(f"以下课程码在课程库中未查到：{', '.join(missing)}")
        if not lines:
            lines.append("所选课程均无先修/互斥/限修记录。")

        return ToolResponse.success(
            text="\n".join(lines),
            data={"missing": missing, "no_prereq_info": no_prereq_info},
        )


if __name__ == "__main__":
    # 冒烟：python -m src.validators
    tool = DegreeAuditTool()
    picked = ["EE6203", "EE6205", "EE6220", "EE6258",  # CCA 专选 4 门
              "EE6111",                                   # 通选（卡片无 AU）
              "SC1003", "SC1005", "CC0001"]               # 本科课（课表库有 SC1003/SC1005/CC0001）
    print("=== check_schedule_conflict ===")
    print(tool.check_schedule_conflict(picked).text)
    print("\n=== check_specialized_electives ===")
    print(tool.check_specialized_electives(picked).text)
    print("\n=== check_au_limit(option=1) ===")
    print(tool.check_au_limit(picked, option=1).text)
    print("\n=== check_prerequisites ===")
    print(tool.check_prerequisites(["SC1003", "EE1102", "SC2001", "CB1131"]).text)
