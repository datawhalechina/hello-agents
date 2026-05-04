"""
数据库Agent助手 - 测试脚本
用于测试各个组件的功能
"""
import os
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from react_agent import DatabaseAgent, DatabaseConfig
from tools import OracleQueryTool, SQLGeneratorTool

load_dotenv()


def test_database_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试1: 数据库连接")
    print("=" * 60)
    
    db_config = DatabaseConfig()
    
    if not db_config.validate():
        print("❌ 数据库配置不完整")
        return False
    
    print(f"配置信息: {db_config.get_connection_string()}")
    
    oracle_tool = OracleQueryTool(db_config)
    
    if oracle_tool.connect():
        print("✅ 数据库连接成功")
        schema_info = oracle_tool.get_schema_info()
        print("\n数据库表结构:")
        print(schema_info)
        oracle_tool.disconnect()
        return True
    else:
        print("❌ 数据库连接失败")
        return False


def test_sql_generation():
    """测试SQL生成功能"""
    print("\n" + "=" * 60)
    print("测试2: SQL生成")
    print("=" * 60)
    
    try:
        llm = HelloAgentsLLM()
        
        sql_generator = SQLGeneratorTool(llm)
        
        test_queries = [
            "查询所有员工信息",
            "查询工资大于5000的员工",
            "统计各部门的员工数量"
        ]
        
        for query in test_queries:
            print(f"\n自然语言: {query}")
            sql = sql_generator.generate_sql(query, "表 EMPLOYEES: ID (NUMBER), NAME (VARCHAR2), SALARY (NUMBER), DEPARTMENT (VARCHAR2)")
            print(f"生成的SQL: {sql}")
            
            is_valid, msg = sql_generator.validate_sql(sql)
            print(f"验证结果: {msg}")
        
        return True
    except Exception as e:
        print(f"❌ SQL生成测试失败: {e}")
        return False


def test_agent_query():
    """测试Agent查询功能"""
    print("\n" + "=" * 60)
    print("测试3: Agent查询")
    print("=" * 60)
    
    try:
        llm = HelloAgentsLLM()
        
        db_config = DatabaseConfig()
        
        if not db_config.validate():
            print("❌ 数据库配置不完整")
            return False
        
        agent = DatabaseAgent(
            name="TestAgent",
            llm=llm,
            db_config=db_config,
            max_steps=5
        )
        
        test_query = "查询所有员工的信息"
        print(f"\n测试查询: {test_query}")
        result = agent.run(test_query)
        print(f"\n查询结果:\n{result}")
        
        return True
    except Exception as e:
        print(f"❌ Agent查询测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("🧪 数据库Agent助手 - 测试套件")
    print("=" * 60)
    
    results = []
    
    results.append(("数据库连接", test_database_connection()))
    results.append(("SQL生成", test_sql_generation()))
    results.append(("Agent查询", test_agent_query()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")


if __name__ == "__main__":
    main()