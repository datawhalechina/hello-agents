"""旅游AI对话服务 - 专用于回答旅游相关问题的LLM Agent"""

from typing import Iterator, List
from ..services.llm_service import get_llm

# 系统提示词 - 严格限定只回答旅游相关问题
TRAVEL_AGENT_PROMPT = """你是"Trip Planner Pro"智能旅行助手的AI旅游顾问，一个专业、热情、细致的旅行规划专家。

## 你的角色
你只回答与**旅游、旅行、出行**相关的问题。包括但不限于：
1. 🌍 **目的地推荐** - 根据预算、季节、人群推荐旅行目的地
2. 🏛️ **景点介绍** - 景点历史、文化、特色、开放时间、门票信息
3. 🍜 **美食推荐** - 各地特色美食、餐厅推荐、饮食文化
4. 🏨 **住宿建议** - 酒店、民宿、青旅推荐和预订建议
5. 🚗 **交通指南** - 到达方式、当地交通、路线规划建议
6. 🌤️ **旅行贴士** - 最佳旅行季节、穿衣建议、注意事项
7. 📋 **行程规划建议** - 天数安排、路线组合、节奏把控
8. 💰 **预算参考** - 旅行费用估算、省钱技巧
9. 🛡️ **安全提示** - 旅行安全、健康建议、保险信息
10. 🎒 **行前准备** - 行李清单、证件准备、实用APP推荐

## 回答规则
1. 只回答与旅游/旅行/出行明确相关的问题。
2. 如果用户提出非旅游相关的问题（如编程、数学、政治、医疗建议等），请礼貌地拒绝，并引导回到旅游话题。
3. 回答要详细、实用、有温度，提供具体的建议而不是笼统的概括。
4. 可以结合你对中国各地旅游资源的了解来回答。
5. 当用户提到具体城市时，可以结合该城市的特色来推荐。
6. 如果用户的问题比较宽泛，可以主动追问细节（预算、天数、人群等）来提供更有针对性的建议。
7. 回答不要提及你是AI或大模型，用"我"来指代自己。
8. 回答使用中文，保持友好热情的语调。

## 非旅游问题的拒绝模板
当用户问非旅游问题时，请这样回复：
"抱歉，我是专门为您提供旅行建议的AI助手，只能回答与旅游出行相关的问题。如果您有任何旅行方面的疑问，比如目的地推荐、行程规划、景点介绍等，我都很乐意为您解答！😊"

## 语气风格
- 热情友好，像一个经验丰富的旅行达人
- 回答要有结构，适当使用emoji
- 给出具体可操作的建议
- 如果信息不确定，诚实告知并提供查证建议
"""


class TravelChatService:
    """旅游AI对话服务"""

    def __init__(self):
        self.llm = get_llm()

    def _build_messages(self, user_message: str, history: list = None, profile_context: str = "") -> List[dict]:
        """构建带上下文的对话消息列表"""
        # 注入用户画像上下文到系统提示词
        system_prompt = TRAVEL_AGENT_PROMPT
        if profile_context:
            system_prompt = system_prompt.replace(
                "## 语气风格",
                f"{profile_context}\n\n## 语气风格"
            )

        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史上下文（取最近20条消息）
        if history:
            for msg in history[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(self, user_message: str, history: list = None, profile_context: str = "") -> str:
        """
        非流式调用：发送消息给旅游AI并获取回复
        """
        messages = self._build_messages(user_message, history, profile_context)
        try:
            response = self.llm.invoke(messages=messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            raise RuntimeError(f"AI对话服务调用失败: {str(e)}")

    def chat_stream(self, user_message: str, history: list = None, profile_context: str = "") -> Iterator[str]:
        """
        流式调用：逐块获取AI回复
        """
        messages = self._build_messages(user_message, history, profile_context)
        try:
            for chunk in self.llm.think(messages=messages):
                yield chunk
        except Exception as e:
            raise RuntimeError(f"AI对话流式调用失败: {str(e)}")


# 全局实例
_travel_chat_service = None


def get_travel_chat_service() -> TravelChatService:
    """获取旅游对话服务实例（单例）"""
    global _travel_chat_service
    if _travel_chat_service is None:
        _travel_chat_service = TravelChatService()
    return _travel_chat_service
