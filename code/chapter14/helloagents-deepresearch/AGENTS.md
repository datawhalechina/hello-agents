# AGENTS.md

本文件是本项目长期生效的 Agent 协作规则。中文部分用于说明项目语境；英文部分是硬性规则，后续 Codex 在本项目内工作时必须优先遵守。

## Project Context / 项目上下文

- 项目定位：基于 Hello-Agents 第十四章 deepresearch 改造的“找实习助手 Agent”。
- Backend: FastAPI. Keep these APIs compatible: `/research`, `/research/stream`, `/applications`.
- Frontend: Vue. Local frontend port is fixed at `5174`.
- 当前重点：低成本、可测试、可回放的 Agent 架构，而不是盲目增加新产品功能。
- Product safety: the app helps students find internships and manage applications locally; it must not auto-apply, log into recruiting platforms, mass-contact HR, or bypass platform rules.

## Mandatory Progress Rule

- MUST update root-level `PROGRESS.md` before finishing every task.
- MUST record code changes, key files, test results, discovered issues, and next steps when code was changed.
- MUST record investigation, analysis, debugging findings, or decisions even when no code was changed.
- MUST keep `PROGRESS.md` concise and high-signal. Do not write a long diary.
- MUST use root-level `PROGRESS.md` as the only progress document. Do not create duplicate progress files.
- MUST include `Progress updated: yes` in the final response after `PROGRESS.md` has been updated.

## Hard Development Rules

- MUST preserve compatibility for `/research`, `/research/stream`, and `/applications` unless the user explicitly requests a breaking change.
- MUST NOT commit or intentionally include `.env`, secrets, runtime data, caches, logs, `node_modules`, `dist`, virtual environments, or build artifacts.
- MUST remind users to open and verify recruiting source links for job details.
- MUST treat match scores, source credibility, and recommendation priority as decision aids only. They do not represent admission or offer probability.
- MUST NOT fabricate jobs, salaries, deadlines, links, company facts, or user experience.
- MUST NOT auto-apply to jobs, log into recruiting platforms, mass-contact HR, scrape behind authentication, or bypass platform rules.
- MUST prefer simple, readable, debuggable code over over-designed abstractions.
- MUST prefer fake, dry-run, cache, and replay modes for development/debugging before using real LLM/search calls.
- MUST avoid reverting user or previous-agent changes unless the user explicitly asks for that.

## Common Validation / 常用验证

后端测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
```

前端构建只在改动影响前端时运行：

```powershell
cd frontend
npm run build
```

## Pre-Final Checklist

Before sending the final response, confirm all items:

- Code/document changes are completed, or the response clearly says this task was investigation/analysis only.
- Tests were run, or the response clearly explains why tests were not run.
- `PROGRESS.md` was updated.
- The final response includes `Progress updated: yes`.
