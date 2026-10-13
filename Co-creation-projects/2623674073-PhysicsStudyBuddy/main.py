"""Interactive entry point for PhysicsStudyBuddy."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from src.study_buddy.core import StudyBuddy
from src.study_buddy.demo import DemoBackend


def show_plan(session: dict) -> None:
    if not session["plan"]:
        print("尚无学习计划，请先完成诊断测验。")
        return
    print("\n学习计划：")
    for index, task in enumerate(session["plan"], 1):
        status = "✓" if task["completed"] else "□"
        print(f"{index}. [{status}] {task['id']} · {task['title']}（约 {task['minutes']} 分钟）")
        print(f"   原因：{task['why']}\n   完成条件：{task['done_when']}")
        for resource in task.get("resources", []):
            print(f"   资源：{resource['title']} — {resource['url']}")
    for notice in dict.fromkeys(session.get("notices", [])):
        print("提示：" + notice)


def show_result(result: dict) -> None:
    print("\n本轮诊断：")
    for item in result["results"]:
        print(f"- {item['question_id']} {item['skill']}：{item['earned']}/{item['possible']}；{item['feedback']}")
    print("能力点掌握情况（仅依据本轮答题）：")
    for skill, value in result["mastery"].items():
        print(f"- {skill}：{value['level']}（{value['earned']}/{value['possible']}，{value['items']} 题）")


def take_quiz(buddy: StudyBuddy, session: dict) -> None:
    questions = buddy.begin_quiz(session)
    answers = {}
    print("\n请完成五道题。提交前不会显示答案。")
    for q in questions:
        print(f"\n{q['id']} [{q['skill']}] {q['stem']}")
        if q["type"] == "choice":
            for letter, option in q["options"].items():
                print(f"  {letter}. {option}")
            while True:
                answer = input("选择 A/B/C/D：").strip().upper()
                if answer in "ABCD" and answer:
                    break
                print("请输入 A、B、C 或 D。")
        else:
            answer = input("你的解答：").strip()
        answers[q["id"]] = answer
    result = buddy.submit(session, answers)
    show_result(result)
    show_plan(session)


def demo_walkthrough() -> None:
    """Non-interactive example; no model key or internet required."""
    with tempfile.TemporaryDirectory() as temp_dir:
        buddy = StudyBuddy(DemoBackend(), Path(temp_dir))
        session = buddy.open("演示学生", "物理", "牛顿第二定律")
        buddy.begin_quiz(session)
        answers = {"q1": "A", "q2": "C", "q3": "C", "q4": "加速度方向与合力相同", "q5": "合力 6 N 向右"}
        result = buddy.submit(session, answers)
        show_result(result)
        show_plan(session)


def main() -> int:
    parser = argparse.ArgumentParser(description="高中物理智能学习伙伴")
    parser.add_argument("--demo", action="store_true", help="使用离线牛顿第二定律演示")
    parser.add_argument("--auto-demo", action="store_true", help="自动完成一轮离线诊断")
    args = parser.parse_args()
    if args.auto_demo:
        demo_walkthrough()
        return 0
    if args.demo:
        backend = DemoBackend()
    else:
        from dotenv import load_dotenv
        from src.study_buddy.agents import HelloAgentsBackend
        load_dotenv()
        backend = HelloAgentsBackend()
    buddy = StudyBuddy(backend, Path("outputs/progress"))
    print("高中物理智能学习伙伴")
    learner = input("学习者昵称：").strip()
    subject = input("科目 [物理]：").strip() or "物理"
    topic = input("知识点 [牛顿第二定律]：").strip() or "牛顿第二定律"
    grade = input("年级 [高一]：").strip() or "高一"
    session = buddy.open(learner, subject, topic, grade)
    if not session["reviewed_topic"]:
        print("该主题未经过项目样例验证，生成题目和评价请自行核对。")
    if not session["rounds"]:
        take_quiz(buddy, session)
    while True:
        print("\n1 查看计划  2 开始或继续测验  3 答疑  4 标记任务完成  5 退出")
        choice = input("请选择：").strip()
        if choice == "1":
            show_plan(session)
        elif choice == "2":
            take_quiz(buddy, session)
        elif choice == "3":
            print(buddy.ask(session, input("请输入问题：")))
        elif choice == "4":
            buddy.complete_task(session, input("任务 ID：").strip())
            show_plan(session)
        elif choice == "5":
            return 0
        else:
            print("请输入 1 到 5。")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as exc:
        print("操作未完成：" + str(exc), file=sys.stderr)
        raise SystemExit(1)
