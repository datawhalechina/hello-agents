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
