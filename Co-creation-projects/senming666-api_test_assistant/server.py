"""
FastAPI 服务层 - 把测试能力暴露成 HTTP 接口

让浏览器（前端）能通过网络调用我们的 Agent。
之前的 src/ 代码一行都不用改，直接复用。
"""

import sys

# Windows 中文控制台 GBK 坑
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    openapi_text: str   # OpenAPI 文档内容（文本）
    base_url: str       # 目标 API 基础地址


@app.post("/api/test")
def test_api(req: TestRequest):
    """一键执行完整测试流程

    接收前端传来的 {openapi_text, base_url}，
    依次调用 5 个 Agent，返回测试结果。
    """
    # ① 解析文档（用 parse_text，因为前端传的是文本）
    parser = ParserAgent()
    endpoints = parser.parse_text(req.openapi_text)

    # ② 生成用例
    generator = GeneratorAgent()
    all_cases = []
    for endpoint in endpoints:
        all_cases.extend(generator.generate(endpoint))

    # ③ 执行测试
    executor = ExecutorAgent()
    execution_results = executor.execute(all_cases, req.base_url)

    # ④ 验证结果
    validator = ValidatorAgent()
    validated_results = validator.validate(execution_results)

    # ⑤ 统计汇总
    reporter = ReporterAgent()
    summary = reporter.summarize(validated_results)

    return {
        "summary": summary,
        "results": validated_results,
    }


@app.get("/")
def index():
    """返回前端页面"""
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
