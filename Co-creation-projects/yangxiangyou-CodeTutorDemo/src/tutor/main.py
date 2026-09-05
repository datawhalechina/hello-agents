"""程序入口，读取用户输入并运行一轮编程导师流程。"""

from __future__ import annotations

from tutor.graph import build_tutor_graph
from tutor.model import build_default_llm
from tutor.state import init_state


def print_summary(state: dict) -> None:
    """用较友好的方式展示最终结果，方便课程演示。"""

    print("=" * 50)
    print("CodeTutorDemo")
    print("=" * 50)
    print(state["summary"])


def main() -> None:
    """读取一次输入，执行一轮导师回答。"""

    user_input = input("请输入你的编程问题，或者直接贴一段 Python 代码：\n")
    try:
        llm_adapter = build_default_llm()
    except ValueError as error:
        print(f"配置错误：{error}")
        return

    tutor_graph = build_tutor_graph(llm_adapter).compile()
    final_state = tutor_graph.invoke(init_state(user_input=user_input))
    print_summary(final_state)


if __name__ == "__main__":
    main()
