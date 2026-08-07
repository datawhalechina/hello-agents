from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from src.agents.conversation import SpeakTeacherAgent

#加载环境变量
load_dotenv()
llm = HelloAgentsLLM()

# 传入参数为 语言、难度、偏好
# 难度可选：入门、初级、中级、高级
# 偏好可选：科技、日常等
talkagent = SpeakTeacherAgent(llm,"英语","中级","科技")
result = talkagent.letstalk()

