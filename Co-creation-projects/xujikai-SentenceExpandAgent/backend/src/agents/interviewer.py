"""
InterviewerAgent - 记者提问 Agent
扮演记者，根据当前阶段生成提问
"""
import json
from typing import Dict, Any, Literal
from hello_agents.agents.tool_aware_agent import ToolAwareSimpleAgent
from .prompts import (
    INTERVIEWER_SYSTEM_PROMPT,
    INTERVIEWER_STAGE1_PROMPT,
    INTERVIEWER_STAGE2_PROMPT,
    INTERVIEWER_STAGE3_PROMPT,
    STAGE_GOALS
)
from config import get_llm, tool_listener

class InterviewerAgent:
    """记者提问 Agent - 根据当前阶段生成提问"""
    
    def __init__(self):
        """初始化 InterviewerAgent"""
        self.llm = get_llm()
        self.agent = ToolAwareSimpleAgent(
            name="Interviewer",
            system_prompt=INTERVIEWER_SYSTEM_PROMPT,
            llm=self.llm,
            tool_call_listener=tool_listener
        )
    
    def ask(self, stage: Literal["stage1", "stage2", "stage3"], 
            current_sentence: str, rounds_history: str = "") -> Dict[str, Any]:
        """
        根据当前阶段生成提问
        
        Args:
            stage: 当前阶段 (stage1/stage2/stage3)
            current_sentence: 当前句子
            rounds_history: 历史轮次摘要（用于 stage2/stage3）
            
        Returns:
            Dict[str, Any]: 提问结果，包含：
                - question: 提问内容
                - hint: 语法结构提示
                - example: 示范改写（可选）
                - stage_goal: 当前阶段目标
        """
        # 根据阶段选择对应的提示词
        if stage == "stage1":
            user_prompt = INTERVIEWER_STAGE1_PROMPT.format(
                current_sentence=current_sentence
            )
        elif stage == "stage2":
            user_prompt = INTERVIEWER_STAGE2_PROMPT.format(
                current_sentence=current_sentence,
                rounds_history=rounds_history
            )
        elif stage == "stage3":
            user_prompt = INTERVIEWER_STAGE3_PROMPT.format(
                current_sentence=current_sentence,
                rounds_history=rounds_history
            )
        else:
            raise ValueError(f"Invalid stage: {stage}")
        
        # 调用 LLM
        response = self.agent.run(user_prompt)
        
        # 解析 JSON 响应
        try:
            result = json.loads(response)
            # 添加阶段目标信息
            result["stage_goal"] = self.get_stage_goal(stage)
            return result
        except json.JSONDecodeError as e:
            # 如果解析失败，返回默认响应
            return {
                "question": f"请为这个句子增加一些细节：{current_sentence}",
                "hint": "尝试使用形容词或副词来修饰核心词",
                "example": "",
                "stage_goal": self.get_stage_goal(stage)
            }
    
    def get_stage_goal(self, stage: Literal["stage1", "stage2", "stage3"]) -> str:
        """
        获取指定阶段的目标描述
        
        Args:
            stage: 当前阶段
            
        Returns:
            str: 阶段目标描述
        """
        return STAGE_GOALS.get(stage, "")


# 创建全局实例（单例模式）
_interviewer_instance = None


def get_interviewer() -> InterviewerAgent:
    """
    获取全局 InterviewerAgent 实例（单例模式）
    
    Returns:
        InterviewerAgent: InterviewerAgent 实例
    """
    global _interviewer_instance
    if _interviewer_instance is None:
        _interviewer_instance = InterviewerAgent()
    return _interviewer_instance


def reset_interviewer():
    """重置 InterviewerAgent 实例（用于测试）"""
    global _interviewer_instance
    _interviewer_instance = None
