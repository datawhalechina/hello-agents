"""Evidence-based match evaluation agent."""

from hello_agents import HelloAgentsLLM

from ..agents import ask, build_prompt
from ..contracts import CV, JobRow, Matches, ParsedJobs
from ..prompts import MATCHER_PROMPT


class MatcherService:
    """Evaluate validated parser results using an injected model."""

    def __init__(self, llm: HelloAgentsLLM) -> None:
        self._llm = llm

    def run(
        self,
        cv: CV,
        jobs: ParsedJobs,
        source: str,
        rows: list[JobRow],
        *,
        correction: tuple[Matches, ValueError] | None = None,
    ) -> Matches:
        """Return contract-validated assessments; source rows provide traceability only."""
        prompt = build_prompt(
            Matches,
            MATCHER_PROMPT,
            {
                "cv": cv.model_dump(),
                "jobs": {
                    **jobs.model_dump(),
                    "source": source,
                    "source_rows": [{"row": row.row, **row.fields} for row in rows],
                },
            },
            correction=correction,
        )
        return ask(self._llm, "matcher", Matches, prompt)
