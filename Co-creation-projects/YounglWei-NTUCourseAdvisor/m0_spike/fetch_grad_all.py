"""M0 数据抓取 ③：批量抓取 NTU 授课型硕士项目页的课程表。

数据源：https://www.ntu.edu.sg/admissions/graduate/coursework（项目列表）
       各项目详情页的 Curriculum 段

页面分三类（脚本自动判定并统计）：
  table  —— 静态 HTML 课程表（可解析，与 CCA 页同构）→ 直接入库
  pdf    —— Curriculum 只给 PDF 链接（如 AAI）→ 记录 URL，暂不解析
  empty  —— 页面无课程表也无 PDF → 跳过

用法：python m0_spike/fetch_grad_all.py
产出：data/grad_all.jsonl（所有解析成功的课程）
      data/grad_coverage.json（项目级覆盖报告：每个项目抓到几门/属于哪类）

礼貌爬取：串行 + 每次请求间隔 0.6s，失败重试一次。
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.ntu.edu.sg"
LIST_URL = f"{BASE}/admissions/graduate/coursework"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DELAY = 0.6


def _get(url: str):
    """GET，失败重试一次（网络抖动是常态，不该让单个项目拖垮整批）。"""
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=30, headers=HEADERS)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(1.0)
    return None


def discover_programmes() -> list[tuple[str, str]]:
    """从列表页提取 (项目名, 详情页 URL)。

    列表页链接指向各学院站点（/computing/...），但含静态课程表的是统一的
    项目页 /education/graduate-programme/<slug>（实测 Robotics 页 4 张课表）。
    因此按 slug 生成 canonical URL，抓取时优先用它，失败再回退学院页。
    """
    r = _get(LIST_URL)
    if r is None:
        raise RuntimeError("项目列表页抓取失败")
    soup = BeautifulSoup(r.text, "html.parser")
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        if "graduate-programme/" not in href or len(text) < 8:
            continue
        slug = href.rstrip("/").split("/")[-1]
        canonical = f"{BASE}/education/graduate-programme/{slug}"
        found.setdefault(canonical, text)
    return [(name, url) for url, name in found.items()]


def classify_table(table) -> str | None:
    """课程表分类：Specialized / General / Core；非课程表返回 None（同 fetch_cca）。"""
    first_row = table.find("tr")
    if first_row is None:
        return None
    header = " ".join(c.get_text(" ", strip=True) for c in first_row.find_all(["td", "th"]))
    if "Course Code" not in header:
        return None
    heading = table.find_previous(["h2", "h3", "h4", "strong", "b"])
    heading_text = heading.get_text(" ", strip=True).lower() if heading else ""
    if "specialized" in heading_text:
        return "specialized_elective"
    if "general" in heading_text:
        return "general_elective"
    if "core" in heading_text or "compulsory" in heading_text:
        return "core"
    return "other"


def parse_courses(soup, programme: str, source_url: str) -> list[dict]:
    courses = []
    for table in soup.find_all("table"):
        category = classify_table(table)
        if category is None:
            continue
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:  # 3 列：Code|Title|AUs；4 列：Code|Title|Content|AUs
                continue
            code = cells[0].get_text(strip=True)
            if not re.fullmatch(r"[A-Z]{2}\d{4}[A-Z]?", code):
                continue
            courses.append({
                "course_code": code,
                "title": cells[1].get_text(" ", strip=True),
                "description": (cells[2].get_text(" ", strip=True)
                                if len(cells) >= 4 else ""),
                "au": cells[-1].get_text(strip=True),
                "category": category,
                "level": "graduate",
                "programme": programme,
                "source_url": source_url,
            })
    return courses


def find_curriculum_pdfs(soup) -> list[str]:
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            full = href if href.startswith("http") else BASE + href
            pdfs.append(full)
    return pdfs


def main():
    DATA_DIR.mkdir(exist_ok=True)
    programmes = discover_programmes()
    print(f"发现 {len(programmes)} 个项目页\n")

    all_courses: dict[str, dict] = {}
    report = []
    for i, (name, url) in enumerate(programmes, 1):
        r = _get(url)
        if r is None:
            report.append({"programme": name, "url": url, "kind": "failed",
                           "courses": 0, "pdfs": []})
            print(f"[{i}/{len(programmes)}] FAILED  {name}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        courses = parse_courses(soup, name, url)
        pdfs = find_curriculum_pdfs(soup)
        kind = "table" if courses else ("pdf" if pdfs else "empty")
        for c in courses:
            all_courses.setdefault(c["course_code"], c)
        report.append({"programme": name, "url": url, "kind": kind,
                       "courses": len(courses), "pdfs": pdfs})
        print(f"[{i}/{len(programmes)}] {kind:6s} {len(courses):3d} 门  {name[:52]}")
        time.sleep(DELAY)

    out = DATA_DIR / "grad_all.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for c in all_courses.values():
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    cov = DATA_DIR / "grad_coverage.json"
    with open(cov, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    kinds: dict[str, int] = {}
    for item in report:
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
    print(f"\n==> 写出 {out}（去重 {len(all_courses)} 门）")
    print(f"==> 写出 {cov}")
    print("项目分类：" + "，".join(f"{k}={v}" for k, v in sorted(kinds.items())))


if __name__ == "__main__":
    main()
