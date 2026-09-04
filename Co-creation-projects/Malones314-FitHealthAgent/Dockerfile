# FitHealthAgent 运行镜像
#
# DATA-10：原来的写法有两个问题。
#   1. `FROM fit_health_agent:dev` —— 镜像以**自己的产物**为基础镜像，全新克隆
#      根本构建不起来（那个 tag 还不存在）。
#   2. `COPY . .` 会把 `data/` 一起打进镜像层，个人健康数据被固化进镜像；
#      同时容器里没有任何数据卷，不挂源码跑镜像时所有数据都写在可写层，
#      **容器重建即全量丢失**。
# 现在改为标准 python 基础镜像 + `.dockerignore` 排除 `data/`，数据目录由
# `FITHEALTH_DATA_DIR` 指定，并在 docker-compose.yml 里 bind-mount 出来。
#
# 关于 hello-agents：`hello-agents==1.0.0` 不在公共 PyPI 上，三种给法——
#   * 把 wheel 放进 `vendor/`（`--find-links` 会优先在那里找）；
#   * 构建时传私有索引：`docker compose build --build-arg PIP_EXTRA_INDEX_URL=...`；
#   * 把 BASE_IMAGE 指向一个已经预装好它的镜像。

# 需要 Python 3.11+：plan_workflow.py 用了 StrEnum（ARCH-05）
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

# 依赖单独成层：只改业务代码时不必重装依赖。
# vendor/ 保存不在公共 PyPI 上的 HelloAgents wheel。
COPY requirements.lock ./
COPY vendor/ /tmp/vendor/
RUN pip install --require-hashes --find-links=/tmp/vendor -r requirements.lock \
    && rm -rf /tmp/vendor

# 业务代码。data/ 由 .dockerignore 排除，不会进镜像。
COPY . .

# 先建好挂载点，避免首次启动时各 store 并发 mkdir
RUN mkdir -p /app/data/health-imports /app/data/hr_streams

EXPOSE 9999

# 用标准库探活，不额外装 curl。/health/storage-status 会顺带报告
# health.db 与记忆库是否处于降级状态（DATA-08 / DATA-09）。
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9999/health/storage-status', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999"]
