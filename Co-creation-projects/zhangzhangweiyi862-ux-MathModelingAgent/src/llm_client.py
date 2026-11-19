import os

from dotenv import load_dotenv
from openai import OpenAI


class LLMClient:
    """
    MathModelingAgent 的统一大语言模型客户端。
    """

    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL")
        self.model = os.getenv("LLM_MODEL_ID")

        if not self.api_key:
            raise ValueError("未检测到 LLM_API_KEY，请检查 .env 文件。")

        if not self.base_url:
            raise ValueError("未检测到 LLM_BASE_URL，请检查 .env 文件。")

        if not self.model:
            raise ValueError("未检测到 LLM_MODEL_ID，请检查 .env 文件。")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 1.0,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("LLM 返回内容为空。")

        return content.strip()


if __name__ == "__main__":
    llm = LLMClient()

    result = llm.chat(
        system_prompt="你是一名数学建模助手。",
        user_prompt="请用一句话解释什么是数学建模。",
    )

    print("=== LLM 连接测试 ===")
    print(result)