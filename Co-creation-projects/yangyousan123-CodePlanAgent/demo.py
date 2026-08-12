"""CodePlanAgent 使用示例"""

import os
from dotenv import load_dotenv
from hello_agents.core.llm import HelloAgentsLLM
from code_plan_agent import CodePlanAgent, create_code_plan_agent


def load_env():
    """加载环境变量"""
    load_dotenv()
    
    # 检查必要的环境变量
    required_vars = ["LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
        print("请在 .env 文件中配置这些变量")
        return False
    
    return True


def main():
    """主函数 - 演示CodePlanAgent的使用"""
    print("🚀 CodePlanAgent 演示程序")
    print("=" * 60)
    
    # 加载环境变量
    if not load_env():
        return
    
    # 初始化LLM
    print("\n🔧 初始化LLM客户端...")
    llm = HelloAgentsLLM(
        model=os.getenv("LLM_MODEL_ID"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0.2,  # 较低温度，生成更确定性的计划
        max_tokens=4096
    )
    
    print(f"✅ LLM客户端已初始化: {llm.model}")
    
    # 创建CodePlanAgent
    print("\n🧠 创建CodePlanAgent...")
    agent = create_code_plan_agent(llm)
    print(f"✅ CodePlanAgent创建成功: {agent.name}")
    
    # 示例需求1：创建待办事项应用
    print("\n" + "=" * 60)
    print("📝 示例1: 创建待办事项应用")
    print("=" * 60)
    
    requirements1 = """创建一个简单的待办事项(Todo)应用，使用Python和Flask框架实现：

功能需求：
1. 添加待办事项（标题、描述、截止日期）
2. 删除待办事项
3. 标记待办事项为已完成/未完成
4. 按状态筛选待办事项（全部/已完成/未完成）
5. 数据持久化存储（使用SQLite）

技术要求：
- 使用Flask框架
- 使用SQLAlchemy ORM
- 提供RESTful API接口
- 支持JSON格式数据
- 包含基本的错误处理"""
    
    # 生成代码计划
    plan1 = agent.run(requirements1)
    
    # 保存结果到文件
    with open("./outputs/todo_app_plan.md", "w", encoding="utf-8") as f:
        f.write(plan1)
    print("\n📄 代码计划已保存到: ./outputs/todo_app_plan.md")
    
    # # 示例需求2：创建用户认证系统
    # print("\n" + "=" * 60)
    # print("🔐 示例2: 创建用户认证系统")
    # print("=" * 60)
    
#     requirements2 = """创建一个用户认证系统，包含以下功能：

# 核心功能：
# 1. 用户注册（用户名、邮箱、密码）
# 2. 用户登录（邮箱/用户名 + 密码）
# 3. 密码重置（通过邮箱）
# 4. JWT token认证
# 5. 权限管理（角色：普通用户、管理员）

# 技术要求：
# - 使用Python FastAPI框架
# - 使用PostgreSQL数据库
# - 密码加密存储（bcrypt）
# - JWT token过期处理
# - 实现API安全措施（限流、CSRF防护）"""
    
#     # 生成代码计划
#     plan2 = agent.run(requirements2)
    
#     # 保存结果到文件
#     with open("./outputs/auth_system_plan.md", "w", encoding="utf-8") as f:
#         f.write(plan2)
#     print("\n📄 代码计划已保存到: ./outputs/auth_system_plan.md")
    
    print("\n🎉 演示完成！")
    # print("=" * 60)
    # print("已生成的代码计划文件:")
    # print("- ./outputs/todo_app_plan.md")
    # print("- ./outputs/auth_system_plan.md")


if __name__ == "__main__":
    main()
    