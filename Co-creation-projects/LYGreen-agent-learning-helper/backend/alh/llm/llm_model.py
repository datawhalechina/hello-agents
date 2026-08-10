from abc import ABC, abstractmethod

class LLMModel(ABC):
    
    def __init__(self, system_prompt: str = None) -> None:
        self.system_prompt = system_prompt
    
    @abstractmethod
    def talk(self, prompt: str) -> str:
        pass
    
    @abstractmethod
    def stream_talk(self, prompt: str):
        pass
