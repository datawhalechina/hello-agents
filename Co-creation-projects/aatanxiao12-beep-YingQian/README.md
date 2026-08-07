# 映前 (YingQian) — 多智能体电影推荐助手

> 基于 HelloAgents + TMDB：关灯之前，先把今晚的片定下来。

## 📝 项目简介

「映前」解决「今晚看什么」的选择困难。用户填写心情、观影对象、类型、时长等偏好后，系统通过 **Pipeline + Tool-use** 多智能体流水线，从 TMDB 真实片库中检索候选并给出带理由的精选推荐。

- **解决问题**：偏好分散、候选太多、容易编造片名
- **特色**：三阶段 Agent 协作 + TMDB 工具取真片 + id 白名单校验
- **适用场景**：个人/情侣/朋友快速定片；也可当 HelloAgents 多 Agent 编排示例

## ✨ 核心功能

- [x] 画像 Agent：生成口味摘要与检索线索（TasteProfile）
- [x] 检索 Agent：调用 TMDB `discover` / `search` 拉取真实候选
- [x] 推荐 Agent：仅在候选 id 内精选并写中文理由
- [x] 「换一批」：复用画像、排除已出 id
- [x] 片库浏览 / 详情双通道 REST API
- [x] React 前端（品牌「映前」）

## 🛠️ 技术栈

- **HelloAgents**：`SimpleAgent` + Tool（多 Agent 串行 Pipeline）
- **后端**：FastAPI、Pydantic、httpx
- **数据源**：TMDB API
- **前端**：Vite + React + TypeScript
- **LLM**：OpenAI 兼容接口（如 DeepSeek）

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（可选，跑前端）
- TMDB Access Token 或 API Key
- OpenAI 兼容 LLM（`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_ID`）

### 安装依赖

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r ../requirements.txt
pip install jupyterlab   # 若要跑 main.ipynb
```

### 配置 API 密钥

**必须把 `.env` 放在 `backend/` 目录**（代码读取 `backend/.env`）：

```bash
# 在项目根目录 aatanxiao12-beep-YingQian/ 下
cp .env.example backend/.env

# Windows PowerShell
# Copy-Item .env.example backend\.env
```

编辑 `backend/.env`，至少填写：

```env
TMDB_ACCESS_TOKEN=你的TMDB_Token
# 或 TMDB_API_KEY=你的Key

LLM_API_KEY=你的LLM密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-v4-flash
```

### 方式 A：Jupyter 快速演示（推荐评审）

```bash
# 仍在 backend/ 且已激活 venv
cd ..
jupyter lab
# 打开 main.ipynb，按顺序运行单元格
```

Notebook 会调用完整推荐流水线，打印画像摘要与推荐片单。

### 方式 B：启动 Web 服务

```bash
cd backend
python run.py
```

- API：http://127.0.0.1:8000  
- 文档：http://127.0.0.1:8000/docs  

前端（可选）：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173

## 📖 使用示例

### 1）Notebook 一键推荐

见 `main.ipynb`。核心调用等价于：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from app.models.schemas import RecommendRequest
from app.agents.movie_recommender_agent import MultiAgentMovieRecommender

req = RecommendRequest(
    mood="放松",
    party_type="独自",
    genres=["剧情", "喜剧"],
    max_runtime_minutes=120,
    region_preference="不限",
    year_preference="近10年",
    free_text="不要太沉重",
)
result, trace_id = MultiAgentMovieRecommender().recommend(req)
for m in result.movies:
    print(m.title, m.reason)
```

### 2）HTTP API

```bash
curl -X POST http://127.0.0.1:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d "{\"mood\":\"虐心\",\"party_type\":\"朋友\",\"genres\":[\"爱情\"],\"region_preference\":\"不限\",\"year_preference\":\"近10年\"}"
```

成功时返回约 5 部电影卡片（含 `title`、`poster_url`、`reason` 等）以及可选的 `taste_profile`。

### 3）前端

打开首页 → 填写偏好 → 「开始荐片」→ 结果页查看理由；可「换一批」或去「片库」浏览。

## 🎯 项目亮点

- **真片约束**：检索必须走 TMDB Tool，推荐阶段用候选 id 白名单，降低幻觉片名
- **多 Agent 分工**：画像 / 检索 / 推荐职责清晰，便于教学与扩展
- **可降级兜底**：检索 Agent 解析失败时可用规则 discover 回退
- **完整产品形态**：不仅有 Agent Demo，还有 FastAPI + 前端交互

## 📊 性能说明（参考）

在 DeepSeek + 本机可访问 TMDB 的环境下，一次完整推荐大约：

| 阶段 | 参考耗时 |
|------|----------|
| 画像 Agent | ~5–8s |
| 检索 Agent（含 1 次 discover） | ~15–25s |
| 推荐 Agent | ~10–15s |
| **合计** | **约 40–50s** |

TMDB 本身通常 <2s；主要时间在 LLM。国内网络若连不上 `api.themoviedb.org`，需代理/VPN。

## 🔮 未来计划

- [ ] 无自由文本时规则化画像，跳过一轮 LLM
- [ ] 默认规则 discover，复杂意图再启用检索 Agent
- [ ] 短片过滤 / 时长下限等检索质量优化
- [ ] 前端进度与真实阶段日志对齐

## 📂 项目结构

```text
aatanxiao12-beep-YingQian/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.ipynb                 # 快速演示入口
├── backend/
│   ├── .env.example           # 同根目录示例（便于放 backend/.env）
│   ├── app/                   # Agents / Tools / API / TMDB
│   ├── tests/
│   ├── run.py
│   └── pyproject.toml
└── frontend/
    ├── src/
    ├── package.json
    └── ...
```

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@aatanxiao12-beep](https://github.com/aatanxiao12-beep)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
