# ResumeAgent Resume Rendering Design

## Goal

Turn a job-specific `ResumeVersion` and its confirmed career evidence into a real, safe preview that the user can download as HTML, Markdown, DOCX, or PDF. The renderer must remain deterministic: it may reorganize confirmed facts, but it must never invent, translate, or strengthen them.

## Product Decisions

- The preview workspace renders one selected version at a time.
- Chinese, English, and Japanese use localized headings and locale-specific visual styles. Confirmed fact text stays in its original language until a later translation/polishing agent is explicitly added.
- The Japanese MVP is a `職務経歴書`. A JIS `履歴書` is deferred because the current fact model does not yet collect birth date, education events, photo, address, or licenses.
- Candidate name and contact details are canonical fact-base profile data, not fields copied into each version.
- Preview is generated on demand and is not written into the repository. The API remains the source of truth, so a rerun cannot accidentally create duplicate artifacts.
- A stale version may still be previewed, but the result contains a warning that its base revision is behind the current fact base.

## Architecture

### Canonical profile

Add `CandidateProfile` to `CareerFactBase` with `name`, `email`, `phone`, `location`, and `links`. Updating it is an explicit fact-base mutation that increments the base revision and therefore makes old versions stale.

### Pure rendering core

`resume_agent/rendering/models.py` defines the transport-neutral render result, warnings, style catalog, and export format enum. `resume_agent/rendering/renderer.py` contains a pure `ResumeRenderer.render(base, version)` operation. It:

1. Resolves only `version.selected_experience_ids`, in `version.ordering` order.
2. Uses only confirmed `FactValue` instances.
3. Creates evidence bullets from action, method, result, responsibility, context, and evidence statements without combining unrelated facts into new causal claims.
4. Escapes every user-controlled value before placing it in HTML.
5. Produces Markdown and a self-contained A4 HTML document from the same intermediate sections.
6. Returns warnings for missing profile data, empty evidence, source-language mismatch, and stale versions.

The first style set migrates the Notebook's color families:

- `zh`: `藏青现代`, `经典墨色`, `清新青碧`
- `en`: `青灰Teal`, `经典黑白`, `现代蓝`
- `ja`: `藏青JIS`, `墨黑JIS`, `蓝灰JIS`

### Export adapters

`resume_agent/rendering/exporters.py` converts an already rendered result:

- HTML and Markdown are returned directly as UTF-8 bytes.
- DOCX is generated with `python-docx` from the render result's structured sections, keeping an ATS-safe single-column document.
- PDF is produced from the same HTML using headless Chrome/Edge. The adapter uses a temporary directory and never exposes local paths. If no browser engine is installed, it raises `RenderEngineUnavailable` and the API returns HTTP 503.

### Application and API

`ResumeRenderService` joins the version repository and fact-base repository and rejects cross-resource mismatches. The API adds:

- `PATCH /fact-bases/{id}/profile`
- `PUT /versions/{id}/style`
- `GET /versions/{id}/preview`
- `GET /versions/{id}/export?format=html|md|docx|pdf`

The export response uses a safe filename and a format-specific media type. No mutation endpoint is called during preview rendering.

### Streamlit workspace

The evidence workspace gains an explicit candidate-profile form. The preview workspace gains:

- version selection;
- style selection persisted to that version;
- visible freshness and evidence warnings;
- an embedded HTML preview;
- enabled HTML, Markdown, DOCX, and PDF download buttons;
- an actionable PDF-engine message if the API reports 503.

Downloads are requested only when their button is rendered/clicked; no file is written into `outputs/` and no old Notebook artifact is treated as current.

## Error Handling

- Unknown selected experience IDs are rejected when a version is created and checked again during rendering.
- Unsupported locale, style, or export format returns HTTP 422.
- A missing version/fact base returns HTTP 404.
- A missing PDF engine returns HTTP 503 without affecting HTML, Markdown, or DOCX preview/download.
- Malicious HTML in any profile or evidence field is escaped and tested.

## Testing

- Pure renderer tests cover selection/order, confirmed-only facts, locale labels, style validation, staleness warnings, and HTML escaping.
- Exporter tests validate MIME-ready bytes, a readable DOCX ZIP, and PDF adapter success/failure with an injected browser command.
- API tests cover profile revision updates, preview purity, all export content types, style persistence, and PDF 503 mapping.
- HTTP-client tests cover typed preview parsing and binary downloads.
- Streamlit AppTest covers a real preview state, style selection, warnings, and enabled download controls.
- Final verification runs the entire pytest suite, `compileall`, `git diff --check`, and a real Uvicorn/Streamlit smoke test.

## Deferred Work

- LLM translation and wording polish with per-sentence provenance.
- HR/ATS scoring and JD keyword-gap analysis.
- Japanese JIS `履歴書` and education/certification/profile expansion.
- Persistent artifact history, cloud storage, and signed download URLs.
