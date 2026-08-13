# ResumeAgent

[中文](README.md) · [日本語](README.ja.md) · **English**

ResumeAgent is an evidence-first resume mentor for Chinese, Japanese, and English resumes. Instead of polishing vague claims, it asks one question at a time, helps you recall what you actually did, separates personal contribution from team output, and writes a fact into the resume only after you confirm it.

![ResumeAgent two-column workbench](docs/assets/resume-agent-workbench.png)

## How it works

1. Select a real experience. The mentor asks about one currently missing evidence dimension.
2. The model turns your answer into a proposed fact. You can confirm or reject it; unconfirmed content never enters the resume.
3. The fact base stores evidence across six dimensions: context, personal responsibility, action, method, result, and supporting evidence or data.
4. Create a job-specific version for a JD, choose the experiences to include, and select a Chinese, Japanese, or English template.
5. Preview and edit in the same workbench, then export HTML, Markdown, DOCX, or PDF.

Follow-ups progress from a direct question to recall anchors and alternative evidence. After two explicit “I can't recall right now” responses, the gap is skipped. Deterministic code controls dimension selection, confirmation rules, version isolation, and rendering; the LLM is limited to proposed-fact extraction and question wording.

## What works today

- A restrained, two-column FastAPI workbench with interview, fact base, JD customization, tools, and live document preview.
- Multiple candidate files, experiences, and job versions; the current session, selections, and server-side manual draft survive a page refresh.
- Six-dimension evidence progress and one-question interviewing; proposed facts can be confirmed or rejected and marked estimated or sensitive.
- Evidence-only rendering: unconfirmed facts are excluded, and versions are marked stale when their fact base changes.
- Separate Chinese, Japanese, and English headings, layouts, and three styles per language. Fact text is not translated automatically.
- Visual or Markdown editing saved on the server, with a reset back to the generated version.
- HTML, Markdown, DOCX, and PDF exports, plus Gregorian/Japanese era date conversion.
- A versioned synthetic evaluation set for one-question behavior, dimension accuracy, evidence preservation, and hallucination resistance.

## Architecture

```text
Browser (vanilla ES modules)
            │ same-origin JSON API
FastAPI ─── application services ─── deterministic planner / renderer
            │                              │
          SQLite                      HelloAgents adapters
     facts, sessions, versions       fact audit + question wording
```

The default UI has no frontend build step. SQLite is the local source of persistence for facts, sessions, versions, and manual drafts. The renderer reads only confirmed facts from experiences selected by the target version.

Key directories:

```text
resume_agent/api/             FastAPI entry point and API
resume_agent/application/     Interview, fact-base, and version use cases
resume_agent/domain/          Domain models and six-dimension quality gate
resume_agent/agents/          HelloAgents adapters and prompts
resume_agent/rendering/       Trilingual templates and exporters
resume_agent/web/             Vanilla HTML/CSS/JavaScript workbench
tests/                        Python and browser-client tests
evaluation/                   Synthetic mentor data and report output
```

## Quick start

Python 3.10+ is required. Google Chrome or Microsoft Edge is additionally required only for PDF export.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[agents,web]'
cp .env.example .env
uvicorn resume_agent.api.main:app --reload
```

Open <http://127.0.0.1:8000/>. The OpenAPI documentation is available at <http://127.0.0.1:8000/docs>.

The values in `.env.example` are placeholders. Replace them with a real OpenAI-compatible model configuration to enable mentor interviews. Keeping the placeholders or omitting the configuration starts the application in offline mode.

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_MODEL_ID` | Model ID | required for mentor mode |
| `LLM_API_KEY` | API key; `DEEPSEEK_API_KEY` is also supported | required for mentor mode |
| `LLM_BASE_URL` | OpenAI-compatible HTTP(S) URL | required for mentor mode |
| `LLM_TIMEOUT` | Request timeout in seconds | `60` |
| `LLM_TEMPERATURE` | Fact-extraction temperature | `0.2` |
| `LLM_MAX_TOKENS` | Maximum tokens per request | `2048` |
| `RESUME_AGENT_DB` | SQLite file path | `data/resume_agent.db` |

Model settings are read only by the server. Starting the application does not automatically call the model. `GET /capabilities` reports mentor and export availability without returning the API key or full provider URL.

## Tests

```bash
.venv/bin/python -m pytest -q
node --test tests/web/*.test.mjs
```

With a model configured, you can also run the synthetic mentor evaluation:

```bash
resume-agent-eval --repeats 3 --fail-under 0.90
```

## Privacy and local data

- Data is stored in local SQLite by default. The API key exists only in server-side environment variables.
- Browser storage contains selection IDs for the candidate file, experience, version, language, and tab. It does not contain answers, facts, drafts, or API keys.
- HelloAgents instances that handle resume content disable trace, session, skills, todo, devlog, and subagent persistence by default.
- The repository ignores `.env`, SQLite databases, virtual environments, and local caches. You should still inspect exported files for personal information before committing or sharing them.

## Current limitations

- This is a local, single-user MVP. It has no hosted service, authentication, multi-user authorization, or cloud data isolation. Do not expose it directly to the public internet.
- Mentor questions and proposed-fact extraction require a working LLM. Candidate files, facts, versions, preview, editing, and export remain available offline without an LLM.
- Trilingual templates localize document structure and headings but do not automatically translate confirmed facts. Supply or review content in the target language before applying.
- The Japanese web output is currently a `職務経歴書`. A complete JIS `履歴書` with personal details, photo, education, and qualification fields has not yet been modeled.
- PDF export depends on a local Chrome or Edge installation. HTML, Markdown, and DOCX remain available without it.
- Importing an existing PDF/DOCX resume, team collaboration, and production deployment configuration are not yet included.

## Open-source origin and license

This project began as a co-created [Datawhale HelloAgents](https://github.com/datawhalechina/hello-agents) tutorial project and is now maintained as a standalone portfolio project.

Released under the [MIT License](LICENSE).
