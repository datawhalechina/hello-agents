"""
10.3.4 在智能体中使用A2A工具
（2）实战案例：智能客服系统
"""

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from hello_agents.protocols import A2AServer
import threading
import time
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# 1. 创建技术专家Agent服务
tech_expert = A2AServer(name="tech_expert", description="技术专家，回答技术问题")


@tech_expert.skill("answer")
def answer_tech_question(text: str) -> str:
    import re

    match = re.search(r"answer\s+(.+)", text, re.IGNORECASE)
    question = match.group(1).strip() if match else text
    # 实际应用中，这里会调用LLM或知识库
    return f"技术回答：关于'{question}'，我建议您查看我们的技术文档..."


# 2. 创建销售顾问Agent服务
sales_advisor = A2AServer(name="sales_advisor", description="销售顾问，回答销售问题")


@sales_advisor.skill("answer")
def answer_sales_question(text: str) -> str:
    import re

    match = re.search(r"answer\s+(.+)", text, re.IGNORECASE)
    question = match.group(1).strip() if match else text
    return f"销售回答：关于'{question}'，我们有特别优惠..."


# 3. 启动服务
threading.Thread(target=lambda: tech_expert.run(port=6000), daemon=True).start()
threading.Thread(target=lambda: sales_advisor.run(port=6001), daemon=True).start()
time.sleep(2)

# 4. 创建接待员Agent（使用HelloAgents的SimpleAgent）
receptionist = SimpleAgent(
    name="接待员",
    llm=llm,
    system_prompt="""你是客服接待员，负责：
1. 分析客户问题类型（技术问题 or 销售问题）
2. 将问题转发给相应的专家
3. 整理专家的回答并返回给客户

请保持礼貌和专业。""",
)

# 添加技术专家工具
tech_tool = A2ATool(
    agent_url="http://localhost:6000",
    name="tech_expert",
    description="技术专家，回答技术相关问题",
)
receptionist.add_tool(tech_tool)

# 添加销售顾问工具
sales_tool = A2ATool(
    agent_url="http://localhost:6001",
    name="sales_advisor",
    description="销售顾问，回答价格、购买相关问题",
)
receptionist.add_tool(sales_tool)


# 5. 处理客户咨询
def handle_customer_query(query):
    print(f"\n客户咨询：{query}")
    print("=" * 50)
    response = receptionist.run(query)
    print(f"\n客服回复：{response}")
    print("=" * 50)


# 测试不同类型的问题
if __name__ == "__main__":
    handle_customer_query("你们的API如何调用？")
    handle_customer_query("企业版的价格是多少？")
    handle_customer_query("如何集成到我的Python项目中？")
