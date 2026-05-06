"""
F15 用户偏好存储 — 自测试代码

验证：
1. 数据库初始化与建表
2. 偏好数据模型CRUD
3. 偏好服务层正确性
4. FastAPI路由正常工作
5. 偏好上下文生成（Agent注入用）
6. 智能体层偏好注入模块
"""

import sys
import os
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
AGENTS_DIR = PROJECT_ROOT / "agents"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(AGENTS_DIR))


async def test_database_init():
    """测试1：数据库初始化与表创建"""
    print("\n[测试1] 数据库初始化与表创建...")
    try:
        # 必须先导入模型，让SQLAlchemy Base.metadata感知到表定义
        from app.models.preference import UserPreference  # noqa: F401
        from app.models.database import init_db, engine, Base, async_session_factory

        # 初始化数据库（创建表）
        await init_db()

        # 验证表存在
        async with engine.begin() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: list(sync_conn.dialect.get_table_names(sync_conn))
            )
        print(f"  ✅ 数据库表: {', '.join(tables)}")
        assert "user_preferences" in tables, "缺少 user_preferences 表"
        print("  ✅ 数据库初始化成功")
        return True
    except Exception as e:
        print(f"  ❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_preference_crud():
    """测试2：偏好CRUD操作"""
    print("\n[测试2] 偏好CRUD操作...")
    try:
        from app.models.database import async_session_factory
        from app.services.preference_service import (
            get_preference,
            get_or_create_preference,
            update_preference,
        )

        async with async_session_factory() as db:
            # 获取默认偏好（此时应该返回默认值）
            pref = await get_preference(db, "test_user")
            assert pref["risk_tolerance"] == "moderate", "默认风险承受度应为moderate"
            assert pref["investment_style"] == "blend", "默认投资风格应为blend"
            print("  ✅ 默认偏好读取正确")

            # 首次读取：自动创建记录
            orm_pref = await get_or_create_preference(db, "test_user")
            assert orm_pref.user_id == "test_user"
            print("  ✅ 偏好记录自动创建")

            # 更新偏好
            updated = await update_preference(db, "test_user", {
                "risk_tolerance": "conservative",
                "investment_style": "value",
                "preferred_sectors": ["消费", "医药"],
                "target_return_rate": 8.0,
                "max_position_ratio": 20.0,
            })
            assert updated["risk_tolerance"] == "conservative", "风险承受度未更新"
            assert updated["investment_style"] == "value", "投资风格未更新"
            assert updated["target_return_rate"] == 8.0, "目标收益率未更新"
            assert updated["max_position_ratio"] == 20.0, "最大仓位未更新"
            # preferred_sectors作为JSON字段，检查内容
            sectors = updated["preferred_sectors"]
            if isinstance(sectors, str):
                import json
                sectors = json.loads(sectors)
            assert "消费" in sectors, "偏好行业未更新"
            print("  ✅ 偏好更新成功")

            # 部分更新：只更新一个字段
            updated2 = await update_preference(db, "test_user", {
                "language": "en",
                "theme": "dark",
            })
            assert updated2["language"] == "en"
            assert updated2["theme"] == "dark"
            # 其他字段应保持不变
            assert updated2["risk_tolerance"] == "conservative", "部分更新不应改变其他字段"
            print("  ✅ 部分更新成功")

            # 验证数据库持久化（重新读取）
            pref_again = await get_preference(db, "test_user")
            assert pref_again["risk_tolerance"] == "conservative"
            assert pref_again["language"] == "en"
            print("  ✅ 数据持久化验证通过")

        return True
    except Exception as e:
        print(f"  ❌ 偏好CRUD测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_preference_context():
    """测试3：偏好上下文生成（Agent注入用）"""
    print("\n[测试3] 偏好上下文生成...")
    try:
        from app.models.database import async_session_factory
        from app.services.preference_service import get_preference_context, get_profile_summary

        async with async_session_factory() as db:
            # 测试上下文生成
            context = await get_preference_context(db, "test_user")
            assert "保守型" in context, "应包含保守型描述"
            assert "消费" in context, "应包含偏好行业"
            print(f"  ✅ 偏好上下文生成成功:")
            print(f"     {context.split(chr(10))[0]}")  # 第一行

            # 测试画像摘要
            profile = await get_profile_summary(db, "test_user")
            assert profile["risk_label"] == "保守型"
            assert profile["style_label"] == "价值投资"
            print(f"  ✅ 画像摘要生成成功: {profile}")

        return True
    except Exception as e:
        print(f"  ❌ 上下文生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fastapi_routes():
    """测试4：FastAPI偏好路由"""
    print("\n[测试4] FastAPI偏好路由...")
    try:
        # 确保模型已导入
        from app.models.preference import UserPreference  # noqa: F401
        from app.models.database import init_db as _init_db_route
        await _init_db_route()

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            # 测试GET /preferences/
            response = client.get("/api/v1/preferences/?user_id=test_api_user")
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "risk_tolerance" in data["data"]
            print(f"  ✅ GET /preferences/ 成功")

            # 测试PUT /preferences/ — 更新偏好
            response = client.put(
                "/api/v1/preferences/?user_id=test_api_user",
                json={
                    "risk_tolerance": "aggressive",
                    "investment_style": "growth",
                    "target_return_rate": 20.0,
                    "preferred_sectors": ["新能源", "半导体"],
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["risk_tolerance"] == "aggressive"
            print(f"  ✅ PUT /preferences/ 更新成功")

            # 验证更新持久化
            response = client.get("/api/v1/preferences/?user_id=test_api_user")
            data = response.json()
            assert data["data"]["risk_tolerance"] == "aggressive"
            print(f"  ✅ 偏好更新持久化验证通过")

            # 测试GET /preferences/profile
            response = client.get("/api/v1/preferences/profile?user_id=test_api_user")
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "risk_label" in data["data"]
            print(f"  ✅ GET /preferences/profile 成功: {data['data']}")

            # 测试空更新（不传任何字段）
            response = client.put(
                "/api/v1/preferences/?user_id=test_api_user",
                json={},
            )
            assert response.status_code == 200  # 路由正常响应
            data = response.json()
            assert data["code"] == 400, f"业务错误码应为400，实际{data['code']}"
            print(f"  ✅ 空更新正确返回400错误码")

            # 测试无效枚举值
            response = client.put(
                "/api/v1/preferences/?user_id=test_api_user",
                json={"risk_tolerance": "invalid_value"},
            )
            # Pydantic会拒绝无效枚举值，返回422
            assert response.status_code == 422, f"应为422, 实际{response.status_code}"
            print(f"  ✅ 无效枚举值正确拒绝")

        return True
    except Exception as e:
        print(f"  ❌ FastAPI路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_injector():
    """测试5：智能体层偏好注入"""
    print("\n[测试5] 智能体层偏好注入...")
    try:
        from agents.preference_injector import inject_preferences, get_risk_profile

        # 测试注入（使用之前创建的test_user）
        context = await inject_preferences("test_user")
        assert "用户投资偏好" in context, "应包含标题"
        assert "保守型" in context, "应包含风险描述"
        print(f"  ✅ 偏好注入成功:")
        print(f"     {context}")

        # 测试获取风险画像
        profile = await get_risk_profile("test_user")
        assert isinstance(profile, dict), "应返回字典"
        assert "risk_tolerance" in profile
        print(f"  ✅ 风险画像获取成功: risk_tolerance={profile['risk_tolerance']}")

        return True
    except Exception as e:
        print(f"  ❌ Agent注入测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_default_preference():
    """测试6：默认偏好（无用户记录时）"""
    print("\n[测试6] 默认偏好...")
    try:
        from app.models.database import async_session_factory
        from app.services.preference_service import get_preference, DEFAULT_PREFERENCE

        async with async_session_factory() as db:
            pref = await get_preference(db, "nonexistent_user")
            assert pref["risk_tolerance"] == "moderate"
            assert pref["investment_style"] == "blend"
            assert pref["user_id"] == "nonexistent_user"
            print(f"  ✅ 不存在用户返回默认偏好")
            print(f"     默认风险: {pref['risk_tolerance']}, 默认风格: {pref['investment_style']}")

        return True
    except Exception as e:
        print(f"  ❌ 默认偏好测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F15 用户偏好存储 — 自测试")
    print("=" * 60)

    # 清理之前的测试数据库
    import os
    db_path = PROJECT_ROOT / "data" / "stock_analyzer.db"
    if db_path.exists():
        db_path.unlink()

    tests = [
        ("数据库初始化与表创建", test_database_init),
        ("偏好CRUD操作", test_preference_crud),
        ("偏好上下文生成", test_preference_context),
        ("FastAPI偏好路由", test_fastapi_routes),
        ("智能体层偏好注入", test_agent_injector),
        ("默认偏好", test_default_preference),
    ]

    results = {}
    for name, test_func in tests:
        results[name] = await test_func()

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

    # 清理测试数据库
    from app.models.database import engine
    await engine.dispose()
    import asyncio as _asyncio
    await _asyncio.sleep(0.5)  # 等待引擎完全释放
    if db_path.exists():
        try:
            db_path.unlink()
            print(f"\n  已清理测试数据库")
        except PermissionError:
            print(f"\n  ⚠️ 数据库文件清理失败（可能被占用，不影响测试结果）")

    return passed == total


if __name__ == "__main__":
    import asyncio
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
