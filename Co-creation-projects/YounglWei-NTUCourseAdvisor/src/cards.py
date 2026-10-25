"""课程卡片构造：三份原始抓取 jsonl → 统一课程卡片。

原始数据（m0_spike 抓取，见 03-数据源侦察.md）：
  - data/ugrad_ccds_2026_1.jsonl / ugrad_ccds_2026_2.jsonl：WIS 本科目录（按学期）
  - data/grad_cca.jsonl：NTU 官网 CCA 项目页（研究生）

卡片原则（design.md「数据与检索」）：
  - 单课整卡：一门课一张卡，进 RAGStore 时不切片
  - 溯源：每张卡必须带官方 source_url
  - 本科双学期同码合并：semesters 取并集，文本字段取更完整者
"""

import hashlib
import json
from pathlib import Path

# 学期显示格式："2026_1" → "2026 Sem 1"
def _semester_label(sem: str) -> str:
    acad, term = sem.split("_")
    return f"{acad} Sem {term}"


def decode_curriculum(category: str) -> str:
    """WIS 分类值转可读课程归属。

    "CSC;;1;F" → "CSC Y1"（Computer Science 一年级课表）
    "GLOAD;CSC;X;F" → "GLOAD-CSC"（跨院通选视角）
    """
    parts = category.split(";")
    unit, sub, year = parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else ""
    if unit == "GLOAD":
        return f"GLOAD-{sub}" if sub else "GLOAD"
    return f"{unit} Y{year}" if year and year != "X" else unit


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _pick_richer(base: dict, other: dict, field: str) -> str:
    """同一课程跨学期字段取更完整者（长的优先，空值兜底）。"""
    a, b = base.get(field, "") or "", other.get(field, "") or ""
    return a if len(a) >= len(b) else b


def merge_ugrad(semesters: dict[str, list[dict]]) -> list[dict]:
    """合并各学期本科课程（按 course_code 聚合）。

    semesters: {"2026_1": [...records], "2026_2": [...records]}
    同码课程：semesters 并集、source_categories 并集、
    description/prerequisite 等文本字段取更完整者。
    """
    merged: dict[str, dict] = {}
    for sem, records in semesters.items():
        for rec in records:
            code = rec["course_code"]
            if code not in merged:
                card = dict(rec)
                card["semesters"] = [sem]
                merged[code] = card
                continue
            card = merged[code]
            if sem not in card["semesters"]:
                card["semesters"].append(sem)
            # 分类并集（去重保序）
            for cat in rec.get("source_categories", []):
                if cat not in card["source_categories"]:
                    card["source_categories"].append(cat)
            # 文本字段取更完整者
            for field in ("description", "prerequisite", "mutually_exclusive",
                          "not_available_to", "admyr_restriction", "title"):
                card[field] = _pick_richer(card, rec, field)
            card["au"] = card.get("au") or rec.get("au")
    return list(merged.values())


def build_grad_cards(records: list[dict]) -> list[dict]:
    """研究生卡（CCA 官网页）：字段已齐，补 semesters 空表。"""
    cards = []
    for rec in records:
        card = dict(rec)
        card["semesters"] = []  # 官网未标学期，以项目页为准
        card["source_categories"] = []
        cards.append(card)
    return cards


def build_card_text(card: dict) -> str:
    """渲染卡片全文：进 RAGStore 与向量索引的唯一文本。

    字段标签用英文（与官方数据一致）；中文查询依赖向量语义路由，
    BM25 分词含课程码/数字等强信号词即可命中。
    """
    sem = ", ".join(_semester_label(s) for s in card.get("semesters", [])) or "not listed (see programme page)"
    # 标题行重复课程码：强化课程码查询的 BM25 命中（tf 提权，NTU 官方列表风格）
    lines = [
        f"Course Code: {card['course_code']}",
        f"Title: {card['course_code']} {card['title']}",
        f"Level: {card['level']} | Programme: {card.get('programme', 'CCDS curricula')} | AU: {card['au']}",
    ]
    if card.get("category"):
        cat = card["category"].replace("_", " ")
        lines[2] += f" | Category: {cat}"
    if card.get("source_categories"):
        curricula = ", ".join(decode_curriculum(c) for c in card["source_categories"])
        lines[2] += f" | Curricula: {curricula}"
    lines.append(f"Semesters: {sem}")
    # 本科限制性字段（研究生卡为空则跳过）
    for label, field in (("Prerequisite:", "prerequisite"),
                         ("Mutually exclusive with:", "mutually_exclusive"),
                         ("Not available to:", "not_available_to"),
                         ("Admission year restriction:", "admyr_restriction")):
        if card.get(field):
            lines.append(f"{label} {card[field]}")
    lines.append(f"Description: {card.get('description', '(no description in source)')}")
    lines.append(f"Source: {card['source_url']}")
    return "\n".join(lines)


def card_version(card_text: str, data_date: str) -> str:
    """RAGStore 版本号 = 数据日期 + 内容摘要。

    同版本同原文幂等；改卡片渲染 → 内容变 → 新版本自动替换旧版，
    避免框架"同版本原文不可变"约束在迭代时炸掉。
    """
    digest = hashlib.sha256(card_text.encode()).hexdigest()[:8]
    return f"{data_date}.{digest}"


def build_all(data_dir: Path) -> tuple[list[dict], dict]:
    """构造全部卡片。返回 (cards, stats)；每张卡含渲染后的 card_text/version。"""
    data_date = "20261022"  # 原始数据抓取日期（M0/D0）

    ugrad_records = {
        "2026_1": load_jsonl(data_dir / "ugrad_ccds_2026_1.jsonl"),
        "2026_2": load_jsonl(data_dir / "ugrad_ccds_2026_2.jsonl"),
    }
    # 研究生卡：CCA 项目页 + 批量抓取的其他项目页（grad_all.jsonl，当前含
    # MSc Robotics and Intelligent Systems 13 门；两组课码无重叠，实测确认）
    grad_records = (load_jsonl(data_dir / "grad_cca.jsonl")
                    + load_jsonl(data_dir / "grad_all.jsonl"))

    cards = merge_ugrad(ugrad_records) + build_grad_cards(grad_records)
    for card in cards:
        card["card_text"] = build_card_text(card)
        card["version"] = card_version(card["card_text"], data_date)

    sem1 = {r["course_code"] for r in ugrad_records["2026_1"]}
    sem2 = {r["course_code"] for r in ugrad_records["2026_2"]}
    stats = {
        "total": len(cards),
        "graduate": len(grad_records),
        "undergraduate": len(sem1 | sem2),
        "ugrad_both_semesters": len(sem1 & sem2),
        "ugrad_sem1_only": len(sem1 - sem2),
        "ugrad_sem2_only": len(sem2 - sem1),
        "missing_description": sum(1 for c in cards if not c.get("description")),
    }
    return cards, stats
