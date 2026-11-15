# -*- coding: utf-8 -*-
"""LabNoteAgent：实验记录整理 Agent（Hello-Agents 框架毕业设计）

用法:
  python main.py            # 交互式多轮对话
  python main.py --demo     # 运行内置演示（几段真实实验记录场景）
"""
import argparse
import os
import sys

os.environ.setdefault("LLM_TIMEOUT", "300")  # 本地小模型生成较慢，放宽客户端超时

from hello_agents import SimpleAgent, HelloAgentsLLM

from labnote.storage import NoteStore
from labnote.tools import CompareExperimentsTool, SaveNoteTool, SearchNotesTool, StatsTool

SYSTEM_PROMPT = """你是 LabNoteAgent，一位实验室记录管理助手，服务对象是做计算机视觉/计算成像科研的学生。

【铁律】你没有任何自带记忆来存储实验数据。所有保存、查询、对比、统计都必须通过调用工具完成。
严禁编造记录 ID、记录内容或统计数字——凡是没看到工具返回的结果，就说"需要查询，请稍候"并去调用工具。

你的职责：
1. 用户随口描述实验 → 调用 save_note：提炼简短 title；方法名/超参数/硬件放入 params；指标放入 results；给 1-3 个英文小写标签（如 stereo, calibration）。不要传 date，工具会自动填今天。
2. 查询历史 → 调用 search_notes（关键词即可）。
3. 对比两次实验 → 直接调用 compare_experiments，a 和 b 都可以传关键词（如实验名里的一两个词），不必先查 ID。
4. "记了多少/最近做了什么" → 调用 note_stats。
5. 工具返回后，用简洁的中文复述结果（列表或一两句话），不要粘贴原始 JSON。
6. 与记录无关的闲聊正常回答，不调用工具。

数值参数保留语义命名（如"基线 12cm"→ baseline_cm=12）。
"""

WELCOME = """LabNoteAgent 已就绪（笔记库：labnote_data.json）
试试：
  · 记一下：今天跑了双目匹配，SGM 方法，基线 12cm，重投影误差 0.8px
  · 上次基线是多少？
  · 对比这两次实验
  · 统计
  quit 退出
"""


def build_agent(store_path: str = None) -> SimpleAgent:
    store = NoteStore(store_path)
    agent = SimpleAgent(name="LabNoteAgent", llm=HelloAgentsLLM(), system_prompt=SYSTEM_PROMPT)
    for tool in (SaveNoteTool(store), SearchNotesTool(store), CompareExperimentsTool(store), StatsTool(store)):
        agent.add_tool(tool)
    return agent


DEMO_TURNS = [
    "记一下：今天跑了双目立体匹配，SGM 方法，基线 12cm，重投影误差 0.8px，图对 35 对",
    "再记一条：换了半全局+左右一致性检查，基线还是 12cm，重投影误差 0.5px",
    "对比一下这两次实验",
    "统计一下",
]


def run_demo(agent):
    for i, q in enumerate(DEMO_TURNS, 1):
        print(f"\n{'='*60}\n[用户] {q}")
        try:
            resp = agent.run(q)
            print(f"[LabNoteAgent] {resp}")
        except Exception as e:
            # 本地小模型可能超时/步数耗尽；单轮失败不中断演示
            print(f"[LabNoteAgent] （本轮出错：{e}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="运行内置演示对话")
    ap.add_argument("--store", type=str, default=None, help="笔记库 JSON 路径")
    args = ap.parse_args()

    agent = build_agent(args.store)
    if args.demo:
        run_demo(agent)
        return

    print(WELCOME)
    while True:
        try:
            q = input("\n[你] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("quit", "exit", "q"):
            break
        if not q:
            continue
        print(f"[LabNoteAgent] {agent.run(q)}")


if __name__ == "__main__":
    sys.exit(main())
