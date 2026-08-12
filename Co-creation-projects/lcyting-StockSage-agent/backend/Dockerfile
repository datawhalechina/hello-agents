# =========================================================================
# 智能股票分析助手 — 后端 Dockerfile
# 
# 基于 Python 3.12，运行 FastAPI 应用
# 构建: docker build -t stock-analyzer-backend -f backend/Dockerfile .
# =========================================================================

FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（gcc用于编译BCrypt等扩展）
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制项目文件
COPY backend/ /app/backend/
COPY agents/ /app/agents/
COPY "HelloAgents Optimized/" "/app/HelloAgents Optimized/"
COPY "skills/" "/app/skills/"
COPY .env /app/.env

# 创建数据目录（SQLite数据库存储位置）
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 应用
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
