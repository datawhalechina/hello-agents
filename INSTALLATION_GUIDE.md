# Hello-Agents 安装指南

本文档提供详细的环境配置和依赖安装指南。

## 📋 环境要求

- **Python 版本**: >= 3.10 (推荐 3.11)
- **操作系统**: Windows / macOS / Linux
- **硬件要求**: 
  - 最低 8GB RAM（推荐 16GB）
  - 如需运行 Transformer 训练（第3章、第11章），推荐使用 GPU

## 🚀 快速开始

### 1. 克隆项目（如适用）

```bash
git clone https://github.com/datawhalechina/hello-agents.git
cd hello-agents
```

### 2. 创建虚拟环境

#### Windows (PowerShell)
```powershell
# 创建虚拟环境
python -m venv venv_hello_agents

# 激活虚拟环境
.\venv_hello_agents\Scripts\Activate.ps1

# 如果遇到权限问题，执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### macOS / Linux
```bash
# 创建虚拟环境
python3 -m venv venv_hello_agents

# 激活虚拟环境
source venv_hello_agents/bin/activate
```

### 3. 安装依赖

#### 选项 A: 完整安装（推荐）
适用于学习所有章节内容：

```bash
pip install -r requirements.txt
```

#### 选项 B: 精简安装
仅安装核心依赖，适合快速上手：

```bash
pip install -r requirements-minimal.txt
```

#### 选项 C: 按章节安装

**基础章节（1-4章）**
```bash
pip install openai requests tavily-python python-dotenv torch
```

**框架实践（6章）**
```bash
# LangGraph
pip install langgraph langchain-openai

# CAMEL
pip install camel-ai

# AutoGen
pip install autogen-agentchat autogen-ext[openai,azure] streamlit

# AgentScope
pip install agentscope
```

**HelloAgents 框架（7-12章）**
```bash
pip install "hello-agents[all]>=0.2.7" python-dotenv
```

**案例实战（13-15章）**
```bash
pip install "hello-agents[protocols]>=0.2.7" fastapi uvicorn[standard] pydantic httpx aiohttp loguru
```

### 4. 验证安装

```bash
# 检查 Python 版本
python --version

# 检查已安装的包
pip list | grep hello-agents

# 测试导入
python -c "from hello_agents import HelloAgentsLLM; print('✅ HelloAgents 安装成功!')"
```

## 🔧 配置 API 密钥

### 1. 创建 `.env` 文件

在项目根目录创建 `.env` 文件（已在 `.gitignore` 中，不会被提交）：

```bash
# 复制模板
cp .env.example .env  # Linux/macOS
copy .env.example .env  # Windows
```

### 2. 配置必要的 API 密钥

编辑 `.env` 文件，添加以下配置：

```env
# OpenAI API（或兼容服务）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Tavily Search API（第1章、第4章）
TAVILY_API_KEY=your_tavily_key_here

# 高德地图 API（第13章旅行助手）
AMAP_API_KEY=your_amap_key_here

# Unsplash API（第13章图片）
UNSPLASH_ACCESS_KEY=your_unsplash_key_here
```

### 3. 获取 API 密钥

- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://tavily.com/ (免费额度)
- **高德地图**: https://lbs.amap.com/ (免费额度)
- **Unsplash**: https://unsplash.com/developers (免费)

**💡 提示**: 也可以使用国产大模型服务（如通义千问、智谱 AI 等）的 OpenAI 兼容接口。

## 📦 特定依赖说明

### PyTorch（第3章、第11章）

如需 GPU 支持，请根据 CUDA 版本安装：

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CPU 版本（仅用于学习）
pip install torch torchvision torchaudio
```

### Jupyter Notebook

启动 Jupyter Notebook：

```bash
jupyter notebook
```

或使用 JupyterLab：

```bash
pip install jupyterlab
jupyter lab
```

## 🐛 常见问题

### 问题 1: `pip install` 速度慢

**解决方案**: 使用国内镜像源

```bash
# 临时使用
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 2: 依赖版本冲突

**解决方案**: 
1. 使用虚拟环境隔离依赖
2. 逐个安装依赖，排查冲突源
3. 查看各章节的独立 requirements.txt

### 问题 3: Windows PowerShell 无法激活虚拟环境

**解决方案**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题 4: `hello-agents` 导入失败

**解决方案**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 重新安装
pip uninstall hello-agents
pip install "hello-agents[all]>=0.2.7"
```

### 问题 5: Jupyter Kernel 找不到

**解决方案**:
```bash
# 安装 ipykernel
pip install ipykernel

# 添加虚拟环境到 Jupyter
python -m ipykernel install --user --name=venv_hello_agents --display-name="HelloAgents"
```

## 📚 按章节学习建议

| 章节 | 核心依赖 | 可选依赖 |
|------|----------|----------|
| 第1章 | openai, requests, tavily-python | - |
| 第2章 | - (纯 Python) | - |
| 第3章 | torch, numpy | - |
| 第4章 | openai, tavily-python | - |
| 第5章 | - (低代码平台) | - |
| 第6章 | langgraph / camel-ai / autogen / agentscope | streamlit |
| 第7-9章 | hello-agents[all] | jupyter |
| 第10章 | hello-agents[protocols], fastmcp | - |
| 第11章 | hello-agents[all], torch | wandb, tensorboard |
| 第12章 | hello-agents[all], pytest | - |
| 第13章 | hello-agents[protocols], fastapi | - |
| 第14-15章 | hello-agents[all], fastapi | - |
| 第16章 | hello-agents[all], jupyter | - |

## 💡 推荐工作流

1. **阶段1（第1-4章）**: 安装基础依赖
   ```bash
   pip install openai requests tavily-python python-dotenv torch
   ```

2. **阶段2（第5-6章）**: 体验主流框架
   ```bash
   pip install langgraph camel-ai autogen-agentchat agentscope
   ```

3. **阶段3（第7-12章）**: 深入 HelloAgents
   ```bash
   pip install "hello-agents[all]>=0.2.7" jupyter
   ```

4. **阶段4（第13-16章）**: 实战项目
   ```bash
   pip install fastapi uvicorn[standard] streamlit
   ```

## 🔗 相关资源

- **项目主页**: https://github.com/datawhalechina/hello-agents
- **在线文档**: https://datawhalechina.github.io/hello-agents/
- **HelloAgents 框架**: https://github.com/jjyaoao/helloagents
- **Issue 反馈**: https://github.com/datawhalechina/hello-agents/issues

## 📞 获取帮助

如遇到问题，可以：
1. 查看项目 Issues: https://github.com/datawhalechina/hello-agents/issues
2. 参考在线文档的常见问题部分
3. 加入 Datawhale 社区交流

---

**祝学习顺利！🎉**

