# 生产部署与验收

本项目的线上拓扑为：Nginx 前端、FastAPI、Celery Worker、PostgreSQL、Redis。
PostgreSQL保存任务与报告，Redis DB 0承担队列和进度事件，Redis DB 1承担共享 LLM 缓存。

## 1. 必填配置

复制根目录 `.env.example` 为 `.env`，至少修改以下项目：

```dotenv
POSTGRES_PASSWORD=使用强随机密码
LLM_API_BASE=https://你的模型服务/v1
LLM_API_KEY=你的密钥
LLM_MODEL=你的模型名
PUBMED_EMAIL=你的有效邮箱
CORS_ORIGINS=https://research.example.com
TRUSTED_HOSTS=research.example.com
```

如果数据库密码包含 `@`、`:`、`/` 等 URL 特殊字符，请另外提供经过 URL 编码的
`POSTGRES_DATABASE_URL`。生产配置存在以下情况时，后端会拒绝启动：开启 Debug、
使用 SQLite、沿用默认数据库密码、CORS 或可信主机使用通配符。

## 2. 启动

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml ps
```

后端管理端口只绑定到主机回环地址 `127.0.0.1:8000`；公开流量应只进入前端
`8080` 端口，并由云负载均衡器或反向代理提供 HTTPS。不要直接把 PostgreSQL、
Redis 或 Backend 管理端口暴露到公网。

## 3. 上线验收

```bash
# API 进程存活
curl -fsS http://127.0.0.1:8000/api/v1/health/live

# PostgreSQL 与 Redis 均可用
curl -fsS http://127.0.0.1:8000/api/v1/health/ready

# 查看服务状态与近期日志
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs --tail=100 backend worker
```

就绪接口只有在数据库和 Redis 都正常时才返回 HTTP 200，否则返回 503。每个 API
响应带有 `X-Request-ID`，API 日志包含同一个 ID、请求路径、状态码和耗时；后台任务
日志记录完整 `job_id`，可用页面显示的任务编号继续定位 Worker 执行记录。

## 4. 扩容与更新

API 保持无状态，检索结果和进度已外置到 PostgreSQL/Redis。需要提高检索吞吐时，
优先增加 Worker 数量：

```bash
docker compose -f deploy/docker-compose.yml up -d --scale worker=3
```

更新版本时重新构建并启动；Backend 会在启动 API 前执行 `alembic upgrade head`：

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

## 5. 性能验收

前端构建后执行包体积门禁；建议在 CI 中运行同一条检查，防止新增依赖使首屏体积意外回退：

```bash
cd frontend
npm run build
npm run check:bundle
```

服务启动后可运行不调用 LLM 的并发烟测。默认向存活接口发送 100 个请求、并发数为
10，并要求 p95 不超过 500 ms：

```bash
python scripts/api_load_smoke.py
python scripts/api_load_smoke.py --path /api/v1/health/ready --requests 50
```

存活接口适合检查 API 自身开销；就绪接口还会覆盖 PostgreSQL 与 Redis。正式容量规划时，
应在目标服务器上逐步提高并发数，并结合 API、Worker、PostgreSQL 和 Redis 指标确定上限。

## 6. 监控与任务恢复

Prometheus 兼容指标由 Backend 的 `/api/v1/metrics` 提供。生产 Nginx 会阻止公网访问
该路径；监控系统应通过 Docker 内部网络抓取 `http://backend:8000/api/v1/metrics`，
或从服务器本机访问 `http://127.0.0.1:8000/api/v1/metrics`。指标包括：

- 按方法、路由模板和状态码统计的请求数与耗时直方图；
- 各状态下的持久化检索任务数量；
- 最早排队任务的等待秒数；
- 超过安全阈值仍未更新的运行中任务数。

建议至少配置三类告警：5xx 比例持续升高、排队时间持续增长、
`pubmed_search_stale_running_jobs` 大于 0。路由指标使用声明模板而不是实际 `job_id`，
不会因任务数量增加而产生无限标签。

先预览陈旧任务；确认 Worker 已恢复且原任务确实不会继续运行后，再显式重新排队：

```bash
python scripts/recover_stale_jobs.py
python scripts/recover_stale_jobs.py --apply
```

`SEARCH_JOB_STALE_AFTER_SECONDS` 必须大于 `CELERY_TASK_TIME_LIMIT`，默认分别为
2100 秒和 1800 秒，防止仍在正常执行的长任务被重复投递。恢复操作使用状态与更新时间
进行条件更新；任务若在检查期间继续推进，不会被恢复工具抢占。

## 7. 备份与恢复

使用项目脚本生成 PostgreSQL 压缩归档；默认写入 `backups/`，该目录中的 dump 文件
不会进入 Git：

```bash
python scripts/database_backup.py backup
python scripts/database_backup.py backup --output D:/backups/pubmed.dump
```

恢复会替换数据库中的同名对象，因此必须显式提供确认参数。恢复完成后检查迁移状态和
就绪接口：

```bash
python scripts/database_backup.py restore D:/backups/pubmed.dump --confirm-restore
docker compose -f deploy/docker-compose.yml exec backend python -m alembic upgrade head
curl -fsS http://127.0.0.1:8000/api/v1/health/ready
```

- 定期执行备份并把归档复制到独立存储；只有完成过恢复演练的备份才算有效。
- Redis 中的任务队列启用了 AOF，但搜索结果必须以 PostgreSQL 为准。
- Redis DB 1 的 LLM 缓存可以丢弃并重建，不应作为业务数据备份。
- 部署前保留旧镜像标签；数据库升级后回滚代码前先确认迁移兼容性。

## 8. 安全边界

- `.env` 不进入 Git，密钥应由部署平台的 Secret 功能注入。
- Compose 中的 Backend 与 Frontend 容器均以非 root 用户运行。
- API 文档在 Compose 生产模式下默认关闭；仅在受控环境设置
  `ENABLE_API_DOCS=true`。
- 当前应用没有面向多租户的账户系统。若公开到互联网，应在负载均衡器、API
  Gateway 或零信任访问层增加身份认证与速率限制。
