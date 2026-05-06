"""
F04 智能选股 — 自测试代码

验证：
1. mx_xuangu_tool HelloAgents工具封装正确
2. screener_service 选股服务层
3. FastAPI路由 /screener 正常工作
4. 选股Agent创建与工具注册
5. 条件参考接口正常
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

# 添加mx-xuangu技能路径
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "智能选股" / "mx-xuangu"))


def test_mx_xuangu_tool_structure():
    """测试1: HelloAgents工具封装结构"""
    print("\n[测试1] mx_xuangu_tool工具封装结构...")
    try:
        from agents.tools.mx_xuangu_tool import MXXuanguTool

        tool = MXXuanguTool(api_key="test_key")

        # 验证基本属性
        assert tool.name == "mx_xuangu", f"工具名应为mx_xuangu, 实际{tool.name}"
        assert "选股" in tool.description, "描述应包含'选股'"

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


def test_mx_xuangu_tool_no_key():
    """测试2: 无API Key时的错误处理"""
    print("\n[测试2] 无API Key错误处理...")
    try:
        from agents.tools.mx_xuangu_tool import MXXuanguTool

        saved_key = os.environ.pop("MX_APIKEY", None)

        tool = MXXuanguTool()
        result = tool.run({"query": "市盈率小于20的A股"})

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


def test_screener_service_structure():
    """测试3: 智能选股服务层结构"""
    print("\n[测试3] 选股服务层结构...")
    try:
        from app.services import screener_service

        # 验证核心函数存在
        functions = [
            "screen_stocks",
            "get_available_conditions",
        ]
        for name in functions:
            assert hasattr(screener_service, name), f"缺少函数 {name}"
            func = getattr(screener_service, name)
            assert callable(func), f"{name} 应为可调用函数"

        print(f"  ✅ 所有{len(functions)}个服务函数已定义")

        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screener_service_no_key():
    """测试4: 无API Key时服务层返回错误"""
    print("\n[测试4] 无API Key服务层错误处理...")
    try:
        from app.services import screener_service

        result = screener_service.screen_stocks("市盈率小于20且ROE大于15%的A股")
        assert result["success"] is False, "无APIKey时应返回success=False"
        assert result["error"] is not None, "应包含错误信息"
        print(f"  ✅ screen_stocks 正确返回错误: {result['error']}")

        return True
    except Exception as e:
        print(f"  ❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_conditions():
    """测试5: 选股条件参考接口"""
    print("\n[测试5] 选股条件参考接口...")
    try:
        from app.services import screener_service

        result = screener_service.get_available_conditions()
        assert result["success"] is True, "应返回success=True"
        assert "categories" in result, "应包含categories"
        assert len(result["categories"]) >= 3, f"应有至少3个分类, 实际{len(result)}"

        for cat in result["categories"]:
            assert "name" in cat, "分类应有name"
            assert "description" in cat, "分类应有description"
            assert "examples" in cat, "分类应有examples"
            assert len(cat["examples"]) > 0, f"分类'{cat['name']}'应至少有1个示例"

        print(f"  ✅ 条件参考包含{len(result['categories'])}个分类")
        for cat in result["categories"]:
            print(f"     - {cat['name']}: {len(cat['examples'])}个示例")

        return True
    except Exception as e:
        print(f"  ❌ 条件参考测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_screener_routes():
    """测试6: FastAPI选股路由"""
    print("\n[测试6] FastAPI选股路由...")
    try:
        import asyncio

        async def _init_db_task():
            from app.models.database import init_db as _init_db
            await _init_db()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_init_db_task())

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            # 测试 GET /screener/conditions
            response = client.get("/api/v1/screener/conditions")
            assert response.status_code == 200, f"应返回200, 实际{response.status_code}"
            data = response.json()
            assert data["code"] == 0, f"成功code应为0, 实际{data['code']}"
            assert "categories" in data["data"], "响应应包含categories"
            print(f"  ✅ /screener/conditions 成功: {len(data['data']['categories'])}个分类")

            # 测试 POST /screener/search（无API Key时应返回500）
            response = client.post("/api/v1/screener/search?query=市盈率小于20且ROE大于15%的A股")
            assert response.status_code in (200, 400, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ /screener/search 正确返回错误（无API Key）: {data['message']}")
            else:
                print(f"  ✅ /screener/search 成功: code={data['code']}")

            # 测试空查询
            response = client.post("/api/v1/screener/search?query=")
            data = response.json()
            assert response.status_code == 422 or data["code"] == 400, "空条件应返回400/422"
            print(f"  ✅ 空条件返回正确状态码")

        return True
    except Exception as e:
        print(f"  ❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hello_agents_tool_integration():
    """测试7: 选股工具与HelloAgents框架集成"""
    print("\n[测试7] mx_xuangu_tool与HelloAgents框架集成...")
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "HelloAgents Optimized"))

        from hello_agents import ToolRegistry
        from agents.tools.mx_xuangu_tool import MXXuanguTool

        registry = ToolRegistry()
        tool = MXXuanguTool(api_key="test_key")
        registry.register_tool(tool)

        registered = registry.get_tool("mx_xuangu")
        assert registered is not None, "工具未成功注册"
        assert registered.name == "mx_xuangu"

        description = registry.get_tools_description()
        assert "mx_xuangu" in description, "工具描述应包含mx_xuangu"

        result = registry.execute_tool("mx_xuangu", "市盈率小于20的A股")
        assert "未配置" in result or "错误" in result, f"无Key时应返回错误: {result[:50]}..."

        print(f"  ✅ 工具注册与执行正常")
        print(f"     注册表工具数: {len(registry.list_tools())}")

        return True
    except Exception as e:
        print(f"  ❌ 工具集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screener_agent_create():
    """测试8: 选股Agent创建"""
    print("\n[测试8] 选股Agent创建...")
    try:
        from agents.screener_agent import create_screener_agent

        saved_llm_key = os.environ.pop("LLM_API_KEY", None)

        try:
            agent = create_screener_agent(api_key="test_key")
            assert agent is not None
            assert agent.name == "选股Agent"
            registered = agent.tool_registry.get_tool("mx_xuangu")
            assert registered is not None, "MXXuanguTool应已注册"
            print(f"  ✅ 选股Agent创建成功")
            print(f"     Agent名称: {agent.name}")
            print(f"     已注册工具: mx_xuangu")
            print(f"     工具调用模式: auto")
        except RuntimeError as e:
            assert "LLM_API_KEY" in str(e), f"应提示LLM_API_KEY: {e}"
            print(f"  ✅ 无LLM Key时正确抛出异常: {str(e)[:80]}")

        if saved_llm_key is not None:
            os.environ["LLM_API_KEY"] = saved_llm_key

        return True
    except Exception as e:
        print(f"  ❌ Agent创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screener_service_data_structure():
    """测试9: 服务层返回数据结构"""
    print("\n[测试9] 服务层返回数据结构...")
    try:
        from app.services.screener_service import screen_stocks

        result = screen_stocks("市盈率小于20且ROE大于15%的A股")
        assert isinstance(result, dict), "应返回字典"
        assert "success" in result
        assert "query" in result
        assert "total_count" in result
        assert "data_source" in result
        assert "stocks" in result
        assert "conditions" in result
        assert "error" in result
        assert isinstance(result["stocks"], list), "stocks应为列表"
        assert isinstance(result["conditions"], list), "conditions应为列表"
        print(f"  ✅ screen_stocks 返回结构正确")

        return True
    except Exception as e:
        print(f"  ❌ 数据结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screener_agent_system_prompt():
    """测试10: 选股Agent系统提示词"""
    print("\n[测试10] 选股Agent系统提示词...")
    try:
        from agents.screener_agent import SCREENER_SYSTEM_PROMPT

        key_elements = [
            "选股策略分析师",
            "行情指标",
            "财务指标",
            "不构成投资建议",
        ]
        for element in key_elements:
            assert element in SCREENER_SYSTEM_PROMPT, f"提示词应包含'{element}'"

        print(f"  ✅ 系统提示词包含所有关键分析维度")
        print(f"     提示词长度: {len(SCREENER_SYSTEM_PROMPT)}字符")

        return True
    except Exception as e:
        print(f"  ❌ 提示词测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F04 智能选股 — 自测试")
    print("=" * 60)

    tests = [
        ("mx_xuangu_tool工具封装结构", test_mx_xuangu_tool_structure),
        ("无API Key错误处理", test_mx_xuangu_tool_no_key),
        ("选股服务层结构", test_screener_service_structure),
        ("无API Key服务层错误", test_screener_service_no_key),
        ("选股条件参考接口", test_get_conditions),
        ("FastAPI选股路由", test_fastapi_screener_routes),
        ("工具与HelloAgents框架集成", test_hello_agents_tool_integration),
        ("选股Agent创建", test_screener_agent_create),
        ("服务层返回数据结构", test_screener_service_data_structure),
        ("选股Agent系统提示词", test_screener_agent_system_prompt),
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
