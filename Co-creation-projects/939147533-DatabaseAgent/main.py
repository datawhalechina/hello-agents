"""
数据库Agent助手 - 主程序
演示如何使用DatabaseAgent进行自然语言查询
"""
import os
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from react_agent import DatabaseAgent, DatabaseConfig

load_dotenv()


def main():
    print("=" * 60)
    print("🤖 数据库Agent助手")
    print("=" * 60)
    
    llm = HelloAgentsLLM()
    
    db_config = DatabaseConfig()
    
    if not db_config.validate():
        print("❌ 数据库配置不完整，请检查.env文件")
        print("需要配置: DB_HOST, DB_PORT, DB_SERVICE_NAME, DB_USERNAME, DB_PASSWORD")
        return
    
    agent = DatabaseAgent(
        name="DatabaseAssistant",
        llm=llm,
        db_config=db_config,
        max_steps=5
    )
    
    print("\n📝 示例查询:")
    print("1. 查询所有员工信息")
    print("2. 查询工资大于5000的员工")
    print("3. 统计各部门的员工数量")
    print("4. 查询最近入职的5名员工")
    print("5. 退出")
    
    while True:
        print("\n" + "=" * 60)
        user_input = input("请输入您的查询 (或输入 '5' 退出): ").strip()
        
        if user_input.lower() in ['5', 'exit', 'quit', '退出']:
            print("👋 感谢使用数据库Agent助手！")
            break

        if not user_input:
            print("⚠️ 请输入有效的查询")
            continue
        
        try:
            result = agent.run(user_input)
            print("\n" + "=" * 60)
            print("📊 查询结果:")
            print("=" * 60)
            print(result)
        except Exception as e:
            print(f"❌ 执行查询时出错: {e}")


if __name__ == "__main__":
    main()