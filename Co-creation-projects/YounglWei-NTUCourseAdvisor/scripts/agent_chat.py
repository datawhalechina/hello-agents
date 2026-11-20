"""D2 端到端问答入口：交互 demo 与自测两种模式。

- 交互模式（demo / 检查点②用）：.venv/Scripts/python.exe scripts/agent_chat.py
  同一 Agent 实例连续提问，支持多轮上下文；输入 q 退出
- 自测模式：.venv/Scripts/python.exe scripts/agent_chat.py --selftest
  跑 SELFTEST_QUERIES（中英混合 + 1 条库外课程验证"查不到明说"），
  打印每题回答与耗时，全部回答应附来源
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.agent import build_agent  # noqa: E402

SELFTEST_QUERIES = [
    "SC2001 是几 AU？哪些学期开课？",                                # 课程码·字段
    "我是 CCA 2027 春入学的新生，想选人工智能/机器学习方向的课，有哪些选择？",  # 中文语义→英文课名
    "Which courses are mutually exclusive with CB1131?",             # 英文·互斥字段
    "I'm interested in renewable energy and smart grid. Any suitable courses?",  # 英文·语义
    "SC4001 这门深度学习课需要什么先修基础？",                          # 中文·先修字段
    "What is CC0001 about, and is it offered in both semesters?",     # 英文·多字段
    "CS1010S 这门课怎么样？讲什么内容？",                              # 库外课程（NUS 课码）→ 必须明说未查到
    "我是研究生，SC4000和SC2300是研究生的课程吗？",                     # 属性查询（不过滤，按 Level 字段答）
]


def run_query(agent, query: str) -> tuple[str, float]:
    start = time.time()
    answer = agent.run(query)
    return answer, time.time() - start


def selftest(only: str | None = None):
    indices = (
        {int(i) for i in only.split(",")} if only else set(range(1, len(SELFTEST_QUERIES) + 1))
    )
    queries = [(i, q) for i, q in enumerate(SELFTEST_QUERIES, 1) if i in indices]
    agent = build_agent()
    for i, query in queries:
        print(f"\n{'=' * 70}\n[自测 {i}/{len(SELFTEST_QUERIES)}] Q: {query}")
        answer, elapsed = run_query(agent, query)
        print(f"\nA: {answer}")
        print(f"[耗时 {elapsed:.1f}s]")
    print(f"\n{'=' * 70}\n自测完成：本次跑 {len(queries)} 条，请人工核对"
          "（全部回答应附来源；第 7 条应明说未查到 CS1010S）")


def chat():
    agent = build_agent()
    print("NTU 选课助手（ReAct 单 Agent · 混合检索 · glm-4-flash）")
    print("输入问题开始提问，输入 q 退出。\n")
    while True:
        try:
            query = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            continue
        if query.lower() in {"q", "quit", "exit"}:
            break
        answer, elapsed = run_query(agent, query)
        print(f"\n助手: {answer}\n[耗时 {elapsed:.1f}s]\n")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        only = None
        if "--only" in sys.argv:
            only = sys.argv[sys.argv.index("--only") + 1]
        selftest(only)
    else:
        chat()
