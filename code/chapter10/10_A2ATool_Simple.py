"""
10.3.4 在智能体中使用A2A工具
（1）  使用A2ATool包装器
"""

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# 假设已经有一个研究员Agent服务运行在 http://localhost:5000

# 创建协调者Agent
coordinator = SimpleAgent(name="协调者", llm=llm)

# 添加A2A工具，连接到研究员Agent
researcher_tool = A2ATool(agent_url="http://localhost:5000")
coordinator.add_tool(researcher_tool)

# 协调者可以调用研究员Agent
# 使用 action="ask" 向 Agent 提问
response = coordinator.run("使用a2a工具，向Agent提问：请研究AI在教育领域的应用")
print(response)

