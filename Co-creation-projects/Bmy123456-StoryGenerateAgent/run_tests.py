#!/usr/bin/env python3
"""
运行所有测试
"""

import sys
import os
import unittest

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入测试模块
try:
    from tests.test_agent import TestStoryGeneratorAgent
    print("✓ 测试模块导入成功")
except ImportError as e:
    print(f"✗ 测试模块导入失败: {e}")
    sys.exit(1)

# 创建测试套件
def run_tests():
    """运行所有测试"""
    print("\n=== 运行故事生成器测试 ===\n")

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTest(TestStoryGeneratorAgent('test_input_validation'))
    suite.addTest(TestStoryGeneratorAgent('test_generate_novel'))
    suite.addTest(TestStoryGeneratorAgent('test_generate_poem'))
    suite.addTest(TestStoryGeneratorAgent('test_generate_script'))
    suite.addTest(TestStoryGeneratorAgent('test_summarize'))
    suite.addTest(TestStoryGeneratorAgent('test_translate'))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n❌ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())