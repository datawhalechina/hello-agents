# Vietnamese Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a complete Vietnamese edition of the main Hello-Agents book under `docs/vi/` without changing or removing the Chinese and English editions.

**Architecture:** Translate each chapter by comparing its Chinese and English source files, using Chinese as the completeness authority and English as the terminology reference. Keep one isolated Vietnamese documentation tree with its own sidebar, shared image assets, and language links from the existing landing pages. Commit by book part so every commit is reviewable and no translation batch mixes unrelated project content.

**Tech Stack:** Markdown, Docsify-compatible navigation, Mermaid, Git, repository-local documentation assets.

---

## File map

**Create:**

- `docs/vi/README.md` — Vietnamese landing page and table of contents.
- `docs/vi/Preface.md` — Vietnamese preface.
- `docs/vi/_sidebar.md` — Vietnamese navigation for all five parts.
- `docs/vi/chapter1/Chuong1-Gioi-thieu-ve-Agent.md`
- `docs/vi/chapter2/Chuong2-Lich-su-phat-trien-cua-Agent.md`
- `docs/vi/chapter3/Chuong3-Co-so-mo-hinh-ngon-ngu-lon.md`
- `docs/vi/chapter4/Chuong4-Xay-dung-cac-mo-hinh-Agent-kinh-dien.md`
- `docs/vi/chapter5/Chuong5-Xay-dung-Agent-voi-nen-tang-low-code.md`
- `docs/vi/chapter6/Chuong6-Thuc-hanh-phat-trien-voi-framework.md`
- `docs/vi/chapter7/Chuong7-Xay-dung-framework-Agent-cua-ban.md`
- `docs/vi/chapter8/Chuong8-Bo-nho-va-truy-xuat.md`
- `docs/vi/chapter9/Chuong9-Ky-thuat-ngu-canh.md`
- `docs/vi/chapter10/Chuong10-Giao-thuc-giao-tiep-Agent.md`
- `docs/vi/chapter11/Chuong11-Agentic-RL.md`
- `docs/vi/chapter12/Chuong12-Danh-gia-hieu-nang-Agent.md`
- `docs/vi/chapter13/Chuong13-Tro-ly-du-lich-thong-minh.md`
- `docs/vi/chapter14/Chuong14-Agent-nghien-cuu-chuyen-sau-tu-dong.md`
- `docs/vi/chapter15/Chuong15-Xay-dung-thi-tran-cyber.md`
- `docs/vi/chapter16/Chuong16-Do-an-tot-nghiep.md`

**Modify:**

- `docs/README.md` — add the Vietnamese language link.
- `docs/README_EN.md` — add the Vietnamese language link.

**Translation invariant for every created document:** preserve heading hierarchy, tables, block quotes, footnotes, HTML blocks, equations, code fences, executable code, external URLs, and source attribution. Translate prose, headings, captions, warnings, exercises, table labels, image alt text, and Mermaid presentation text. Internal links to translated chapters must target the Vietnamese tree; links to code and external resources remain unchanged.

### Task 1: Vietnamese landing page, preface, and navigation

**Files:**
- Create: `docs/vi/README.md`
- Create: `docs/vi/Preface.md`
- Create: `docs/vi/_sidebar.md`
- Modify: `docs/README.md:1-3`
- Modify: `docs/README_EN.md:1-3`
- Reference: `docs/README.md`
- Reference: `docs/README_EN.md`
- Reference: `docs/前言.md`
- Reference: `docs/Preface.md`
- Reference: `docs/_sidebar.md`
- Reference: `docs/_sidebar_en.md`

- [ ] **Step 1: Translate the landing page**

Create `docs/vi/README.md` with all sections from the current Chinese landing page. Compare each section against `docs/README_EN.md`, keep Chinese-only updates, use Vietnamese chapter links from the file map, and prefix shared landing-page image paths with `../images/`.

- [ ] **Step 2: Translate the preface**

Create `docs/vi/Preface.md` from `docs/前言.md`, using `docs/Preface.md` to normalize technical terms and proper nouns. Preserve all attribution and formatting.

