"""WIS Class Schedule 抓取脚本（D0 抢救验证成功后的正式版，2026-10-22）

数据源入口：https://wis.ntu.edu.sg/webexe/owa/aus_schedule.main
提交端点：  POST https://wis.ntu.edu.sg/webexe/owa/AUS_SCHEDULE.main_display1

关键教训（2026-10-22 实测）：
    此前侦察直接 POST 该端点返回 404，原因是载荷不全。
    浏览器实际提交的完整载荷包含：
    - boption=CLoad            （隐藏字段，按钮 onclick 写入）
    - staff_access=false       （隐藏字段）
    - 两个同名 acadsem         （select 当前值 + 隐藏默认值 "2026;2"，浏览器会双发）
    - r_subj_code 必须是占位符文本 "Enter Keywords or Course Code"（JS 在 CLoad 模式下重置）
    缺任何一个都可能 404。以下载荷为逐字段照抄浏览器行为。

已知边界：研究生（MSc）课程时间表不在此系统公开（两学期 × F/P 搜索模式均
"not available"，697 个分类中无 MSc 类）。本脚本只对本科分类有效。

用法：
    python fetch_schedule.py <acadsem> <r_course_yr> <输出.jsonl>
    例：python fetch_schedule.py "2026;1" "CSC;;1;F" ../../data/schedule_csc_y1_2026_1.jsonl

抓取纪律：单次请求；如需批量抓多分类，调用方自行控制间隔 >= 1 秒。
"""

import json
import re
import sys

import requests
from bs4 import BeautifulSoup

ENTRY_URL = "https://wis.ntu.edu.sg/webexe/owa/aus_schedule.main"
POST_URL = "https://wis.ntu.edu.sg/webexe/owa/AUS_SCHEDULE.main_display1"

HEADERS = {
    # 标明用途的 UA（礼貌抓取，与 M0 约定一致）
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NTU-Course-Assistant/0.1 (academic project)",
    "Referer": ENTRY_URL,
    "Origin": "https://wis.ntu.edu.sg",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 课程代码格式：2-4 个大写字母 + 4 位数字（如 CC0001 / SC1003 / HW0008）
COURSE_CODE_RE = re.compile(r"^[A-Z]{2,4}\d{4}[A-Z]?$")


def fetch_category_schedule(session: requests.Session, acadsem: str, r_course_yr: str) -> list[dict]:
    """按「学期 + 分类」抓取课表，返回结构化记录列表。

    acadsem:     学期，格式 "2026;1"（分号分隔）
    r_course_yr: 分类值，如 "CSC;;1;F"（Computer Science Year 1）
    """
    # 逐字段照抄浏览器载荷（见文件头"关键教训"）
    payload = [
        ("acadsem", acadsem),
        ("r_course_yr", r_course_yr),
        ("r_subj_code", "Enter Keywords or Course Code"),
        ("boption", "CLoad"),
        ("acadsem", "2026;2"),
        ("staff_access", "false"),
    ]
    resp = session.post(POST_URL, data=payload, timeout=30)
    resp.raise_for_status()
    return parse_schedule_html(resp.text, acadsem, r_course_yr)


def parse_schedule_html(html: str, acadsem: str, r_course_yr: str) -> list[dict]:
    """解析课表页。

    页面结构（2026-10-22 实测）：每门课两张表成对出现——
      1) 课程头表：第一行三格 = 课程代码 | 标题 | AU
      2) 明细表：  含 <th>INDEX</th> 表头，数据行 = INDEX|TYPE|GROUP|DAY|TIME|VENUE|REMARK
    解析策略：顺序遍历所有 <table>，遇课程头表就记为"当前课程"，
    遇明细表就把每行挂到当前课程名下。
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    current: dict | None = None  # 最近一次识别到的课程头

    for table in soup.find_all("table"):
        ths = [th.get_text(strip=True).upper() for th in table.find_all("th")]
        if "INDEX" in ths:
            # ---- 明细表：逐行提取课表条目 ----
            if current is None:
                continue
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(cells) < 6 or not cells[0]:
                    continue  # 跳过表头/空行
                records.append(
                    {
                        "course_code": current["code"],
                        "course_title": current["title"],
                        "au": current["au"],
                        "index": cells[0],
                        "type": cells[1],   # LEC / TUT / LAB / SEM ...
                        "group": cells[2],
                        "day": cells[3],    # MON / TUE / ...
                        "time": cells[4],   # 如 1030-1220
                        "venue": cells[5],
                        "remark": cells[6] if len(cells) > 6 else "",
                        "semester": acadsem,
                        "category": r_course_yr,
                        "source_url": ENTRY_URL,  # 溯源字段，与 M0 数据约定一致
                    }
                )
        else:
            # ---- 候选课程头表：第一行三格且首格形如课程代码 ----
            first_tr = table.find("tr")
            if not first_tr:
                continue
            tds = [td.get_text(strip=True) for td in first_tr.find_all("td")]
            if len(tds) >= 3 and COURSE_CODE_RE.match(tds[0]):
                current = {
                    "code": tds[0],
                    "title": tds[1],
                    "au": tds[2].replace("AU", "").strip(),
                }
    return records


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    acadsem, r_course_yr, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(ENTRY_URL, timeout=30)  # 先访问入口页建立会话（与浏览器行为一致）

    records = fetch_category_schedule(session, acadsem, r_course_yr)

    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[{r_course_yr} @ {acadsem}] 抓到 {len(records)} 条课表记录 -> {out_path}")


if __name__ == "__main__":
    main()
