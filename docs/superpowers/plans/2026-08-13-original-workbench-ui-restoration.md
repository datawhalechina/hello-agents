# ResumeAgent Original Workbench UI Restoration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default Streamlit-style dashboard shell with the original two-column ResumeAgent workbench while preserving the current FastAPI, SQLite, mentor, versioning, rendering, export, and evaluation systems.

**Architecture:** FastAPI serves a zero-build HTML/CSS/ES-module frontend from the installed Python package. The browser keeps only navigation identifiers and preferences; all candidate facts, sessions, versions, drafts, and exports flow through same-origin JSON APIs and SQLite. Streamlit remains an optional fallback entry.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2, SQLite, vanilla HTML/CSS/JavaScript ES modules, Node built-in test runner, pytest, Playwright CLI.

## Global Constraints

- The visual reference is `/Users/wangzhe/workbuddy-ai/agent/resume-generator/web/index.html`.
- The default page has no dark sidebar, hero gradient, robot avatar, glow, glassmorphism, or AI marketing copy.
- Keep the original `访谈 / 事实库 / JD 定制 / 工具` tabs and desktop two-column workbench.
- Model credentials remain server-side and must never enter HTML, JSON responses, localStorage, or reports.
- Browser storage may contain only selected IDs, language, active tab, and view preferences.
- Existing Streamlit files remain available but are not the default product entry.
- Every task follows red-green TDD and ends with a focused commit.

---

### Task 1: Packaged workbench shell and default FastAPI entry

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web/index.html`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web/styles.css`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web/api.js`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web/app.js`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web/package.json`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/app.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/pyproject.toml`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_web_entry.py`

**Interfaces:**
- Produces: `GET /` returning the workbench HTML.
- Produces: `GET /assets/styles.css`, `/assets/api.js`, and `/assets/app.js`.
- Produces DOM anchors: `#app-header`, `#primary-tabs`, `#chat-panel`, `#chat-composer`, `#preview-frame`, `#document-toolbar`.

- [ ] **Step 1: Write failing entry and asset tests**

```python
def test_root_serves_original_workbench_shell(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="primary-tabs"' in response.text
    assert [label in response.text for label in ("访谈", "事实库", "JD 定制", "工具")] == [True] * 4
    assert "stSidebar" not in response.text
    assert "把做过的事，讲成有证据的职业故事" not in response.text

def test_web_assets_are_served_and_packaged(client):
    assert client.get("/assets/styles.css").headers["content-type"].startswith("text/css")
    assert client.get("/assets/api.js").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_web_entry.py -q`

Expected: FAIL because `/` and `/assets/*` are not registered.

- [ ] **Step 3: Implement packaged static serving**

Add a package-relative web directory in `create_app`:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

web_dir = Path(__file__).resolve().parents[1] / "web"
app.mount("/assets", StaticFiles(directory=web_dir), name="web-assets")

@app.get("/", include_in_schema=False)
def web_workbench() -> FileResponse:
    return FileResponse(web_dir / "index.html", media_type="text/html")
```

Add package data:

```toml
[tool.setuptools.package-data]
"resume_agent.evaluation" = ["datasets/*.jsonl"]
"resume_agent.web" = ["*.html", "*.css", "*.js", "*.json"]
```

`resume_agent/web/package.json` contains `{ "type": "module" }` so the same `api.js` module works in browsers and the Node built-in test runner.

Create the semantic two-column shell using the original IDs and these primary structures:

```html
<header id="app-header">
  <a class="brand" href="/">⚡ <strong>ResumeAgent</strong></a>
  <span class="product-note">中日英简历工作台</span>
  <span class="header-spacer"></span>
  <span id="service-status"><span class="status-dot"></span><span>正在连接</span></span>
  <button id="language-button" type="button">中文简历</button>
  <button id="sample-button" type="button">示例档案</button>
  <button id="settings-button" type="button">设置</button>
