#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本 - 直接运行故事生成器
"""

import os
import sys

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def demo():
    """演示故事生成功能"""
    print("=== 故事生成器智能体演示 ===\n")

    # 显示配置
    print(f"API类型: {os.getenv('BASE_URL', 'OpenAI')}")
    print(f"模型: {os.getenv('MODEL_NAME', 'gpt-4')}")
    print(f"API密钥: {'已设置' if os.getenv('OPENAI_API_KEY') else '未设置'}\n")

    try:
        # 导入智能体
        from src.agent import StoryGeneratorAgent

        # 创建实例
        agent = StoryGeneratorAgent()
        print("[成功] 故事生成器初始化成功\n")

        # 1. 小说演示
        print("1. 生成小说...")
        novel = agent.generate_novel(
            theme="一个关于友谊的故事",
            style="现实主义",
            length="短篇"
        )
        print("\n--- 小说内容 ---\n")
        print(novel[:500] + "..." if len(novel) > 500 else novel)
        print()

        # 2. 诗歌演示
        print("\n2. 生成诗歌...")
        poem = agent.generate_poem(
            theme="春天",
            style="抒情诗",
            form="十四行诗"
        )
        print("\n--- 诗歌内容 ---\n")
        print(poem)
        print()

        # 3. 剧本演示
        print("\n3. 生成剧本...")
        script = agent.generate_script(
            theme="一个悬疑故事",
            style="现代剧",
            genre="悬疑",
            scene_count=2
        )
        print("\n--- 剧本内容 ---\n")
        print(script)
        print()

        print("[成功] 所有演示完成!")

    except Exception as e:
        print(f"\n[错误]: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo()