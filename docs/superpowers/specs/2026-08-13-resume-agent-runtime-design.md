# ResumeAgent Configured Agent Runtime Design

## Goal

Make the standard FastAPI entry point automatically enable the mentor's HelloAgents specialists when valid OpenAI-compatible LLM configuration is present, while keeping offline resume data, rendering, and exports available when it is not.

## Chosen Approach

HelloAgents remains an optional `agents` dependency instead of becoming a core dependency. The default entry point loads `.env`, validates `LLM_MODEL_ID`, `LLM_API_KEY`, `LLM_BASE_URL`, and numeric generation settings, and lazily imports HelloAgents only after configuration is valid.

This preserves three useful modes:

- `pip install -e '.[web]'`: offline evidence/version/rendering product;
- `pip install -e '.[agents,web]'` plus valid LLM variables: complete mentor Agent product;
- missing dependency or configuration: API still starts and reports why mentor extraction is unavailable.

## Runtime Components

`resume_agent/agents/runtime.py` owns:

- `AgentRuntimeSettings`, a validated and secret-safe environment model;
- `AgentCapabilityStatus`, the public capability read model;
- `MentorRuntime`, containing optional fact-audit/question-writer ports plus status;
- `build_mentor_runtime(environ)`, which never performs an LLM request.

Settings reject blank values, placeholder keys such as `sk-your-api-key-here`, malformed HTTP(S) base URLs, and invalid numeric ranges. Public status contains model and framework names but never returns API keys or the full base URL.

## Stateless Agent Execution

HelloAgents `SimpleAgent` keeps conversation history. ResumeAgent must not reuse one instance across requests because that could mix candidate data between sessions. A new factory-backed runner creates a fresh `SimpleAgent` for every structured invocation. ResumeAgent prompts already contain the relevant target, experience, quality state, and current user answer, so framework history is unnecessary.

The same configured `HelloAgentsLLM` client may be reused, but both specialist Agent instances are fresh per call:

- fact audit uses `FACT_AUDIT_PROMPT`;
- question writing uses `QUESTION_WRITER_PROMPT`.

Provider/network/framework exceptions are converted to `AgentUnavailableError` with a safe message. Invalid JSON remains `AgentOutputError` and maps to HTTP 502.

## API and UI

`create_app` accepts an optional `AgentCapabilityStatus`. The default Uvicorn module builds one runtime and injects its ports. `GET /capabilities` returns API, mentor, rendering, and export readiness without making an external request.

The Streamlit client reads capabilities once per rerun. The sidebar shows either “导师 Agent 已启用” with model name or an actionable offline/degraded notice. The mentor workspace warns before the user answers when fact audit is unavailable; it does not block evidence viewing, version management, or exports.

## Configuration

Supported variables:

- `LLM_MODEL_ID` (required)
- `LLM_API_KEY` or legacy `DEEPSEEK_API_KEY` (required)
- `LLM_BASE_URL` (required, HTTP/HTTPS)
- `LLM_TIMEOUT` (default `60`, range 1–300 seconds)
- `LLM_TEMPERATURE` (default `0.2`, range 0–2)
- `LLM_MAX_TOKENS` (default `2048`, range 128–32768)

The runtime loads a project `.env` without overriding already exported environment variables. It does not log secrets.

## Testing

- Unit tests cover configured, missing, placeholder, malformed, dependency-missing, and factory-failure states.
- A fake HelloAgents module proves two calls receive two fresh `SimpleAgent` instances and pass exact settings.
- API tests prove capability output is secret-free and that default offline startup remains healthy.
- Adapter tests prove provider exceptions become HTTP 503 while structured-output failures remain HTTP 502.
- Streamlit AppTest covers enabled and degraded capability notices.
- Final verification includes the full suite, compileall, OpenAPI checks, and real dual-process offline startup. A paid LLM call is not made automatically.
