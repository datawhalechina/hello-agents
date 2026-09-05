#!/usr/bin/env python3
"""
验证所有模块导入是否成功
"""

import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"当前目录: {current_dir}")
print(f"Python路径: {sys.path[0]}\n")

# 测试导入
success_count = 0
total_count = 0

# 测试配置模块
total_count += 1
try:
    from config.settings import settings
    from config.prompts import NOVEL_PROMPT, POEM_PROMPT, SCRIPT_PROMPT
    print("✅ 配置模块导入成功")
    success_count += 1
except Exception as e:
    print(f"❌ 配置模块导入失败: {e}")

# 测试utils模块
total_count += 1
try:
    from src.utils.validation import validate_input
    print("✅ 验证工具导入成功")
    success_count += 1
except Exception as e:
    print(f"❌ 验证工具导入失败: {e}")

# 测试models模块
total_count += 1
try:
    from src.models.llm_client import LLMClient
    print("✅ LLM客户端导入成功")
    success_count += 1
except Exception as e:
    print(f"❌ LLM客户端导入失败: {e}")

# 测试generator模块
total_count += 1
try:
    from src.generator.novel import NovelGenerator
    from src.generator.poem import PoemGenerator
    from src.generator.script import ScriptGenerator
    print("✅ 生成器模块导入成功")
    success_count += 1
except Exception as e:
    print(f"❌ 生成器模块导入失败: {e}")

# 测试agent模块
total_count += 1
try:
    from src.agent import StoryGeneratorAgent
    print("✅ Agent模块导入成功")
    success_count += 1
except Exception as e:
    print(f"❌ Agent模块导入失败: {e}")
    import traceback
    traceback.print_exc()

# 输出结果
print(f"\n导入结果: {success_count}/{total_count} 模块导入成功")

if success_count == total_count:
    print("🎉 所有模块导入成功！")
    print("\n你可以直接使用 StoryGeneratorAgent:")
    print("from src.agent import StoryGeneratorAgent")
    print("agent = StoryGeneratorAgent('your_api_key')")
    print("result = agent.generate_novel('测试主题', '现实主义')")
else:
    print("⚠️ 部分模块导入失败，请检查错误信息")