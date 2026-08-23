"""
MathModelAgent 项目测试脚本

测试项目的基本功能
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def test_imports():
    """测试所有必要的库导入"""
    print("=" * 50)
    print("测试1: 库导入测试")
    print("=" * 50)
    
    try:
        # HelloAgents
        from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
        print("✓ HelloAgents 导入成功")
        
        # LangChain
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        print("✓ LangChain 导入成功")
        
        # 数据分析
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        import seaborn as sns
        print("✓ 数据分析库 导入成功")
        
        # 联网搜索
        import requests
        from bs4 import BeautifulSoup
        print("✓ 联网搜索库 导入成功")
        
        # LaTeX生成
        from jinja2 import Template
        print("✓ LaTeX生成库 导入成功")
        
        print("\n所有库导入测试通过！")
        return True
        
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_knowledge_base():
    """测试RAG知识库功能"""
    print("\n" + "=" * 50)
    print("测试2: RAG知识库测试")
    print("=" * 50)
    
    try:
        # 检查知识库目录
        knowledge_dir = project_dir / "knowledge"
        if not knowledge_dir.exists():
            print("✗ 知识库目录不存在")
            return False
        
        # 检查示例知识文档
        example_file = knowledge_dir / "example_knowledge.md"
        if not example_file.exists():
            print("✗ 示例知识文档不存在")
            return False
        
        # 读取示例知识文档
        with open(example_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if len(content) > 0:
            print("✓ 知识库目录存在")
            print("✓ 示例知识文档存在")
            print(f"✓ 知识文档内容长度: {len(content)} 字符")
            return True
        else:
            print("✗ 知识文档内容为空")
            return False
            
    except Exception as e:
        print(f"✗ 知识库测试失败: {e}")
        return False

def test_data_files():
    """测试数据文件"""
    print("\n" + "=" * 50)
    print("测试3: 数据文件测试")
    print("=" * 50)
    
    try:
        # 检查数据目录
        data_dir = project_dir / "data"
        if not data_dir.exists():
            print("✗ 数据目录不存在")
            return False
        
        # 检查示例数据文件
        sample_file = data_dir / "sample_data.csv"
        if not sample_file.exists():
            print("✗ 示例数据文件不存在")
            return False
        
        # 读取示例数据
        import pandas as pd
        df = pd.read_csv(sample_file)
        
        if len(df) > 0:
            print("✓ 数据目录存在")
            print("✓ 示例数据文件存在")
            print(f"✓ 数据行数: {len(df)}")
            print(f"✓ 数据列数: {len(df.columns)}")
            print(f"✓ 数据列名: {list(df.columns)}")
            return True
        else:
            print("✗ 数据文件为空")
            return False
            
    except Exception as e:
        print(f"✗ 数据文件测试失败: {e}")
        return False

def test_template_files():
    """测试模板文件"""
    print("\n" + "=" * 50)
    print("测试4: 模板文件测试")
    print("=" * 50)
    
    try:
        # 检查模板目录
        template_dir = project_dir / "templates"
        if not template_dir.exists():
            print("✗ 模板目录不存在")
            return False
        
        # 检查.gitkeep文件
        gitkeep_file = template_dir / ".gitkeep"
        if not gitkeep_file.exists():
            print("✗ .gitkeep文件不存在")
            return False
        
        print("✓ 模板目录存在")
        print("✓ .gitkeep文件存在")
        return True
            
    except Exception as e:
        print(f"✗ 模板文件测试失败: {e}")
        return False

def test_output_directory():
    """测试输出目录"""
    print("\n" + "=" * 50)
    print("测试5: 输出目录测试")
    print("=" * 50)
    
    try:
        # 检查输出目录
        output_dir = project_dir / "outputs"
        if not output_dir.exists():
            print("✗ 输出目录不存在")
            return False
        
        # 检查.gitkeep文件
        gitkeep_file = output_dir / ".gitkeep"
        if not gitkeep_file.exists():
            print("✗ .gitkeep文件不存在")
            return False
        
        print("✓ 输出目录存在")
        print("✓ .gitkeep文件存在")
        return True
            
    except Exception as e:
        print(f"✗ 输出目录测试失败: {e}")
        return False

def test_documentation():
    """测试文档文件"""
    print("\n" + "=" * 50)
    print("测试6: 文档文件测试")
    print("=" * 50)
    
    try:
        # 检查必要的文档文件
        required_files = [
            "README.md",
            "requirements.txt",
            "main.ipynb",
            ".env.example",
            ".gitignore",
            "DEVELOPMENT.md",
            "USER_MANUAL.md"
        ]
        
        missing_files = []
        for file_name in required_files:
            file_path = project_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"✗ 缺少以下文件: {missing_files}")
            return False
        else:
            print("✓ 所有必要的文档文件都存在")
            return True
            
    except Exception as e:
        print(f"✗ 文档文件测试失败: {e}")
        return False

def test_environment_config():
    """测试环境配置"""
    print("\n" + "=" * 50)
    print("测试7: 环境配置测试")
    print("=" * 50)
    
    try:
        # 检查.env.example文件
        env_example = project_dir / ".env.example"
        if not env_example.exists():
            print("✗ .env.example文件不存在")
            return False
        
        # 读取.env.example文件
        with open(env_example, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必要的配置项
        required_configs = [
            "LLM_MODEL_ID",
            "LLM_API_KEY",
            "LLM_BASE_URL"
        ]
        
        missing_configs = []
        for config in required_configs:
            if config not in content:
                missing_configs.append(config)
        
        if missing_configs:
            print(f"✗ 缺少以下配置项: {missing_configs}")
            return False
        else:
            print("✓ .env.example文件存在")
            print("✓ 所有必要的配置项都存在")
            return True
            
    except Exception as e:
        print(f"✗ 环境配置测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("MathModelAgent 项目测试")
    print("=" * 60)
    
    tests = [
        ("库导入测试", test_imports),
        ("RAG知识库测试", test_knowledge_base),
        ("数据文件测试", test_data_files),
        ("模板文件测试", test_template_files),
        ("输出目录测试", test_output_directory),
        ("文档文件测试", test_documentation),
        ("环境配置测试", test_environment_config)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ 测试 {test_name} 发生异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！项目可以正常运行。")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关文件。")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
