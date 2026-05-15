# 猜历史人物 Agent

一个基于 `hello_agents` 框架开发的交互式"猜历史人物"游戏应用。用户通过与扮演历史人物的 AI Agent 进行多轮对话，猜测该历史人物的身份。

## 项目特色

- 🤖 基于 `hello_agents` 框架的智能对话 Agent
- 🎮 有趣的猜历史人物游戏机制
- 🌐 现代化 Web 前端界面
- ⚡ FastAPI 高性能后端
- 📱 响应式设计，支持移动端

## 项目结构

```
GuessHistoricalFigure/
├── backend/           # 后端服务
│   ├── main.py        # FastAPI 入口
│   ├── agent.py       # Agent 核心逻辑
│   ├── game_logic.py  # 游戏状态管理
│   ├── config.py      # 配置管理
│   ├── data/
│   │   └── figures.json  # 历史人物数据库
│   ├── .env          # 环境变量配置
│   └── requirements.txt  # Python 依赖
└── frontend/          # 前端界面
    ├── index.html    # 主页面
    ├── style.css     # 样式文件
    └── app.js        # 交互逻辑
```

## 环境要求

- Python 3.8+
- Node.js (可选，用于 Live Server)
- ModelScope API 访问权限

## 快速开始

### 1. 安装依赖

```bash
cd /home/afei/hello-agents/code/chapter16/GuessHistoricalFigure/backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板并配置：
```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下配置：
```env
# LLM 配置（ModelScope API）
LLM_MODEL_ID=GLM-5
LLM_API_KEY=your_modelscope_api_key
LLM_BASE_URL=https://modelscope.cn/api/v1

# 游戏配置
MAX_QUESTIONS=20
MAX_HINTS=3

# 服务配置
BACKEND_PORT=8000
FRONTEND_PORT=5500
```

### 3. 启动后端服务

方式一：使用 Python 直接运行
```bash
cd backend
python main.py
```

方式二：使用 Uvicorn 生产环境运行
```bash
cd backend
uvicorn main:app --reload --port 8000
```

后端服务将在 `http://localhost:8000` 启动

### 4. 访问前端界面

方式一：通过后端静态文件服务（推荐）
后端已配置静态文件服务，直接访问：
```
http://localhost:8000
```

方式二：使用 Live Server（开发时）
```bash
# 在前端目录启动 Live Server
cd frontend
# 使用你喜欢的 Live Server 工具，如：
# python -m http.server 5500
# 或使用 VS Code Live Server 扩展
```

## API 接口

### 游戏 API

- `POST /api/game/start` - 开始新游戏
- `POST /api/game/chat` - 发送消息给 Agent
- `POST /api/game/guess` - 猜测历史人物
- `GET /api/game/hint` - 获取提示
- `POST /api/game/end` - 结束当前游戏
- `GET /api/game/status` - 获取游戏状态

### 响应格式

```json
{
  "success": true,
  "data": {...},
  "message": "操作成功"
}
```

## 游戏规则

1. 系统随机选择一位历史人物
2. 用户通过提问获取线索（最多20次提问）
3. 用户可以请求提示（最多3次）
4. 用户猜测人物身份
5. 猜对则获胜，猜错或提问次数用完则游戏结束

## 技术栈

### 后端
- **FastAPI** - Web 框架
- **hello_agents** - AI Agent 框架
- **Pydantic** - 数据验证
- **Uvicorn** - ASGI 服务器

### 前端
- **HTML5** - 页面结构
- **CSS3** - 样式设计
- **JavaScript** - 交互逻辑
- **Fetch API** - HTTP 请求

### AI/ML
- **ModelScope API** - 大语言模型服务
- **GLM-5** - 语言模型

## 开发说明

### 添加新历史人物

编辑 `backend/data/figures.json` 文件，按照现有格式添加新人物：

```json
{
  "name": "人物姓名",
  "dynasty": "朝代/时代",
  "profession": "职业/身份",
  "achievements": "主要成就",
  "characteristics": "关键特征"
}
```

### 自定义配置

- 修改 `backend/config.py` 中的 `Settings` 类
- 调整游戏参数：最大提问次数、提示次数等
- 配置不同的 LLM 模型和 API

## 故障排除

### 常见问题

1. **LLM API 调用失败**
   - 检查 `.env` 中的 API 配置
   - 确认网络连接正常

2. **CORS 错误**
   - 后端已配置 CORS，确保前端访问正确端口

3. **静态文件无法加载**
   - 检查前端文件路径配置

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！