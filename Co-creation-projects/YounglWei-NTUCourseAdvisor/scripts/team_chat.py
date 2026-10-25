"""D3 三 Agent 端到端入口：交互 demo 与自测两种模式。

- 交互模式：.venv/Scripts/python.exe scripts/team_chat.py
  CourseAdvisorTeam 连续对话（身份缓存、反问-答复挂起），输入 q 退出
- 自测模式：.venv/Scripts/python.exe scripts/team_chat.py --selftest [--only n,n]
  D2 基线 8 条回归（不退化）+ D3 新场景（身份消歧/反问-答复流/校验工具触发），
  每场景独立会话；全部回答应附来源，阶段日志含 Planner/Retrieval/Reviewer 轨迹
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.team import CourseAdvisorTeam  # noqa: E402

# 场景 = (名称, 用户输入序列)；序列 >1 = 身份反问后的答复步
SCENARIOS = [
    # ---- D2 基线 8 条（回归，不退化） ----
    ("基线1·课程码字段", ["SC2001 是几 AU？哪些学期开课？"]),
    ("基线2·中文语义检索", ["我是 CCA 2027 春入学的新生，想选人工智能/机器学习方向的课，有哪些选择？"]),
    ("基线3·英文互斥字段", ["Which courses are mutually exclusive with CB1131?"]),
    ("基线4·英文语义", ["I'm interested in renewable energy and smart grid. Any suitable courses?"]),
    ("基线5·中文先修字段", ["SC4001 这门深度学习课需要什么先修基础？"]),
    ("基线6·英文多字段", ["What is CC0001 about, and is it offered in both semesters?"]),
    ("基线7·库外课程码", ["CS1010S 这门课怎么样？讲什么内容？"]),  # 必须明说未查到
    ("基线8·属性查询", ["我是研究生，SC4000和SC2300是研究生的课程吗？"]),  # 不过滤，按 Level 字段答
    # ---- D3 新场景 ----
    ("D3·身份消歧-项目词唯一命中", ["我是 CCA 新生，推荐几门机器学习相关的课"]),
    # 期望：不再反问（D2 已知限制根治），项目词唯一命中 → graduate → 只推研究生课
    ("D3·身份消歧-反问答复流", ["推荐几门好课", "研究生"]),
    # 期望：第 1 步零身份信号且推荐需要 level → 反问；第 2 步答复 → 身份确认 → 完整回答
    ("D3·校验工具触发", ["我是 CCA 学生，已选 EE6203、EE6204、EE6221、SC1003、CC0001，"
                       "帮我检查是否符合学位要求、有没有时间冲突"]),
    # 期望：触发 check_specialized_electives / check_au_limit / check_schedule_conflict，
    # 结论引用工具返回与规则来源；SC1003/CC0001 本科课如实提示不在 CCA 库
]


def run_scenario(team: CourseAdvisorTeam, inputs: list[str]) -> float:
    start = time.time()
    for step, text in enumerate(inputs, 1):
        print(f"  你({step}): {text}")
        answer = team.run(text)
        print(f"  助手({step}): {answer}\n")
    return time.time() - start


def selftest(only: str | None = None):
    indices = (
        {int(i) for i in only.split(",")} if only else set(range(1, len(SCENARIOS) + 1))
    )
    picked = [(i, s) for i, s in enumerate(SCENARIOS, 1) if i in indices]
    for i, (name, inputs) in picked:
        print(f"\n{'=' * 70}\n[自测 {i}/{len(SCENARIOS)}] {name}")
        team = CourseAdvisorTeam()  # 每场景独立会话（身份互不污染）
        elapsed = run_scenario(team, inputs)
        print(f"[耗时 {elapsed:.1f}s]")
    print(f"\n{'=' * 70}\n自测完成：本次跑 {len(picked)} 个场景，请人工核对：\n"
          "- 基线 1-8：回答附来源、第 7 条明说未查到、第 8 条按 Level 字段如实答\n"
          "- D3 场景：阶段日志中 Planner 身份判定 / Reviewer PASS-FAIL 轨迹 / 校验工具调用\n"
          "- Reviewer 打回-重试流：观察日志是否出现 FAIL→修订（未出现时 Reviewer 防线"
          "由单元冒烟兜底：python -m src.team）")


WELCOME = """\
NTU 选课助手 —— 课程信息问答与选课参考（Planner / Retrieval / Reviewer 三 Agent）

我能做：
  查课程信息    学分（AU）、开课学期、先修要求、互斥课程、课程简介
  查专业课程    某个专业开设哪些课（专选 / 通选）
  核对学位要求  专选门数、AU 上限、先修 / 互斥、时间冲突
  按兴趣推荐    告诉我身份和感兴趣的方向

课程信息可以直接问，例如：EE6407 讲什么？
需要按专业推荐时，先说明身份，例如：我是 CCA 新生，想选机器学习方向的课

所有课程信息均来自 NTU 官方课程库，回答附来源；查不到会明说，不编造。

当前课程库覆盖范围：
  本科   CCDS 学院 5 个专业 — CSC 计算机科学 / CE 计算机工程 /
         DSAI 数据科学与人工智能 / AISC 人工智能与社会 / COMP 计算
  研究生 MSc Computer Control & Automation（CCA）
         MSc Robotics and Intelligent Systems
其他学院的专业暂未收录。

输入问题开始，输入 q 退出。
"""


def chat():
    team = CourseAdvisorTeam()
    print(WELCOME)
    while True:
        try:
            query = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            continue
        if query.lower() in {"q", "quit", "exit"}:
            break
        start = time.time()
        answer = team.run(query)
        print(f"\n助手: {answer}\n[耗时 {time.time() - start:.1f}s]\n")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        only = None
        if "--only" in sys.argv:
            only = sys.argv[sys.argv.index("--only") + 1]
        selftest(only)
    else:
        chat()
