# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 依赖层：与 backend/pyproject.toml [project.dependencies] 保持一致
RUN pip install --no-cache-dir \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.30.0" \
        "langgraph>=0.2.0" \
        "langchain-openai>=0.1.0" \
        "openai>=1.0.0" \
        "akshare>=1.14.0" \
        "yfinance>=0.2.0" \
        "pydantic>=2.0.0" \
        "pydantic-settings>=2.0.0" \
        "pypinyin>=0.50.0" \
        "requests>=2.31.0" \
        "python-dotenv>=1.0.0"

# 代码层
COPY backend /app/backend
# 三个市场的股票列表 CSV（stock_list.py 从项目根读取）
COPY A-stock.csv G-stock.csv U-stock.csv /app/

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fs http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
