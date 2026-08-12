"""Agent基类"""

from abc import ABC, abstractmethod
from typing import Optional, Iterator
from .message import Message
from .llm import HelloAgentsLLM
from .config import Config
from .stream import StreamEvent
from .conversation_manager import ConversationManager


class Agent(ABC):
    """Agent基类"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        conversation_manager: Optional[ConversationManager] = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []
        self.conversation_manager = conversation_manager

    def _resolve_history(self, conversation_id: Optional[str] = None) -> list[Message]:
        if self.conversation_manager and conversation_id:
            conv = self.conversation_manager.get_conversation(conversation_id)
            if conv:
                return conv.messages
        return self._history

    def _save_conversation_messages(
        self, input_text: str, response: str, conversation_id: Optional[str] = None
    ) -> None:
        if self.conversation_manager and conversation_id:
            self.conversation_manager.add_message(conversation_id, input_text, "user")
            self.conversation_manager.add_message(
                conversation_id, response, "assistant"
            )
        else:
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response, "assistant"))

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        pass

    def stream_run(self, input_text: str, **kwargs) -> Iterator[StreamEvent]:
        result = self.run(input_text, **kwargs)
        yield StreamEvent.text(result)
        yield StreamEvent.done(result)

    def add_message(self, message: Message):
        self._history.append(message)

    def clear_history(self):
        self._history.clear()

    def get_history(self) -> list[Message]:
        return self._history.copy()

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"

    def __repr__(self) -> str:
        return self.__str__()
