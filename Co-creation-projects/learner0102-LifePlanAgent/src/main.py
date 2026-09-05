# main.py
from agent import MainAgent
from model import UserMemory


def build_demo_user_memory() -> UserMemory:
    return UserMemory(
        user_id="user_001",
        work_start="08:00",
        work_end="18:00",
        rest_days=["Saturday", "Sunday"],
        avoid_time=["12:00‑13:30"],
        preference={"priority_rule": "工作类任务优先安排"},
        hobbies=["慢跑", "看书"],
        dislike=["早起高强度运动"]
    )


def main():
    print("===== 多智能体协同日程规划助手 =====")
    agent = MainAgent()
    try:
        mem, plan = agent.load_session("../data/session.json")
    except:
        mem, plan = None, None
    memory = build_demo_user_memory()
    current_plan = None

    while True:
        print("\n--------------------------------")
        user_input = input("请输入你的需求(exit退出)：").strip()
        if user_input.lower() in ("exit", "quit"):
            agent.save_session("../data/session.json", memory, current_plan)
            print("程序退出。")
            break
        if not user_input:
            print("输入不能为空，请重新输入。")
            continue
        if mem and plan:
            plan, output_text = agent.run(user_input, memory, current_plan, mem, plan)
        else:
            plan, output_text = agent.run(user_input, memory, current_plan)
        print(f"\n【助手回复】：{output_text}")

        if plan is not None:
            current_plan = plan
            print("\n=====📋 当前生效计划 =====")
            print(f"计划ID：{plan.plan_id}")
            print(f"创建时间：{plan.create_time}")
            print(f"冲突校验结果：{plan.conflict_check_result}")
            print("---日程列表---")
            for item in plan.schedule_items:
                print(f"{item.start_time} ~ {item.end_time} | {item.task_name}")
        else:
            print("\n⚠️未生成有效计划，请根据提示补充信息或者重新输入。")


if __name__ == "__main__":
    main()
