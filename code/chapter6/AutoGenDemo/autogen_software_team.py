"""
AutoGen 软件开发团队协作案例
"""

import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 先测试一个版本，使用 OpenAI 客户端
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console

def create_openai_model_client():
    """创建 OpenAI 模型客户端用于测试"""
    return OpenAIChatCompletionClient(
        model=os.getenv("LLM_MODEL_ID", "gpt-4o"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    )

def create_product_manager(model_client):
    """创建产品经理智能体"""
    system_message = """你是一位经验丰富的产品经理，专门负责软件产品的需求分析和项目规划。

你的核心职责包括：
1. **需求分析**：深入理解用户需求，识别核心功能和边界条件
2. **技术规划**：基于需求制定清晰的技术实现路径
3. **风险评估**：识别潜在的技术风险和用户体验问题
4. **协调沟通**：与工程师和其他团队成员进行有效沟通

当接到开发任务时，请按以下结构进行分析：
1. 需求理解与分析
2. 功能模块划分
3. 技术选型建议
4. 实现优先级排序
5. 验收标准定义

请简洁明了地回应，并在分析完成后说"请工程师开始实现"。"""

    return AssistantAgent(
        name="ProductManager",
        model_client=model_client,
        system_message=system_message,
    )

def create_engineer(model_client):
    """创建软件工程师智能体"""
    system_message = """你是一位资深的软件工程师，擅长 Python 开发和 Web 应用构建。

你的技术专长包括：
1. **Python 编程**：熟练掌握 Python 语法和最佳实践
2. **Web 开发**：精通 Streamlit、Flask、Django 等框架
3. **API 集成**：有丰富的第三方 API 集成经验
4. **错误处理**：注重代码的健壮性和异常处理

当收到开发任务时，请：
1. 仔细分析技术需求
2. 选择合适的技术方案
3. 编写完整的代码实现
4. 添加必要的注释和说明
5. 考虑边界情况和异常处理

请提供完整的可运行代码，并在完成后说"请代码审查员检查"。"""

    return AssistantAgent(
        name="Engineer",
        model_client=model_client,
        system_message=system_message,
    )

def create_code_reviewer(model_client):
    """创建代码审查员智能体"""
    system_message = """你是一位经验丰富的代码审查专家，专注于代码质量和最佳实践。

你的审查重点包括：
1. **代码质量**：检查代码的可读性、可维护性和性能
2. **安全性**：识别潜在的安全漏洞和风险点
3. **最佳实践**：确保代码遵循行业标准和最佳实践
4. **错误处理**：验证异常处理的完整性和合理性

审查流程：
1. 仔细阅读和理解代码逻辑
2. 检查代码规范和最佳实践
3. 识别潜在问题和改进点
4. 提供具体的修改建议
5. 评估代码的整体质量

请提供具体的审查意见，完成后说"代码审查完成，请用户代理测试"。"""

    return AssistantAgent(
        name="CodeReviewer",
        model_client=model_client,
        system_message=system_message,
    )

def create_user_proxy():
    """创建用户代理智能体"""
    return UserProxyAgent(
        name="UserProxy",
        description="""用户代理，负责以下职责：
1. 代表用户提出开发需求
2. 在代码审查完成后执行测试验证
3. 验证功能是否符合原始需求
4. 对工程师提供的代码进行实际验证和测试

你刚刚收到的代码是工程师为黄金价格显示应用开发的完整实现，包含：
- 完整的app.py文件代码
- Streamlit应用的所有功能
- 数据获取、UI展示、错误处理等完整模块

测试验证步骤：
1. **代码语法检查**：分析代码是否有语法错误或导入问题
2. **核心功能验证**：检查以下功能是否实现：
   - 实时黄金价格显示（美元/盎司）
   - 24小时价格趋势图表
   - 手动刷新按钮功能
   - 错误处理和加载状态
3. **用户体验评估**：评估界面是否简洁美观、用户友好
4. **运行环境检查**：确认代码依赖（streamlit, requests, pandas, altair等）是否合理
5. **安全性检查**：确认API密钥通过环境变量注入，前端不可见

请基于工程师提供的完整代码进行上述测试验证，然后提供具体的测试结果反馈，包括：
- 哪些功能已经正确实现
- 是否存在任何问题或改进建议
- 代码的整体质量评估

完成测试验证后，请总结测试结果并回复 TERMINATE。""",
    )

async def run_software_development_team():
    """运行软件开发团队协作"""
    
    print("🔧 正在初始化模型客户端...")
    
    # 先使用标准的 OpenAI 客户端测试
    model_client = create_openai_model_client()
    
    print("👥 正在创建智能体团队...")
    
    # 创建智能体团队
    product_manager = create_product_manager(model_client)
    engineer = create_engineer(model_client)
    code_reviewer = create_code_reviewer(model_client)
    user_proxy = create_user_proxy()
    
    # 添加终止条件
    termination = TextMentionTermination("TERMINATE")
    
    # 创建团队聊天
    team_chat = RoundRobinGroupChat(
        participants=[
            product_manager,
            engineer, 
            code_reviewer,
            user_proxy
        ],
        termination_condition=termination,
        max_turns=20,  # 增加最大轮次
    )
    
    # 定义开发任务
    task = """我们需要开发一个黄金价格显示应用，具体要求如下：

核心功能：
- 实时显示黄金当前价格（美元/盎司）
- 显示24小时价格变化趋势（涨跌幅和涨跌额）
- 提供价格刷新功能

技术要求：
- 使用 Streamlit 框架创建 Web 应用
- 界面简洁美观，用户友好
- 添加适当的错误处理和加载状态

请团队协作完成这个任务，从需求分析到最终实现。"""
    
    # 执行团队协作
    print("🚀 启动 AutoGen 软件开发团队协作...")
    print("=" * 60)
    
    # 使用 Console 来显示对话过程
    result = await Console(team_chat.run_stream(task=task))
    
    print("\n" + "=" * 60)
    print("✅ 团队协作完成！")
    
    return result

# 主程序入口
if __name__ == "__main__":
    try:
        # 运行异步协作流程
        result = asyncio.run(run_software_development_team())
        
        print(f"\n📋 协作结果摘要：")
        print(f"- 参与智能体数量：4个")
        print(f"- 任务完成状态：{'成功' if result else '需要进一步处理'}")
        
    except ValueError as e:
        print(f"❌ 配置错误：{e}")
        print("请检查 .env 文件中的配置是否正确")
    except Exception as e:
        print(f"❌ 运行错误：{e}")
        import traceback
        traceback.print_exc()
