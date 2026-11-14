# 智能故事生成器 · StoryCreat Agent

基于 **写作 Agent + 独立审稿 Agent** 的闭环故事生成 Demo：先写初稿，再用“规则检查 + LLM 审稿”双重评审，未达标就带着修改意见自动重写，直到通过或达到轮次上限。支持 **CLI / HTTP API / 网页前端** 三种入口，附带离线测试与批量评测脚本。

- 三种体裁：小说 `novel`、剧本 `script`、诗歌 `poem`
- 双 Agent 职责分离：写作者只创作，审稿人只评分与给修改指令，避免“自写自夸”
- 规则层保底：字数、体裁格式、必含/禁含元素、段落与重复度等硬性检查先于 LLM 执行
- 全流程可追溯：每轮草稿、评分、问题清单、耗时与 token 用量都落盘
- 开箱即用：无构建步骤的原生前端，由 FastAPI 直接托管

## 1. 快速开始

要求 Python 3.10+。

```bash
cd Noob9331x-StoryCreat-Agent
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

配置模型（任意 OpenAI 兼容接口均可）：

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

编辑 `.env`，至少填写：

```ini
LLM_MODEL_ID=glm-4-flash
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
```

生成第一个故事：

```bash
python main.py "写一个雨夜便利店的故事，夜班店员遇到寻找女儿的陌生老人" --genre novel --length 800 --must "雨,便利店,老人" --rounds 2
```

### Notebook 演示（推荐用于验收）

```bash
jupyter lab
# 打开根目录 main.ipynb，按顺序运行
```

Notebook 覆盖：项目介绍、环境自检、规则检查工具、SimpleAgent / WriterAgent / ReviewerAgent 构建、离线规则演示、真实双 Agent 闭环、无 Key 离线回退、测试与批量评测说明。未配置 `.env` 时真实生成会自动跳过，不会中断整个 Notebook。

## 2. 三种使用方式

### 2.1 命令行

```bash
python main.py "写一个发生在末班地铁上的故事" --genre novel --style "克制、留白"
python main.py "写一首关于城市雨夜的现代诗" --genre poem --length 320 --forbid "口号"
python main.py "写一个三场次短剧：深夜关东煮摊" --genre script --json
python main.py "..." --quiet          # 只输出正文
python main.py --list                 # 最近 20 次运行
python main.py --version
```

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--genre` | `novel` / `script` / `poem` | `novel` |
| `--style` | 文风描述 | 无 |
| `--length` | 目标字数（200–5000） | `1200` |
| `--must` / `--forbid` | 必含 / 禁含元素，逗号分隔，各最多 5 个 | 空 |
| `--rounds` | 最大修订轮次（0–3），`0` 表示只写初稿 | 配置值，默认 2 |
| `--json` | 输出完整 JSON（含逐轮审稿） | 关闭 |
| `--quiet` | 不打印逐轮摘要 | 关闭 |
| `--serve` | 启动 Web 服务（含前端） | 关闭 |

退出码：`0` 成功，`1` 生成失败，`2` 参数或配置错误。

### 2.2 Web 服务 + 前端

```bash
python main.py --serve --port 8000
```

打开 <http://127.0.0.1:8000/> 即可使用网页版：左侧填写需求、选择样例，中间查看评分与逐轮审稿，右侧浏览历史记录。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查与配置状态（不含密钥） |
| `GET` | `/api/samples` | 内置示例 |
| `POST` | `/api/generate` | 执行完整生成流程 |
| `GET` | `/api/runs?limit=20` | 历史运行摘要 |
| `GET` | `/api/runs/{run_id}` | 某次运行详情 |
| `GET` | `/api/runs/{run_id}/final.md` | 定稿 Markdown（加 `?download=true` 触发下载） |

请求示例：

```bash
curl -X POST http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"写一个雨夜便利店的故事，夜班店员遇到寻找女儿的陌生老人","genre":"novel","target_length":800,"must_include":["雨","便利店"],"max_rounds":2}'
```

错误映射：参数非法 `422`、未配置 LLM `503`、业务异常 `502`、未知异常 `500`。

### 2.3 批量评测与图表

```bash
python eval/run_eval.py --limit 3 --rounds 1   # 先小规模验证
python eval/run_eval.py                        # 跑全部 9 条样例
python eval/run_eval.py --chart-only           # 根据已有 CSV 重新绘图
python scripts/make_demo_chart.py              # 等价的绘图入口
```

输出：

- `outputs/eval_summary.csv`：每条样例的状态、轮次、最终/平均分、问题数、token、耗时
- `outputs/demo_result.png`：各用例得分 + 逐轮平均得分双栏图（自动检测中文字体，缺失时使用英文标签）


## 3. 工作原理

```text
用户需求 StoryRequest
        │
        ▼
┌───────────────┐   初稿 / 修订稿    ┌─────────────────────────┐
│  WriterAgent  │ ─────────────────▶ │ 规则层 run_rule_review   │
│  （写作）      │                    │ 字数/格式/必含/禁含/重复  │
└───────────────┘                    └────────────┬────────────┘
        ▲                                         │ 规则问题
        │ 修改意见 + 问题清单                        ▼
        │                              ┌─────────────────────────┐
        └───────────────────────────── │ ReviewerAgent（LLM 审稿）│
                                       │ 四维评分 + 问题 + 指令    │
                                       └────────────┬────────────┘
                                                    ▼
                                   合并问题 → 判定是否通过 → 落盘
```

