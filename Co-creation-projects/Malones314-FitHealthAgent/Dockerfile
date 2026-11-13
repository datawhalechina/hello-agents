# FitHealthAgent 运行镜像
# 需要 Python 3.11+（项目使用 StrEnum）。
ARG BASE_IMAGE=python:3.12-bookworm
FROM ${BASE_IMAGE}

ARG PIP_EXTRA_INDEX_URL=""

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai \
    FITHEALTH_DATA_DIR=/app/data

WORKDIR /app

COPY requirements.txt requirements.lock ./
RUN pip install --require-hashes -r requirements.lock

# 业务代码。data/ 由 .dockerignore 排除，不会进镜像。
COPY . .

# 先建好挂载点，避免首次启动时各 store 并发 mkdir
RUN mkdir -p /app/data/health-imports /app/data/hr_streams

EXPOSE 9999

# 用标准库探活，不额外安装 curl。
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9999/health/storage-status', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999"]
