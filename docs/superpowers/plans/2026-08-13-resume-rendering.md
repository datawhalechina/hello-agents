# ResumeAgent Resume Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate evidence-only Chinese, English, and Japanese resume previews from `ResumeVersion` and export the same document as HTML, Markdown, DOCX, or PDF.

**Architecture:** A canonical candidate profile lives in the fact base. A pure renderer converts the fact base plus version overlay into a structured `RenderedResume` and self-contained HTML/Markdown. Export adapters consume that result, while an application service, FastAPI routes, typed HTTP client, and Streamlit preview workspace expose the behavior without reading Notebook outputs.

**Tech Stack:** Python 3.10+, Pydantic 2, FastAPI, python-docx 1.1+, headless Chrome/Edge, HTTPX, Streamlit, pytest.

## Global Constraints

- Rendering never invokes an LLM and never invents or translates fact text.
- Only selected experiences and non-unverified facts appear.
- Every user-controlled string is HTML escaped.
- Preview is read-only and creates no repository rows or output files.
- Style changes and candidate profile changes require explicit mutations.
- PDF failure does not disable HTML, Markdown, or DOCX.
- Japanese output is a `職務経歴書`; JIS `履歴書` remains deferred.

---

### Task 1: Canonical candidate profile and version style

**Files:**
- Modify: `resume_agent/domain/models.py`
- Modify: `resume_agent/application/fact_base_service.py`
- Modify: `resume_agent/application/version_service.py`
- Modify: `resume_agent/api/schemas.py`
- Modify: `resume_agent/api/app.py`
- Test: `tests/test_profile_and_style.py`

**Interfaces:**
- Produces: `CandidateProfile(name, email, phone, location, links)` on `CareerFactBase.profile`.
- Produces: `FactBaseService.update_profile(fact_base_id, profile) -> CareerFactBase`.
- Produces: `VersionService.set_style(version_id, style) -> ResumeVersion`, storing the choice in `version.styles[version.locale]`.
- Produces: `PATCH /fact-bases/{id}/profile` and `PUT /versions/{id}/style`.

- [ ] **Step 1: Write failing profile and style tests**

```python
def test_profile_update_increments_revision_and_persists(tmp_path):
    client = TestClient(create_app(tmp_path / "resume.db"))
    base = client.post("/fact-bases", json={}).json()
    response = client.patch(
        f"/fact-bases/{base['id']}/profile",
        json={"name": "王明", "email": "wang@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["revision"] == base["revision"] + 1
    assert response.json()["profile"]["name"] == "王明"


def test_version_style_is_explicitly_persisted(tmp_path):
    client, version = create_version_fixture(tmp_path, locale="zh")
    response = client.put(
        f"/versions/{version['id']}/style",
        json={"style": "经典墨色"},
    )
    assert response.status_code == 200
    assert response.json()["styles"]["zh"] == "经典墨色"
```

- [ ] **Step 2: Run the targeted tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_profile_and_style.py -q`

Expected: collection/import or route failures because `CandidateProfile` and both endpoints do not exist.

- [ ] **Step 3: Implement the profile and style mutations**

Add the profile model and default:

```python
class CandidateProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = Field(default_factory=list)


class CareerFactBase(BaseModel):
    profile: CandidateProfile = Field(default_factory=CandidateProfile)
```

Implement `update_profile` with optimistic revision save, and implement `set_style` by deep-copying `version.styles`, setting the current locale key, and calling `save`. Add `ProfileUpdateRequest` and `VersionStyleRequest`, then expose both routes.

- [ ] **Step 4: Verify targeted and full tests**

Run: `.venv/bin/python -m pytest tests/test_profile_and_style.py -q && .venv/bin/python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_profile_and_style.py
git commit -m "feat: add resume profile and style settings"
```

---

### Task 2: Pure evidence-only resume renderer

**Files:**
- Create: `resume_agent/rendering/__init__.py`
- Create: `resume_agent/rendering/models.py`
- Create: `resume_agent/rendering/styles.py`
- Create: `resume_agent/rendering/renderer.py`
- Test: `tests/test_resume_renderer.py`

**Interfaces:**
- Produces: `STYLE_CATALOG: dict[str, dict[str, StyleTheme]]` and `default_style(locale: str) -> str`.
- Produces: `RenderedExperience`, `RenderWarning`, and `RenderedResume` Pydantic models.
- Produces: `ResumeRenderer.render(base: CareerFactBase, version: ResumeVersion) -> RenderedResume`.

- [ ] **Step 1: Write failing renderer behavior tests**

```python
def test_renderer_uses_selected_order_and_excludes_unverified():
    base, first, second = evidence_fixture()
    version = ResumeVersion(
        fact_base_id=base.id,
        name="Analyst",
        locale="zh",
        selected_experience_ids=[first.id, second.id],
        ordering=[second.id, first.id],
        base_revision=base.revision,
    )
    result = ResumeRenderer().render(base, version)
    assert [item.organization for item in result.experiences] == ["第二家公司", "第一家公司"]
    assert "未确认内容" not in result.markdown


