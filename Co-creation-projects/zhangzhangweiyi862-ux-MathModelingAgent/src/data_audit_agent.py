from .llm_client import LLMClient


class DataAuditAgent:
    """
    数据与信息审计智能体。

    根据原始赛题以及 ProblemAnalysisAgent 的分析结果，
    检查数据可用性、信息完整性、潜在数据泄漏、
    指标选择以及进入建模前的风险。
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def audit(
        self,
        problem_text: str,
        problem_analysis: str,
    ) -> str:

        if not problem_text.strip():
            raise ValueError("problem_text 不能为空。")

        if not problem_analysis.strip():
            raise ValueError("problem_analysis 不能为空。")

        system_prompt = """
你是一名严谨的数学建模“数据审计智能体”。

你的任务不是建立最终数学模型，而是在建模之前检查：
数据、时间信息、统计口径、评价指标和信息边界是否可靠。

必须遵守：

1. 不能虚构数据；
2. 题目没有给出的信息必须明确标记为“待确认”；
3. 区分原始数据、预测数据、决策时可用信息和未来真实数据；
4. 特别检查未来信息泄漏风险；
5. 判断异常值、缺失值、重复值、量纲和时间粒度可能产生的问题；
6. 评价指标必须与数据特点相匹配；
7. 最后必须判断是否可以进入建模阶段。

你的目标是防止“数据没搞清楚就直接建模”。
"""

        user_prompt = f"""
下面是一道数学建模题及前序智能体的解析结果。

【原始赛题】
{problem_text}

【ProblemAnalysisAgent 输出】
{problem_analysis}

请完成建模前数据审计，并严格按照下面结构输出：

# 1. 数据对象清单
列出问题涉及的主要数据对象。

# 2. 数据角色
分别说明哪些属于：
- 已知输入
- 预测输入
- 状态变量相关数据
- 决策输出
- 结果评价数据

# 3. 数据质量检查项
检查或建议检查：
- 缺失值
- 重复值
- 异常值
- 极端值
- 时间戳
- 时间粒度
- 单位与量纲
- 数据范围
- 数据对齐

如果题目没有真实数据文件，不要虚构检查结果，
而应明确写成“需要检查”。

# 4. 时间与信息集审计
明确在每个决策时刻：
- 可以知道什么
- 不可以知道什么
- 哪些信息属于未来信息

重点判断是否存在未来信息泄漏风险。

# 5. 数据预处理建议
仅提出必要的数据处理步骤，不要为了复杂而复杂。

# 6. 评价指标建议
根据问题性质提出合理指标，并解释理由。

# 7. 潜在风险
列出会导致模型结论失真的数据风险。

# 8. 待确认信息
列出题目或数据中仍然缺失的关键内容。

# 9. Gate 判断
只能从下面三种结论中选择一种：

- Gate：通过，可以进入建模
- Gate：有条件通过，需要明确若干假设
- Gate：不通过，需要补充关键信息

必须说明理由。

# 10. 给 ModelingAgent 的输入建议
总结下一阶段建模时必须遵守的数据边界。
"""

        return self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1.0,
        )


if __name__ == "__main__":

    from .problem_analysis_agent import ProblemAnalysisAgent

    sample_problem = """
某微电网包含用户负荷、光伏发电系统、储能设备和外部电网。
每个时间段内，光伏、储能放电和外网购电共同满足用户负荷。
多余的光伏电量可以用于储能，无法利用的部分允许弃置。
储能容量和最大充放电功率均有限制。

已知未来一天各时段的负荷预测、光伏预测和电价，
要求制定购电与储能充放电策略，使全天购电费用尽可能低，
同时保证每个时段的供需平衡。
"""

    problem_agent = ProblemAnalysisAgent()

    analysis = problem_agent.analyze(sample_problem)

    audit_agent = DataAuditAgent()

    audit = audit_agent.audit(
        problem_text=sample_problem,
        problem_analysis=analysis,
    )

    print("=== DataAuditAgent 测试 ===")
    print(audit)