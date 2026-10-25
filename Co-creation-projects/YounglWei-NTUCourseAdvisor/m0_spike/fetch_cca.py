"""M0 数据抓取 ②：NTU 官网 CCA 项目页（研究生课程表）

数据源（官方，无需登录，实测静态 HTML 即含课程表）：
https://www.ntu.edu.sg/education/graduate-programme/master-of-science-in-computer-control-automation

页面结构：Curriculum 段落下有两个课程表（表头 Course Code | Course Title | Course Content | AUs）：
  - Specialized Elective（专业选修）
  - General Elective（通选）

用法：python m0_spike/fetch_cca.py
产出：data/grad_cca.jsonl
"""

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------- 配置 ----------

URL = ("https://www.ntu.edu.sg/education/graduate-programme/"
       "master-of-science-in-computer-control-automation")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PROGRAMME = "MSc Computer Control & Automation (CCA)"


# ---------- 解析 ----------

def classify_table(table) -> str | None:
    """判断一个 table 是哪种课程表：返回表头前的分类标题。

    官网页面里课程表的表头第一格是 "Course Code"，
    表格上方最近的标题文字含 Specialized / General / Core 等关键词。
    不是课程表（如项目结构表）返回 None。
    """
    header_cells = table.find("tr").find_all(["td", "th"])
    header = " ".join(c.get_text(strip=True) for c in header_cells)
    if "Course Code" not in header:
        return None

    # 往前找最近的标题（h2/h3/h4/strong）来判断表的类型
    heading = table.find_previous(["h2", "h3", "h4", "strong", "b"])
    heading_text = heading.get_text(" ", strip=True).lower() if heading else ""
    if "specialized" in heading_text:
        return "specialized_elective"
    if "general" in heading_text:
        return "general_elective"
    if "core" in heading_text or "compulsory" in heading_text:
        return "core"
    return "unknown_elective"  # 是课程表但标题没匹配上，标记出来人工核对


def parse_tables(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    courses = []

    for table in soup.find_all("table"):
        category = classify_table(table)
        if category is None:
            continue

        rows = table.find_all("tr")
        for row in rows[1:]:  # 跳过表头
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            code = cells[0].get_text(strip=True)
            if not code:  # 跳过空行/分隔行
                continue
            courses.append({
                "course_code": code,
                "title": cells[1].get_text(" ", strip=True),
                "description": cells[2].get_text(" ", strip=True),  # Course Content 列
                "au": cells[3].get_text(strip=True),
                "category": category,          # specialized_elective / general_elective
                "level": "graduate",
                "programme": PROGRAMME,
                "source_url": URL,
            })

    return courses


# ---------- 主流程 ----------

def main():
    DATA_DIR.mkdir(exist_ok=True)

    print(f"抓取 {URL}")
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    courses = parse_tables(resp.text)
    # 按课程代码去重（同门课可能出现在多个表）
    merged = {c["course_code"]: c for c in courses}

    out_path = DATA_DIR / "grad_cca.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for course in merged.values():
            f.write(json.dumps(course, ensure_ascii=False) + "\n")

    # 分类统计，方便人工核对
    stats: dict[str, int] = {}
    for c in merged.values():
        stats[c["category"]] = stats.get(c["category"], 0) + 1
    print(f"==> 写出 {out_path}（{len(merged)} 门）")
    for cat, n in sorted(stats.items()):
        print(f"    {cat}: {n} 门")


if __name__ == "__main__":
    main()
