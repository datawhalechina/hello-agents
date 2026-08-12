"""StockInsightAgent — 智能股票分析助手

用法:
  python main.py             交互菜单
  python main.py "问题"       快速分析 (框架 ReAct)
  python main.py -d "问题"    深度分析 (框架 PlanSolve)
  python main.py -r "问题"    批判分析 (框架 Reflection)
"""
import sys
from llm_client import HelloAgentsLLM
from agent import StockInsightAgent
from plan_agent import PlanAndSolveStockAgent
from reflection_agent import ReflectionStockAgent
from framework_agent import FrameworkStockAgent
from memory import memory_get_watchlist, memory_get_history
from rag import rag_import, rag_stats


def show_banner():
    print()
    print("  ╔═════════════════════════════════════════════════════════════╗")
    print("  ║                                                             ║")
    print("  ║         StockInsightAgent v2.0   智能股票分析助手             ║")
    print("  ║                                                             ║")
    print("  ║   数据: akshare 实时行情 + 财务 + 新闻                        ║")
    print("  ║   记忆: 关注列表 | 分析历史 | 用户偏好                         ║")
    print("  ║   知识: 估值体系 | 技术指标 | 风控原则                         ║")
    print("  ║                                                             ║")
    print("  ╚═════════════════════════════════════════════════════════════╝")
    print()


MENU = """
  ┌────────────────────────────────────────────────────────────┐
  │                                                            │
  │  [1]  快速分析        框架 ReAct           ~30秒            │
  │  [2]  深度分析        框架 PlanSolve       ~2分钟            │
  │  [3]  批判分析        框架 Reflection      ~3分钟            │
  │                                                            │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │  [4]  ReAct           手写解析+循环                         │
  │  [5]  PlanSolve       手写规划+执行                         │
  │  [6]  Reflection      手写记忆+反思                         │
  │                                                            │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │  [w]  查看关注列表                                          │
  │  [h]  查看分析历史                                          │
  │  [k]  导入投资文档到知识库                                   │
  │                                                            │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │  [m]  重新显示菜单                                          │
  │  [0]  退出                                                  │
  │                                                            │
  └────────────────────────────────────────────────────────────┘
"""

EXAMPLES = """
  直接输入问题即可开始分析，例如:
    Stock> 分析贵州茅台600519当前估值
    Stock> 对比五粮液和茅台的估值

  先选模式，再输入问题:
    Stock> 2                (切换到深度分析)
    Stock> 全面评估比亚迪002594
"""


def main():
    # ── 命令行参数快捷模式 ──
    if len(sys.argv) > 1:
        a = FrameworkStockAgent()
        if "-d" in sys.argv:
            sys.argv.remove("-d")
            q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("问题: ").strip()
            print(a.plan_solve(q))
        elif "-r" in sys.argv:
            sys.argv.remove("-r")
            q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("问题: ").strip()
            print(a.reflect(q))
        else:
            q = " ".join(sys.argv[1:])
            print(a.react(q))
        return

    # ── 交互菜单模式 ──
    show_banner()
    print(MENU)
    print(EXAMPLES)

    fw = FrameworkStockAgent()
    mode = "react"  # 当前模式

    while True:
        try:
            q = input("\nStock> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见")
            break

        if not q:
            continue

        # 菜单选择
        if q in ("1", "2", "3", "4", "5", "6", "w", "h", "k", "m", "0"):
            if q == "1":
                mode = "react"
                print("  >> 切换到 [快速分析] 模式。输入你的问题:")
            elif q == "2":
                mode = "plan"
                print("  >> 切换到 [深度分析] 模式。输入你的问题:")
            elif q == "3":
                mode = "reflect"
                print("  >> 切换到 [批判分析] 模式。输入你的问题:")
            elif q == "4":
                mode = "raw-react"
                print("  >> 切换到 [教学版 ReAct] 模式。输入你的问题:")
            elif q == "5":
                mode = "raw-plan"
                print("  >> 切换到 [教学版 PlanSolve] 模式。输入你的问题:")
            elif q == "6":
                mode = "raw-reflect"
                print("  >> 切换到 [教学版 Reflection] 模式。输入你的问题:")
            elif q == "w":
                print(memory_get_watchlist())
            elif q == "h":
                code = input("  股票代码 (回车看全部): ").strip()
                print(memory_get_history(code))
            elif q == "k":
                path = input("  文档路径: ").strip()
                print(rag_import(path))
                print(rag_stats())
            elif q == "m":
                print(MENU)
            elif q == "0":
                print("再见")
                break
            continue

        # 执行分析
        print()
        if mode == "react":
            print(fw.react(q))
        elif mode == "plan":
            print(fw.plan_solve(q))
        elif mode == "reflect":
            print(fw.reflect(q))
        elif mode == "raw-react":
            StockInsightAgent(HelloAgentsLLM(), max_steps=6).run(q)
        elif mode == "raw-plan":
            PlanAndSolveStockAgent(HelloAgentsLLM()).run(q)
        elif mode == "raw-reflect":
            ReflectionStockAgent(HelloAgentsLLM(), max_iterations=2).run(q)


if __name__ == "__main__":
    main()
