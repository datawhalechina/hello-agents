# 1. 选用 FastAPI 作为后端框架

日期: 2026-03-09

## 状态

已采纳

## 背景

我们需要构建一个高性能、易于维护且能良好支持 AI/LLM 生态的后端服务。备选方案包括 Django (Python), Flask (Python), Express/NestJS (Node.js), Gin (Go)。

## 决策

选择 **FastAPI** (Python)。

## 理由

1.  **原生异步支持 (AsyncIO)**: 多智能体系统涉及大量 I/O 密集型任务（如调用 LLM API、WebSocket 推送），FastAPI 的异步特性通过 `async/await` 能显著提高并发处理能力。
2.  **AI 生态亲和力**: Python 是 AI/ML 领域的首选语言。使用 Python 作为后端可以直接集成 HelloAgents、StepFun 与 MCP 工具，无需跨语言调用。
3.  **开发效率与类型安全**: 基于 Pydantic 的类型提示提供了自动的数据验证和文档生成 (Swagger UI)，大幅降低了前后端联调成本。
4.  **性能**: 在 Python web 框架中，FastAPI 的性能仅次于 Starlette，足以满足本系统的实时性需求。

## 后果

- 需要团队熟悉 Python 的异步编程模式。
- 相比 Go/Java，Python 的 CPU 密集型计算能力较弱，但本系统主要是 I/O 密集型，影响有限。