- [ ] **Step 3: Build complete Vietnamese navigation**

Create `docs/vi/_sidebar.md` with `README.md`, `Preface.md`, all five part headings, and all 16 chapter paths exactly as listed in the file map. Use paths relative to `docs/vi/`.

- [ ] **Step 4: Add language switching**

Change the language selector in `docs/README.md` and `docs/README_EN.md` to include `[Tiếng Việt](./vi/README.md)`. Add `[中文](../README.md)` and `[English](../README_EN.md)` to the Vietnamese landing page.

- [ ] **Step 5: Verify the entry points**

Run:

```bash
git diff --check -- docs/README.md docs/README_EN.md docs/vi/README.md docs/vi/Preface.md docs/vi/_sidebar.md
```

Expected: no output and exit status 0. Manually confirm that `_sidebar.md` contains 18 document links: landing page, preface, and 16 chapters.

- [ ] **Step 6: Commit the entry points**

```bash
git add docs/README.md docs/README_EN.md docs/vi/README.md docs/vi/Preface.md docs/vi/_sidebar.md
git commit -m "docs(vi): add book navigation and introduction"
```

### Task 2: Translate Part I — agent and language-model fundamentals

**Files:**
- Create: `docs/vi/chapter1/Chuong1-Gioi-thieu-ve-Agent.md`
- Create: `docs/vi/chapter2/Chuong2-Lich-su-phat-trien-cua-Agent.md`
- Create: `docs/vi/chapter3/Chuong3-Co-so-mo-hinh-ngon-ngu-lon.md`
- Reference: `docs/chapter1/第一章 初识智能体.md`
- Reference: `docs/chapter1/Chapter1-Introduction-to-Agents.md`
- Reference: `docs/chapter2/第二章 智能体发展史.md`
- Reference: `docs/chapter2/Chapter2-History-of-Agents.md`
- Reference: `docs/chapter3/第三章 大语言模型基础.md`
- Reference: `docs/chapter3/Chapter3-Fundamentals-of-Large-Language-Models.md`

- [ ] **Step 1: Translate Chapter 1 completely**

Translate every prose section, table, caption, callout, exercise, and Mermaid label. Change each chapter image prefix from `../images/` to `../../images/`; preserve code and formulas byte-for-byte unless a code comment is explanatory prose.

- [ ] **Step 2: Translate Chapter 2 completely**

Apply the same invariant. Preserve historical names, dates, paper titles, citations, and external links; translate their surrounding explanations.

- [ ] **Step 3: Translate Chapter 3 completely**

Apply the same invariant. Keep model names, mathematical notation, token examples, API names, and executable snippets unchanged.

- [ ] **Step 4: Check Part I formatting**

Run:

```bash
git diff --check -- docs/vi/chapter1 docs/vi/chapter2 docs/vi/chapter3
```

Expected: no output and exit status 0. Compare heading and code-fence counts for each Vietnamese file with its Chinese source; investigate every mismatch rather than accepting a lower count.

- [ ] **Step 5: Commit Part I**

```bash
git add docs/vi/chapter1 docs/vi/chapter2 docs/vi/chapter3
git commit -m "docs(vi): translate agent fundamentals"
```

### Task 3: Translate Part II — building LLM agents

**Files:**
- Create: `docs/vi/chapter4/Chuong4-Xay-dung-cac-mo-hinh-Agent-kinh-dien.md`
- Create: `docs/vi/chapter5/Chuong5-Xay-dung-Agent-voi-nen-tang-low-code.md`
- Create: `docs/vi/chapter6/Chuong6-Thuc-hanh-phat-trien-voi-framework.md`
- Create: `docs/vi/chapter7/Chuong7-Xay-dung-framework-Agent-cua-ban.md`
- Reference: Chinese and English chapter files under `docs/chapter4/` through `docs/chapter7/`

- [ ] **Step 1: Translate Chapter 4 completely**

Preserve the ReAct, Plan-and-Solve, and Reflection identifiers and all executable examples. Translate conceptual explanations, comments intended for readers, prompts shown as prose, figure captions, and exercises.

