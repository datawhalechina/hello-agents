from typing import Dict, List

from dotenv import load_dotenv
import os
from pathlib import Path

from openai import OpenAI

# 明确指向脚本所在目录下的 .env，避免工作目录不同导致加载失败
load_dotenv(Path(__file__).parent / ".env")

class HelloAgentsLLM:
    def __init__(self,model:str = None , apiKey: str = None, baseUrl: str = None, timeout: int = None):
        self.model = model or os.getenv("LLM_MODEL_ID")
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))
        
        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)
    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        print(f"🧠 正在调用 {self.model} 模型...")
        try:
            response = self.client.chat.completions.create(model = self.model ,
                                                messages = messages,
                                                temperature = temperature,
                                                stream = True)
            # 处理流式响应
            print("✅ 大语言模型响应成功:")
            collected_content = []
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print()  # 在流式输出结束后换行
            return "".join(collected_content)
        # print("✅ 大语言模型响应成功:")
        #     return response.choices[0].message.content
    
    
        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            return None

if __name__ == '__main__':
    try:
        llmClient = HelloAgentsLLM()
        exmaple_message = [
            {"role" : "system","content" : "You are a helpful assistant that writes Python code."},
            {"role" : "user" , "content" : "帮我写一个快速排序"}
        ]
        print("--- 调用LLM ---")
        responseText = llmClient.think(exmaple_message)
        if responseText:
            print("\n\n--- 完整模型响应 ---")
            print(responseText)
    except Exception as e:
        print(e)        
