# SRE On-Call Agent

> AI-powered incident triage, root cause investigation, and post-mortem generation

> **中文简介**：本项目构建了一个 AI 驱动的 SRE 值班助手，自动完成告警分诊、根因调查和故障复盘报告生成。通过三阶段智能体流水线（Plan-and-Solve → ReAct → Reflection）演示了第四章三种经典范式在真实运维场景下的串联应用，是社区首个 SRE/运维领域项目。

## 📝 Project Introduction

When a production alert fires at 3am, an on-call SRE must triage the incident, investigate root cause across logs and metrics, consult runbooks, and write a post-mortem — all under pressure. This project automates that workflow using a three-stage AI agent pipeline:

- **Stage 1 — TriageAgent** (Plan-and-Solve): converts a raw alert JSON into an ordered investigation plan
- **Stage 2 — InvestigationAgent** (ReAct): iterates through log search, metric queries, and runbook lookups to identify root cause
- **Stage 3 — PostmortemAgent** (Reflection): drafts a structured RCA report, self-critiques it against quality criteria, and revises

This is the **first SRE/operations domain project** in the Hello-Agents community, and demonstrates all three agent paradigms from Chapter 4 in a single coherent system.

## ✨ Core Features

- [x] Three incident fixtures: DB pool exhaustion, memory leak OOM, external API rate limit cascade
- [x] ReAct investigation loop with 3 tools: `log_search`, `metric_query`, `runbook_lookup`
- [x] Reflection-based post-mortem with draft → critique → revise cycle
- [x] FastAPI REST backend — CORS-enabled and ready for frontend integration
- [x] Structured RCA reports: timeline, 5-whys, impact assessment, action items

## 🛠️ Technology Stack

- **Agent paradigms**: Plan-and-Solve, ReAct, Reflection (Chapter 4)
- **LLM**: Any OpenAI-compatible API (AIHubmix, ModelScope/Qwen, OpenAI)
- **Backend**: FastAPI + Uvicorn
- **Data**: JSON incident fixtures + YAML runbooks (no external services needed)

## 🚀 Quick Start

### Environment Requirements

- Python 3.10+

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure API Keys

```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID
```

Free LLM options:
- **AIHubmix** (recommended): `https://aihubmix.com/v1` — free tier, OpenAI-compatible
- **ModelScope/Qwen**: `https://api-inference.modelscope.cn/v1` — 2000 free calls/day

### Run in Jupyter Notebook

```bash
jupyter lab
# Open main.ipynb and run all cells
```

### Run the FastAPI Server

```bash
uvicorn src.api.main:app --reload --port 8000
```

API endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/incidents/fixtures` | List sample incident IDs |
| `POST` | `/incidents/investigate` | Run the full 3-agent pipeline |
| `GET` | `/incidents/{id}/report` | Retrieve a generated report |

## 📖 Usage Examples

### Via Python (notebook or script)

```python
from src.agents.pipeline import run_pipeline

result = run_pipeline("db_pool_exhaustion")
print(result["report"])    # Markdown RCA report
print(result["findings"])  # Root cause + evidence dict
```

### Via API

```bash
# List available incidents
curl http://localhost:8000/incidents/fixtures

# Run the pipeline
curl -X POST http://localhost:8000/incidents/investigate \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "db_pool_exhaustion"}'

# Get the generated report
curl http://localhost:8000/incidents/db_pool_exhaustion/report
```

### Sample Output

```
🚨 STAGE 1: TRIAGE — Generating investigation plan
   1. [log_search] pool exhausted — Find DB pool error log entries
   2. [metric_query] db_pool — Check connection pool saturation over time
   3. [metric_query] latency — Quantify request latency degradation
   4. [runbook_lookup] DB pool exhausted — Get remediation steps

🔍 STAGE 2: INVESTIGATION — ReAct tool loop
   Step 1 — log_search[pool exhausted] → 3 matching entries found
   Step 2 — metric_query[db_pool] → pool maxed at 10/10 from 14:01 onward
   Step 3 — runbook_lookup[DB pool exhausted] → runbook steps retrieved
   ✅ Root cause: Missing index on orders.user_id causing full table scan...

📝 STAGE 3: POST-MORTEM — Reflection (draft → critique → revise)
   Quality score: 9/10 — no revision needed.
   ✅ Final post-mortem ready.
```

## 🎯 Project Highlights

- **Three agent paradigms in one system**: most co-creation projects use a single paradigm; this chains Plan-and-Solve → ReAct → Reflection into a coherent pipeline
- **Domain novelty**: SRE/operations is not covered by any other project in this community
- **Production-realistic fixtures**: log entries, metric time-series, and runbook YAML match real incident patterns (DB pool exhaustion, memory leak, rate limit cascade)
- **Upgrade path built in**: FastAPI backend is CORS-enabled; SSE streaming and a frontend can be added without changing the agent code

## 📊 Performance Evaluation

On 3 incident fixtures (tested with Llama-3.3-70b via Groq, compatible with any OpenAI-compatible API):

| Incident | Root Cause Identified | Pipeline Time |
|---|---|---|
| DB pool exhaustion | ✅ Missing index on orders.user_id | ~30s |
| Memory leak OOM | ✅ Session cache with no TTL/eviction | ~25s |
| External API rate limit | ✅ Retry storm from no exponential backoff | ~28s |

Root cause accuracy: **3/3 (100%)** on sample fixtures

## 🔮 Future Plans

- [ ] SSE streaming: stream agent reasoning steps to frontend in real-time
- [ ] Vue/React frontend: incident selector + live trace + markdown viewer
- [ ] Real log ingestion: connect to Loki / CloudWatch / Datadog
- [ ] Vector memory: embed past RCA reports for faster future investigations
- [ ] Safe runbook execution: let the agent run low-risk remediation commands

## 🤝 Contribution Guidelines

Issues and PRs welcome! See the [Hello-Agents contributing guide](../../README.md).

## 📄 License

MIT License — see [LICENSE.txt](../../LICENSE.txt) for details.

## 👤 Author

- **GitHub**: [@zjzhou](https://github.com/zjzhou)
- **Email**: jijiezhou@gmail.com

## 🙏 Acknowledgments

Thanks to the [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) team for the excellent curriculum, and to Chapter 4's ReAct, Plan-and-Solve, and Reflection examples which this project builds on directly.
