"""Step 1: LLM 客户端 — 兼容 OpenAI 接口，支持流式响应"""
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()


class HelloAgentsLLM:
    def __init__(self, model: str = None, apiKey: str = None,
                 baseUrl: str = None, timeout: int = None):
        self.model = model or os.getenv("LLM_MODEL_ID")
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("请在 .env 中配置 LLM_MODEL_ID, LLM_API_KEY, LLM_BASE_URL")

        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        print(f"\n[{self.model}] 思考中...")
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=temperature, stream=True,
            )
            collected = []
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                # 过滤无效代理字符 (surrogates)
                clean = content.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")
                print(clean, end="", flush=True)
                collected.append(clean)
            print()
            result = "".join(collected)
            return result
        except Exception as e:
            print(f"[ERR] LLM 调用失败: {e}")
            # 尝试非流式重试
            try:
                print("  尝试非流式重试...")
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=temperature, stream=False,
                )
                content = response.choices[0].message.content or ""
                clean = content.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")
                print(clean)
                return clean
            except Exception as e2:
                print(f"[ERR] 非流式也失败: {e2}")
                raise RuntimeError(f"LLM调用完全失败: {e2}")
