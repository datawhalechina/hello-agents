# 项目运行与调试命令

## 1. 一键启动推荐方式

打开 PowerShell：

```powershell
cd D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch
.\start_dev.ps1
```

这个命令会自动打开两个新的 PowerShell 窗口：

- 后端窗口：启动 FastAPI 后端。
- 前端窗口：启动 Vue 前端。

如果 PowerShell 提示脚本执行策略限制，可以改用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_dev.ps1
```

只启动后端：

```powershell
cd D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch
.\start_backend.ps1
```

只启动前端：

```powershell
cd D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch
.\start_frontend.ps1
```

## 2. 手动启动后端

打开一个 PowerShell 终端：

```powershell
cd D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch\backend
.\.venv\Scripts\activate
python src/main.py
```

启动成功后会看到类似输出：

```text
Uvicorn running on http://0.0.0.0:8000
Application startup complete.
```

也可以使用更标准的 Uvicorn 命令：

```powershell
cd D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch\backend\src
..\.venv\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 3. 测试后端是否启动成功

另开一个 PowerShell 终端：

```powershell
curl http://127.0.0.1:8000/healthz
```

正常返回：

```json
{"status":"ok"}
```

## 4. 手动启动前端

另开一个 PowerShell 终端：

```powershell
cd D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

前端地址是：

```text
http://127.0.0.1:5174
```

## 5. 推荐调试流程

1. 优先运行 `.\start_dev.ps1` 一键启动。
2. 用 `/healthz` 确认后端正常。
3. 浏览器打开 `http://127.0.0.1:5174`。
4. 输入求职需求，观察后端终端日志和前端页面变化。

## 6. Mock 行为回归验证清单

当前仓库不内置 mock 验证脚本。如需在不依赖真实 LLM/搜索服务的情况下复测前端交互，可以临时启动一个仓库外 mock 后端，并让前端通过 `VITE_API_BASE_URL` 指向它。

建议 mock 后端覆盖以下接口：

- `GET /healthz`
- `GET /applications`
- `POST /applications`
- `PATCH /applications/{item_id}`
- `DELETE /applications/{item_id}`
- `POST /research`
- `POST /research/stream`

推荐验证场景：

1. 普通完成流：返回任务清单、来源、岗位清单、搜索诊断、最终报告和 `done`，前端应展示时间线、任务区、岗位区和报告区。
2. 取消流：持续发送慢速事件，点击“取消找实习”后应显示取消状态，不自动重试。
3. 断线恢复：首次流结束但不发送 `done/error`，第二次请求成功，前端应自动重试一次并保留已有结果。
4. 手动重试：自动重试后仍断线，前端应显示“重新尝试”，点击后可继续完成。
5. 业务错误：发送 `type: "error"`，前端应显示失败状态，不自动重试。
6. 保存岗位：保存、刷新、更新状态、更新备注、移除岗位后，岗位计数和已保存清单应同步变化。
7. 复制操作：复制来源、报告、笔记路径后应出现成功日志；若浏览器限制剪贴板，应出现手动复制 fallback。

验证期间不要提交运行产物：

- `.env`
- `.venv`
- `node_modules`
- `dist`
- `backend/data`
- `backend/notes`
- `backend/memory`

## 7. 常见注意事项

### 运行日志隐私与 replay

新运行默认使用：

```text
LLM_RUN_LOG_LEVEL=metadata
```

该模式只在 `backend/logs` 中保存请求哈希、模型、用量、耗时，以及敏感内容的长度和 SHA-256，不能用于 replay。

需要生成可回放日志时，必须在 `.env` 中显式设置：

```text
LLM_RUN_LOG_LEVEL=full
```

`full` 日志会保留模型响应、解析结果、搜索结果、最终报告和错误信息原文，可能包含用户信息，应作为敏感本地数据保护。生成日志后，再配置：

```text
LLM_MODE=replay
LLM_REPLAY_LOG=logs/run_xxx.json
```

旧 schema v2 日志仍可 replay。系统不会自动删除或改写已有日志。不需要运行日志时可设置 `LLM_RUN_LOG_LEVEL=off`。

### LLM 响应缓存隐私

LLM 缓存与运行日志是两套独立机制。即使使用默认的：

```text
LLM_RUN_LOG_LEVEL=metadata
```

只要启用了可写缓存，`backend/.llm_cache` 仍会保存完整模型响应，包括响应正文、reasoning、tool calls 和相关元数据。缓存文件应作为敏感本地数据保护。

推荐默认关闭缓存：

```text
LLM_CACHE_MODE=off
```

需要复用已有缓存但不希望产生新文件时使用：

```text
LLM_CACHE_MODE=read_only
```

仅在明确接受响应原文落盘时使用：

```text
LLM_CACHE_MODE=read_write
LLM_CACHE_DIR=.llm_cache
```

三种模式的行为：

- `off`：不读取、不创建缓存目录、不写入缓存。
- `read_only`：命中已有缓存时复用；未命中时正常调用底层模型，但不创建目录或写文件。
- `read_write`：读取已有缓存，并将未命中的完整模型响应写入 JSON。

缓存只应用于 `LLM_MODE=real` 和 `LLM_MODE=fake`。`dry_run` 与 `replay` 始终绕过缓存。缓存不能替代 replay；`LLM_MODE=replay` 仍只读取旧 schema v2 或 `LLM_RUN_LOG_LEVEL=full` 生成的 schema v3 运行日志。

旧配置 `LLM_CACHE_ENABLED=true` 仍受支持，并在未设置 `LLM_CACHE_MODE` 时等价于 `read_write`。如果两者同时设置，以 `LLM_CACHE_MODE` 为准。

项目不会自动删除或改写已有缓存。建议调试任务结束后立即手动清理；确需跨日调试时，建议最长保留 7 天。先在 `backend` 目录预览缓存路径和文件：

```powershell
Set-Location D:\1-school\agent\14\hello-agents-gitee\code\chapter14\helloagents-deepresearch\backend
$cachePath = Join-Path (Get-Location) ".llm_cache"
$cachePath
Get-ChildItem -LiteralPath $cachePath -File -ErrorAction SilentlyContinue |
    Select-Object Name, Length, LastWriteTime
```

确认 `$cachePath` 指向当前项目的 `backend\.llm_cache` 后，再手动清理：

```powershell
Remove-Item -LiteralPath $cachePath -Recurse -Force
```

### 修改后端代码

如果使用：

```powershell
python src/main.py
```

代码变动通常会被 Uvicorn reload 检测到并自动重启。

### 修改 `.env`

修改 `.env` 后建议手动重启后端：

```powershell
Ctrl+C
.\start_backend.ps1
```

### 前端依赖已安装时

后续不需要每次都运行 `npm install`，直接：

```powershell
npm run dev -- --host 127.0.0.1 --port 5174
```

### 后端虚拟环境未激活时

如果看到依赖找不到，先确认命令行前面有：

```text
(.venv)
```

没有的话运行：

```powershell
.\.venv\Scripts\activate
```

## 8. 关闭项目

分别在后端和前端终端按：

```powershell
Ctrl+C
```
