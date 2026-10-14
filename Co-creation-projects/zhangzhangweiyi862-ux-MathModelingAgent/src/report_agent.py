from .llm_client import LLMClient


class ReportAgent:
    """
    报告汇总智能体。

    将前面三个 Agent 的输出整理为一份
    结构化、可提交、可继续扩展的建模报告。
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(
        self,
        problem_text: str,
        problem_analysis: str,
        data_audit: str,
        model_design: str,
    ) -> str:

        if not problem_text.strip():
            raise ValueError("problem_text 不能为空。")

        if not problem_analysis.strip():
            raise ValueError("problem_analysis 不能为空。")

        if not data_audit.strip():
            raise ValueError("data_audit 不能为空。")

        if not model_design.strip():
            raise ValueError("model_design 不能为空。")

        system_prompt = """
你是一名数学建模项目的“报告汇总智能体”。

你的任务不是重新发明模型，
而是根据前三个智能体已经完成的分析，
生成一份逻辑一致、边界清楚、可复查的最终建模报告。

必须遵守：

1. 不得虚构题目未给出的数据；
2. 不得擅自覆盖 DataAuditAgent 的 Gate 结论；
3. 缺失参数必须继续明确标注；
4. 模型必须与 ModelingAgent 的方案保持一致；
5. 区分事实、假设、模型设计和升级建议；
6. 最终输出使用 Markdown；
7. 内容要适合进一步修改为数学建模论文或项目技术文档。
"""

        user_prompt = f"""
请根据以下材料生成最终建模报告。

【原始问题】
{problem_text}

【ProblemAnalysisAgent】
{problem_analysis}

【DataAuditAgent】
{data_audit}

【ModelingAgent】
{model_design}

请严格按照以下结构输出：

# MathModelingAgent 建模分析报告

## 1. 问题概述
简明描述研究对象和任务。

## 2. 核心建模任务
总结真正需要解决的问题。

## 3. 信息与数据边界
整理已知信息、预测信息、缺失信息，
并明确是否存在未来信息泄漏风险。

## 4. 数据审计结论
总结 DataAuditAgent 的关键结论。

必须明确给出 Gate 状态。

## 5. 建模假设
只保留必要且有依据的假设。

## 6. 符号与变量
整理最核心的参数、状态变量和决策变量。

## 7. Baseline 数学模型
说明模型类型、核心机制和为什么选择它。

## 8. 目标函数
给出主要目标函数及解释。

## 9. 核心约束
整理最主要的约束体系。

## 10. 求解与实现方案
说明输入、求解器/算法和输出。

## 11. 模型验证方案
说明如何验证模型正确性和可靠性。

## 12. 当前限制
说明当前仍然无法解决或必须补充的信息。

## 13. 可升级方向
最多保留 3 个真正有必要的方向。

## 14. 最终结论
总结当前可以确定的模型框架，
并说明在什么条件下可以进入数值求解。

禁止编造实验结果、求解结果和数据统计结果。
"""

        return self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1.0,
        )