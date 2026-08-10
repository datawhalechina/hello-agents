import os
from dotenv import load_dotenv
from alh.llm.openai_model import OpenAIModel
from alh.agents.schedule_generate_agent import ScheduleGenerateAgent
from alh.agents.question_generate_agent import QuestionGenerateAgent
from alh.agents.check_answer_agent import CheckAnswerAgent

load_dotenv()

MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class Command:
    def __init__(self):
        raise RuntimeError("Command is an abstract class")
    
    def _init_command(self):
        self.model = OpenAIModel(BASE_URL, OPENAI_API_KEY, MODEL)
        self.schedule_generate_agent = ScheduleGenerateAgent(self.model)
        self.question_generate_agent = QuestionGenerateAgent(self.model)
        self.check_answer_agent = CheckAnswerAgent(self.model)

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
            cls._init_command(cls)
        return cls.instance
    
    def run(self, command: str, data: dict):
        if command == "/generate":
            subject = data["subject"]
            return self.schedule_generate_agent.run({ "subject": subject })
        elif command == "/generate_question":
            subject = data["subject"]
            title = data["title"]
            description = data["description"]
            content = data["content"]
            return self.question_generate_agent.run({ "subject": subject, "title": title, "description": description, "content": content })
        elif command == "/check_answer":
            subject = data["subject"]
            question = data["question"]
            user_answer = data["user_answer"]
            return self.check_answer_agent.run({ "subject": subject, "question": question, "user_answer": user_answer })
        else:
            pass