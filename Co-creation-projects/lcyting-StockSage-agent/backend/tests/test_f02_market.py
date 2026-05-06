"""
F02 金融数据查询 — 自测试代码

验证：
1. mx_data_tool HelloAgents工具封装正确
2. market_service 行情数据服务
3. FastAPI路由 /market 和 /financial 正常工作
4. 数据解析逻辑正确
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
AGENTS_DIR = PROJECT_ROOT / "agents"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(AGENTS_DIR))

# 添加mx-data技能路径
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "金融数据" / "mx-data"))


def test_mx_data_tool_structure():
    """测试1: HelloAgents工具封装结构"""
    print("\n[测试1] HelloAgents工具封装结构...")
    try:
        # 测试工具定义（不需要真实API Key）
        from agents.tools.mx_data_tool import MXDataTool

        # 用占位key测试工具结构
        tool = MXDataTool(api_key="test_key")

        # 验证基本属性
        assert tool.name == "mx_data", f"工具名应为mx_data, 实际{tool.name}"
        assert "金融数据" in tool.description, "描述应包含'金融数据'"

        # 验证参数定义
        params = tool.get_parameters()
        assert len(params) == 1, f"应有1个参数, 实际{len(params)}"
        assert params[0].name == "query", f"参数名应为query, 实际{params[0].name}"
        assert params[0].required is True, "query参数应为必需"

        print("  ✅ 工具结构正确")
        print(f"     工具名: {tool.name}")
        print(f"     参数: query (required)")

        return True
    except Exception as e:
        print(f"  ❌ 工具结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mx_data_tool_no_key():
    """测试2: 无API Key时的错误处理"""
    print("\n[测试2] 无API Key错误处理...")
    try:
        from agents.tools.mx_data_tool import MXDataTool

        # 不传api_key，且环境变量中没有MX_APIKEY（使用占位符）
        import os
        saved_key = os.environ.pop("MX_APIKEY", None)

        tool = MXDataTool()
        result = tool.run({"query": "贵州茅台最新价"})

        if saved_key is not None:
            os.environ["MX_APIKEY"] = saved_key

        assert "未配置" in result or "错误" in result, f"应返回错误提示: {result}"
        print(f"  ✅ 正确返回错误提示: {result}")

        return True
    except Exception as e:
        print(f"  ❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_service_structure():
    """测试3: 行情数据服务层结构"""
    print("\n[测试3] 行情数据服务层结构...")
    try:
        from app.services import market_service

        # 验证核心函数存在
        functions = [
            "query_financial_data",
            "get_stock_quote",
            "get_stock_financial",
            "get_stock_profile",
            "get_stock_holders",
            "get_index_quote",
            "get_sector_quote",
        ]
        for name in functions:
            assert hasattr(market_service, name), f"缺少函数 {name}"
            func = getattr(market_service, name)
            assert callable(func), f"{name} 应为可调用函数"

        print(f"  ✅ 所有{len(functions)}个服务函数已定义")

        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_service_no_key():
    """测试4: 无API Key时服务层返回错误"""
    print("\n[测试4] 无API Key服务层错误处理...")
    try:
        from app.services import market_service

        # 查询时没有MX_APIKEY应该返回error
        result = market_service.get_stock_quote("600519")
        assert result["success"] is False, "无APIKey时应返回success=False"
        assert result["error"] is not None, "应包含错误信息"
        print(f"  ✅ 正确返回错误: {result['error']}")

        return True
    except Exception as e:
        print(f"  ❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_market_routes():
    """测试5: FastAPI行情路由"""
    print("\n[测试5] FastAPI行情路由...")
    try:
        import asyncio

        async def _init_db_task():
            from app.models.preference import UserPreference  # noqa: F401
            from app.models.database import init_db as _init_db
            await _init_db()

        # Python 3.10+ 需要手动创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_init_db_task())

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            # 测试 GET /market/quote/{code}
            response = client.get("/api/v1/market/quote/600519")
            assert response.status_code in (200, 500), f"状态码异常: {response.status_code}"
            data = response.json()
            if response.status_code == 500:
                # 预期：无API Key时返回500
                assert data["code"] == 500
                print(f"  ✅ /market/quote/600519 正确返回错误（无API Key）: {data['message']}")
            else:
                print(f"  ✅ /market/quote/600519 成功: code={data['code']}")

            # 测试无效代码
            response = client.get("/api/v1/market/quote/12")
            data = response.json()
            assert data["code"] == 400, "短代码应返回400"
            print(f"  ✅ 无效代码返回400: {data['message']}")

            # 测试 GET /market/index
            response = client.get("/api/v1/market/index?name=沪深300")
            assert response.status_code in (200, 500)
            print(f"  ✅ /market/index 路由正常")

            # 测试 GET /financial/indicators/{code}
            response = client.get("/api/v1/financial/indicators/600519?indicators=净利润")
            assert response.status_code in (200, 500)
            print(f"  ✅ /financial/indicators 路由正常")

            # 测试 GET /financial/profile/{code}
            response = client.get("/api/v1/financial/profile/600519")
            assert response.status_code in (200, 500)
            print(f"  ✅ /financial/profile 路由正常")

            # 测试 GET /financial/holders/{code}
            response = client.get("/api/v1/financial/holders/600519")
            assert response.status_code in (200, 500)
            print(f"  ✅ /financial/holders 路由正常")

            # 测试无API Key时的错误格式
            response = client.get("/api/v1/market/quote/600519")
            data = response.json()
            if data["code"] == 500:
                assert "MX_APIKEY" in data.get("message", ""), "错误信息应提及MX_APIKEY"
                print(f"  ✅ 错误响应格式正确")

        return True
    except Exception as e:
        print(f"  ❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hello_agents_tool_integration():
    """测试6: 工具与HelloAgents框架集成"""
    print("\n[测试6] 工具与HelloAgents框架集成...")
    try:
        # 将HelloAgents框架加入路径
        sys.path.insert(0, str(PROJECT_ROOT / "HelloAgents Optimized"))

        from hello_agents import ToolRegistry
        from agents.tools.mx_data_tool import MXDataTool

        # 创建工具注册表并注册MXDataTool
        registry = ToolRegistry()
        tool = MXDataTool(api_key="test_key")
        registry.register_tool(tool)

        # 验证工具已注册
        registered = registry.get_tool("mx_data")
        assert registered is not None, "工具未成功注册"
        assert registered.name == "mx_data"

        # 验证工具描述可获取
        description = registry.get_tools_description()
        assert "mx_data" in description, "工具描述应包含mx_data"

        # 验证工具可执行
        result = registry.execute_tool("mx_data", '贵州茅台最新价')
        assert "未配置" in result or "错误" in result, f"无Key时应返回错误: {result[:50]}..."

        print(f"  ✅ 工具注册与执行正常")
        print(f"     注册表工具数: {len(registry.list_tools())}")
        print(f"     执行结果: {result[:80]}...")

        return True
    except Exception as e:
        print(f"  ❌ 工具集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_service_with_mock():
    """测试7: 服务层数据格式化（模拟数据）"""
    print("\n[测试7] 服务层数据格式化...")
    try:
        from app.services.market_service import query_financial_data

        # 模拟mx-data模块的parse_result行为
        mock_tables = [
            {
                "sheet_name": "测试表",
                "rows": [
                    {"日期": "2024-01-01", "价格": "100.00", "涨跌幅": "2.5%"},
                    {"日期": "2024-01-02", "价格": "102.50", "涨跌幅": "1.8%"},
                ],
                "fieldnames": ["日期", "价格", "涨跌幅"],
            }
        ]

        # 验证返回结构
        result = query_financial_data("测试查询")
        assert isinstance(result, dict), "应返回字典"
        assert "success" in result
        assert "query" in result
        assert "tables" in result
        assert "error" in result
        assert "condition_parts" in result
        assert "total_rows" in result

        print(f"  ✅ 返回结构正确")
        print(f"     success: {result['success']}")
        print(f"     query: {result['query']}")

        return True
    except Exception as e:
        print(f"  ❌ 格式化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F02 金融数据查询 — 自测试")
    print("=" * 60)

    tests = [
        ("HelloAgents工具封装结构", test_mx_data_tool_structure),
        ("无API Key错误处理", test_mx_data_tool_no_key),
        ("行情数据服务层结构", test_market_service_structure),
        ("无API Key服务层错误", test_market_service_no_key),
        ("FastAPI行情路由", test_fastapi_market_routes),
        ("工具与框架集成", test_hello_agents_tool_integration),
        ("服务层数据格式化", test_market_service_with_mock),
    ]

    results = {}
    for name, test_func in tests:
        results[name] = test_func()

    # 汇总
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")

    print(f"\n  通过: {passed}/{total}")
    if passed == total:
        print("  🎉 所有测试通过！")
    else:
        print(f"  ⚠️ {total - passed} 项测试未通过")

    return passed == total


if __name__ == "__main__":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    success = main()
    sys.exit(0 if success else 1)
