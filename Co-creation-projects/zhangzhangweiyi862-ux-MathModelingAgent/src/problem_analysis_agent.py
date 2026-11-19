from .llm_client import LLMClient


class ProblemAnalysisAgent:
    """
    赛题解析智能体。

    负责将原始数学建模问题转化为结构化的建模任务描述，
    为后续数据审计与模型设计提供基础。
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def analyze(self, problem_text: str) -> str:
        if not problem_text or not problem_text.strip():
            raise ValueError("problem_text 不能为空。")

        system_prompt = """
你是一名数学建模竞赛中的“赛题解析智能体”。

你的任务不是立即给出最终模型，而是首先准确理解题目，
将复杂的实际问题拆解成清晰、可执行的数学建模任务。

请特别遵守以下原则：
1. 不虚构题目中没有提供的数据或条件；
2. 明确区分已知条件、待求量和需要补充的信息；
3. 优先识别目标、约束、决策变量和评价指标；
4. 如果存在信息缺失或歧义，必须明确指出；
5. 暂时不要展开复杂算法和代码实现。
"""

        user_prompt = f"""
请对下面的数学建模问题进行结构化分析：

【原始问题】
{problem_text}

请严格按照以下结构输出：

# 1. 问题背景
概括现实场景以及研究对象。

# 2. 核心任务
列出题目真正需要解决的主要任务。

# 3. 已知信息
整理题目明确给出的数据、规则和条件。

# 4. 待求量
说明最终需要计算、预测或优化的对象。

# 5. 决策变量候选
给出后续数学模型可能需要定义的主要决策变量。

# 6. 目标函数候选
判断可能涉及哪些优化目标。

# 7. 关键约束
整理可能存在的物理、资源、时间或逻辑约束。

# 8. 数据需求
说明完成建模需要哪些数据，以及哪些数据可能需要进一步检查。

# 9. 建模类型初判
判断问题可能属于优化、预测、评价、分类、仿真或其他类型。
可以存在多种类型，但要解释理由。

# 10. 信息缺口与风险
列出当前不能确定、容易误解或可能导致错误建模的地方。

最后给出一句“下一步建议”，但不要直接构建最终数学模型。
"""

        return self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1.0,
        )


if __name__ == "__main__":
    sample_problem = """
某微电网包含用户负荷、光伏发电系统、储能设备和外部电网。
每个时间段内，光伏、储能放电和外网购电共同满足用户负荷。
多余的光伏电量可以用于储能，无法利用的部分允许弃置。
储能容量和最大充放电功率均有限制。

已知未来一天各时段的负荷预测、光伏预测和电价，
要求制定购电与储能充放电策略，使全天购电费用尽可能低，
同时保证每个时段的供需平衡。
"""

    agent = ProblemAnalysisAgent()

    result = agent.analyze(sample_problem)

    print("=== ProblemAnalysisAgent 测试 ===")
    print(result)