1. **写作**：首轮按体裁模板生成；后续轮次带上上一轮草稿、合并后的问题和修改指令重写。
2. **规则审查**：不依赖模型，检查目标字数区间、剧本场次/诗歌行数、必含与禁含元素、段落结构、重复句等。
3. **LLM 审稿**：输出结构化 JSON（四维评分、问题清单、修改指令、是否通过），解析失败会自动重试并降级为纯规则判定。
4. **判定**：`LLM approved == true` **且** 加权总分 ≥ `APPROVE_SCORE` **且** 相关性 ≥ `MIN_RELEVANCE_SCORE` **且** 无 fatal 问题，才算通过。
5. **选稿**：无论是否通过，最终返回历史最高分稿件；同分优先更靠后的轮次、fatal 更少的轮次。

运行状态：

| 状态 | 含义 |
| --- | --- |
| `approved` | 在轮次内通过审稿 |
| `max_rounds_reached` | 达到轮次上限仍未通过，返回最高分稿 |
| `degraded` | 审稿 LLM 不可用或落盘异常，降级为规则判定，结果仅供参考 |
| `failed` | 生成过程失败，未产生可用稿件 |

评分（0–100）：正常审稿时 `weighted = relevance×0.4 + completeness×0.2 + genre_format×0.2 + style×0.2`。审稿降级时，四个维度从 100 分起按规则问题扣分（fatal −30 / major −12 / minor −4）再加权。具体实现见 `src/models.py`、`src/pipeline.py` 与 `src/rules.py`。

## 4. 项目结构

```text
.
├── main.py                  # CLI 入口（生成 / 历史 / 启动服务）
├── src/
│   ├── api.py               # FastAPI 应用与路由
│   ├── pipeline.py          # 双 Agent 编排、评分合并、选稿、落盘
│   ├── agents/
│   │   ├── base.py          # hello-agents SimpleAgent 适配与重试
│   │   ├── writer.py        # 写作 / 修订 Agent
│   │   └── reviewer.py      # 审稿 Agent（结构化 JSON 解析）
│   ├── rules.py             # 离线规则审查
│   ├── prompts.py           # 分体裁提示词与版本号
│   ├── models.py            # Pydantic 数据模型与校验
│   ├── storage.py           # 运行目录、结果、定稿与清理
│   ├── config.py            # 环境变量配置
│   ├── llm_utils.py         # JSON 提取、文本后处理
│   ├── samples.py           # 内置样例加载
│   ├── logging_utils.py     # 日志与 trace
│   └── errors.py            # 领域异常
├── frontend/index.html      # 单页前端（原生 HTML/CSS/JS）
├── data/
│   ├── samples.json         # 前端样例
│   └── sample.csv           # 批量评测样例
├── eval/run_eval.py         # 批量评测 + 图表
├── scripts/make_demo_chart.py
├── tests/                   # 离线单测（FakeLLM，不访问网络）
├── outputs/                 # 运行结果（自动生成，已忽略）
├── requirements.txt
└── .env.example
```

每次运行会在 `outputs/runs/<run_id>/` 下生成：`request.json`、`draft_round_N.md`、`review_round_N.json`、`trace.jsonl`、`result.json`、`final.md`，并在 `outputs/index.json` 维护历史索引。

## 5. 配置项

| 环境变量 | 说明 | 默认 |
| --- | --- | --- |
| `LLM_MODEL_ID` | 模型名称（必填） | 空 |
| `LLM_API_KEY` | API Key（必填，不写日志） | 空 |
| `LLM_BASE_URL` | OpenAI 兼容端点（必填） | 空 |
| `LLM_TIMEOUT` | 单次调用超时（秒） | `180` |
| `LLM_TEMPERATURE_WRITER` | 写作温度 | `0.8` |
| `LLM_TEMPERATURE_REVIEWER` | 审稿温度 | `0.0` |
| `APPROVE_SCORE` | 加权总分通过线 | `80` |
| `MIN_RELEVANCE_SCORE` | 相关性最低分 | `80` |
| `MAX_ROUNDS_DEFAULT` | 默认轮次（0–3） | `2` |
| `OUTPUT_DIR` / `FRONTEND_DIR` / `DATA_DIR` | 目录，相对路径按项目根解析 | `outputs` / `frontend` / `data` |
| `HOST` / `PORT` | 服务监听地址与端口 | `127.0.0.1` / `8000` |
| `CORS_ORIGINS` | 允许跨域来源，逗号分隔 | 本地 5173 |
| `CLEANUP_KEEP_RUNS` | 保留最近运行数量 | `50` |
| `TRACE_ENABLED` | 是否写 `trace.jsonl` | `true` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 6. 测试

测试全部离线运行：`FakeLLM` 替换真实模型，临时目录隔离输出，不需要 API Key。

```bash
python -m pytest -q
python -m pytest tests/test_pipeline.py -v
```

覆盖范围：数据模型校验、规则审查、LLM 输出解析与重试、提示词构建、流水线状态机（一次通过 / 多轮修订 / 轮次耗尽 / 审稿降级 / 生成失败）、FastAPI 接口与静态页。

## 7. 已知限制

- 生成接口是**同步**的，长文本多轮生成可能耗时数十秒；生产环境建议改为任务队列 + 轮询。
- 历史记录基于本地文件，未做多进程并发写锁；单机 Demo 足够，多实例部署需换数据库。
- 审稿质量依赖模型能力，规则层只能覆盖可机械判定的维度。
- 前端为原生实现，未做移动端深度适配与无障碍审计。
- 批量评测串行执行以避免限流，样例规模较小（9 条），指标用于演示而非基准排名。

## 8. 致谢
核心贡献者
Noob9331x - 项目维护者
### 特别鸣谢
Datawhale 社区：提供学习资源与支持
Hello-Agents 项目：提供框架基础
OpenAI & DeepSeek：LLM 技术支持
