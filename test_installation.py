#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hello-Agents 安装验证脚本
用于测试环境配置是否正确
"""

import sys
import os

def check_python_version():
    """检查 Python 版本"""
    print("=" * 60)
    print("1. 检查 Python 版本")
    print("=" * 60)
    version = sys.version_info
    print(f"当前 Python 版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("✅ Python 版本符合要求 (>=3.10)")
        return True
    else:
        print("❌ Python 版本过低，请升级到 3.10 或更高版本")
        return False

def check_core_packages():
    """检查核心包是否安装"""
    print("\n" + "=" * 60)
    print("2. 检查核心包安装情况")
    print("=" * 60)
    
    packages = {
        'hello_agents': 'HelloAgents 框架',
        'openai': 'OpenAI SDK',
        'requests': 'HTTP 请求库',
        'dotenv': '环境变量管理',
    }
    
    all_installed = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"✅ {description} ({package})")
        except ImportError:
            print(f"❌ {description} ({package}) - 未安装")
            all_installed = False
    
    return all_installed

def check_optional_packages():
    """检查可选包"""
    print("\n" + "=" * 60)
    print("3. 检查可选包")
    print("=" * 60)
    
    optional_packages = {
        'pandas': '数据处理',
        'numpy': '科学计算',
        'fastapi': 'Web 框架',
        'torch': '深度学习',
        'jupyter': 'Jupyter Notebook',
        'tavily': '搜索工具',
    }
    
    for package, description in optional_packages.items():
        try:
            __import__(package)
            print(f"✅ {description} ({package})")
        except ImportError:
            print(f"⚠️  {description} ({package}) - 未安装（可选）")

def check_env_file():
    """检查环境变量文件"""
    print("\n" + "=" * 60)
    print("4. 检查环境变量配置")
    print("=" * 60)
    
    if os.path.exists('.env'):
        print("✅ .env 文件存在")
        
        # 检查关键的环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL']
        all_set = True
        
        for var in required_vars:
            value = os.getenv(var)
            if value and not value.startswith('your_'):
                print(f"✅ {var}: 已配置")
            else:
                print(f"⚠️  {var}: 未配置或使用默认值")
                all_set = False
        
        return all_set
    else:
        print("❌ .env 文件不存在")
        print("   请复制 .env.example 为 .env 并配置 API 密钥")
        return False

def test_hello_agents():
    """测试 HelloAgents 导入"""
    print("\n" + "=" * 60)
    print("5. 测试 HelloAgents 框架")
    print("=" * 60)
    
    try:
        from hello_agents import HelloAgentsLLM, SimpleAgent
        from hello_agents.tools import ToolRegistry
        print("✅ HelloAgents 核心模块导入成功")
        
        # 尝试创建实例（不调用 API）
        print("✅ HelloAgentsLLM 类可用")
        print("✅ SimpleAgent 类可用")
        print("✅ ToolRegistry 类可用")
        
        return True
    except Exception as e:
        print(f"❌ HelloAgents 测试失败: {e}")
        return False

def test_llm_connection():
    """测试 LLM 连接（可选）"""
    print("\n" + "=" * 60)
    print("6. 测试 LLM API 连接（可选）")
    print("=" * 60)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key.startswith('your_'):
            print("⚠️  OPENAI_API_KEY 未配置，跳过 API 测试")
            return False
        
        from hello_agents import HelloAgentsLLM
        llm = HelloAgentsLLM()
        
        print("正在测试 LLM 连接...")
        response = llm.invoke([{"role": "user", "content": "你好，请回复'测试成功'"}])
        
        if response:
            print(f"✅ LLM API 连接成功！")
            print(f"   响应: {response[:100]}...")
            return True
        else:
            print("❌ LLM 返回空响应")
            return False
            
    except Exception as e:
        print(f"⚠️  LLM API 测试失败: {e}")
        print("   这可能是由于 API 密钥配置错误或网络问题")
        return False

def print_summary(results):
    """打印总结"""
    print("\n" + "=" * 60)
    print("安装验证总结")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 恭喜！所有检查都通过了！")
        print("现在您可以开始学习 Hello-Agents 了！")
    else:
        print("⚠️  部分检查未通过")
        print("请参考上述提示修复问题，或查看 INSTALLATION_GUIDE.md")
    print("=" * 60)

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Hello-Agents 安装验证工具")
    print("=" * 60)
    print("此脚本将检查您的环境配置是否正确\n")
    
    results = {}
    
    # 必需检查
    results['Python 版本'] = check_python_version()
    results['核心包安装'] = check_core_packages()
    
    # 可选检查
    check_optional_packages()
    results['环境变量配置'] = check_env_file()
    results['HelloAgents 框架'] = test_hello_agents()
    
    # API 测试（可选，需要配置）
    api_test = test_llm_connection()
    if api_test:
        results['LLM API 连接'] = api_test
    
    # 打印总结
    print_summary(results)
    
    # 返回退出码
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()

