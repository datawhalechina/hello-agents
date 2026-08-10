from alh.agents.agent import Agent
from alh.llm.llm_model import LLMModel
from dataclasses import dataclass
from typing import List
from pydantic import BaseModel

SCHEDULE_GENERATE_AGENT_PROMPT = """
你是一个课程生成器，你的任务是根据用户的输入设计一个课程，尽量多并具体。
你需要根据下面的 Json Schema 生成一个课程（可以用 \\n 表示换行）:
{json_schema}
你必须只能输出 Json 格式，用 ```json ```包裹，不要输出任何其他内容。

现在，请开始吧。

用户输入:
{user_input}

"""

@dataclass
class Step:
    title: str
    description: str
    content: str

class ScheduleGenerateModel(BaseModel):
    steps: List[Step]

class ScheduleGenerateAgent(Agent):
    def __init__(self, llm_model: LLMModel):
        super().__init__(llm_model)
        self.prompt_template = SCHEDULE_GENERATE_AGENT_PROMPT

    def _execute(self, data: dict = None):
        subject = data["subject"]

        max_steps = 10

        # 减少出错
        for step in range(max_steps):
            formatted_prompt = self.prompt_template.format(
                json_schema=ScheduleGenerateModel.model_json_schema(),
                user_input=f"生成一个 {subject} 的学习计划"
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
