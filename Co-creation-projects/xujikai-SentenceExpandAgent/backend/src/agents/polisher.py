"""
PolisherAgent - 满分润色 Agent
接收三轮扩写记录，生成润色后的满分句子
"""
import json
from typing import Dict, Any
from hello_agents.agents.tool_aware_agent import ToolAwareSimpleAgent
from .prompts import (
    POLISHER_SYSTEM_PROMPT,
    POLISHER_USER_PROMPT
)
from config import get_llm, tool_listener


class PolisherAgent:
    """满分润色 Agent - 生成根据三轮扩写记录生成润色后的满分句子"""
    
    def __init__(self):
        """初始化 PolisherAgent"""
        self.llm = get_llm()
        self.agent = ToolAwareSimpleAgent(
            name="Polisher",
            system_prompt=POLISHER_SYSTEM_PROMPT,
            llm=self.llm,
            tool_call_listener=tool_listener
        )
    
    def polish(self, seed_sentence: str, rounds_detail: str) -> Dict[str, Any]:
        """
        根据三轮扩写记录生成润色后的满分句子
        
        Args:
            seed_sentence: 种子句（原始句子）
            rounds_detail: 历史轮次详情（包含三个阶段的完整信息）
            
        Returns:
            Dict[str, Any]: 润色结果，包含：
                - polished_sentence: 最终润色后的英文句子
                - structure_analysis: 语法结构分析（列表）
                - highlight: 最亮眼的结构特点
        """
        # 构建用户提示词
        user_prompt = POLISHER_USER_PROMPT.format(
            seed_sentence=seed_sentence,
            rounds_detail=rounds_detail
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
                "polished_sentence": seed_sentence,
                "structure_analysis": [
                    "润色失败，使用原始句子"
                ],
                "highlight": "无法生成润色版本"
            }
    
    def format_rounds_detail(self, rounds: list) -> str:
        """
        格式化轮次记录为字符串，供 Polisher 使用
        
        Args:
            rounds: 轮次记录列表（RoundRecord 对象列表）
            
        Returns:
            str: 格式化后的轮次详情字符串
        """
        if not rounds:
            return "暂无扩写记录"
        
        detail_parts = []
        for i, round_record in enumerate(rounds, 1):
            # 提取阶段编号
            stage_num = round_record.stage.replace("stage", "")
            
            # 格式化单个轮次
            round_detail = f"""【阶段{stage_num}】
- 记者提问：{round_record.question}
- 学生提交：{round_record.user_answer}
- 语法点评：{round_record.evaluation}
- 本阶段扩写结果：{round_record.expanded_sentence}"""
            
            detail_parts.append(round_detail)
        
        return "\n\n".join(detail_parts)


# 创建全局实例（单例模式）
_polisher_instance = None


def get_polisher() -> PolisherAgent:
    """
    获取全局 PolisherAgent 实例（单例模式）
    
    Returns:
        PolisherAgent: PolisherAgent 实例
    """
    global _polisher_instance
    if _polisher_instance is None:
        _polisher_instance = PolisherAgent()
    return _polisher_instance


def reset_polisher():
    """重置 PolisherAgent 实例（用于测试）"""
    global _polisher_instance
    _polisher_instance = None
