from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from TraceableCodeAgent import build_traceable_agent


def _check_env() -> list[str]:
    required = ["LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL"]
    missing = [name for name in required if not os.getenv(name)]
    return missing


def _save_result_markdown(repo_root: Path, prompt: str, result: str, step_count: int) -> Path:
    reports_dir = repo_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = reports_dir / f"smoke-test-output-{ts}.md"

    content = (
        "# Smoke Test 输出\n\n"
        f"- 时间: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- 步骤数: {step_count}\n"
        "\n"
        "## Prompt\n\n"
        f"{prompt}\n\n"
        "## Agent 输出\n\n"
        f"{result}\n"
    )

    output_file.write_text(content, encoding="utf-8")
    return output_file


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    os.chdir(repo_root)

    missing = _check_env()
    if missing:
        print("缺少必要环境变量：")
        for name in missing:
            print(f"- {name}")
        print("请先在 .env 中配置好后再运行 smoke test。")
        return 1

    prompt = (
        "请用非常简短的方式验证你已经启动成功，并说明当前仓库的顶层文件/目录是否可读取。"
        "你是一个测试智能体，专门用来分析 TraceableCodeAgent 的基本功能是否正常。请直接返回一个简短的文本说明，不需要任何格式化或额外信息。"
        "另外，请绘制出你的思考流程图（flowchart），展示你是如何处理这个任务的，特别是你如何决定读取哪些文件，以及你是如何记录这些步骤的。流程图可以使用 Mermaid 语法，直接包裹在代码块中返回即可。"
        "最后，请分析traceable agent的 Research Map 中是否正确记录了你的每一步操作，包括工具调用、观察结果和思考过程。如果有任何步骤没有被正确记录，请指出来并说明原因。"
        "另外，可以给出对 TraceableCodeAgent 的初步反馈和改进建议，特别是关于 Research Map 的设计和使用方面。"
    )

    try:
        agent = build_traceable_agent(max_steps=100)
        print("智能体已创建，开始执行 smoke test...\n")
        result = agent.run(prompt)
        print("\n===== Agent 返回结果 =====")
        print(result)

        research_map = agent.get_research_map()
        step_count = len(getattr(research_map, "steps", {}))
        print("\n===== Trace 统计 =====")
        print(f"步骤数: {step_count}")

        md_path = _save_result_markdown(repo_root, prompt, result, step_count)
        print("\n===== Markdown 输出 =====")
        print(f"已写入: {md_path}")

        return 0
    except Exception as exc:
        print("smoke test 执行失败：")
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())