def test_renderer_escapes_profile_and_fact_html():
    base, version = malicious_fixture("<script>alert(1)</script>")
    result = ResumeRenderer().render(base, version)
    assert "<script>" not in result.html
    assert "&lt;script&gt;" in result.html


@pytest.mark.parametrize("locale, heading", [("zh", "工作经历"), ("en", "Experience"), ("ja", "職務経歴")])
def test_renderer_localizes_headings_without_translating_facts(locale, heading):
    base, version = render_fixture(locale=locale)
    result = ResumeRenderer().render(base, version)
    assert heading in result.html
    assert "原始事实文本" in result.html
```

Also test unknown locale/style rejection, missing profile warnings, estimated fact warnings, stale revision warnings, selected-ID validation, linked skill aggregation, and deterministic output.

- [ ] **Step 2: Run renderer tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_resume_renderer.py -q`

Expected: import failure for `resume_agent.rendering`.

- [ ] **Step 3: Implement render models and style catalog**

Use these stable result fields:

```python
class RenderWarning(BaseModel):
    code: str
    message: str


class RenderedExperience(BaseModel):
    organization: str
    role: str
    period: str
    bullets: list[str]


class RenderedResume(BaseModel):
    version_id: UUID
    base_revision: int
    version_base_revision: int
    locale: str
    style: str
    title: str
    filename_stem: str
    candidate_name: str
    headline: str
    contact_line: str
    summary: str
    experiences: list[RenderedExperience]
    skills: list[str]
    markdown: str
    html: str
    warnings: list[RenderWarning]
```

Port the Notebook accent colors into immutable `StyleTheme` values and reject names outside the current locale catalog.

- [ ] **Step 4: Implement the pure renderer**

Resolve selection and ordering explicitly. Include values whose confidence is not `UNVERIFIED`, keep each source fact as its own bullet, and preserve dimension priority `ACTION, METHOD, RESULT, RESPONSIBILITY, CONTEXT, EVIDENCE`. Build the intermediate `RenderedExperience` list once; derive Markdown and HTML from that list. Escape with `html.escape(..., quote=True)` and sanitize the filename with an ASCII/CJK allowlist plus underscore replacement.

- [ ] **Step 5: Verify targeted and full tests**

Run: `.venv/bin/python -m pytest tests/test_resume_renderer.py -q && .venv/bin/python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/rendering Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_resume_renderer.py
git commit -m "feat: extract evidence-only resume renderer"
```

---

### Task 3: Export adapters and rendering API

**Files:**
- Create: `resume_agent/rendering/exporters.py`
- Create: `resume_agent/application/render_service.py`
- Modify: `resume_agent/api/app.py`
- Modify: `resume_agent/api/main.py`
- Modify: `pyproject.toml`
- Test: `tests/test_resume_exporters.py`
- Test: `tests/test_api_rendering.py`

**Interfaces:**
- Produces: `RenderFormat(str, Enum)` values `html`, `md`, `docx`, `pdf`.
- Produces: `ResumeExporter.export(rendered, format) -> ExportedFile`.
- Produces: `RenderEngineUnavailable` and injectable `PdfExporter(browser_candidates=...)`.
- Produces: `ResumeRenderService.preview(version_id) -> RenderedResume` and `export(version_id, format) -> ExportedFile`.
- Produces: `GET /versions/{id}/preview` and `GET /versions/{id}/export?format=...`.

- [ ] **Step 1: Write failing exporter tests**

```python
def test_docx_export_is_a_readable_office_zip(rendered_resume):
    exported = ResumeExporter().export(rendered_resume, RenderFormat.DOCX)
    assert exported.media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    with ZipFile(BytesIO(exported.content)) as archive:
        assert "word/document.xml" in archive.namelist()


def test_pdf_export_reports_missing_engine(rendered_resume):
    exporter = ResumeExporter(pdf_exporter=PdfExporter(browser_candidates=[]))
    with pytest.raises(RenderEngineUnavailable):
        exporter.export(rendered_resume, RenderFormat.PDF)
```

Test HTML/Markdown bytes and a fake executable PDF command path that writes a `%PDF-` fixture to the requested output.

- [ ] **Step 2: Write failing API rendering tests**

```python
def test_preview_is_read_only_and_contains_self_contained_html(client, populated_version):
    before = client.get(f"/versions/{populated_version['id']}").json()
    response = client.get(f"/versions/{populated_version['id']}/preview")
    after = client.get(f"/versions/{populated_version['id']}").json()
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.json()["html"]
    assert before == after


@pytest.mark.parametrize("format, media_type", [
    ("html", "text/html"),
    ("md", "text/markdown"),
    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
])
def test_export_content_types(client, populated_version, format, media_type):
    response = client.get(f"/versions/{populated_version['id']}/export?format={format}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
```

