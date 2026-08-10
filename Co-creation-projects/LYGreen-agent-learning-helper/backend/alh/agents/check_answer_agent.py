from alh.agents.agent import Agent
from alh.llm.llm_model import LLMModel
from pydantic import BaseModel

CHECK_ANSWER_AGENT_PROMPT = """
你是一个学习助手，你的任务是帮助用户进行学习辅导，根据问题和用户给出的答案，进行反馈。
若答案基本正确，则设置 can_pass 为 True，反之为 False；content 输出解析。
若答案不正确，则设置 can_pass 为 False；content 可以给出提示。
你需要根据下面的 Json Schema 来生成，可以插入 \\n 表示换行:
{json_schema}
你必须只能输出 Json 格式，用 ```json ```包裹，不要输出任何其他内容。

现在，请开始吧。

问题：
{question}

用户的答案：
{user_input}

"""

class FeedbackModel(BaseModel):
    content: str
    can_pass: bool

class CheckAnswerAgent(Agent):
    def __init__(self, llm_model: LLMModel):
        super().__init__(llm_model)
        self.prompt_temperate = CHECK_ANSWER_AGENT_PROMPT

    def _execute(self, data: dict = None):
        subject = data["subject"]
        question = data["question"]
        user_answer = data["user_answer"]

        max_steps = 10

        for step in range(max_steps):
            formatted_prompt = self.prompt_temperate.format(
                json_schema=FeedbackModel.model_json_schema(),
                question=f"学科：{subject}\n问题：{question}",
                user_input=user_answer
            )

            streamer = self.llm_model.stream_talk(formatted_prompt)

            response = ""

            for chunk in streamer:
                response += chunk

            try:
                json_str = self._extract_json_str(response)
                json = self._parse_json(json_str)
                return json
            except Exception as e:
                print("Error: " + str(e))
                continue
        
        return None

    def _extract_json_str(self, response: str):
        import re
        return re.search(r"```json(.*?)```", response, re.DOTALL).group(1)

    def _parse_json(self, json_str: str):
        import json
        return json.loads(json_str)