</header>
<main class="workbench">
  <section class="panel task-panel">
    <nav id="primary-tabs" aria-label="简历工作区">
      <button data-tab="chat" aria-selected="true">访谈</button>
      <button data-tab="facts">事实库</button>
      <button data-tab="jd">JD 定制</button>
      <button data-tab="tools">工具</button>
    </nav>
    <div id="chat-panel" class="tab-panel"><div id="chat-messages"></div></div>
    <form id="chat-composer">
      <textarea id="chat-input" aria-label="回答导师" placeholder="回答导师的问题，或直接补充一段真实经历"></textarea>
      <button class="primary" type="submit">发送</button>
    </form>
  </section>
  <section class="panel document-panel">
    <div id="document-toolbar">
      <div id="document-switcher"></div>
      <select id="style-select" aria-label="版式风格"></select>
      <button id="edit-button" type="button">编辑</button>
      <a id="export-pdf">PDF</a><a id="export-html">HTML</a>
      <a id="export-markdown">Markdown</a><a id="export-docx">DOCX</a>
    </div>
    <iframe id="preview-frame" title="简历预览" sandbox=""></iframe>
  </section>
</main>
```

Base CSS must use `#f4f6f9`, white panels, `#1f4e79`, 1px borders, light shadows, system fonts, and a `400px 1fr` desktop grid. `app.js` may only mark the selected tab in this task.

- [ ] **Step 4: Verify tests, package contents, and shell syntax**

Run: `.venv/bin/python -m pytest tests/test_web_entry.py tests/test_api_openapi.py -q`

Run: `.venv/bin/python -m pip wheel --no-deps --wheel-dir /tmp/resume-agent-wheel .`

Expected: PASS; the wheel contains `resume_agent/web/index.html`, `styles.css`, `api.js`, and `app.js`.

- [ ] **Step 5: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/app.py Co-creation-projects/shiyuanyeming-hub-ResumeAgent/pyproject.toml
git add -f Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_web_entry.py
git commit -m "feat: restore original resume workbench shell"
```

### Task 2: Browser API client, persisted UI selection, and inline onboarding

**Files:**
- Modify: `resume_agent/web/api.js`
- Modify: `resume_agent/web/app.js`
- Modify: `resume_agent/web/index.html`
- Test: `tests/web/api.test.mjs`
- Test: `tests/test_web_entry.py`

**Interfaces:**
- Produces: `createApi(fetchImpl = globalThis.fetch)` with `health`, `capabilities`, `listFactBases`, `createFactBase`, and `addExperience` methods.
- Produces: `ApiError` with `status`, `category`, and safe `message`.
- Produces: localStorage key `resume-agent-ui-v1` containing only `factBaseId`, `experienceId`, `sessionId`, `versionId`, `locale`, and `tab`.

- [ ] **Step 1: Write failing Node client tests**

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { createApi, ApiError } from "../../resume_agent/web/api.js";

test("createFactBase posts the validated target", async () => {
  const calls = [];
  const api = createApi(async (url, init) => {
    calls.push([url, init]);
    return new Response(JSON.stringify({ id: "base-1", target: { role: "分析师" }, experiences: [] }), { status: 201 });
  });
  await api.createFactBase({ role: "分析师", country: "日本", languages: ["zh", "ja", "en"] });
  assert.equal(calls[0][0], "/fact-bases");
  assert.equal(JSON.parse(calls[0][1].body).target.role, "分析师");
});

test("503 becomes a safe unavailable error", async () => {
  const api = createApi(async () => new Response(JSON.stringify({ detail: "provider secret" }), { status: 503 }));
  await assert.rejects(api.health(), error => error instanceof ApiError && error.category === "unavailable" && !error.message.includes("provider secret"));
});
```

- [ ] **Step 2: Run Node tests and verify RED**

Run: `node --test tests/web/api.test.mjs`

Expected: FAIL because `createApi` and `ApiError` do not exist.

- [ ] **Step 3: Implement fetch injection and safe errors**

