## 多角色历史辩论智能体（Historical Review Agent）

立场预设：**官修史书不等于真相**；须联系**权力、文官书写、时代政治与语境**，对记载抱**怀疑目光**；野史笔记虽多不可靠，可与正史**对读缝隙**。本项目用 **五角色人设** + **终局综合模板** 落实上述取向；可选 **维基 + 检索** 作为考据附录（可关闭）。

### 目录结构（核心）

- `historical_review/`: Python 包（辩论编排、证据附录、交互 CLI）
- `historical_review/web/`: FastAPI Web 与静态前端（`static/`）
- `.env.example`: 环境变量示例

### 安装

建议使用虚拟环境，然后在本目录执行：

```bash
pip install -r requirements.txt
pip install -e .
```

### 配置（OpenRouter / OpenAI 兼容）

复制示例并填入 Key：

```bash
cp .env.example .env
```

常用变量：

- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL`（默认 `https://openrouter.ai/api/v1`）
- `OPENROUTER_MODEL`（默认 `openai/gpt-4o-mini`）

也支持通用变量：`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_ID`。

### 命令行运行

交互模式（会询问议题/是否启用附录/开始确认）：

```bash
python -m historical_review.run_agent
```

非交互（适合脚本/自动化）：

```bash
python -m historical_review.run_agent -y
python -m historical_review.run_agent -y "你的历史议题"
python -m historical_review.run_agent -y --no-evidence "你的议题"
```

安装后也可直接用脚本入口：

```bash
history-review -y "你的历史议题"
```

### Web 界面（推荐）

启动：

```bash
python run_web.py
```

或安装后使用脚本入口：

```bash
history-review-web
```

浏览器打开 `http://127.0.0.1:8777`。

- 页面可填写 Key/Base URL/模型/温度/超时/是否启用考据附录，并可保存到浏览器 `localStorage`
- 服务端会读取本机 `.env`（页面 Key 留空时会使用环境变量）

### 说明与免责声明

- 输出为 **思辨与方法论训练**，不构成学术鉴定或考试标准答案
- 终局综合不会给出“唯一真相”，而强调：官修的制度性偏差、野史可补之处、政治语境中的疑点、可采纳的谦逊判断、以及阴谋论 vs 正当怀疑的边界