- [ ] **Step 2: Translate Chapter 5 completely**

Preserve Coze, Dify, n8n, configuration keys, workflow node names that must match each product, and URLs. Translate narrative instructions and UI descriptions while retaining the original UI label in parentheses where readers must locate that exact control.

- [ ] **Step 3: Translate Chapter 6 completely**

Preserve AutoGen, AgentScope, CAMEL, LangGraph, package names, imports, API signatures, and command lines. Translate all surrounding instructional content.

- [ ] **Step 4: Translate Chapter 7 completely**

Preserve framework source code and machine-readable prompt templates. Translate prose and explanatory prompt examples that are not consumed by code.

- [ ] **Step 5: Check Part II formatting**

Run:

```bash
git diff --check -- docs/vi/chapter4 docs/vi/chapter5 docs/vi/chapter6 docs/vi/chapter7
```

Expected: no output and exit status 0. Compare heading, table-delimiter, image, and code-fence counts with each Chinese source; resolve all missing structures.

- [ ] **Step 6: Commit Part II**

```bash
git add docs/vi/chapter4 docs/vi/chapter5 docs/vi/chapter6 docs/vi/chapter7
git commit -m "docs(vi): translate agent construction chapters"
```

### Task 4: Translate Part III — advanced topics

**Files:**
- Create: `docs/vi/chapter8/Chuong8-Bo-nho-va-truy-xuat.md`
- Create: `docs/vi/chapter9/Chuong9-Ky-thuat-ngu-canh.md`
- Create: `docs/vi/chapter10/Chuong10-Giao-thuc-giao-tiep-Agent.md`
- Create: `docs/vi/chapter11/Chuong11-Agentic-RL.md`
- Create: `docs/vi/chapter12/Chuong12-Danh-gia-hieu-nang-Agent.md`
- Reference: Chinese and English chapter files under `docs/chapter8/` through `docs/chapter12/`

- [ ] **Step 1: Translate Chapters 8 and 9 completely**

Keep `Memory`, `RAG`, `embedding`, context-window terminology, identifiers, formulas, code, and commands stable. Translate definitions and explanatory labels consistently.

- [ ] **Step 2: Translate Chapter 10 completely**

Keep protocol names and normative keywords such as MCP, A2A, ANP, JSON-RPC, HTTP, method names, schemas, payloads, and wire examples unchanged. Translate protocol explanations and diagram labels that are not literal wire values.

- [ ] **Step 3: Translate Chapter 11 completely**

Keep SFT, RL, PPO, GRPO, reward-model names, equations, dataset fields, training parameters, code, and shell commands unchanged. Translate pedagogical text and non-machine-readable examples.

- [ ] **Step 4: Translate Chapter 12 completely**

Keep benchmark names, metric symbols, model identifiers, JSON fields, evaluation commands, and sample machine outputs unchanged. Translate evaluation methodology and interpretation.

- [ ] **Step 5: Check Part III formatting**

Run:

```bash
git diff --check -- docs/vi/chapter8 docs/vi/chapter9 docs/vi/chapter10 docs/vi/chapter11 docs/vi/chapter12
```

Expected: no output and exit status 0. Compare structural counts with Chinese sources, paying special attention to Mermaid fences, nested HTML, equations, and long tables.

- [ ] **Step 6: Commit Part III**

```bash
git add docs/vi/chapter8 docs/vi/chapter9 docs/vi/chapter10 docs/vi/chapter11 docs/vi/chapter12
git commit -m "docs(vi): translate advanced agent topics"
```

### Task 5: Translate Part IV — comprehensive case studies

**Files:**
- Create: `docs/vi/chapter13/Chuong13-Tro-ly-du-lich-thong-minh.md`
- Create: `docs/vi/chapter14/Chuong14-Agent-nghien-cuu-chuyen-sau-tu-dong.md`
- Create: `docs/vi/chapter15/Chuong15-Xay-dung-thi-tran-cyber.md`
- Reference: Chinese and English chapter files under `docs/chapter13/` through `docs/chapter15/`

