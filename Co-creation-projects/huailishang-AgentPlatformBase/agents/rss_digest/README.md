# RSS Digest

一个最小可用的日更阅读简报工具：

- 拉取 RSS/Atom 订阅源
- 抓取文章正文
- 调用 SiliconFlow 兼容 OpenAI 的 API 生成中文摘要
- 可选生成中文全译
- 输出每日 HTML 简报，适合每天点开看一眼

## 目录结构

```text
rss_digest/
├─ config/
│  ├─ sources.json
│  └─ sources_full.opml
├─ data/
│  ├─ raw/
│  ├─ extracted/
│  ├─ translated/
│  └─ digests/
├─ scripts/
│  └─ run_daily.ps1
├─ src/
│  └─ rss_digest/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ db.py
│     ├─ digest.py
│     ├─ extractor.py
│     ├─ feeds.py
│     ├─ llm.py
│     └─ pipeline.py
├─ state/
├─ .env
├─ .env.example
└─ main.py
```

## 环境变量

在 `rss_digest/.env` 里配置：

```env
LLM_MODEL_ID=Qwen/Qwen3-235B-A22B-Instruct-2507
LLM_API_KEY=sk-xxxxx
LLM_BASE_URL=https://api.siliconflow.cn/v1
DISABLE_SYSTEM_PROXY=true
# PROXY_URL=http://127.0.0.1:7890
FETCH_FULL_TRANSLATION=false
MAX_ARTICLES_PER_RUN=12
REQUEST_TIMEOUT_SECONDS=30
```

说明：
- 当前只读取 `LLM_*` 变量名。
- 默认会清掉继承到进程里的系统代理，避免被无效代理拦住。
- 如果你确实需要代理，在 `.env` 里设置 `PROXY_URL` 即可。
- 默认只做中文摘要，不做全文翻译。
- 如果把 `FETCH_FULL_TRANSLATION=true`，会额外为文章生成中文全译，成本更高。

## 运行方式

在 `D:\SoftWare\pycharm\Project\regularTest` 下执行：

```powershell
.venv\Scripts\python.exe rss_digest\main.py
```

或直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\rss_digest\scripts\run_daily.ps1
```

## 输出结果

- 状态文件：`rss_digest\state\articles.json`
- 日报 HTML：`rss_digest\data\digests\digest_YYYY-MM-DD.html`

## 目前实现范围

- 已支持 RSS/Atom 的基础拉取
- 已支持正文抓取和基础文本清洗
- 已支持中文摘要生成
- 已支持 HTML 简报

## 后续建议

下一步如果你要把质量做稳，优先补这三项：

1. 接入 `trafilatura` 做正文抽取
2. 给摘要增加分类标签和“建议细读/可跳过”
3. 增加 Windows 计划任务，真正每天自动跑
