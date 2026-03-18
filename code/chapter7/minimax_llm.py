# minimax_llm.py
"""
MiniMax LLM Provider Extension for HelloAgents.

MiniMax provides high-performance cloud LLM models with 204K context window
via an OpenAI-compatible API endpoint.

Supported models:
  - MiniMax-M2.7        : Latest flagship model with enhanced reasoning and coding (default)
  - MiniMax-M2.7-highspeed : High-speed version of M2.7 for low-latency scenarios
  - MiniMax-M2.5        : Peak performance, ultimate value
  - MiniMax-M2.5-highspeed : Same performance, faster and more agile

API docs: https://platform.minimax.io/docs/api-reference/text-openai-api

Usage:
    from minimax_llm import MiniMaxLLM

    llm = MiniMaxLLM()  # reads MINIMAX_API_KEY from env
    response = llm.think([{"role": "user", "content": "Hello!"}])
"""
import os
from typing import Optional, List, Dict
from openai import OpenAI
from hello_agents import HelloAgentsLLM


# MiniMax available models
MINIMAX_MODELS = {
    "MiniMax-M2.7": "Latest flagship model with enhanced reasoning and coding.",
    "MiniMax-M2.7-highspeed": "High-speed version of M2.7 for low-latency scenarios.",
    "MiniMax-M2.5": "Peak Performance. Ultimate Value. Master the Complex.",
    "MiniMax-M2.5-highspeed": "Same performance, faster and more agile.",
}

# Default configuration
MINIMAX_DEFAULT_MODEL = "MiniMax-M2.7"
MINIMAX_DEFAULT_BASE_URL = "https://api.minimax.io/v1"
MINIMAX_CN_BASE_URL = "https://api.minimaxi.com/v1"  # China mainland endpoint


class MiniMaxLLM(HelloAgentsLLM):
    """
    MiniMax LLM provider for HelloAgents framework.

    Extends HelloAgentsLLM with MiniMax-specific configuration and
    temperature constraint handling (MiniMax requires temperature in (0.0, 1.0]).

    Example:
        # Using environment variables
        export MINIMAX_API_KEY=your-api-key
        llm = MiniMaxLLM()

        # Or pass parameters directly
        llm = MiniMaxLLM(api_key="your-key", model="MiniMax-M2.7-highspeed")
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "minimax",
        **kwargs
    ):
        print("Initializing MiniMax Provider")
        self.provider = "minimax"

        # Resolve MiniMax credentials (priority: args > MINIMAX env > generic LLM env)
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY") or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("MINIMAX_BASE_URL") or MINIMAX_DEFAULT_BASE_URL
        self.model = model or os.getenv("LLM_MODEL_ID") or MINIMAX_DEFAULT_MODEL
        self.timeout = kwargs.get("timeout", int(os.getenv("LLM_TIMEOUT", "60")))

        if not self.api_key:
            raise ValueError(
                "MiniMax API key not found. Please set the MINIMAX_API_KEY "
                "environment variable or pass api_key parameter."
            )

        # Create OpenAI-compatible client pointing to MiniMax endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def think(self, messages: List[Dict[str, str]], temperature: float = 1.0) -> str:
        """
        Call MiniMax LLM for inference with streaming response.

        Note: MiniMax requires temperature in (0.0, 1.0].
        A value of 0 is not accepted and will be clamped to 0.01.
        The default temperature is 1.0 (recommended by MiniMax).

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature in (0.0, 1.0]. Default: 1.0.

        Returns:
            The model's response text, or None on error.
        """
        # Clamp temperature to MiniMax's valid range (0.0, 1.0]
        if temperature <= 0:
            temperature = 0.01
        if temperature > 1.0:
            temperature = 1.0

        print(f"Calling {self.model} (MiniMax)...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )

            print("MiniMax response:")
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print()
            return "".join(collected_content)

        except Exception as e:
            print(f"MiniMax API error: {e}")
            return None

    @staticmethod
    def list_models() -> dict:
        """List available MiniMax models and their descriptions."""
        return MINIMAX_MODELS


# --- Usage Example ---
if __name__ == "__main__":
    try:
        llm = MiniMaxLLM()

        print(f"Available MiniMax models: {MiniMaxLLM.list_models()}")
        print()

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Please briefly introduce yourself."},
        ]

        print("--- Calling MiniMax LLM ---")
        response = llm.think(messages)
        if response:
            print(f"\n--- Full Response ---\n{response}")

    except ValueError as e:
        print(e)
