"""D4 端到端评估：直接跑 CourseAdvisorTeam.run()，不绕过编排/审查链路。

用法：
  .venv/Scripts/python.exe scripts/eval_e2e.py
  .venv/Scripts/python.exe scripts/eval_e2e.py --only Q06,Q07
  .venv/Scripts/python.exe scripts/eval_e2e.py --out eval/e2e_results.json

判据（eval/e2e_queries.json）在跑分前固定，脚本只做机械判定，不修改判据。
输出：逐条结果表 + 总准确率 + 分类准确率 + 单轮/整案耗时（中位数 / P90 / 最大值）。
"""

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import COURSE_CARDS_PATH, EVAL_DIR, ZHIPU_MODEL  # noqa: E402
from src.guards import _allowed_urls, _extract_urls, _norm_url  # noqa: E402
from src.team import CourseAdvisorTeam  # noqa: E402

# 课程码匹配用 ASCII 边界（中文字符在 Unicode 下算 \w，\b 会漏掉「的SC2001」这类写法）
_CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2}\d{4}[A-Z]?)(?![A-Za-z0-9])")

# 「如实说明未收录/查不到」的判定短语（覆盖课程、字段、项目三类边界）
UNKNOWN_PHRASES = [
    "未查到", "未收录", "查不到", "没有查到", "不在课程库", "不在当前课程库",
    "未提供", "未标注", "无法确认", "暂无", "官方未公开", "尚未收录",
    "未包含", "没有相关数据", "没有收录", "未列出",
    "not found", "not available", "no description", "not listed",
    "no data", "no information",
]


def load_cases(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw["cases"]
    assert len(cases) == 20, f"评估集应为 20 条，当前 {len(cases)} 条"
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "case id 重复"
    return cases


def load_cards() -> dict:
    cards = {}
    with open(COURSE_CARDS_PATH, encoding="utf-8") as f:
        for line in f:
            card = json.loads(line)
            cards[card["course_code"].upper()] = card
    return cards


def answer_codes(answer: str) -> set[str]:
    return set(_CODE_RE.findall(answer.upper()))


def curricula_codes(card: dict) -> set[str]:
    """本科卡片 source_categories → 专业代码集合（如 CSC;;1;F → CSC）。"""
    out = set()
    for item in card.get("source_categories") or []:
        out.add(str(item).split(";")[0].upper())
    return out


def _norm_text(text: str) -> str:
    """判据匹配归一化（不改判据，只消除等价写法差异）。

    实测 Q02 回答写「3 个学分（AU）」而判据写「3 学分」，旧匹配器按字面子串
    判 FAIL——这是匹配器缺陷，不是回答错误。归一化只做两件事：去掉空白、
    去掉数字后的量词「个」，让「3 个学分」「3个学分」「3 学分」等价。
    """
    t = text.lower()
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"(?<=\d)个(?=[a-z\u4e00-\u9fa5])", "", t)
    return t


