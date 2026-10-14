from .llm_client import LLMClient


class ModelingAgent:
    """
    数学模型设计智能体。

    接收：
    1. 原始问题
    2. ProblemAnalysisAgent 输出
    3. DataAuditAgent 输出

    在严格遵守数据边界的前提下，
    给出可实现、可解释、可验证的模型方案。
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def design(
        self,
        problem_text: str,
        problem_analysis: str,
        data_audit: str,
    ) -> str:

        if not problem_text.strip():
            raise ValueError("problem_text 不能为空。")

        if not problem_analysis.strip():
            raise ValueError("problem_analysis 不能为空。")

        if not data_audit.strip():
            raise ValueError("data_audit 不能为空。")

        system_prompt = """
你是一名严谨的数学建模“模型设计智能体”。

你的任务是在赛题解析和数据审计之后，
构造一个可解释、可实现、可验证的数学模型方案。

必须遵守以下原则：

1. 不允许虚构题目未给出的参数；
2. 如果 DataAuditAgent 判定 Gate 不通过，
   不得直接编造参数强行构建数值模型；
3. 可以使用符号参数建立通用模型；
4. 必须明确变量、参数、目标函数和约束；
5. 优先建立简单、透明、可验证的 Baseline；
6. 不能为了复杂而复杂；
7. 如果需要升级模型，必须说明 Baseline 的不足；
8. 所有时间、功率、能量单位必须一致；
9. 不得引入决策时刻不可获得的未来真实信息；
10. 必须给出验证方法。
"""

        user_prompt = f"""
下面是一道数学建模问题，以及前两个智能体的结果。

【原始问题】
{problem_text}

【ProblemAnalysisAgent 输出】
{problem_analysis}

【DataAuditAgent 输出】
{data_audit}

请根据以上信息完成模型设计。

严格按照以下结构输出：

# 1. 建模目标

说明本问题最终要解决什么问题。

# 2. 建模假设

只列必要假设。

如果数据审计中某些参数缺失，
必须明确标记为“符号参数”或“待题目补充参数”，
不能擅自指定数值。

# 3. 符号与参数

建立清晰的符号系统，包括：

- 时间索引
- 已知参数
- 状态变量
- 决策变量
- 必要辅助变量

给出物理含义和单位。

# 4. Baseline 模型

优先构造最简单且能够正确解决问题的模型。

说明属于：

- 线性规划 LP
- 混合整数规划 MILP
- 动态规划
- 非线性规划
- 预测模型
- 评价模型
- 仿真模型
- 其他

并解释理由。

# 5. 目标函数

给出数学表达式，并逐项解释。

# 6. 核心约束

至少检查是否涉及：

- 供需平衡
- 状态递推
- 容量约束
- 功率约束
- 非负约束
- 逻辑约束
- 边界条件
- 初始条件
- 终端条件

没有依据的约束不要虚构。

# 7. 模型求解方法

说明：

- 推荐求解器或算法
- 输入
- 输出
- 求解流程

# 8. Gate 未通过时的处理

如果 DataAuditAgent 判定关键信息不足，
明确说明：

哪些公式可以先建立，
哪些参数必须补充后才能进行数值求解。

# 9. 模型验证

提出可执行的验证方法，例如：

- 约束残差
- 供需平衡误差
- 状态递推残差
- 边界检查
- 敏感性分析
- Baseline 对比

# 10. 可升级方向

只有存在明确理由时，
提出最多 3 个升级方向。

每个方向说明：
- 为什么升级
- 解决 Baseline 什么不足
- 新增什么复杂度

# 11. 给 ReportAgent 的核心结论

用简洁语言总结最终模型设计框架。
"""

        return self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1.0,
        )


if __name__ == "__main__":

    from .problem_analysis_agent import ProblemAnalysisAgent
    from .data_audit_agent import DataAuditAgent

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

    modeling_agent = ModelingAgent()
    model_design = modeling_agent.design(
        problem_text=sample_problem,
        problem_analysis=analysis,
        data_audit=audit,
    )

    print("=== ModelingAgent 测试 ===")
    print(model_design)