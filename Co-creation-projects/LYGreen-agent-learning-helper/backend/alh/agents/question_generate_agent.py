from alh.agents.agent import Agent
from alh.llm.llm_model import LLMModel
from pydantic import BaseModel

QUESTION_GENERATE_AGENT_PROMPT = """
你是一个问题生成器，你的任务是根据用户的学习内容生成一个问题。
你需要根据下面的 Json Sehcma 来生成（可以用 \\n 表示换行）:
{json_schema}
你必须只能输出 Json 格式，用 ```json ```包裹，不要输出任何其他内容。

现在，请开始吧。

用户：
{user_input}

"""

class QuestionWritingModel(BaseModel):
    question: str

class QuestionGenerateAgent(Agent):
    def __init__(self, llm_model: LLMModel):
        super().__init__(llm_model)
        self.prompt_temperate = QUESTION_GENERATE_AGENT_PROMPT

    def _execute(self, data: dict = None):
        subject = data["subject"]
        title = data["title"]
        description = data["description"]
        content = data["content"]

        max_steps = 10

        for step in range(max_steps):
            formatted_prompt = self.prompt_temperate.format(
                json_schema=QuestionWritingModel.model_json_schema(),
                user_input=f"学科：{subject}\n标题：{title}\n描述：{description}\n内容：{content}\n"
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