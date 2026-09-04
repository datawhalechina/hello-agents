"""
FastAPI 服务层 - 把测试能力暴露成 HTTP 接口

让浏览器（前端）能通过网络调用我们的 Agent。
之前的 src/ 代码一行都不用改，直接复用。
"""

import sys
from pathlib import Path

# Windows 中文控制台 GBK 坑
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# 关键：先加载 .env，再 import Agent
load_dotenv()

from src.agents.parser_agent import ParserAgent
from src.agents.generator_agent import GeneratorAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.validator_agent import ValidatorAgent
from src.agents.reporter_agent import ReporterAgent


app = FastAPI(title="智能API测试助手")

# CORS 配置：允许前端跨域调用（简单起见先放开所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求体模型：前端 POST 过来的数据结构
class TestRequest(BaseModel):
    # 保留 openapi_text，兼容原来的前端和外部调用方；两者与 openapi_url 二选一
    openapi_text: str | None = None  # OpenAPI 文档内容（文本）
    openapi_url: str | None = None   # OpenAPI 文档地址（由后端抓取）
    base_url: str                    # 目标 API 基础地址
    # 全局请求头（可选），如 {"Authorization": "Bearer xxx"}，
    # 用于给受保护接口传认证信息，会原样透传给 ExecutorAgent
    headers: dict[str, str] | None = None


def _json_safe(value):
    """把执行内部使用的 multipart 二进制转换成可返回给前端的值。

    文件内容必须以 bytes 传给 requests，但不能把原始 bytes 放进 FastAPI
    响应；PNG 等二进制不是合法 UTF-8，jsonable_encoder 会因此抛异常。
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<binary data: {len(value)} bytes>"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


@app.post("/api/test")
def test_api(req: TestRequest):
    """一键执行完整测试流程

    接收前端传来的 {openapi_text, base_url} 或 {openapi_url, base_url}，
    依次调用 5 个 Agent，返回测试结果。
    """
    try:
        source_text = (req.openapi_text or "").strip()
        source_url = (req.openapi_url or "").strip()
        if bool(source_text) == bool(source_url):
            raise HTTPException(
                status_code=400,
                detail="请在 OpenAPI 文档内容和文档 URL 中二选一",
            )

        # ① 解析文档：文本模式沿用原逻辑，URL 模式复用已有 parse_url
        parser = ParserAgent()
        if source_url:
            endpoints = parser.parse_url(source_url)
        else:
            endpoints = parser.parse_text(source_text)

        # 文档里没有解析出任何接口，直接返回明确错误
        if not endpoints:
            source_hint = "URL" if source_url else "文档内容"
            raise HTTPException(
                status_code=400,
                detail=f"未能从 {source_hint} 解析出任何接口，请检查地址或内容是否正确",
            )

        # ② 生成用例
        generator = GeneratorAgent()
        all_cases = []
        for endpoint in endpoints:
            all_cases.extend(generator.generate(endpoint))

        # ③ 执行测试（把前端传来的认证头一并透传）
        executor = ExecutorAgent()
        execution_results = executor.execute(all_cases, req.base_url, headers=req.headers)

        # ④ 验证结果
        validator = ValidatorAgent()
        validated_results = validator.validate(execution_results)

        # ⑤ 统计汇总
        reporter = ReporterAgent()
        summary = reporter.summarize(validated_results)

        return {
            "summary": summary,
            # 内部结果可能包含 multipart 的 bytes，响应前统一转成 JSON 安全值。
            "results": _json_safe(validated_results),
        }
    except HTTPException:
        raise
    except Exception as e:
        # LLM 调用失败、网络异常等，返回 500 并给出友好提示，避免无信息崩溃
        raise HTTPException(status_code=500, detail=f"测试执行失败：{e}")


# ===== 前端托管 =====
# Vue3 工程每次 `npm run build` 会把打包产物生成到 frontend/dist/
# 只托管 Vue 构建产物，不再回退到旧版单文件页面
DIST_DIR = Path(__file__).resolve().parent / "frontend" / "dist"

if DIST_DIR.exists():
    # 注意：挂载必须放在所有 /api 路由定义【之后】，FastAPI 按注册顺序匹配，
    # 前面的 /api/test 会先命中，静态目录只接管其余请求
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def index():
        """未构建 Vue 前端时返回明确提示"""
        raise HTTPException(
            status_code=503,
            detail="Vue 前端尚未构建，请先执行 cd frontend && npm run build",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
