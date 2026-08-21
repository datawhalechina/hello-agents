# -*- coding: utf-8 -*-
"""三国狼人杀中文提示词"""

class ChinesePrompts:
    """中文提示词管理类"""
    
    @staticmethod
    def get_role_prompt(role: str, character: str) -> str:
        """获取角色提示词"""
        base_prompt = f"""你是{character}，在这场三国狼人杀游戏中扮演{role}。

请严格按照以下JSON格式回复，不要添加任何其他文字：
{{
    "reach_agreement": true/false,
    "confidence_level": 1-10的数字,
    "key_evidence": "你的证据或观点"
}}

角色特点：
"""
        
        if role == "狼人":
            return base_prompt + f"""
- 你是狼人阵营，目标是消灭所有好人
- 夜晚可以与其他狼人协商击杀目标，可以选择任何存活玩家（包括自己或队友）
- 白天要隐藏身份，误导好人
- 以{character}的性格说话和行动
"""
        elif role == "预言家":
            return base_prompt + f"""
- 你是好人阵营的预言家，目标是找出所有狼人
- 每晚可以查验一名玩家的真实身份
- 要合理公布查验结果，引导好人投票
- 以{character}的智慧和洞察力分析局势
"""
        elif role == "女巫":
            return base_prompt + f"""
- 你是好人阵营的女巫，拥有解药和毒药各一瓶
- 解药可以救活被狼人击杀的玩家
- 毒药可以毒杀一名玩家
- 要谨慎使用道具，在关键时刻发挥作用
"""
        elif role == "猎人":
            return base_prompt + f"""
- 你是好人阵营的猎人
- 被投票出局时可以开枪带走一名玩家
- 要在关键时刻使用技能，带走狼人
- 以{character}的勇猛和决断力行动
"""
        else:  # 村民
            return base_prompt + f"""
- 你是好人阵营的村民
- 没有特殊技能，只能通过推理和投票
- 要仔细观察，找出狼人的破绽
- 以{character}的性格参与讨论
"""
