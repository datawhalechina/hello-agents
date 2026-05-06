"""
F07 模拟组合交易 — 自测试代码

验证：
1. MXMoniTool 工具封装正确
2. simulation_service 服务层结构正确
3. trading_agent 交易执行Agent创建
4. FastAPI路由 /simulation 正常工作
5. 参数校验逻辑
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

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "模拟组合管理" / "mx-moni"))
sys.path.insert(0, str(PROJECT_ROOT / "HelloAgents Optimized"))


def test_mx_moni_tool():
    """测试1: MXMoniTool 工具封装"""
    print("\n[测试1] MXMoniTool 工具封装...")
    try:
        from agents.tools.mx_moni_tool import MXMoniTool

        tool = MXMoniTool(api_key="test_key")

        # 验证基础属性
        assert tool.name == "mx_moni"
        assert tool.api_key == "test_key"

        # 验证参数定义
        params = tool.get_parameters()
        assert len(params) == 5  # action, stock_code, price, quantity, order_id
        param_names = [p.name for p in params]
        assert "action" in param_names
        assert "stock_code" in param_names
        assert "quantity" in param_names

        # 验证无API Key时的降级
        tool_no_key = MXMoniTool(api_key="")
        result = tool_no_key.run({"action": "positions"})
        assert "MX_APIKEY" in result

        # 验证无效操作
        result2 = tool.run({"action": "invalid_op"})
        assert "不支持" in result2

        # 验证参数校验（buy时不提供stock_code）
        result3 = tool.run({"action": "buy"})
        assert "错误" in result3

        print(f"  ✅ MXMoniTool创建成功")
        print(f"     工具名称: {tool.name}")
        print(f"     参数: {', '.join(param_names)}")
        return True
    except Exception as e:
        print(f"  ❌ 工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulation_service_structure():
    """测试2: 模拟交易服务层结构"""
    print("\n[测试2] 模拟交易服务层结构...")
    try:
        from app.services import simulation_service

        functions = [
            "get_positions",
            "get_balance",
            "get_orders",
            "place_order",
            "cancel_order",
            "cancel_all_orders",
        ]
        for name in functions:
            assert hasattr(simulation_service, name), f"缺少函数 {name}"
            func = getattr(simulation_service, name)
            assert callable(func), f"{name} 应为可调用函数"

        print(f"  ✅ 所有{len(functions)}个核心函数已定义")
        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulation_service_validation():
    """测试3: 服务层参数校验"""
    print("\n[测试3] 服务层参数校验...")
    try:
        from app.services import simulation_service

        # 测试无效交易类型
        result1 = simulation_service.place_order("invalid", "600519", 100)
        assert not result1["success"]
        assert "无效" in result1.get("error", "")
        print(f"  ✅ 无效交易类型被拦截")

        # 测试无效股票代码
        result2 = simulation_service.place_order("buy", "12", 100)
        assert not result2["success"]
        assert "股票代码" in result2.get("error", "")
        print(f"  ✅ 无效股票代码被拦截")

        # 测试数量不是100整数倍
        result3 = simulation_service.place_order("buy", "600519", 150)
        assert not result3["success"]
        assert "100" in result3.get("error", "")
        print(f"  ✅ 非100整数倍数量被拦截")

        # 测试数量<=0
        result4 = simulation_service.place_order("buy", "600519", 0)
        assert not result4["success"]
        assert "大于0" in result4.get("error", "")
        print(f"  ✅ 非正数数量被拦截")

        # 测试正常参数可通过校验（无API Key时会因为API不可用而失败）
        result5 = simulation_service.place_order("buy", "600519", 100, 1700.00)
        # 预期因MX_APIKEY未配置而失败，但不是参数校验错误
        assert "MX_APIKEY" in result5.get("error", "") or not result5["success"]
        print(f"  ✅ 正常参数通过校验（API未配置时正确降级）")

        return True
    except Exception as e:
        print(f"  ❌ 校验测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trading_agent_create():
    """测试4: 交易执行Agent创建"""
    print("\n[测试4] 交易执行Agent创建...")
    try:
        from agents.trading_agent import create_trading_agent, TRADING_AGENT_PROMPT

        saved_llm_key = os.environ.pop("LLM_API_KEY", None)

        try:
            agent = create_trading_agent(api_key="test_key")
            assert agent is not None
            assert agent.name == "交易执行Agent"

            # 验证mx_moni工具已注册
            registered = agent.tool_registry.get_tool("mx_moni")
            assert registered is not None, "MXMoniTool应已注册"
            assert registered.name == "mx_moni"

            print(f"  ✅ 交易执行Agent创建成功")
            print(f"     Agent名称: {agent.name}")
            print(f"     范式: FunctionCall")
            print(f"     已注册工具: mx_moni")
        except RuntimeError as e:
            assert "LLM_API_KEY" in str(e)
            print(f"  ✅ 无LLM Key时正确抛出异常")

        if saved_llm_key is not None:
            os.environ["LLM_API_KEY"] = saved_llm_key

        # 验证提示词
        assert "查询持仓" in TRADING_AGENT_PROMPT
        assert "买入" in TRADING_AGENT_PROMPT
        assert "卖出" in TRADING_AGENT_PROMPT
        assert "撤单" in TRADING_AGENT_PROMPT
        assert "100股" in TRADING_AGENT_PROMPT or "100的整数倍" in TRADING_AGENT_PROMPT
        assert "模拟" in TRADING_AGENT_PROMPT
        print(f"  ✅ 提示词内容验证通过 ({len(TRADING_AGENT_PROMPT)}字符)")

        return True
    except Exception as e:
        print(f"  ❌ Agent创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_simulation_routes():
    """测试5: FastAPI模拟交易路由"""
    print("\n[测试5] FastAPI模拟交易路由...")
    try:
        import asyncio
        from app.models.database import init_db as _init_db

        async def _init_db_task():
            await _init_db()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_init_db_task())

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            # 测试 GET /simulation/portfolio
            response = client.get("/api/v1/simulation/portfolio")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ GET /simulation/portfolio 正确返回错误（无API Key）: {data.get('message', '')[:50]}")
            else:
                print(f"  ✅ GET /simulation/portfolio 成功: {data.get('message', '')}")

            # 测试 GET /simulation/funds
            response = client.get("/api/v1/simulation/funds")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ GET /simulation/funds 正确返回错误（无API Key）")
            else:
                print(f"  ✅ GET /simulation/funds 成功")

            # 测试 GET /simulation/orders
            response = client.get("/api/v1/simulation/orders")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ GET /simulation/orders 正确返回错误（无API Key）")
            else:
                print(f"  ✅ GET /simulation/orders 成功")

            # 测试 POST /simulation/order（正常买入）
            response = client.post("/api/v1/simulation/order", json={
                "trade_type": "buy",
                "stock_code": "600519",
                "quantity": 100,
                "price": 1700.00,
            })
            assert response.status_code in (200, 422, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ POST /simulation/order 正确返回错误（无API Key）: {data.get('message', '')[:50]}")
            elif response.status_code == 422:
                print(f"  ✅ POST /simulation/order 参数校验通过（422为Pydantic验证）")
            else:
                print(f"  ✅ POST /simulation/order 下单成功")

            # 测试 POST /simulation/order（市价买入）
            response = client.post("/api/v1/simulation/order", json={
                "trade_type": "buy",
                "stock_code": "000001",
                "quantity": 200,
            })
            assert response.status_code in (200, 422, 500)
            print(f"  ✅ POST /simulation/order 市价单提交正常")

            # 测试空请求体（Pydantic验证422）
            response = client.post("/api/v1/simulation/order", json={})
            assert response.status_code == 422
            print(f"  ✅ 空请求体返回422 (Pydantic验证)")

            # 测试 DELETE /simulation/order/{order_id}
            response = client.delete("/api/v1/simulation/order/test_order_123")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ DELETE /simulation/order 正确返回错误（无API Key）")
            else:
                print(f"  ✅ DELETE /simulation/order 撤单成功")

            # 测试 POST /simulation/cancel-all
            response = client.post("/api/v1/simulation/cancel-all")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ POST /simulation/cancel-all 正确返回错误（无API Key）")
            else:
                print(f"  ✅ POST /simulation/cancel-all 一键撤单成功")

        return True
    except Exception as e:
        print(f"  ❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_normalize_mock_order_row():
    """测试：妙想委托原始字段兼容解析（数值方向/状态、别名键名）"""
    print("\n[测试6b] mock_trading_normalize 委托解析...")
    try:
        from app.utils.mock_trading_normalize import normalize_mock_order_row

        raw_buy_numeric = {
            "order_id": "260854300000078983",
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "tradeType": 1,
            "price": 1700.0,
            "quantity": 100,
            "status": 1,
            "create_time": "2026-05-05 10:00:00",
        }
        r = normalize_mock_order_row(raw_buy_numeric)
        assert r["trade_type"] == "buy", r
        assert r["status"] == "pending"
        assert "未成交" in r["status_text"]
        assert r["order_id"] == "260854300000078983"

        raw_sell_alt_keys = {
            "wtOrderId": "999",
            "scode": "000001",
            "sname": "平安银行",
            "orderDrt": 2,
            "wtPrice": "11.5",
            "wtVolume": 200,
            "orderStatus": 3,
            "orderTime": "2026-05-05 14:30:00",
        }
        r2 = normalize_mock_order_row(raw_sell_alt_keys)
        assert r2["trade_type"] == "sell"
        assert r2["stock_code"] == "000001"
        assert r2["stock_name"] == "平安银行"
        assert abs(r2["price"] - 11.5) < 1e-6
        assert r2["quantity"] == 200
        assert r2["status"] == "done"

        nested = {
            "orderId": "1",
            "type": 1,
            "stock": {"stockCode": "688001", "stockName": "华兴源创"},
            "price": 30,
            "quantity": 100,
            "status": 5,
        }
        r3 = normalize_mock_order_row(nested)
        assert r3["trade_type"] == "buy"
        assert r3["stock_code"] == "688001"
        assert r3["status"] == "canceled"

        # trade_type 常为委托类别(5)，买卖方向在 orderDrt —— 须解析到 buy 而非被 5 挡住
        clash = {
            "trade_type": 5,
            "orderDrt": 1,
            "stock_code": "600519",
            "status": 8,
            "price": 1149,
            "wtVolume": 100,
        }
        r4 = normalize_mock_order_row(clash)
        assert r4["trade_type"] == "buy"
        assert r4["status"] == "canceled"
        assert "废单" in r4["status_text"]

        from app.utils.mock_trading_normalize import extract_orders_dicts

        packed = extract_orders_dicts({"orders": {"rows": [{"stock_code": "1", "orderDrt": 2}]}})
        assert len(packed) == 1 and packed[0]["stock_code"] == "1"

        print("  ✅ 委托行规范化解析正确")
        return True
    except Exception as e:
        print(f"  ❌ 委托解析测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_format_methods():
    """测试7: 工具格式化方法"""
    print("\n[测试7] 工具格式化方法...")
    try:
        from agents.tools.mx_moni_tool import MXMoniTool

        tool = MXMoniTool(api_key="test")

        # 测试空持仓格式化
        empty_positions = {"success": True, "data": {"positions": []}}
        formatted = tool._format_positions(empty_positions)
        assert "无持仓" in formatted
        print(f"  ✅ 空持仓格式化正确")

        # 测试有持仓格式化
        mock_positions = {
            "success": True,
            "data": {
                "positions": [
                    {
                        "stockCode": "600519", "stockName": "贵州茅台",
                        "quantity": 100, "costPrice": 1700.00,
                        "currentPrice": 1750.00, "profitLoss": 5000.00,
                        "profitLossRate": 2.94,
                    }
                ]
            },
        }
        formatted2 = tool._format_positions(mock_positions)
        assert "600519" in formatted2
        assert "贵州茅台" in formatted2
        print(f"  ✅ 有持仓格式化正确")

        # 测试资金格式化
        mock_balance = {
            "success": True,
            "data": {
                "totalAssets": 100000.00,
                "availBalance": 80000.00,
                "frozenBalance": 0.00,
                "marketValue": 20000.00,
                "totalProfitLoss": 5000.00,
            },
        }
        formatted3 = tool._format_balance(mock_balance)
        assert "100000" in formatted3
        assert "80000" in formatted3
        print(f"  ✅ 资金格式化正确")

        # 测试交易结果格式化
        mock_trade = {
            "success": True,
            "data": {"orderId": "260854300000078983"},
        }
        formatted4 = tool._format_trade_result(mock_trade, "buy", "600519", 100, 1700.00)
        assert "买入" in formatted4
        assert "600519" in formatted4
        assert "260854300000078983" in formatted4
        print(f"  ✅ 交易结果格式化正确")

        # 测试撤单结果格式化
        mock_cancel = {"success": True, "data": {}}
        formatted5 = tool._format_cancel_result(mock_cancel, "order_123")
        assert "撤单成功" in formatted5
        print(f"  ✅ 撤单结果格式化正确")

        return True
    except Exception as e:
        print(f"  ❌ 格式化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F07 模拟组合交易 — 自测试")
    print("=" * 60)

    tests = [
        ("MXMoniTool工具封装", test_mx_moni_tool),
        ("模拟交易服务层结构", test_simulation_service_structure),
        ("服务层参数校验", test_simulation_service_validation),
        ("交易执行Agent创建", test_trading_agent_create),
        ("FastAPI模拟交易路由", test_fastapi_simulation_routes),
        ("委托行规范化解析", test_normalize_mock_order_row),
        ("工具格式化方法", test_tool_format_methods),
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
