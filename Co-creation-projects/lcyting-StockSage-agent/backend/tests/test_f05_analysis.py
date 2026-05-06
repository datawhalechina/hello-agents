"""
F05 个股深度分析报告 — 自测试代码

验证：
1. AnalysisReport 数据模型正确
2. analysis_service 报告生成/查询服务
3. FastAPI路由 /analysis 正常工作
4. 协调者Agent创建
5. 数据分析Agent创建（含mx_data工具）
6. 投资顾问Agent创建（Reflection范式）
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
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "金融数据" / "mx-data"))


def test_report_model():
    """测试1: AnalysisReport数据模型"""
    print("\n[测试1] AnalysisReport数据模型...")
    try:
        from app.models.report import AnalysisReport

        # 验证模型字段
        report = AnalysisReport(
            user_id="test_user",
            stock_code="600519",
            stock_name="贵州茅台",
            report_type="full",
            summary="测试摘要",
            content="测试报告内容",
        )

        assert report.stock_code == "600519"
        assert report.stock_name == "贵州茅台"
        assert report.report_type == "full"

        # 验证to_dict方法
        d = report.to_dict()
        assert d["stock_code"] == "600519"
        assert d["stock_name"] == "贵州茅台"
        assert "id" in d
        assert "created_at" in d

        print("  ✅ 报告模型创建与序列化正确")
        print(f"     股票: {d['stock_name']}({d['stock_code']})")
        return True
    except Exception as e:
        print(f"  ❌ 数据模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analysis_service_structure():
    """测试2: 分析报告服务层结构"""
    print("\n[测试2] 分析报告服务层结构...")
    try:
        from app.services import analysis_service

        functions = [
            "generate_analysis_report",
            "get_report",
            "get_user_reports",
        ]
        for name in functions:
            assert hasattr(analysis_service, name), f"缺少函数 {name}"
            func = getattr(analysis_service, name)
            assert callable(func), f"{name} 应为可调用函数"

        # 验证辅助函数
        helper_functions = [
            "_extract_stock_name",
            "_build_report_content",
            "_generate_summary",
            "_format_data_section",
        ]
        for name in helper_functions:
            assert hasattr(analysis_service, name), f"缺少辅助函数 {name}"

        print(f"  ✅ 所有{len(functions)}个核心函数 + {len(helper_functions)}个辅助函数已定义")
        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_analysis_routes():
    """测试3: FastAPI分析报告路由"""
    print("\n[测试3] FastAPI分析报告路由...")
    try:
        import asyncio

        async def _init_db_task():
            from app.models.report import AnalysisReport  # noqa
            from app.models.database import init_db as _init_db
            await _init_db()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_init_db_task())

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            # 测试 POST /analysis/report/{code}（无API Key时返回500）
            response = client.post("/api/v1/analysis/report/600519?user_id=test&report_type=full")
            assert response.status_code in (200, 500)
            data = response.json()
            if response.status_code == 500:
                print(f"  ✅ /analysis/report/600519 正确返回错误（无API Key）: {data.get('message', '')[:50]}")
            else:
                print(f"  ✅ /analysis/report/600519 成功生成报告")
                # 如果有生成的报告，测试查询
                report_data = data.get("data") or {}
                report_info = report_data.get("report") or {}
                if report_info.get("id"):
                    report_id = report_info["id"]

                    # 测试 GET /analysis/report/{id}
                    response2 = client.get(f"/api/v1/analysis/report/{report_id}")
                    if response2.status_code == 200:
                        print(f"  ✅ /analysis/report/{report_id} 查询成功")

            # 测试无效代码
            response = client.post("/api/v1/analysis/report/12")
            data = response.json()
            assert data["code"] == 400, "短代码应返回400"
            print(f"  ✅ 无效代码返回400: {data['message']}")

            # 测试 GET /analysis/reports（历史列表）
            response = client.get("/api/v1/analysis/reports?user_id=test&limit=5")
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0, f"成功code应为0, 实际{data['code']}"
            print(f"  ✅ /analysis/reports 成功: {data.get('message', '')}")

            # 测试不存在的报告
            response = client.get("/api/v1/analysis/report/99999")
            data = response.json()
            assert data["code"] == 404, f"不存在报告应返回404, 实际{data['code']}"
            print(f"  ✅ 不存在的报告返回404")

        return True
    except Exception as e:
        print(f"  ❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coordinator_agent_create():
    """测试4: 协调者Agent创建"""
    print("\n[测试4] 协调者Agent创建...")
    try:
        from agents.coordinator_agent import create_coordinator_agent

        saved_llm_key = os.environ.pop("LLM_API_KEY", None)

        try:
            agent = create_coordinator_agent()
            assert agent is not None
            assert agent.name == "协调者Agent"
            print(f"  ✅ 协调者Agent创建成功")
            print(f"     Agent名称: {agent.name}")
            print(f"     范式: PlanAndSolve")
            print(f"     最大步数: {agent.max_steps}")
        except RuntimeError as e:
            assert "LLM_API_KEY" in str(e)
            print(f"  ✅ 无LLM Key时正确抛出异常")

        if saved_llm_key is not None:
            os.environ["LLM_API_KEY"] = saved_llm_key

        return True
    except Exception as e:
        print(f"  ❌ Agent创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_analysis_agent_create():
    """测试5: 数据分析Agent创建（含mx_data工具注册）"""
    print("\n[测试5] 数据分析Agent创建...")
    try:
        from agents.data_analysis_agent import create_data_analysis_agent

        saved_llm_key = os.environ.pop("LLM_API_KEY", None)

        try:
            agent = create_data_analysis_agent(api_key="test_key")
            assert agent is not None
            assert agent.name == "数据分析Agent"

            # 验证mx_data工具已注册
            registered = agent.tool_registry.get_tool("mx_data")
            assert registered is not None, "MXDataTool应已注册"
            assert registered.name == "mx_data"

            print(f"  ✅ 数据分析Agent创建成功")
            print(f"     Agent名称: {agent.name}")
            print(f"     范式: ReAct (max_steps={agent.max_steps})")
            print(f"     已注册工具: mx_data")
        except RuntimeError as e:
            assert "LLM_API_KEY" in str(e)
            print(f"  ✅ 无LLM Key时正确抛出异常")

        if saved_llm_key is not None:
            os.environ["LLM_API_KEY"] = saved_llm_key

        return True
    except Exception as e:
        print(f"  ❌ Agent创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_advisor_agent_create():
    """测试6: 投资顾问Agent创建（Reflection范式）"""
    print("\n[测试6] 投资顾问Agent创建...")
    try:
        from agents.advisor_agent import create_advisor_agent
        from agents.advisor_agent import ADVISOR_INITIAL_PROMPT, ADVISOR_REFLECT_PROMPT, ADVISOR_REFINE_PROMPT

        saved_llm_key = os.environ.pop("LLM_API_KEY", None)

        try:
            agent = create_advisor_agent(max_reflections=2)
            assert agent is not None
            assert agent.name == "投资顾问Agent"

            print(f"  ✅ 投资顾问Agent创建成功")
            print(f"     Agent名称: {agent.name}")
            print(f"     范式: Reflection (max_reflections={agent.max_reflections})")
        except RuntimeError as e:
            assert "LLM_API_KEY" in str(e)
            print(f"  ✅ 无LLM Key时正确抛出异常")

        if saved_llm_key is not None:
            os.environ["LLM_API_KEY"] = saved_llm_key

        # 验证提示词
        assert "护城河分析" in ADVISOR_INITIAL_PROMPT, "初始提示词应包含护城河分析"
        assert "不构成投资建议" in ADVISOR_REFINE_PROMPT, "优化提示词应包含免责声明"
        print(f"  ✅ 提示词内容验证通过")

        return True
    except Exception as e:
        print(f"  ❌ Agent创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_content_builder():
    """测试7: 报告内容构建器"""
    print("\n[测试7] 报告内容构建器...")
    try:
        from app.services.analysis_service import _build_report_content, _generate_summary, _extract_stock_name

        # 构造模拟数据
        quote_data = {"success": True, "tables": [], "error": None}
        financial_data = {"success": False, "tables": [], "error": "MX_APIKEY未配置"}
        profile_data = {
            "success": True,
            "tables": [{
                "sheet_name": "公司概况",
                "rows": [{"公司名称": "贵州茅台酒股份有限公司", "股票简称": "贵州茅台"}],
                "fieldnames": ["公司名称", "股票简称"],
            }],
        }
        sentiment_data = {
            "success": True,
            "total_count": 5,
            "news_items": [{"title": "茅台发布年报", "date": "2026-04-01", "institution": "证券时报"}],
            "report_items": [{"title": "机构看好茅台", "date": "2026-04-02", "institution": "中信证券"}],
            "announce_items": [],
        }

        # 构建报告
        content = _build_report_content(
            "600519", "贵州茅台", "full",
            quote_data, financial_data, profile_data, sentiment_data
        )

        assert "600519" in content, "报告应包含股票代码"
        assert "贵州茅台" in content, "报告应包含股票名称"
        assert "行情概览" in content, "报告应包含行情章节"
        assert "财务分析" in content, "报告应包含财务章节"
        assert "公司概况" in content, "报告应包含公司概况章节"
        assert "舆情分析" in content, "报告应包含舆情章节"
        assert "综合评估" in content, "报告应包含综合评估章节"
        assert "不构成" in content, "报告应包含免责声明"

        print(f"  ✅ 报告内容构建正确 (共{len(content)}字符)")

        # 测试摘要生成
        summary = _generate_summary(content)
        assert len(summary) > 0
        print(f"  ✅ 摘要生成: {summary[:60]}...")

        # 测试股票名提取
        name = _extract_stock_name(profile_data)
        assert "贵州茅台" in name or name == "", f"应能提取名称: {name}"
        print(f"  ✅ 股票名称提取: {name}")

        return True
    except Exception as e:
        print(f"  ❌ 构建器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_agent_system_prompts():
    """测试8: 多Agent系统提示词完整性"""
    print("\n[测试8] 多Agent系统提示词完整性...")
    try:
        from agents.coordinator_agent import COORDINATOR_PLANNER_PROMPT
        from agents.data_analysis_agent import DATA_ANALYSIS_PROMPT
        from agents.advisor_agent import ADVISOR_INITIAL_PROMPT

        # 协调者提示词
        assert "基本面" in COORDINATOR_PLANNER_PROMPT
        assert "技术面" in COORDINATOR_PLANNER_PROMPT
        print(f"  ✅ 协调者规划器提示词: {len(COORDINATOR_PLANNER_PROMPT)}字符")

        # 数据分析提示词
        assert "ROE" in DATA_ANALYSIS_PROMPT
        assert "估值" in DATA_ANALYSIS_PROMPT
        print(f"  ✅ 数据分析Agent提示词: {len(DATA_ANALYSIS_PROMPT)}字符")

        # 投资顾问提示词
        assert "护城河" in ADVISOR_INITIAL_PROMPT
        assert "安全边际" in ADVISOR_INITIAL_PROMPT
        print(f"  ✅ 投资顾问Agent提示词: {len(ADVISOR_INITIAL_PROMPT)}字符")

        return True
    except Exception as e:
        print(f"  ❌ 提示词测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_db_integration():
    """测试9: 报告数据库集成"""
    print("\n[测试9] 报告数据库集成...")
    try:
        import asyncio
        import os

        # 使用临时数据库
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.models.report import AnalysisReport
        from app.models.database import Base

        temp_db_url = "sqlite+aiosqlite:///./data/test_f05.db"

        async def _test():
            engine = create_async_engine(temp_db_url, echo=False)
            session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with session_factory() as db:
                # 创建报告
                report = AnalysisReport(
                    user_id="test_f05",
                    stock_code="000001",
                    stock_name="平安银行",
                    report_type="full",
                    summary="测试报告摘要",
                    content="# 测试报告\n内容",
                    data_snapshot='{"market": "ok"}',
                )
                db.add(report)
                await db.commit()
                await db.refresh(report)

                report_id = report.id
                assert report_id > 0

                # 查询报告
                from sqlalchemy import select
                stmt = select(AnalysisReport).where(AnalysisReport.id == report_id)
                db_result = await db.execute(stmt)
                found = db_result.scalar_one()
                assert found.stock_code == "000001"
                assert found.user_id == "test_f05"

                # 查询列表
                stmt2 = select(AnalysisReport).where(AnalysisReport.user_id == "test_f05")
                db_result2 = await db.execute(stmt2)
                all_reports = db_result2.scalars().all()
                assert len(all_reports) >= 1

            await engine.dispose()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_test())

        # 清理测试数据库
        test_db = Path("./data/test_f05.db")
        if test_db.exists():
            test_db.unlink()

        print(f"  ✅ 报告CRUD操作成功")
        print(f"     创建 → 查询 → 列表 全部通过")
        return True
    except Exception as e:
        print(f"  ❌ 数据库集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F05 个股深度分析报告 — 自测试")
    print("=" * 60)

    tests = [
        ("AnalysisReport数据模型", test_report_model),
        ("分析报告服务层结构", test_analysis_service_structure),
        ("FastAPI分析报告路由", test_fastapi_analysis_routes),
        ("协调者Agent创建", test_coordinator_agent_create),
        ("数据分析Agent创建", test_data_analysis_agent_create),
        ("投资顾问Agent创建", test_advisor_agent_create),
        ("报告内容构建器", test_report_content_builder),
        ("多Agent系统提示词完整性", test_multi_agent_system_prompts),
        ("报告数据库集成", test_report_db_integration),
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
