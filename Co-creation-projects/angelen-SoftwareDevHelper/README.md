# SoftwareDevHelper - 软件开发学习助手

> 基于 HelloAgents 框架的智能软件开发学习助手，能够记忆用户水平、出题、测试代码并打分。

## 📝 项目简介

SoftwareDevHelper 是一个专为软件开发初学者设计的智能学习助手。它能够：
- 记忆和评估用户的编程水平。
- 根据用户水平自动出题或从网上搜索真实案例。
- 提供开发过程中的智能建议。
- 用户上传项目压缩包后，自动编写测试样例并进行测试。
- 对用户的代码进行打分并记录学习轨迹。

本项目包含完整的前后端实现，前端使用 HTML+JavaScript，后端使用 Python (FastAPI) 和 HelloAgents 框架。

## ✨ 核心功能

- [x] **用户水平记忆与评估**：记录用户的做题历史和水平信息（支持前端侧边栏实时查看与修改，跨会话共享）。
- [x] **智能出题系统**：根据用户当前水平，动态生成编程题目或搜索实际案例。
- [x] **开发建议助手**：在开发过程中提供代码审查和优化建议。
- [x] **自动化测试与打分**：接收用户上传的项目压缩包，自动解压、编写稳健的测试用例（支持子目录模块动态导入，避免了暴力全量导入导致触发 Python `antigravity` 彩蛋的问题）、执行测试并给出评分。
- [x] **完整的前后端交互**：提供友好的 Web 界面供用户交互。
- [x] **多会话管理**：支持创建多个独立会话，聊天记录持久化存储在后端。支持在会话列表中悬停并优雅地删除历史会话。后端实现了稳健的上下文恢复机制，确保在服务重启或刷新页面后，智能体依然能准确记住之前的对话内容。
- [x] **工具调用可视化**：在聊天界面中实时渲染智能体调用工具的过程，清晰展示输入参数和执行结果。

## 🛠️ 技术栈

- **智能体框架**：HelloAgents (SimpleAgent, ToolRegistry 等)
- **后端框架**：FastAPI, Uvicorn
- **前端技术**：HTML5, CSS3, Vanilla JavaScript
- **大语言模型**：预留接口支持多种 LLM (如 Qwen 等)
- **其他工具**：Python `zipfile` (处理压缩包), `pytest` 或内置 `unittest` (自动化测试)

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 推荐使用 Conda 环境

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

创建 `.env` 文件并填入相关配置：

```bash
cp .env.example .env
```

`.env` 文件内容示例：
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
```

### 运行项目

1. **激活虚拟环境**（如果你使用的是 conda）：
   ```bash
   conda activate hello-agent-homework
   ```

2. **进入项目目录并配置路径**：
   ```bash
   cd Co-creation-projects/angelen-SoftwareDevHelper
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   ```

3. **启动 FastAPI 后端服务**：
   ```bash
   uvicorn src.main:app --reload
   ```

4. **体验项目**：
   打开浏览器，访问 [http://127.0.0.1:8000](http://127.0.0.1:8000) 即可开始与助手对话。

**💡 常见启动问题与注意事项：**
- **修改了 `.env` 文件？** `uvicorn` 的 `--reload` 参数默认只会监听 `.py` 代码文件的变化。如果你修改了 API Key 或模型配置，请在终端按 `Ctrl + C` 停止服务，然后重新运行启动命令。
- **提示端口被占用？** 如果启动时遇到 `[Errno 48] Address already in use`，说明 8000 端口被占用。你可以指定新端口启动：`uvicorn src.main:app --reload --port 8001`，或者在终端执行 `lsof -ti :8000 | xargs kill -9` 杀掉占用该端口的进程。

## 🎯 项目亮点

- **个性化学习**：通过记忆机制实现因材施教。
- **全链路自动化**：从出题到代码测试打分，实现闭环。
- **前后端分离**：清晰的架构设计，易于扩展和维护。

## 👤 作者

- GitHub: [@angelen](https://github.com/angelen)
- 项目链接: [SoftwareDevHelper](https://github.com/datawhalechina/hello-agents/tree/main/Co-creation-projects/angelen-SoftwareDevHelper)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
