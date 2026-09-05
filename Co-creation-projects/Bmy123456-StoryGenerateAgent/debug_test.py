#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本
"""

import sys
import os

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"Python版本: {sys.version}")
print(f"当前工作目录: {os.getcwd()}")
print(f"Python路径: {sys.path[0]}")

try:
    import openai
    print(f"OpenAI版本: {openai.__version__}")
    print("✓ OpenAI导入成功")
except ImportError as e:
    print(f"✗ OpenAI导入失败: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ 环境变量加载成功")
except Exception as e:
    print(f"⚠ 环境变量加载失败: {e}")

try:
    # 测试导入配置
    from src.config.settings import settings
    print("✓ 配置导入成功")
    print(f"  模型: {settings.model_name}")
    print(f"  温度: {settings.temperature}")
except Exception as e:
    print(f"⚠ 配置导入失败: {e}")

try:
    # 测试导入LLM客户端
    from src.models.llm_client import LLMClient
    print("✓ LLM客户端导入成功")
except Exception as e:
    print(f"✗ LLM客户端导入失败: {e}")
    import traceback
    traceback.print_exc()