# ResumeAgent Public MVP Design

## Objective

Turn the current tutorial contribution into a usable standalone portfolio project while preserving the restored original workbench layout. Publish it as the public repository `shiyuanyeming-hub/ResumeAgent` with Chinese, Japanese, and English project documentation.

## Product scope

This pass is a public MVP, not a final visual redesign. It keeps the white two-column workbench and improves the parts that block real use:

- make the active candidate file visible and switchable;
- clarify interview progress and prevent a mentor question from feeling stuck;
- keep the confirmed-fact, JD-version, preview, edit, and export flow intact;
- improve small-screen behavior and action feedback without gradients, glow, or promotional AI copy.

## Mentor behavior

When an answer supplies a different evidence dimension from the one asked, the fact is still accepted after confirmation, but the unanswered dimension records an attempt. A later question for that gap uses dimension-specific recall anchors instead of repeating the same sentence. After two explicit “暂时想不到” responses, the gap is skipped as before. The deterministic planner remains responsible for selecting one evidence gap; the LLM remains responsible only for fact extraction and wording.

The chat panel shows a compact evidence-progress summary derived from the existing quality endpoint. It does not invent a new score or hide the six evidence dimensions.

## Interface changes

The header gains an existing-file selector so multiple candidate files are usable. The sample action is demoted to onboarding/demo use. Interview controls state whether the user should answer, confirm a fact, or continue. Responsive behavior keeps the chat composer and document toolbar reachable.

No new frontend framework or build step is introduced. The browser remains same-origin ES modules served by FastAPI.

## Documentation and publication

`README.md` is the Chinese landing page and links to `README.ja.md` and `README.en.md`. All three explain the same verified feature set, architecture, local startup, model configuration, privacy model, test commands, and current limitations. Claims from the notebook that are not exposed in the default workbench are clearly separated as legacy/demo capabilities.

The standalone repository is created from the project subdirectory using a Git subtree split, preserving relevant history without publishing the surrounding HelloAgents monorepo. The public default branch is `main`; the existing tutorial fork and branch remain untouched.

## Verification

- Unit/API tests cover mismatched-answer follow-up escalation and exact one-question behavior.
- Browser client tests cover safe UI state and any new pure helpers.
- Playwright verifies file switching, mentor progression, version preview, editing, and responsive layouts with zero console errors.
- Full Python and Node suites, compile checks, clean diff checks, and a clean standalone export are required before publication.

## Non-goals

- authentication, billing, hosted databases, analytics, and cloud deployment;
- a new visual identity or component framework;
- autonomous rewriting of unconfirmed facts;
- full Japanese JIS personal-data fields and photo handling.