```javascript
export class ApiError extends Error {
  constructor(status, category, message) {
    super(message); this.status = status; this.category = category;
  }
}

export function createApi(fetchImpl = globalThis.fetch) {
  async function request(path, init = {}) {
    const response = await fetchImpl(path, { headers: { "Content-Type": "application/json", ...(init.headers || {}) }, ...init });
    if (!response.ok) {
      const category = response.status === 503 ? "unavailable" : response.status === 409 ? "conflict" : "request";
      throw new ApiError(response.status, category, category === "unavailable" ? "导师服务暂不可用" : "操作没有完成");
    }
    return response.status === 204 ? null : response.json();
  }
  return {
    health: () => request("/health"),
    capabilities: () => request("/capabilities"),
    listFactBases: () => request("/fact-bases"),
    createFactBase: target => request("/fact-bases", { method: "POST", body: JSON.stringify({ target }) }),
    addExperience: (id, payload) => request(`/fact-bases/${id}/experiences`, { method: "POST", body: JSON.stringify(payload) }),
  };
}
```

Implement boot ordering, safe selection persistence, language selection, settings instructions, and a compact onboarding form inside the chat panel. Successful onboarding must create the fact base, add the first experience, persist only returned IDs, and render the interview start state without navigating away. `示例档案` uses the same two existing endpoints to create a synthetic target `数据分析师` and experience `星河科技 · 数据分析实习生`; it must never inject confirmed facts or real personal information.

- [ ] **Step 4: Run client and Python tests**

Run: `node --test tests/web/api.test.mjs`

Run: `.venv/bin/python -m pytest tests/test_web_entry.py tests/test_api_fact_bases.py -q`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web
git add -f Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/web/api.test.mjs Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_web_entry.py
git commit -m "feat: connect workbench onboarding"
```

### Task 3: Mentor conversation and evidence tab

**Files:**
- Modify: `resume_agent/web/api.js`
- Modify: `resume_agent/web/app.js`
- Modify: `resume_agent/web/index.html`
- Modify: `resume_agent/web/styles.css`
- Test: `tests/web/api.test.mjs`
- Test: `tests/test_api_interviews.py`
- Test: `tests/test_api_ui_contract.py`

**Interfaces:**
- Adds API methods: `listSessions`, `createSession`, `getSession`, `currentQuestion`, `answer`, `confirmProposal`, `rejectProposal`, `recordUnknown`, `updateProfile`, and `experienceQuality`.
- Produces render functions: `renderConversation(session)`, `renderPendingProposal(proposal)`, and `renderFactBase(base)`.

- [ ] **Step 1: Add failing API client request-shape tests**

Test that `answer("s1", "我搭建了看板")` posts `{message: "我搭建了看板"}` to `/sessions/s1/answers`; confirmation posts to `/sessions/s1/proposals/p1/confirm`; unknown posts `{dimension}`; profile uses `PATCH`.

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test tests/web/api.test.mjs`

Expected: FAIL because the interview and fact methods are absent.

- [ ] **Step 3: Implement the original single-panel interview rhythm**

The chat panel must show, in order: compact experience selector, `开始访谈 / 下一轮提问`, message history, current single question, pending fact confirmation, then the persistent composer. It must use direct copy:

```javascript
const COPY = {
  start: "开始访谈",
  next: "下一轮提问",
  placeholder: "回答导师的问题，或直接补充一段真实经历",
  unknown: "暂时想不到",
  confirm: "确认事实并继续",
  reject: "这不是我的意思",
};
```

On a 503 answer failure, keep the textarea value and show “导师暂不可用，这段回答还没有发送。” beside the composer. Do not put the failure in a global sidebar.

The facts tab must render profile fields, experience cards, six named dimensions, quality completion, confirmed/estimated/sensitive labels, and a `继续访谈` action that selects the experience and returns to the chat tab.

- [ ] **Step 4: Verify frontend request contracts and backend interview behavior**

Run: `node --test tests/web/api.test.mjs`

