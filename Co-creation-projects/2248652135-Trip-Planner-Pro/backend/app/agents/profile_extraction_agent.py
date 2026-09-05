"""用户画像提取子Agent

将用户画像提取逻辑封装为独立的 SimpleAgent 子类，使其成为多智能体系统中的
一个专门子代理，而不是在服务层直接调用 LLM。
"""

from hello_agents import SimpleAgent, HelloAgentsLLM

# ============ Agent 系统提示词 ============

SYSTEM_PROMPT = """你是一个用户偏好分析专家。你的任务是根据用户的对话消息，提取该用户的旅行偏好。

## 核心规则
1. 只从「用户消息」中提取用户**自己表达**的偏好，不要提取AI助手的建议或推荐
2. 如果用户消息需要结合对话历史才能理解（如"好的"、"这个不错"、"是的"），参考上下文来推断用户偏好
3. 不要提取一次性信息（如"明天去故宫"），只提取稳定的偏好特征（如"喜欢历史文化景点"）
4. 每条控制在20字以内，总条目不超过8条
5. 宁缺毋滥，只输出有明显依据的偏好

## 冲突处理（重要）
将新提取的偏好与「已有画像」逐条对比：
- **冲突**：如果新消息表达的偏好与某条旧画像矛盾（如"喜欢安静" vs "喜欢热闹"），删除旧条目，用新条目替代
- **一致**：如果新消息与旧画像一致，保留旧画像条目（不重复添加）
- **新增**：如果新消息表达了旧画像中没有的偏好，作为新条目添加
- **无关**：如果用户消息不包含偏好信息，跳过本轮提取

## 输出格式
只输出更新后的完整画像，每行一条，以"- "开头，不要输出任何其他内容：

- 偏好1
- 偏好2
"""


class ProfileExtractionAgent(SimpleAgent):
    """用户画像提取子Agent

    专门从用户对话消息中提取旅行偏好，与已有画像合并更新。
    不需要工具调用，纯 LLM 文本分析任务。
    """

    def __init__(self, llm: HelloAgentsLLM):
        """
        初始化画像提取 Agent

        Args:
            llm: LLM 实例
        """
        super().__init__(
            name="用户画像提取专家",
            llm=llm,
            system_prompt=SYSTEM_PROMPT,
            enable_tool_calling=False,  # 纯文本分析，无需工具
        )

    def extract(
        self,
        existing_profile: str,
        conversation_context: str,
        user_message: str,
    ) -> str:
        """
        从用户消息中提取偏好，与已有画像对比合并

        Args:
            existing_profile: 已有画像文本（"- "开头的条目），无则传空字符串
            conversation_context: 对话上下文文本（含历史会话摘要+当前会话最近消息）
            user_message: 最新用户消息

        Returns:
            更新后的完整画像文本（"- "开头的行），若无可提取内容则返回空字符串
        """
        input_text = (
            f"已有画像：\n{existing_profile or '（无）'}\n\n"
            f"对话历史（用于理解上下文）：\n{conversation_context or '（无）'}\n\n"
            f"最新用户消息：{user_message}\n\n"
            f"请输出更新后的完整画像："
        )

        result = self.run(input_text)
        return result.strip()
