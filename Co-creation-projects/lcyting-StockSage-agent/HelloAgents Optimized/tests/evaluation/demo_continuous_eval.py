"""
持续评估系统 + 报告生成系统 演示脚本
运行: python -m hello_agents.evaluation.examples.demo_continuous_eval
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from hello_agents import SimpleAgent
from hello_agents.evaluation import (
    # 持续评估
    EvalDB,
    TrendDetector,
    AlertNotifier,
    ReportGenerator,
)


def demo_continuous_eval_system():
    """演示1: 持续评估系统"""
    print("\n" + "=" * 60)
    print(" 持续评估系统 - 演示")
    print("=" * 60)

    # 1. 创建智能体（示例用mock，实际需传入真实agent）
    _agent = SimpleAgent(name="DemoAgent", llm=None)

    # 2. 创建持续评估系统（简化版本，无需真实BFCL数据）
    db = EvalDB(db_path="data/eval_data/demo_eval.db")

    # 3. 模拟一次快速评估结果
    mock_result = {
        "level": "quick",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "bfcl_simple_accuracy": 0.92,
            "bfcl_multiple_accuracy": 0.85,
            "bfcl_parallel_accuracy": 0.78,
            "bfcl_irrelevance_accuracy": 0.95,
        },
        "details": {
            "bfcl_details": [
                {
                    "sample_id": "s1",
                    "question": "test",
                    "predicted": "{}",
                    "expected": "{}",
                    "success": True,
                },
                {
                    "sample_id": "s2",
                    "question": "find weather",
                    "predicted": "{}",
                    "expected": "{}",
                    "success": False,
                },
            ],
            "error_types": {"参数错误": 3, "函数名错误": 2, "格式错误": 1},
            "sample_summary": {"查找天气": True, "计算面积": False, "调用API": True},
        },
        "duration_min": 5,
        "agent_version": "v2.3.1",
    }

    # 4. 数据库操作
    db.save_snapshot(mock_result)

    print("已保存评估快照")
    print(
        f"  基线 (bfcl_simple_accuracy): {db.get_baseline('bfcl_simple_accuracy'):.2%}"
    )

    # 5. 趋势检测
    detector = TrendDetector(db)

    # 模拟一个退化结果
    degraded_result = {
        **mock_result,
        "metrics": {**mock_result["metrics"], "bfcl_simple_accuracy": 0.75},
    }
    alerts = detector.check(degraded_result)
    notifier = AlertNotifier()
    notifier.notify(alerts)

    print("✅ 持续评估系统演示完成")


def demo_report_generator():
    """演示2: 报告生成系统"""
    print("\n" + "=" * 60)
    print(" 报告生成系统 - 演示")
    print("=" * 60)

    data = {
        "agent_version": "v2.3.1",
        "level": "standard",
        "duration_min": 45,
        "metrics": {
            "bfcl_simple_accuracy": 0.92,
            "bfcl_multiple_accuracy": 0.85,
            "bfcl_parallel_accuracy": 0.78,
            "bfcl_irrelevance_accuracy": 0.95,
        },
        "baseline": {
            "bfcl_simple_accuracy": 0.93,
            "bfcl_multiple_accuracy": 0.86,
            "bfcl_parallel_accuracy": 0.82,
            "bfcl_irrelevance_accuracy": 0.94,
        },
        "details": {
            "bfcl_details": [
                {
                    "sample_id": "s1",
                    "question": "What's the weather?",
                    "predicted": '{"name":"get_weather","args":{"city":"Beijing"}}',
                    "expected": '{"name":"get_weather","args":{"city":"Beijing"}}',
                    "success": True,
                },
                {
                    "sample_id": "s2",
                    "question": "Calculate factorial of 5",
                    "predicted": '{"name":"factorial","args":{"n":5}}',
                    "expected": '{"name":"factorial","args":{"n":5}}',
                    "success": True,
                },
                {
                    "sample_id": "s3",
                    "question": "Find area of triangle",
                    "predicted": '{"name":"area","args":{"base":10,"height":5}}',
                    "expected": '{"name":"triangle_area","args":{"base":10,"height":5}}',
                    "success": False,
                },
            ],
            "error_types": {"函数名错误": 2, "参数缺失": 1},
            "sample_summary": {"查找天气": True, "计算阶乘": True, "计算面积": False},
        },
    }

    gen = ReportGenerator(output_dir="data/eval_reports")
    reports = gen.generate_all(data)

    print("\n生成的三份报告：")
    for audience, content in reports.items():
        lines = content.strip().split("\n")
        print(f"\n  [{audience}] 共 {len(lines)} 行")
        for line in lines[:5]:
            print(f"    {line}")
        print("    ...")

    print("\n✅ 报告生成系统演示完成")


def demo_integration():
    """演示3: 完整集成使用"""
    print("\n" + "=" * 60)
    print(" 完整集成 - 持续评估 + 报告生成")
    print("=" * 60)

    # 1. 创建报告生成器（用于后续生成报告）
    gen = ReportGenerator()

    # 2. 模拟连续7次评估，模拟性能退化
    db = EvalDB(db_path="data/eval_data/demo_integration.db")

    accuracies = [0.93, 0.92, 0.91, 0.88, 0.85, 0.82, 0.78]
    for i, acc in enumerate(accuracies):
        ts = (datetime.now() - timedelta(days=6 - i)).isoformat()
        db.save_snapshot(
            {
                "level": "quick",
                "timestamp": ts,
                "metrics": {"bfcl_simple_accuracy": acc},
                "details": {},
            }
        )

    # 3. 最新的退化结果触发告警
    latest = {
        "level": "quick",
        "timestamp": datetime.now().isoformat(),
        "metrics": {"bfcl_simple_accuracy": 0.78},
        "details": {},
    }
    detector = TrendDetector(db)
    alerts = detector.check(latest)
    AlertNotifier().notify(alerts)

    # 4. 生成综合报告
    data = {
        "agent_version": "v2.3.5",
        "level": "quick",
        "duration_min": 5,
        "metrics": {"bfcl_simple_accuracy": 0.78},
        "baseline": {
            "bfcl_simple_accuracy": db.get_baseline("bfcl_simple_accuracy", days=7)
        },
        "details": {},
    }

    gen.generate(data, "developer")
    pm_report = gen.generate(data, "product")
    user_report = gen.generate(data, "user")

    # 5. 打印告警摘要和报告结论
    print(f"\n基线 (7天滑动): {data['baseline']['bfcl_simple_accuracy']:.2%}")
    print("当前值: 78%")
    print(f"退化: {data['baseline']['bfcl_simple_accuracy'] - 0.78:.1%}")

    print("\n产品经理报告核心结论:")
    for line in pm_report.split("\n")[3:7]:
        print(f"  {line}")

    print("\n用户报告健康状态:")
    for line in user_report.split("\n")[3:6]:
        print(f"  {line}")

    print("\n✅ 完整集成演示完成")


if __name__ == "__main__":
    demo_continuous_eval_system()
    print("\n")
    demo_report_generator()
    print("\n")
    demo_integration()