Run: `.venv/bin/python -m pytest tests/test_api_interviews.py tests/test_api_ui_contract.py tests/test_profile_and_style.py -q`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web
git add -f Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/web/api.test.mjs
git commit -m "feat: add workbench mentor conversation"
```

### Task 4: JD versions, document preview, styles, and exports

**Files:**
- Modify: `resume_agent/web/api.js`
- Modify: `resume_agent/web/app.js`
- Modify: `resume_agent/web/index.html`
- Modify: `resume_agent/web/styles.css`
- Test: `tests/web/api.test.mjs`
- Test: `tests/test_api_versions.py`
- Test: `tests/test_api_rendering.py`

**Interfaces:**
- Adds API methods: `listVersions`, `createVersion`, `activateVersion`, `setVersionStyle`, `previewVersion`, and `exportUrl`.
- Produces: `renderJdTab(base, versions)`, `renderToolsTab(capabilities)`, `renderDocumentToolbar(version)`, and `renderPreview(renderedResume)`.
- Produces pure helpers `toWareki(isoDate)` and `fromWareki(value)` for the tools tab.

- [ ] **Step 1: Add failing version and preview client tests**

Test exact endpoints and methods for create, activate, style, preview, and export URL. Assert `createVersion` sends `name`, `target_role`, `company`, `raw_jd`, `locale`, and `selected_experience_ids`. Add fixed era-boundary tests for `2019-05-01 → 令和元年5月1日` and `平成31年4月30日 → 2019-04-30`.

- [ ] **Step 2: Run Node tests and verify RED**

Run: `node --test tests/web/api.test.mjs`

Expected: FAIL for absent version methods.

- [ ] **Step 3: Implement JD and persistent right-hand document panel**

The JD tab edits the current version or creates a new one. The right panel never disappears: without a version it renders a paper-shaped empty state; with a version it loads `/versions/{id}/preview`, writes `rendered.html` into `iframe.srcdoc`, displays warnings above the paper, and exposes HTML/Markdown/DOCX/PDF actions.

Language changes create/select a version with matching `locale`; Japanese versions show `履歴書 / 職務経歴書` document buttons. Style choices come from the existing locale style catalog and save through `PUT /versions/{id}/style`. The tools tab contains the compact service status, export shortcuts, and local 和暦 conversion; it contains no promotional “AI polish” card when no corresponding backend endpoint exists.

- [ ] **Step 4: Verify client and backend version/render paths**

Run: `node --test tests/web/api.test.mjs`

Run: `.venv/bin/python -m pytest tests/test_api_versions.py tests/test_api_rendering.py tests/test_resume_exporters.py -q`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web
git add -f Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/web/api.test.mjs
git commit -m "feat: connect workbench resume preview"
```

### Task 5: Server-persisted manual document drafts

**Files:**
- Modify: `resume_agent/domain/models.py`
- Modify: `resume_agent/api/schemas.py`
- Modify: `resume_agent/application/version_service.py`
- Modify: `resume_agent/application/render_service.py`
- Modify: `resume_agent/api/app.py`
- Modify: `resume_agent/web/api.js`
- Modify: `resume_agent/web/app.js`
- Test: `tests/test_version_service.py`
- Test: `tests/test_api_rendering.py`
- Test: `tests/web/api.test.mjs`

**Interfaces:**
- Adds `ResumeVersion.manual_markdown: str = ""` and `manual_html: str = ""`.
- Adds `VersionDraftRequest(markdown: str, html: str)` with a 500,000-character limit per field.
- Produces: `VersionService.set_draft(version_id: UUID, markdown: str, html: str) -> ResumeVersion`.
- Produces: `PUT /versions/{version_id}/draft`.

- [ ] **Step 1: Write failing domain/API tests**

```python
def test_manual_draft_is_persisted_and_used_for_preview(client, created_version):
    response = client.put(
        f"/versions/{created_version.id}/draft",
        json={"markdown": "# 手工稿", "html": "<main>手工稿</main>"},
    )
    assert response.status_code == 200
    preview = client.get(f"/versions/{created_version.id}/preview").json()
    assert preview["markdown"] == "# 手工稿"
    assert preview["html"] == "<main>手工稿</main>"
```

