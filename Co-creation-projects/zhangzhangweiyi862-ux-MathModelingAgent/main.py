from pathlib import Path

from src.llm_client import LLMClient
from src.problem_analysis_agent import ProblemAnalysisAgent
from src.data_audit_agent import DataAuditAgent
from src.modeling_agent import ModelingAgent
from src.report_agent import ReportAgent


SAMPLE_PROBLEM = """
某微电网包含用户负荷、光伏发电系统、储能设备和外部电网。
每个时间段内，光伏、储能放电和外网购电共同满足用户负荷。
多余的光伏电量可以用于储能，无法利用的部分允许弃置。
储能容量和最大充放电功率均有限制。

已知未来一天各时段的负荷预测、光伏预测和电价，
要求制定购电与储能充放电策略，使全天购电费用尽可能低，
同时保证每个时段的供需平衡。
"""


def run_pipeline(problem_text: str) -> str:
    """
    运行完整的多智能体建模流程。
    """

    llm = LLMClient()

    problem_agent = ProblemAnalysisAgent(llm)
    audit_agent = DataAuditAgent(llm)
    modeling_agent = ModelingAgent(llm)
    report_agent = ReportAgent(llm)

    print("\n[1/4] ProblemAnalysisAgent 正在分析赛题...")
    problem_analysis = problem_agent.analyze(problem_text)

    print("[2/4] DataAuditAgent 正在进行数据与信息审计...")
    data_audit = audit_agent.audit(
        problem_text=problem_text,
        problem_analysis=problem_analysis,
    )

    print("[3/4] ModelingAgent 正在设计数学模型...")
    model_design = modeling_agent.design(
        problem_text=problem_text,
        problem_analysis=problem_analysis,
        data_audit=data_audit,
    )

    print("[4/4] ReportAgent 正在生成最终报告...")
    final_report = report_agent.generate(
        problem_text=problem_text,
        problem_analysis=problem_analysis,
        data_audit=data_audit,
        model_design=model_design,
    )

    return final_report


def save_report(report: str) -> Path:
    """
    保存最终 Markdown 报告。
    """

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "modeling_report.md"

    output_file.write_text(
        report,
        encoding="utf-8",
    )

    return output_file


def main():
    print("=" * 60)
    print("MathModelingAgent")
    print("数学建模多智能体研究助手")
    print("=" * 60)

    report = run_pipeline(SAMPLE_PROBLEM)

    output_file = save_report(report)

    print("\n" + "=" * 60)
    print("多智能体任务完成")
    print(f"报告已保存：{output_file.resolve()}")
    print("=" * 60)

    print("\n=== 最终报告 ===\n")
    print(report)


if __name__ == "__main__":
    main()