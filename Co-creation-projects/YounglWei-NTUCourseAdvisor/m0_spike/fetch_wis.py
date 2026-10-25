"""M0 数据抓取 ①：WIS 本科课程目录（计算机学院 CCDS 相关分类）

数据源：https://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main（NTU 官方，无需登录）
提交端点（POST）：https://wis.ntu.edu.sg/pls/webexe/AUS_SUBJ_CONT.main_display1
页面结构与表单参数见 03-数据源侦察.md。

用法：python m0_spike/fetch_wis.py
产出：data/ugrad_ccds_2026_1.jsonl、data/ugrad_ccds_2026_2.jsonl
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------- 配置 ----------

# WIS 查询端点（/pls/webexe/ 与 /webexe/owa/ 两路径等效，实测通过）
URL = "https://wis.ntu.edu.sg/pls/webexe/AUS_SUBJ_CONT.main_display1"

# 溯源用入口页（POST 参数无法直接还原，但可按 source_categories 在入口页复现查询）
ENTRY_URL = "https://wis.ntu.edu.sg/webexe/owa/aus_subj_cont.main"

# 抓哪些学期：
#   2026_1 = 2026 年 8-12 月
#   2026_2 = 2027 年 1-5 月（CCA 2027 春入学新生的第一个学期）
SEMESTERS = ["2026_1", "2026_2"]

# 抓哪些分类（值格式 "学院代码;细分;年级;F"，取自入口页下拉框）
# 冷启动范围：CCDS 五个专业全年级 + 跨院通选视角（GLOAD）
CATEGORIES = (
    [f"CSC;;{y};F" for y in range(1, 5)]    # Computer Science
    + [f"CE;;{y};F" for y in range(1, 5)]   # Computer Engineering
    + [f"DSAI;;{y};F" for y in range(1, 5)]  # Data Science & AI
    + [f"COMP;;{y};F" for y in range(1, 4)]  # Computing（通识年份）
    + [f"AISC;;{y};F" for y in range(1, 5)]  # Artificial Intelligence & Society
    + ["GLOAD;CSC;X;F", "GLOAD;CE;X;F"]     # 跨院通选视角
)

# 请求间隔（秒）——抓取纪律：礼貌优先，间隔 >= 1 秒
SLEEP_SECONDS = 1.0

# 输出目录：项目根下的 data/
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 课程代码格式：2-3 个大写字母 + 4 位数字，可带尾字母（如 SC1003、CC0001、HW0310）
COURSE_CODE_RE = re.compile(r"^[A-Z]{2,3}\d{4}[A-Z]?$")


# ---------- 抓取 ----------

def fetch_category_html(category: str, semester: str) -> str:
    """POST 一个分类的课程列表 HTML。

    参数与浏览器表单一一对应（侦察报告 §一）：
    boption=CLoad 按分类加载；acadsem 形如 "2026_1"；r_course_yr 是分类值。
    """
    acad, sem = semester.split("_")
    resp = requests.post(
        URL,
        data={
            "boption": "CLoad",
            "acad": acad,
            "semester": sem,
            "acadsem": semester,
            "r_course_yr": category,
            "r_subj_code": "",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


# ---------- 解析 ----------

def parse_courses(html: str, semester: str, category: str) -> list[dict]:
    """解析一个分类页面里的所有课程信息块。

    页面结构（一门课一个 <table>，全部是 90 年代风格 font 标签）：
      第 1 行（蓝色字）：<TD>课程代码</TD><TD>标题</TD><TD>3.0 AU</TD>
      第 2 行（洋红标签）：Prerequisite: | 先修课程串
      第 3 行（棕色标签）：Mutually exclusive with: | 互斥课程串
      第 4 行（绿色标签）：Not available to all Programme with: | 限选专业串
                          或 (Admyr 2011-2019) 入学年份限制
      最后一行：<TD colspan=3> 课程简介长文本
    标签行可能出现也可能缺省，按文字内容识别而非按位置。
    """
    soup = BeautifulSoup(html, "html.parser")
    courses = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        # 第 1 行第 1 格必须像课程代码，否则跳过（排除页头等无关 table）
        first_cells = rows[0].find_all("td")
        if len(first_cells) < 3:
            continue
        code = first_cells[0].get_text(strip=True)
        if not COURSE_CODE_RE.match(code):
            continue

        course = {
            "course_code": code,
            "title": first_cells[1].get_text(strip=True),
            "au": first_cells[2].get_text(strip=True).replace("AU", "").strip(),
            "prerequisite": "",
            "mutually_exclusive": "",
            "not_available_to": "",
            "admyr_restriction": "",
            "description": "",
            "level": "undergraduate",
            "semester": semester,
            "source_categories": [category],
            "source_url": ENTRY_URL,
        }

        # 其余行：按标签文字识别字段
        for row in rows[1:]:
            cells = row.find_all("td")
            texts = [c.get_text(" ", strip=True) for c in cells]
            joined = " ".join(texts)
            if "Prerequisite" in joined:
                course["prerequisite"] = texts[-1]
            elif "Mutually exclusive" in joined:
                course["mutually_exclusive"] = texts[-1]
            elif "Not available" in joined:
                course["not_available_to"] = texts[-1]
            elif "Not offered as Unrestricted" in joined:
                course["not_offered_as_ue"] = True
            elif "(Admyr" in joined:
                # 入学年份限制，如 "(Admyr 2011-2019)-Non Direct Entry"
                course["admyr_restriction"] = texts[-1] if len(texts) > 1 else texts[0]
            else:
                # 无标签的长文本行 = 课程简介
                desc = "\n".join(t for t in texts if t)
                if len(desc) > 50:
                    course["description"] = desc

        courses.append(course)

    return courses


# ---------- 主流程 ----------

def main():
    DATA_DIR.mkdir(exist_ok=True)

    for semester in SEMESTERS:
        merged: dict[str, dict] = {}  # 按课程代码去重（同一门课会出现在多个年级分类）

        for category in CATEGORIES:
            html = fetch_category_html(category, semester)
            found = parse_courses(html, semester, category)
            for course in found:
                code = course["course_code"]
                if code in merged:
                    # 已见过：只把新分类并入溯源信息
                    merged[code]["source_categories"].append(category)
                else:
                    merged[code] = course
            print(f"[{semester}] {category:<16} 本分类 {len(found):>3} 门，累计去重 {len(merged)} 门")
            time.sleep(SLEEP_SECONDS)

        out_path = DATA_DIR / f"ugrad_ccds_{semester}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for course in merged.values():
                f.write(json.dumps(course, ensure_ascii=False) + "\n")
        print(f"==> 写出 {out_path}（{len(merged)} 门）\n")


if __name__ == "__main__":
    main()
