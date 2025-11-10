# test_quick.py
from hello_agents import HelloAgentsLLM
from dotenv import load_dotenv
import os

load_dotenv()

llm = HelloAgentsLLM()
print("✅ HelloAgents 导入成功！")
print(f"✅ OpenAI API Key 已配置: {bool(os.getenv('OPENAI_API_KEY'))}")