Add tests proving empty strings return to generated output and oversized drafts return 422.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_version_service.py tests/test_api_rendering.py -q`

Expected: FAIL because draft fields and endpoint do not exist.

- [ ] **Step 3: Implement draft overlay without mutating facts**

```python
class VersionDraftRequest(BaseModel):
    markdown: str = Field(default="", max_length=500_000)
    html: str = Field(default="", max_length=500_000)

def preview(self, version_id: UUID) -> RenderedResume:
    version = self.versions.get(version_id)
    base = self.fact_bases.get(version.fact_base_id)
    rendered = self.renderer.render(base, version)
    return rendered.model_copy(update={
        "markdown": version.manual_markdown or rendered.markdown,
        "html": version.manual_html or rendered.html,
    })
```

The iframe edit mode must save through the draft endpoint, display `编辑稿` in the toolbar, and provide `恢复自动生成` by sending empty strings. It must not write resume HTML into localStorage.

- [ ] **Step 4: Run service, API, client, and exporter tests**

Run: `.venv/bin/python -m pytest tests/test_version_service.py tests/test_api_rendering.py tests/test_resume_exporters.py -q`

Run: `node --test tests/web/api.test.mjs`

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_version_service.py
git add -f Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_api_rendering.py Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/web/api.test.mjs
git commit -m "feat: persist workbench document drafts"
```

### Task 6: Responsive polish, end-to-end browser verification, and default-run documentation

**Files:**
- Modify: `resume_agent/web/styles.css`
- Modify: `resume_agent/web/app.js`
- Modify: `README.md`
- Test: `tests/test_web_entry.py`

**Interfaces:**
- Desktop breakpoint: greater than 960px uses `400px minmax(0, 1fr)`.
- Tablet breakpoint: 640–960px stacks task and document panels.
- Mobile breakpoint: below 640px collapses secondary header actions and keeps tab/composer controls visible.

- [ ] **Step 1: Add failing static contract tests for responsive and non-AI styling**

```python
def test_styles_define_all_required_breakpoints(client):
    css = client.get("/assets/styles.css").text
    assert "@media (max-width: 960px)" in css
    assert "@media (max-width: 640px)" in css
    assert "400px minmax(0, 1fr)" in css
    assert "linear-gradient" not in css
    assert "backdrop-filter" not in css
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_web_entry.py -q`

Expected: FAIL until both responsive rules and forbidden-style checks pass.

- [ ] **Step 3: Finish responsive behavior and documentation**

At 1440×900 the composer and document toolbar remain visible without page-level horizontal scrolling. At 1024×768 the two columns remain usable. At 390×844 panels stack, tabs scroll horizontally, and no Chinese header text uses vertical writing or one-character wrapping.

Update README default launch to:

```bash
uvicorn resume_agent.api.main:app --reload
# Open http://127.0.0.1:8000/
```

Document Streamlit as the optional fallback command, not the main product command.

- [ ] **Step 4: Run full automated verification**

Run: `.venv/bin/python -m pytest -q`

Run: `node --test tests/web/api.test.mjs`

Run: `.venv/bin/python -m compileall -q resume_agent`

Run: `git diff --check`

Expected: all Python and Node tests PASS; compileall and diff check exit 0.

- [ ] **Step 5: Run Playwright CLI acceptance at three viewports**

Start the API with a temporary SQLite database and a local fake OpenAI-compatible mentor service. Use Playwright CLI to complete onboarding, start an interview, submit an answer, confirm the proposed fact, create a JD version, preview it, enter/exit edit mode, and switch all four tabs.

Capture screenshots at `1440×900`, `1024×768`, and `390×844`. For each viewport assert with browser evaluation:

```javascript
({
  horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  tabsVisible: [...document.querySelectorAll("#primary-tabs button")].every(x => x.getBoundingClientRect().height > 0),
  composerVisible: document.querySelector("#chat-composer").getBoundingClientRect().height > 0,
})
```

Expected: `horizontalOverflow` is false and both visibility checks are true; browser console has zero errors.

- [ ] **Step 6: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/web Co-creation-projects/shiyuanyeming-hub-ResumeAgent/README.md
git add -f Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_web_entry.py
git commit -m "feat: make original workbench the default UI"
```
