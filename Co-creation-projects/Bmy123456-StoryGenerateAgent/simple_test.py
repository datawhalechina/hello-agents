#!/usr/bin/env python3
"""
简单的测试脚本
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"当前目录: {current_dir}")
print(f"Python版本: {sys.version}")

# 检查是否存在.env文件
if os.path.exists('.env'):
    print("找到.env文件")
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if 'OPENAI_API_KEY' in line:
                print(f"API密钥: {line[:20]}...")
                break
else:
    print("未找到.env文件")

# 测试导入
try:
    import openai
    print(f"OpenAI版本: {openai.__version__}")
except Exception as e:
    print(f"导入OpenAI失败: {e}")

try:
    from src.agent import StoryGeneratorAgent
    print("成功导入StoryGeneratorAgent")
    agent = StoryGeneratorAgent()
    print("成功创建agent实例")
except Exception as e:
    print(f"导入或创建agent失败: {e}")
    import traceback
    traceback.print_exc()