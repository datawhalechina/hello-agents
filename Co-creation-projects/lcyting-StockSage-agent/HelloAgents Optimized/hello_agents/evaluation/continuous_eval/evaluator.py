"""分层评估执行器 - 快速/标准/全面三层评估"""

from datetime import datetime
from typing import Any, Dict, Optional, List

from ..benchmarks.bfcl.dataset import BFCLDataset
from ..benchmarks.bfcl.evaluator import BFCLEvaluator


def run_quick_eval(
    agent: Any,
    db: "EvalDB",  # noqa: F821
    bfcl_data_dir: str = "./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
    core_scenarios: Optional[List[Dict]] = None,
) -> Dict:
    """快速评估 - 低成本，用于日常开发迭代"""
    print("\n" + "=" * 40)
    print("快速评估 - 开始")
    print("=" * 40)

    results = {"level": "quick", "timestamp": datetime.now().isoformat(), "metrics": {}}

    # 1. BFCL simple 20条
    try:
        ds = BFCLDataset(bfcl_data_dir=bfcl_data_dir, category="simple_python")
        ev = BFCLEvaluator(dataset=ds, category="simple_python")
        r = ev.evaluate(agent, max_samples=20)
        results["metrics"]["bfcl_simple_accuracy"] = r["overall_accuracy"]
        results["metrics"]["bfcl_correct"] = r["correct_samples"]
        results["metrics"]["bfcl_total"] = r["total_samples"]
        results["bfcl_details"] = r.get("detailed_results", [])
        print(
            f"  BFCL simple: {r['overall_accuracy']:.2%} ({r['correct_samples']}/{r['total_samples']})"
        )
    except Exception as e:
        results["metrics"]["bfcl_simple_accuracy"] = 0.0
        print(f"  BFCL 失败: {e}")

    # 2. 核心场景测试
    if core_scenarios:
        pass

    db.save_snapshot(results)
    return results


def run_standard_eval(
    agent: Any,
    db: "EvalDB",  # noqa: F821
    bfcl_data_dir: str = "./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
) -> Dict:
    """标准评估 - 中等成本，用于版本发布前"""
    print("\n" + "=" * 40)
    print("标准评估 - 开始")
    print("=" * 40)

    results = {
        "level": "standard",
        "timestamp": datetime.now().isoformat(),
        "metrics": {},
    }

    bfcl_categories = ["simple_python", "multiple", "parallel", "irrelevance"]
    for cat in bfcl_categories:
        try:
            ds = BFCLDataset(bfcl_data_dir=bfcl_data_dir, category=cat)
            ev = BFCLEvaluator(dataset=ds, category=cat)
            r = ev.evaluate(agent, max_samples=50)
            results["metrics"][f"bfcl_{cat}_accuracy"] = r["overall_accuracy"]
            print(
                f"  BFCL {cat}: {r['overall_accuracy']:.2%} ({r['correct_samples']}/{r['total_samples']})"
            )
        except Exception as e:
            results["metrics"][f"bfcl_{cat}_accuracy"] = 0.0
            print(f"  BFCL {cat} 失败: {e}")

    db.save_snapshot(results)
    return results


def run_full_eval(
    agent: Any,
    db: "EvalDB",  # noqa: F821
    bfcl_data_dir: str = "./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
) -> Dict:
    """全面评估 - 高成本，用于重大更新或对外发布"""
    print("\n" + "=" * 40)
    print("全面评估 - 开始")
    print("=" * 40)

    results = {"level": "full", "timestamp": datetime.now().isoformat(), "metrics": {}}

    bfcl_categories = [
        "simple_python",
        "multiple",
        "parallel",
        "parallel_multiple",
        "irrelevance",
    ]
    for cat in bfcl_categories:
        try:
            ds = BFCLDataset(bfcl_data_dir=bfcl_data_dir, category=cat)
            ev = BFCLEvaluator(dataset=ds, category=cat)
            r = ev.evaluate(agent, max_samples=None)
            results["metrics"][f"bfcl_{cat}_accuracy"] = r["overall_accuracy"]
            results["metrics"][f"bfcl_{cat}_correct"] = r["correct_samples"]
            results["metrics"][f"bfcl_{cat}_total"] = r["total_samples"]
            print(
                f"  BFCL {cat}: {r['overall_accuracy']:.2%} ({r['correct_samples']}/{r['total_samples']})"
            )
        except Exception as e:
            print(f"  BFCL {cat} 失败: {e}")

    db.save_snapshot(results)
    return results
