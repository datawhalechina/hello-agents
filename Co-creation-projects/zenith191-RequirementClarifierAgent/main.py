"""RequirementClarifierAgent 命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agents import build_agent_team
from src.config import ConfigurationError, LLMSettings
from src.tools import create_tool_registry
from src.workflow import RequirementClarifierWorkflow, WorkflowExecutionError


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "sample_requirement.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "requirement_report.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用 HelloAgents 多智能体协作澄清需求并生成技术方案"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="UTF-8 需求文本路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="最终 Markdown 报告路径",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="只运行确定性需求完整度检查，不调用 LLM",
    )
    parser.add_argument(
        "--show-intermediate",
        action="store_true",
        help="在控制台显示三个专家的中间结果",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        requirement = args.input.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"错误：找不到输入文件 {args.input}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(f"错误：输入文件必须使用 UTF-8 编码：{args.input}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"错误：无法读取输入文件 {args.input}：{exc}", file=sys.stderr)
        return 2

    registry = create_tool_registry()
    if args.audit_only:
        tool = registry.get_tool("requirement_audit")
        if tool is None:
            print("错误：需求初检工具未注册", file=sys.stderr)
            return 2
        response = tool.run({"requirement_text": requirement})
        print(response)
        payload = json.loads(response)
        return 0 if payload.get("ok") else 2

    load_dotenv(PROJECT_ROOT / ".env")
    try:
        settings = LLMSettings.from_env()
        team = build_agent_team(settings, registry)
        workflow = RequirementClarifierWorkflow(team, registry)
        result = workflow.run(requirement)
        output_path = workflow.save_report(result, args.output)
    except (ConfigurationError, WorkflowExecutionError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    if args.show_intermediate:
        print("\n=== 需求分析师 ===\n" + result.analysis)
        print("\n=== 方案架构师 ===\n" + result.architecture)
        print("\n=== 风险审查员 ===\n" + result.risk_review)
    print(
        f"完成：报告已保存到 {output_path}；"
        f"结构评分 {result.quality.get('score', 0)}/100。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