def evaluate(case: dict, answer: str, cards: dict) -> list[dict]:
    """按预注册判据逐项机械判定，返回 [{name, ok, detail}]。"""
    crit = case["criteria"]
    checks: list[dict] = []
    codes = answer_codes(answer)
    lower = _norm_text(answer)

    def add(name: str, ok: bool, detail: str = ""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # expected_codes：至少 min_expected_codes 个出现
    expected = [c.upper() for c in crit.get("expected_codes") or []]
    if expected:
        hits = [c for c in expected if c in codes]
        need = crit.get("min_expected_codes", len(expected))
        add("expected_codes", len(hits) >= need,
            f"命中 {hits} / 需要 {need} / 期望池 {expected}")

    # expected_keywords：全部出现
    for kw in crit.get("expected_keywords") or []:
        add(f"keyword:{kw}", _norm_text(kw) in lower)

    # any_keywords：每组至少一个
    for i, group in enumerate(crit.get("any_keywords") or [], 1):
        hit = [w for w in group if _norm_text(w) in lower]
        add(f"any_keywords#{i}", bool(hit), f"命中 {hit} / 候选 {group}")

    # must_say_unknown
    if crit.get("must_say_unknown"):
        hit = [w for w in UNKNOWN_PHRASES if _norm_text(w) in lower]
        add("must_say_unknown", bool(hit), f"命中 {hit or '无'}")

    # must_contain_programme
    if crit.get("must_contain_programme"):
        terms = crit.get("programme_terms") or []
        hit = [w for w in terms if _norm_text(w) in lower]
        add("must_contain_programme", bool(hit), f"命中 {hit or '无'}")

    # max_codes / min_course_codes
    if crit.get("max_codes") is not None:
        add("max_codes", len(codes) <= crit["max_codes"],
            f"回答课程码 {sorted(codes)}（{len(codes)} 个，上限 {crit['max_codes']}）")
    if crit.get("min_course_codes") is not None:
        add("min_course_codes", len(codes) >= crit["min_course_codes"],
            f"回答课程码 {len(codes)} 个，下限 {crit['min_course_codes']}")

    # expected_level：库内课程码层次一致
    level = crit.get("expected_level")
    if level:
        wrong = sorted(c for c in codes
                       if c in cards and cards[c].get("level") != level)
        add("expected_level", not wrong,
            f"层次不符课程 {wrong or '无'}（期望 {level}）")

    # all_codes_in_curricula：本科码必须属于指定专业
    target = crit.get("all_codes_in_curricula")
    if target:
        wrong = sorted(c for c in codes
                       if c in cards and target.upper() not in curricula_codes(cards[c]))
        add("all_codes_in_curricula", not wrong,
            f"不属于 {target} 的课程 {wrong or '无'}")

    # all_codes_in_programme：研究生码必须属于指定项目
    target = crit.get("all_codes_in_programme")
    if target:
        wrong = sorted(c for c in codes
                       if c in cards and cards[c].get("programme") != target)
        add("all_codes_in_programme", not wrong,
            f"不属于「{target}」的课程 {wrong or '无'}")

    # must_ask_identity：反问里同时给出本科/研究生两个选项
    if crit.get("must_ask_identity"):
        ok = ("本科" in answer and "研究生" in answer
              and any(w in answer for w in ("请回复", "身份", "还是")))
        add("must_ask_identity", ok, "回答须包含本科/研究生两个选项且明确询问")

    # 来源：must_have_source + URL 白名单（编造来源直接判 FAIL）
    urls = _extract_urls(answer)
    if crit.get("must_have_source"):
        add("must_have_source", bool(urls), f"发现 {len(urls)} 个 URL")
    if urls:
        allowed = _allowed_urls()
        bad = sorted({u for u in urls if _norm_url(u) not in allowed})
        add("source_whitelist", not bad,
            f"库外/编造 URL {bad or '无'}")

    return checks


def percentile_nearest_rank(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    idx = max(0, math.ceil(p * len(ordered)) - 1)
    return ordered[min(idx, len(ordered) - 1)]


def time_stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "median_s": None, "p90_s": None, "max_s": None, "mean_s": None}
    return {
        "n": len(values),
        "median_s": round(statistics.median(values), 2),
        "p90_s": round(percentile_nearest_rank(values, 0.9), 2),
        "max_s": round(max(values), 2),
        "mean_s": round(statistics.mean(values), 2),
    }


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=ROOT, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="D4 端到端评估")
    parser.add_argument("--only", help="只跑指定 case（逗号分隔，如 Q06,Q07）")
    parser.add_argument("--set", default=str(EVAL_DIR / "e2e_queries.json"),
                        help="判据集 JSON 路径（默认 v1；D4.2 用 eval/e2e_queries_v2.json）")
    parser.add_argument("--out", default=str(EVAL_DIR / "e2e_results.json"),
                        help="原始结果 JSON 路径")
    args = parser.parse_args()

    cases = load_cases(Path(args.set))
    if args.only:
        picked = {x.strip().upper() for x in args.only.split(",") if x.strip()}
        cases = [c for c in cases if c["id"] in picked]
        assert cases, f"--only 未匹配任何 case：{args.only}"

    cards = load_cards()
    out_path = Path(args.out)
    started = datetime.now().astimezone()
    payload = {
        "meta": {
            "timestamp": started.isoformat(timespec="seconds"),
            "model": ZHIPU_MODEL,
            "git_commit": git_commit(),
            "eval_set": args.set,
            "script": "scripts/eval_e2e.py",
            "note": "判据跑分前固定；本文件为真实执行记录，answer 全文保留供归因。",
        },
        "summary": {},
        "cases": [],
    }

    print("=" * 78)
    print(f"D4 端到端评估 | 模型 {ZHIPU_MODEL} | {len(cases)} 条 | "
          f"{started.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 78)

    team = CourseAdvisorTeam(verbose=False)
    all_turn_times: list[float] = []
    all_case_times: list[float] = []

    for idx, case in enumerate(cases, 1):
        team.reset()  # 每条 case 独立会话（多轮 case 内部共享上下文）
        answers, times = [], []
        error = None
        t_case = time.perf_counter()
        try:
            for turn in case["turns"]:
                t0 = time.perf_counter()
                answers.append(team.run(turn))
                times.append(round(time.perf_counter() - t0, 2))
        except Exception as exc:  # 保留异常，不静默重试（真实失败也算结果）
            error = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        case_elapsed = round(time.perf_counter() - t_case, 2)

        answer = answers[-1] if answers else ""
        checks = evaluate(case, answer, cards) if answer else []
        passed = bool(answer) and error is None and all(c["ok"] for c in checks)
        failed = [f"{c['name']}({c['detail']})" for c in checks if not c["ok"]]

        result = {
            "id": case["id"],
            "category": case["category"],
            "turns": case["turns"],
            "answers": answers,
            "turn_times_s": times,
            "case_elapsed_s": case_elapsed,
            "checks": checks,
            "passed": passed,
            "error": error,
        }
        payload["cases"].append(result)
        if times:
            all_turn_times.extend(times)
            all_case_times.append(case_elapsed)

        status = "PASS" if passed else ("ERROR" if error else "FAIL")
        print(f"[{idx:02d}/{len(cases)}] {case['id']:<4}{case['category']:<12}"
              f"{status:<6}{case_elapsed:>7.1f}s  {case['turns'][-1][:32]}")
        if not passed:
            if error:
                print(f"        异常：{error}")
            for item in failed:
                print(f"        失败：{item}")

        # 增量落盘：长跑中断也不丢已完成结果
        write_json(out_path, payload)

    total = len(payload["cases"])
    passed_n = sum(1 for c in payload["cases"] if c["passed"])
    by_cat: dict[str, list[bool]] = {}
    for c in payload["cases"]:
        by_cat.setdefault(c["category"], []).append(c["passed"])

    summary = {
        "total": total,
        "passed": passed_n,
        "failed": total - passed_n,
        "accuracy": round(passed_n / total, 4) if total else None,
        "by_category": {
            cat: {"passed": sum(v), "total": len(v), "accuracy": round(sum(v) / len(v), 4)}
            for cat, v in by_cat.items()
        },
        "turn_time": time_stats(all_turn_times),
        "case_time": time_stats(all_case_times),
        "errors": sum(1 for c in payload["cases"] if c["error"]),
    }
    payload["summary"] = summary
    write_json(out_path, payload)

    print("-" * 78)
    print(f"准确率：{passed_n}/{total} = {summary['accuracy'] * 100:.1f}%")
    print("分类：" + " | ".join(
        f"{cat} {v['passed']}/{v['total']}" for cat, v in summary["by_category"].items()))
    tt, ct = summary["turn_time"], summary["case_time"]
    print(f"单轮耗时（n={tt['n']}）：中位数 {tt['median_s']}s | P90 {tt['p90_s']}s | "
          f"最大 {tt['max_s']}s | 均值 {tt['mean_s']}s")
    print(f"整案耗时（n={ct['n']}，多轮 case 为各轮之和）：中位数 {ct['median_s']}s | "
          f"P90 {ct['p90_s']}s | 最大 {ct['max_s']}s | 均值 {ct['mean_s']}s")
    print(f"结果已写入 {out_path}")


if __name__ == "__main__":
    main()
