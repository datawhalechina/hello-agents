"""
F03 资讯搜索与舆情分析 — 自测试代码

验证：
1. mx_search_tool HelloAgents工具封装正确
2. news_service 资讯搜索服务
3. FastAPI路由 /news 正常工作
4. 舆情分析Agent创建与工具注册
5. 数据解析逻辑正确
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

# 添加mx-search技能路径
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "资讯搜索" / "mx-search"))


def test_mx_search_tool_structure():
    """测试1: HelloAgents工具封装结构"""
    print("\n[测试1] mx_search_tool工具封装结构...")
    try:
        from agents.tools.mx_search_tool import MXSearchTool

        # 用占位key测试工具结构
        tool = MXSearchTool(api_key="test_key")

        # 验证基本属性
        assert tool.name == "mx_search", f"工具名应为mx_search, 实际{tool.name}"
        assert "资讯" in tool.description, "描述应包含'资讯'"

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


def test_mx_search_tool_no_key():
    """测试2: 无API Key时的错误处理"""
    print("\n[测试2] 无API Key错误处理...")
    try:
        from agents.tools.mx_search_tool import MXSearchTool

        # 不传api_key，且环境变量中没有MX_APIKEY（使用占位符）
        saved_key = os.environ.pop("MX_APIKEY", None)

        tool = MXSearchTool()
        result = tool.run({"query": "人工智能板块近期新闻"})

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


def test_news_service_structure():
    """测试3: 资讯搜索服务层结构"""
    print("\n[测试3] 资讯搜索服务层结构...")
    try:
        from app.services import news_service

        # 验证核心函数存在
        functions = [
            "search_news",
            "search_stock_news",
            "search_sector_news",
            "search_market_news",
            "analyze_sentiment",
        ]
        for name in functions:
            assert hasattr(news_service, name), f"缺少函数 {name}"
            func = getattr(news_service, name)
            assert callable(func), f"{name} 应为可调用函数"

        print(f"  ✅ 所有{len(functions)}个服务函数已定义")

        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_news_service_no_key():
    """测试4: 无API Key时服务层返回错误"""
    print("\n[测试4] 无API Key服务层错误处理...")
    try:
        from app.services import news_service

        # 通用搜索
        result = news_service.search_news("人工智能板块近期新闻")
        assert result["success"] is False, "无APIKey时应返回success=False"
        assert result["error"] is not None, "应包含错误信息"
        print(f"  ✅ search_news 正确返回错误: {result['error']}")

        # 个股搜索
        result = news_service.search_stock_news("600519")
        assert result["success"] is False
        assert result["error"] is not None
        print(f"  ✅ search_stock_news 正确返回错误: {result['error']}")

        # 行业搜索
        result = news_service.search_sector_news("人工智能")
        assert result["success"] is False
        assert result["error"] is not None
        print(f"  ✅ search_sector_news 正确返回错误: {result['error']}")

        # 个股舆情分析
        result = news_service.analyze_sentiment("600519")
        assert result["success"] is False
        assert result["error"] is not None
        print(f"  ✅ analyze_sentiment 正确返回错误: {result['error']}")

        # 热门资讯
        result = news_service.search_market_news()
        assert result["success"] is False
        assert result["error"] is not None
        print(f"  ✅ search_market_news 正确返回错误: {result['error']}")

        return True
    except Exception as e:
        print(f"  ❌ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_news_routes():
    """测试5: FastAPI资讯路由"""
    print("\n[测试5] FastAPI资讯路由...")
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
            # 测试 GET /news/search
            response = client.get("/api/v1/news/search?query=人工智能板块近期新闻")
            assert response.status_code in (200, 400, 500), f"状态码异常: {response.status_code}"
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ /news/search 正确返回错误（无API Key）: {data['message']}")
            else:
                print(f"  ✅ /news/search 成功: code={data['code']}")

            # 测试空查询
            response = client.get("/api/v1/news/search?query=")
            data = response.json()
            assert response.status_code == 422 or data["code"] == 400, "空查询应返回400或422"
            print(f"  ✅ 空查询返回正确状态码")

            # 测试 GET /news/sentiment/{code}
            response = client.get("/api/v1/news/sentiment/600519")
            assert response.status_code in (200, 500)
            print(f"  ✅ /news/sentiment/600519 路由正常")

            # 测试无效代码
            response = client.get("/api/v1/news/sentiment/12")
            data = response.json()
            assert data["code"] == 400, "短代码应返回400"
            print(f"  ✅ 无效代码返回400: {data['message']}")

            # 测试 GET /news/hot
            response = client.get("/api/v1/news/hot")
            assert response.status_code in (200, 500)
            print(f"  ✅ /news/hot 路由正常")

            # 测试无API Key时的错误格式
            response = client.get("/api/v1/news/search?query=贵州茅台最新研报")
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
    """测试6: 资讯搜索工具与HelloAgents框架集成"""
    print("\n[测试6] mx_search_tool与HelloAgents框架集成...")
    try:
        # 将HelloAgents框架加入路径
        sys.path.insert(0, str(PROJECT_ROOT / "HelloAgents Optimized"))

        from hello_agents import ToolRegistry
        from agents.tools.mx_search_tool import MXSearchTool

        # 创建工具注册表并注册MXSearchTool
        registry = ToolRegistry()
        tool = MXSearchTool(api_key="test_key")
        registry.register_tool(tool)

        # 验证工具已注册
        registered = registry.get_tool("mx_search")
        assert registered is not None, "工具未成功注册"
        assert registered.name == "mx_search"

        # 验证工具描述可获取
        description = registry.get_tools_description()
        assert "mx_search" in description, "工具描述应包含mx_search"

        # 验证工具可执行（无Key时返回错误）
        result = registry.execute_tool("mx_search", "人工智能板块近期新闻")
        assert "未配置" in result or "错误" in result, f"无Key时应返回错误: {result[:50]}..."

        print(f"  ✅ 工具注册与执行正常")
        print(f"     注册表工具数: {len(registry.list_tools())}")

        return True
    except Exception as e:
        print(f"  ❌ 工具集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_agent_create():
    """测试7: 舆情分析Agent创建"""
    print("\n[测试7] 舆情分析Agent创建...")
    try:
        from agents.sentiment_agent import create_sentiment_agent

        # 无LLM Key时应该抛出异常或至少能验证代码结构
        import os
        saved_llm_key = os.environ.pop("LLM_API_KEY", None)

        try:
            agent = create_sentiment_agent(api_key="test_key")
            # 如果成功创建（环境变量中有LLM配置），验证Agent结构
            assert agent is not None
            assert agent.name == "舆情分析Agent"
            registered = agent.tool_registry.get_tool("mx_search")
            assert registered is not None, "MXSearchTool应已注册"
            print(f"  ✅ 舆情分析Agent创建成功")
            print(f"     Agent名称: {agent.name}")
            print(f"     已注册工具: mx_search")
        except RuntimeError as e:
            # 预期：无LLM Key时抛出RuntimeError
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


def test_news_service_data_structure():
    """测试8: 服务层返回数据结构"""
    print("\n[测试8] 服务层返回数据结构...")
    try:
        from app.services.news_service import search_news, analyze_sentiment

        # 验证 search_news 返回结构
        result = search_news("人工智能板块近期新闻")
        assert isinstance(result, dict), "应返回字典"
        assert "success" in result
        assert "query" in result
        assert "total_count" in result
        assert "items" in result
        assert "error" in result
        assert isinstance(result["items"], list), "items应为列表"
        print(f"  ✅ search_news 返回结构正确")

        # 验证 analyze_sentiment 返回结构
        result = analyze_sentiment("600519")
        assert isinstance(result, dict), "应返回字典"
        assert "success" in result
        assert "code" in result
        assert "total_count" in result
        assert "news_items" in result
        assert "report_items" in result
        assert "announce_items" in result
        assert "error" in result
        assert isinstance(result["news_items"], list), "news_items应为列表"
        assert isinstance(result["report_items"], list), "report_items应为列表"
        assert isinstance(result["announce_items"], list), "announce_items应为列表"
        print(f"  ✅ analyze_sentiment 返回结构正确")

        return True
    except Exception as e:
        print(f"  ❌ 数据结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_news_item_original_url_extraction():
    """测试: 资讯条目原文地址解析（嵌套 / 非常规字段名）"""
    print("\n[测试] 资讯原文地址字段解析...")
    try:
        from app.services.news_service import _item_original_url

        assert _item_original_url({"url": "https://example.com/a"}) == "https://example.com/a"
        assert _item_original_url({"detail": {"pcUrl": "https://x.com/p"}}) == "https://x.com/p"
        assert _item_original_url({"title": "t", "content": "正文不含链接"}) == ""
        assert (
            _item_original_url({"blocks": [{"shareUrl": "https://nested.io/z"}]})
            == "https://nested.io/z"
        )
        print("  ✅ 原文地址解析正确")
        return True
    except Exception as e:
        print(f"  ❌ 原文地址解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_agent_system_prompt():
    """测试9: 舆情分析Agent系统提示词"""
    print("\n[测试9] 舆情分析Agent系统提示词...")
    try:
        from agents.sentiment_agent import SENTIMENT_SYSTEM_PROMPT

        # 验证提示词包含关键分析维度
        key_elements = [
            "金融舆情分析师",
            "情感倾向",
            "利好",
            "不构成投资建议",
        ]
        for element in key_elements:
            assert element in SENTIMENT_SYSTEM_PROMPT, f"提示词应包含'{element}'"

        print(f"  ✅ 系统提示词包含所有关键分析维度")
        print(f"     提示词长度: {len(SENTIMENT_SYSTEM_PROMPT)}字符")

        return True
    except Exception as e:
        print(f"  ❌ 提示词测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F03 资讯搜索与舆情分析 — 自测试")
    print("=" * 60)

    tests = [
        ("mx_search_tool工具封装结构", test_mx_search_tool_structure),
        ("无API Key错误处理", test_mx_search_tool_no_key),
        ("资讯搜索服务层结构", test_news_service_structure),
        ("无API Key服务层错误", test_news_service_no_key),
        ("FastAPI资讯路由", test_fastapi_news_routes),
        ("资讯原文地址字段解析", test_news_item_original_url_extraction),
        ("工具与HelloAgents框架集成", test_hello_agents_tool_integration),
        ("舆情分析Agent创建", test_sentiment_agent_create),
        ("服务层返回数据结构", test_news_service_data_structure),
        ("舆情分析Agent系统提示词", test_sentiment_agent_system_prompt),
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
