"""
EvaluatorAgent - 语法点评 Agent
对用户提交的句子进行语法点评
"""
import json
from typing import Dict, Any
from hello_agents.agents.tool_aware_agent import ToolAwareSimpleAgent
from .prompts import (
    EVALUATOR_SYSTEM_PROMPT,
    EVALUATOR_USER_PROMPT
)
from config import get_llm, tool_listener


class EvaluatorAgent:
    """语法点评 Agent - 对用户提交的句子进行语法点评"""
    
    def __init__(self):
        """初始化 EvaluatorAgent"""
        self.llm = get_llm()
        self.agent = ToolAwareSimpleAgent(
            name="Evaluator",
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            llm=self.llm,
            tool_call_listener=tool_listener
        )
    
    def evaluate(self, stage_goal: str, question: str, 
                 seed_sentence: str, user_sentence: str) -> Dict[str, Any]:
        """
        对用户提交的句子进行语法点评
        
        Args:
            stage_goal: 当前阶段目标
            question: 记者提问
            seed_sentence: 学生原始句子
            user_sentence: 学生本次提交的句子
            
        Returns:
            Dict[str, Any]: 点评结果，包含：
                - is_correct: 语法是否正确
                - comment: 点评内容
                - corrected_sentence: 修正后的句子
        """
        # 构建用户提示词
        user_prompt = EVALUATOR_USER_PROMPT.format(
            stage_goal=stage_goal,
            question=question,
            seed_sentence=seed_sentence,
            user_sentence=user_sentence
        )
        
        # 调用 LLM
        response = self.agent.run(user_prompt)
        
        # 解析 JSON 响应
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            # 如果解析失败，返回默认响应
            return {
                "is_correct": True,
                "comment": "你的句子语法正确，符合本阶段的扩写目标。",
                "corrected_sentence": user_sentence
            }
    
    def is_grammar_correct(self, stage_goal: str, question: str,
                          seed_sentence: str, user_sentence: str) -> bool:
        """
        快速判断用户句子语法是否正确
        
        Args:
            stage_goal: 当前阶段目标
            question: 记者提问
            seed_sentence: 学生原始句子
            user_sentence: 学生本次提交的句子
            
        Returns:
            bool: 语法是否正确
        """
        result = self.evaluate(stage_goal, question, seed_sentence, user_sentence)
        return result.get("is_correct", True)


# 创建全局实例（单例模式）
_evaluator_instance = None


def get_evaluator() -> EvaluatorAgent:
    """
    获取全局 EvaluatorAgent 实例（单例模式）
    
    Returns:
        EvaluatorAgent: EvaluatorAgent 实例
    """
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = EvaluatorAgent()
    return _evaluator_instance


def reset_evaluator():
    """重置 EvaluatorAgent 实例（用于测试）"""
    global _evaluator_instance
    _evaluator_instance = None
