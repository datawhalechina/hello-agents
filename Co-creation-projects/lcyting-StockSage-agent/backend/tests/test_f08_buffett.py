"""
F08 巴菲特投资评估 — 自测试代码

验证：
1. buffett_service 服务层框架结构正确
2. 评估报告模板完整性
3. 巴菲特参考文件加载
4. FastAPI路由 /buffett 正常工作
5. 评估上下文构建
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


def test_buffett_framework():
    """测试1: 巴菲特评估框架完整性"""
    print("\n[测试1] 巴菲特评估框架完整性...")
    try:
        from app.services.buffett_service import BUFFETT_FRAMEWORK, BUFFETT_FRAMEWORK_DESC

        # 验证框架各部分
        sections = [
            "quick_filter",
            "moat_analysis",
            "management_assessment",
            "financial_metrics",
            "valuation",
            "risk_analysis",
            "sell_criteria",
        ]
        for section in sections:
            assert section in BUFFETT_FRAMEWORK, f"缺少框架部分: {section}"

        # 验证快速筛选8问
        questions = BUFFETT_FRAMEWORK["quick_filter"]["questions"]
        assert len(questions) == 8, f"应有8问，实际{len(questions)}问"

        # 验证护城河5类型
        moat_types = BUFFETT_FRAMEWORK["moat_analysis"]["types"]
        assert len(moat_types) == 5

        # 验证卖出4条标准
        sell_criteria = BUFFETT_FRAMEWORK["sell_criteria"]["criteria"]
        assert len(sell_criteria) == 4

        # 验证框架描述
        assert len(BUFFETT_FRAMEWORK_DESC) > 100

        print(f"  ✅ 巴菲特框架完整")
        print(f"     {len(sections)}个框架章节 / 8个筛选问题 / 5种护城河 / 4条卖出标准")
        return True
    except Exception as e:
        print(f"  ❌ 框架测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buffett_service():
    """测试2: 巴菲特服务层函数"""
    print("\n[测试2] 巴菲特服务层函数...")
    try:
        from app.services import buffett_service

        # 验证核心函数
        functions = [
            "get_buffett_framework",
            "evaluate_with_buffett",
            "slim_evaluation_context_for_api",
            "prepare_buffett_ai_messages",
            "make_buffett_llm_client",
            "iter_buffett_ai_report_events",
            "generate_buffett_ai_report",
            "_build_buffett_report_template",
            "load_buffett_reference",
        ]
        for name in functions:
            assert hasattr(buffett_service, name), f"缺少函数 {name}"

        # 测试框架获取
        framework_result = buffett_service.get_buffett_framework()
        assert framework_result["success"]
        assert "framework" in framework_result
        assert "quick_filter" in framework_result["framework"]

        # 测试评估上下文构建
        eval_result = buffett_service.evaluate_with_buffett("600519", "贵州茅台")
        assert eval_result["success"]
        assert eval_result["stock_code"] == "600519"
        assert eval_result["stock_name"] == "贵州茅台"
        assert "evaluation_context" in eval_result
        assert "report_template" in eval_result

        # 测试带数据上下文的评估
        data_ctx = {
            "market": {"success": True, "tables": []},
            "financial": {"success": True, "tables": []},
            "profile": {"success": True, "tables": [{"sheet_name": "公司概况", "rows": []}]},
            "sentiment": {"success": True, "total_count": 0},
        }
        eval_result2 = buffett_service.evaluate_with_buffett("000001", "平安银行", data_ctx)
        assert eval_result2["success"]
        assert eval_result2["evaluation_context"]["market_data"] == data_ctx["market"]

        print(f"  ✅ 所有{len(functions)}个核心函数正常")
        print(f"     框架获取 ✅ / 评估构建 ✅ / 数据上下文 ✅")
        return True
    except Exception as e:
        print(f"  ❌ 服务层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_template():
    """测试3: 评估报告模板完整性"""
    print("\n[测试3] 评估报告模板完整性...")
    try:
        from app.services.buffett_service import _build_buffett_report_template

        template = _build_buffett_report_template("600519", "贵州茅台")

        # 验证报告必包含的章节
        required_sections = [
            "结论",
            "能力圈判断",
            "关键假设",
            "快速筛选",
            "企业质量分析",
            "财务快照",
            "估值分析",
            "卖出标准逐条检验",
            "主要风险",
            "监控指标",
            "综合判断",
            "不构成投资建议",
        ]
        for section in required_sections:
            assert section in template, f"报告缺少章节: {section}"

        # 验证8问检查表
        for i in range(1, 9):
            assert f"| {i} |" in template, f"报告缺少第{i}问"

        # 验证卖出4标准
        assert "价格严重高估" in template
        assert "护城河破坏" in template
        assert "诚信问题" in template
        assert "更好的机会" in template

        print(f"  ✅ 报告模板完整 (共{len(template)}字符)")
        print(f"     包含{len(required_sections)}个必填章节 / 8问检查表 / 4条卖出标准")
        return True
    except Exception as e:
        print(f"  ❌ 模板测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reference_loading():
    """测试4: 巴菲特参考文件加载"""
    print("\n[测试4] 巴菲特参考文件加载...")
    try:
        from app.services.buffett_service import load_buffett_reference

        # 测试加载存在的参考文件
        content = load_buffett_reference("03-business-moat")
        if content:
            assert len(content) > 100, f"参考文件内容应>100字符, 实际{len(content)}"
            print(f"  ✅ 成功加载 03-business-moat ({len(content)}字符)")
        else:
            # 文件可能不存在（路径问题），验证返回值为None而非异常
            assert content is None
            print(f"  ⚠️ 参考文件未找到（路径可能不正确），但返回值正确为None")

        # 测试不存在的文件
        content2 = load_buffett_reference("99-nonexistent")
        assert content2 is None
        print(f"  ✅ 不存在文件正确返回None")

        # 测试路径遍历防护
        content3 = load_buffett_reference("../../etc/passwd")
        assert content3 is None
        print(f"  ✅ 路径遍历防护有效")

        return True
    except Exception as e:
        print(f"  ❌ 参考文件加载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_buffett_routes():
    """测试5: FastAPI巴菲特评估路由"""
    print("\n[测试5] FastAPI巴菲特评估路由...")
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
            # 测试 GET /buffett/framework
            response = client.get("/api/v1/buffett/framework")
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "quick_filter" in data["data"]["framework"]
            print(f"  ✅ GET /buffett/framework 返回框架成功")

            # 测试 POST /buffett/evaluate
            response = client.post("/api/v1/buffett/evaluate", json={
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "include_market": False,
                "include_financial": False,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["stock_code"] == "600519"
            assert "report_template" in data["data"]
            assert "结论" in data["data"]["report_template"]
            ctx = data["data"]["evaluation_context"]
            assert "framework" in ctx
            assert "market_snapshot" in ctx and "financial_snapshot" in ctx
            print(f"  ✅ POST /buffett/evaluate 评估成功")

            # POST /buffett/report/generate-ai（无 LLM 时多为 503）
            response = client.post(
                "/api/v1/buffett/report/generate-ai",
                json={"stock_code": "600519", "stock_name": "贵州茅台"},
            )
            assert response.status_code == 200
            gen_body = response.json()
            assert gen_body["code"] in (0, 503)
            if gen_body["code"] == 0:
                assert gen_body["data"].get("report_markdown")
            print(f"  ✅ POST /buffett/report/generate-ai 路由可用")

            response = client.post(
                "/api/v1/buffett/report/generate-ai/stream",
                json={"stock_code": "600519", "stock_name": "贵州茅台"},
            )
            assert response.status_code == 200
            ct = response.headers.get("content-type", "")
            assert "ndjson" in ct or "json" in ct
            head = response.text[:800]
            assert '"type"' in head
            print(f"  ✅ POST /buffett/report/generate-ai/stream 流式路由可用")

            # 测试无效代码（Pydantic min_length校验返回422）
            response = client.post("/api/v1/buffett/evaluate", json={
                "stock_code": "12",
            })
            assert response.status_code == 422, f"短代码应返回422, 实际{response.status_code}"
            print(f"  ✅ 短代码校验返回422 (Pydantic验证)")

            # 测试 GET /buffett/report/template
            response = client.get("/api/v1/buffett/report/template?code=600519&name=贵州茅台")
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "template" in data["data"]
            print(f"  ✅ GET /buffett/report/template 模板生成成功")

            # 测试 GET /buffett/reference/{ref_name}
            response = client.get("/api/v1/buffett/reference/03-business-moat")
            assert response.status_code in (200, 404)  # 文件可能存在也可能不存在
            print(f"  ✅ GET /buffett/reference 路由正常响应")

        return True
    except Exception as e:
        print(f"  ❌ API路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_framework_sections_content():
    """测试6: 框架各节内容完整性"""
    print("\n[测试6] 框架各节内容完整性...")
    try:
        from app.services.buffett_service import BUFFETT_FRAMEWORK

        # 验证关键内容存在
        qf = BUFFETT_FRAMEWORK["quick_filter"]
        assert "规则" in qf or "rule" in qf

        ma = BUFFETT_FRAMEWORK["management_assessment"]
        assert "诚信" in ma["dimensions"][0]

        fm = BUFFETT_FRAMEWORK["financial_metrics"]
        assert "ROIC" in str(fm["metrics"])

        v = BUFFETT_FRAMEWORK["valuation"]
        assert "安全边际" in v["name"] or "margin_of_safety" in v

        sc = BUFFETT_FRAMEWORK["sell_criteria"]
        assert "卖出" in sc["name"]

        print(f"  ✅ 所有框架节内容完整")
        return True
    except Exception as e:
        print(f"  ❌ 框架内容测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  F08 巴菲特投资评估 — 自测试")
    print("=" * 60)

    tests = [
        ("巴菲特评估框架完整性", test_buffett_framework),
        ("巴菲特服务层函数", test_buffett_service),
        ("评估报告模板完整性", test_report_template),
        ("巴菲特参考文件加载", test_reference_loading),
        ("FastAPI巴菲特评估路由", test_fastapi_buffett_routes),
        ("框架各节内容完整性", test_framework_sections_content),
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
