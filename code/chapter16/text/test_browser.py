#!/usr/bin/env python3
"""
测试 browser_tool 的独立运行
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.browser_tool import BrowserTool

def test_browser_tool():
    print("🔍 测试 BrowserTool 独立运行")

    # 创建工具实例
    browser = BrowserTool()

    print(f"工具名称: {browser.name}")
    print(f"工具描述: {browser.description}")
    print(f"参数定义: {browser.get_parameters()}")

    # 测试搜索
    test_query = "长沙有什么美食"
    print(f"\n🧪 测试搜索: {test_query}")

    try:
        # 直接调用工具
        result = browser.run({"input": test_query})
        print("✅ 工具调用成功")
        print(f"结果长度: {len(result)} 字符")
        print(f"结果预览: {result[:500]}...")

        return result

    except Exception as e:
        print(f"❌ 工具调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_browser_tool()
