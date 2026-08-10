from abc import ABC, abstractmethod
from alh.llm.llm_model import LLMModel

class Agent(ABC):

    def __init__(self, llm_model: LLMModel):
        self.llm_model = llm_model

    def run(self, data: dict = None):
        try:
            return self._execute(data)
        except Exception as e:
            raise e

    @abstractmethod
    def _execute(self, data: dict = None):
        pass