Also test 404, invalid format 422, cross-resource mismatch, safe `Content-Disposition`, and PDF engine 503.

- [ ] **Step 3: Run targeted tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_resume_exporters.py tests/test_api_rendering.py -q`

Expected: imports/routes fail because adapters and service do not exist.

- [ ] **Step 4: Implement adapters and dependency**

Add `python-docx>=1.1,<2` to core dependencies. `ResumeExporter` returns:

```python
class ExportedFile(BaseModel):
    filename: str
    media_type: str
    content: bytes
```

DOCX uses `Document()`, heading/paragraph/list APIs, and `BytesIO`. PDF writes HTML to a `TemporaryDirectory`, invokes the first available Chrome/Edge executable with `--headless=new`, `--no-pdf-header-footer`, and `--print-to-pdf=<path>`, verifies a non-empty `%PDF-` output, and returns bytes. Capture subprocess output and raise `RenderEngineUnavailable` without leaking local paths.

- [ ] **Step 5: Implement service and API routes**

Inject `ResumeRenderer` and `ResumeExporter` through `ServiceContainer`. Build `Response(content=..., media_type=..., headers={"Content-Disposition": ...})` for export. Add a `RenderEngineUnavailable` exception handler returning 503.

- [ ] **Step 6: Install and verify targeted/full tests**

Run: `.venv/bin/python -m pip install -e '.[dev]' && .venv/bin/python -m pytest tests/test_resume_exporters.py tests/test_api_rendering.py -q && .venv/bin/python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests Co-creation-projects/shiyuanyeming-hub-ResumeAgent/pyproject.toml
git commit -m "feat: expose resume preview and exports"
```

---

### Task 4: Typed client and live Streamlit preview

**Files:**
- Modify: `resume_agent/ui/client.py`
- Modify: `resume_agent/ui/app.py`
- Modify: `resume_agent/ui/components.py`
- Modify: `README.md`
- Test: `tests/test_ui_rendering_client.py`
- Modify: `tests/test_streamlit_app.py`

**Interfaces:**
- Produces: `HttpResumeAgentClient.update_profile`, `set_version_style`, `preview_version`, and `version_export_url`.
- Consumes: `RenderedResume`, profile/style endpoints, and browser-download export URLs.

- [ ] **Step 1: Write failing client tests**

```python
def test_client_parses_preview(mock_transport, preview_payload):
    client = make_client(mock_transport(preview_payload))
    result = client.preview_version(PREVIEW_VERSION_ID)
    assert result.version_id == PREVIEW_VERSION_ID
    assert result.html.startswith("<!DOCTYPE html>")


def test_export_url_is_absolute_and_encoded():
    client = HttpResumeAgentClient("http://127.0.0.1:8000")
    assert client.version_export_url(PREVIEW_VERSION_ID, "pdf") == (
        f"http://127.0.0.1:8000/versions/{PREVIEW_VERSION_ID}/export?format=pdf"
    )
```

Also verify profile/style request payloads and no automatic retries.

- [ ] **Step 2: Write failing AppTest preview test**

Extend the online fake client with one evidence-bearing version and `preview_version`. Assert that preview no longer shows “渲染服务尚未接入”, shows the selected version/style/warnings, and exposes HTML/Markdown download buttons plus DOCX/PDF links. Add an AppTest for the explicit candidate-profile save form.

- [ ] **Step 3: Run targeted tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_ui_rendering_client.py tests/test_streamlit_app.py -q`

Expected: missing client methods and old empty-state assertions fail.

- [ ] **Step 4: Implement client methods and profile editor**

Keep JSON preview parsing in the typed client. Store the base URL so `version_export_url` can safely compose a direct browser link. Add an evidence-workspace profile expander with an explicit `保存基本信息` submit button; no update occurs on rerun.

- [ ] **Step 5: Implement preview workspace**

Render the HTML with `streamlit.components.v1.html`. Show warning cards. Let the user choose a catalog style and click `保存样式`; do not persist on selectbox change alone. Use `st.download_button` with the already-returned `preview.html` and `preview.markdown`. Use `st.link_button` for DOCX and PDF so generation happens only when the browser requests the export URL.

- [ ] **Step 6: Update documentation and verify**

Document profile completion, locale behavior, style options, Chrome/Edge PDF requirement, and all four download formats. Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q resume_agent streamlit_app.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Run real dual-process smoke test**

Start Uvicorn and Streamlit on temporary local ports, create a fact base/version through HTTP, assert preview HTML is returned, assert DOCX is a ZIP, assert PDF begins `%PDF-` when Chrome is installed, and assert the Streamlit shell returns HTTP 200. Stop both processes cleanly.

- [ ] **Step 8: Commit**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/ui Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests Co-creation-projects/shiyuanyeming-hub-ResumeAgent/README.md
git commit -m "feat: connect live resume preview workspace"
```
