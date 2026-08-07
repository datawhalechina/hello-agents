import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()


class HelloAgentsLLM:
    """OpenAI-compatible LLM client (works with AIHubmix, ModelScope, OpenAI)."""

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        timeout: int = None,
        verbose: bool = True,
    ):
        self.model = model or os.getenv("LLM_MODEL_ID")
        api_key = api_key or os.getenv("LLM_API_KEY")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))
        self.verbose = verbose

        if not all([self.model, api_key, base_url]):
            raise ValueError(
                "LLM_MODEL_ID, LLM_API_KEY, and LLM_BASE_URL must be set "
                "(via constructor args or .env file)."
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        if self.verbose:
            print(f"🧠 Calling {self.model}...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            collected = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                if self.verbose:
                    print(content, end="", flush=True)
                collected.append(content)
            if self.verbose:
                print()
            return "".join(collected)
        except Exception as e:
            print(f"❌ LLM API error: {e}")
            return ""