- [ ] **Step 1: Translate Chapter 13 completely**

Keep itinerary schemas, MCP calls, agent names used by code, configuration, and commands unchanged. Translate user-facing examples unless exact output matching is required.

- [ ] **Step 2: Translate Chapter 14 completely**

Keep research-agent class names, API names, prompts consumed directly by code, schemas, citations, and commands unchanged. Translate architecture explanations and reader-facing prompt demonstrations.

- [ ] **Step 3: Translate Chapter 15 completely**

Keep game entities referenced by code, database fields, endpoints, commands, and source snippets unchanged. Translate narrative dialogue only where it is documentation rather than fixture data.

- [ ] **Step 4: Check Part IV formatting**

Run:

```bash
git diff --check -- docs/vi/chapter13 docs/vi/chapter14 docs/vi/chapter15
```

Expected: no output and exit status 0. Compare all headings, images, tables, code fences, and Mermaid blocks with the Chinese sources.

- [ ] **Step 5: Commit Part IV**

```bash
git add docs/vi/chapter13 docs/vi/chapter14 docs/vi/chapter15
git commit -m "docs(vi): translate agent case studies"
```

### Task 6: Translate Part V — graduation project

**Files:**
- Create: `docs/vi/chapter16/Chuong16-Do-an-tot-nghiep.md`
- Reference: `docs/chapter16/第十六章 毕业设计.md`
- Reference: `docs/chapter16/Chapter16-Graduation-Project.md`

- [ ] **Step 1: Translate Chapter 16 completely**

Preserve requirements, evaluation criteria, commands, source snippets, URLs, and proper nouns. Translate every instruction, rubric label, recommendation, and future-outlook section.

- [ ] **Step 2: Check Part V formatting**

Run:

```bash
git diff --check -- docs/vi/chapter16
```

Expected: no output and exit status 0. Compare headings, tables, images, code fences, and Mermaid blocks with the Chinese source.

- [ ] **Step 3: Commit Part V**

```bash
git add docs/vi/chapter16
git commit -m "docs(vi): translate graduation project"
```

### Task 7: Validate the complete Vietnamese edition

**Files:**
- Verify: `docs/vi/**/*.md`
- Verify: `docs/README.md`
- Verify: `docs/README_EN.md`

- [ ] **Step 1: Validate the deliverable inventory**

Confirm that the 19 files in the file map exist, are non-empty, and that `docs/vi/_sidebar.md` links to every Vietnamese document exactly once.

- [ ] **Step 2: Validate local links and images**

Resolve every relative Markdown link and HTML image source from its containing Vietnamese file. Fail validation for every missing local target; ignore only absolute HTTP(S), mail, and anchor-only targets.

- [ ] **Step 3: Validate structural preservation**

For each chapter pair, compare counts for ATX headings, fenced code blocks by language, Markdown images, Markdown tables, Mermaid blocks, HTML details blocks, and displayed equations. Review every difference against the source and correct unintended omissions.

- [ ] **Step 4: Search for untranslated prose**

Search `docs/vi/` for CJK characters and long English prose. Classify every match: translate reader-facing prose; retain only proper nouns, citations, code, literal output, protocol fields, or technical terms covered by the design.

- [ ] **Step 5: Run repository formatting checks**

Run:

```bash
git diff --check
```

Expected: no output and exit status 0.

- [ ] **Step 6: Smoke-test the rendered documentation**

Start the repository’s existing documentation server from its documented command, open the Vietnamese landing page, then navigate to the preface and Chapters 1, 8, 12, and 16. Confirm navigation, headings, tables, code blocks, Mermaid diagrams, and images render without broken paths. Also follow the language links from the Chinese and English landing pages to Vietnamese.

- [ ] **Step 7: Correct validation findings and commit only if needed**

If validation requires corrections, stage only those documentation files and commit:

```bash
git add docs/README.md docs/README_EN.md docs/vi
git commit -m "docs(vi): correct translation links and formatting"
```

If no corrections are needed, do not create an empty commit.
