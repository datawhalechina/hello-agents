# 项目运行与调试命令

## 1. 一键启动推荐方式

打开 PowerShell：

```powershell
cd D:\1-school\agent\14\helloagents-deepresearch
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
cd D:\1-school\agent\14\helloagents-deepresearch
.\start_backend.ps1
```

只启动前端：

```powershell
cd D:\1-school\agent\14\helloagents-deepresearch
.\start_frontend.ps1
```

## 2. 手动启动后端

打开一个 PowerShell 终端：

```powershell
cd D:\1-school\agent\14\helloagents-deepresearch\backend
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
cd D:\1-school\agent\14\helloagents-deepresearch\backend
.\.venv\Scripts\activate
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
cd D:\1-school\agent\14\helloagents-deepresearch\frontend
npm install
npm run dev
```

前端默认地址通常是：

```text
http://localhost:5173
```

## 5. 推荐调试流程

1. 优先运行 `.\start_dev.ps1` 一键启动。
2. 用 `/healthz` 确认后端正常。
3. 浏览器打开 `http://localhost:5173`。
4. 输入求职需求，观察后端终端日志和前端页面变化。

## 6. 常见注意事项

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
npm run dev
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

## 7. 关闭项目

分别在后端和前端终端按：

```powershell
Ctrl+C
```
