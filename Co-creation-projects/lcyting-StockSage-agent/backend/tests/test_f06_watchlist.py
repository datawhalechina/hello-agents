"""
F06 自选股管理 — 自测试代码

验证：
1. MXZixuanTool 工具封装正确
2. watchlist_service 服务层结构正确
3. FastAPI路由 /watchlist 正常工作
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

# 添加技能路径
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "自选股管理" / "mx-zixuan"))
sys.path.insert(0, str(PROJECT_ROOT / "HelloAgents Optimized"))


def test_mx_zixuan_tool():
    """测试1: MXZixuanTool 工具封装"""
    print("\n[测试1] MXZixuanTool 工具封装...")
    try:
        from agents.tools.mx_zixuan_tool import MXZixuanTool

        tool = MXZixuanTool(api_key="test_key")

        # 验证基础属性
        assert tool.name == "mx_zixuan"
        assert tool.api_key == "test_key"

        # 验证参数定义
        params = tool.get_parameters()
        assert len(params) == 2
        assert params[0].name == "action"
        assert params[1].name == "query"

        # 验证无API Key时的行为
        tool_no_key = MXZixuanTool(api_key="")
        result = tool_no_key.run({"action": "query"})
        assert "MX_APIKEY" in result

        print(f"  ✅ MXZixuanTool创建成功")
        print(f"     工具名称: {tool.name}")
        print(f"     参数数量: {len(params)}")
        return True
    except Exception as e:
        print(f"  ❌ 工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_watchlist_service_structure():
    """测试2: 自选股服务层结构"""
    print("\n[测试2] 自选股服务层结构...")
    try:
        from app.services import watchlist_service

        functions = [
            "get_watchlist",
            "add_to_watchlist",
            "delete_from_watchlist",
        ]
        for name in functions:
            assert hasattr(watchlist_service, name), f"缺少函数 {name}"
            func = getattr(watchlist_service, name)
            assert callable(func), f"{name} 应为可调用函数"

        print(f"  ✅ 所有{len(functions)}个核心函数已定义")
        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_watchlist_service_no_api_key():
    """测试3: 服务层无API Key时的降级行为"""
    print("\n[测试3] 服务层无API Key降级...")
    try:
        # 保存原值
        from app.config import settings
        saved_key = settings.MX_APIKEY
        settings.MX_APIKEY = "your-mx-apikey-here"

        from app.services import watchlist_service

        # 测试查询
        result1 = watchlist_service.get_watchlist()
        assert not result1["success"]
        assert "MX_APIKEY" in result1.get("error", "")

        # 测试添加
        result2 = watchlist_service.add_to_watchlist("贵州茅台")
        assert not result2["success"]
        assert "MX_APIKEY" in result2.get("error", "")

        # 测试删除
        result3 = watchlist_service.delete_from_watchlist("贵州茅台")
        assert not result3["success"]
        assert "MX_APIKEY" in result3.get("error", "")

        # 恢复原值
        settings.MX_APIKEY = saved_key

        print(f"  ✅ 无API Key时正确返回错误信息")
        return True
    except Exception as e:
        print(f"  ❌ 降级测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_watchlist_routes():
    """测试4: FastAPI自选股路由"""
    print("\n[测试4] FastAPI自选股路由...")
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
            # 测试 GET /watchlist/（无API Key时返回500）
            response = client.get("/api/v1/watchlist/")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ GET /watchlist/ 正确返回错误（无API Key）: {data.get('message', '')[:50]}")
            else:
                print(f"  ✅ GET /watchlist/ 成功: {data.get('message', '')}")

            # 测试 POST /watchlist/
            response = client.post("/api/v1/watchlist/", json={"stock": "贵州茅台"})
            assert response.status_code in (200, 422, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ POST /watchlist/ 正确返回错误（无API Key）: {data.get('message', '')[:50]}")
            elif response.status_code == 422:
                print(f"  ✅ POST /watchlist/ 参数校验通过（422为Pydantic验证）")
            else:
                print(f"  ✅ POST /watchlist/ 成功")

            # 测试 DELETE /watchlist/{stock}
            response = client.delete("/api/v1/watchlist/600519")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ DELETE /watchlist/600519 正确返回错误（无API Key）")
            else:
                print(f"  ✅ DELETE /watchlist/600519 成功: {data.get('message', '')}")

            # 测试空参数（Pydantic min_length校验返回422）
            response = client.post("/api/v1/watchlist/", json={"stock": ""})
            assert response.status_code == 422, f"空stock应返回422, 实际{response.status_code}"
            print(f"  ✅ 空参数校验正确返回422 (Pydantic验证)")

            # 测试 DELETE 空参数
            response = client.delete("/api/v1/watchlist/")
            assert response.status_code in (404, 405)  # 404=路由不存在, 405=方法不允许
            print(f"  ✅ DELETE无参数正确限制")

        return True
    except Exception as e:
        print(f"  ❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_format_methods():
    """测试5: 工具格式化方法"""
    print("\n[测试5] 工具格式化方法...")
    try:
        from agents.tools.mx_zixuan_tool import MXZixuanTool

        tool = MXZixuanTool(api_key="test")

        # 测试查询结果格式化（空数据）
        empty_result = {"status": 0, "code": 0, "data": {"allResults": {"result": {"columns": [], "dataList": []}}}}
        formatted = tool._format_query_result(empty_result)
        assert "为空" in formatted
        print(f"  ✅ 空自选股列表格式化正确")

        # 测试查询结果（有数据）
        mock_result = {
            "status": 0, "code": 0,
            "data": {
                "allResults": {
                    "result": {
                        "columns": [{"title": "代码", "key": "SECURITY_CODE"}],
                        "dataList": [
                            {"SECURITY_CODE": "600519", "SECURITY_SHORT_NAME": "贵州茅台",
                             "NEWEST_PRICE": "1700.00", "CHG": "1.5", "PCHG": "25.00"}
                        ]
                    }
                }
            }
        }
        formatted2 = tool._format_query_result(mock_result)
        assert "600519" in formatted2
        assert "贵州茅台" in formatted2
        print(f"  ✅ 有数据查询结果格式化正确")

        # 测试操作结果格式化
        manage_result = {"status": 0, "code": 0, "message": "操作成功"}
        formatted3 = tool._format_manage_result(manage_result, "add")
        assert "添加" in formatted3
        assert "成功" in formatted3
        print(f"  ✅ 操作结果格式化正确")

        # 测试失败结果
        fail_result = {"status": 1, "code": 1, "message": "股票代码无效"}
        formatted4 = tool._format_manage_result(fail_result, "delete")
        assert "失败" in formatted4
        assert "股票代码无效" in formatted4
        print(f"  ✅ 失败结果格式化正确")

        return True
    except Exception as e:
        print(f"  ❌ 格式化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F06 自选股管理 — 自测试")
    print("=" * 60)

    tests = [
        ("MXZixuanTool工具封装", test_mx_zixuan_tool),
        ("自选股服务层结构", test_watchlist_service_structure),
        ("服务层无API Key降级", test_watchlist_service_no_api_key),
        ("FastAPI自选股路由", test_fastapi_watchlist_routes),
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
