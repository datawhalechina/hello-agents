"""Markdown source reading and CV fact extraction."""

from pathlib import Path

from hello_agents import HelloAgentsLLM

from ..agents import ask, build_prompt
from ..contracts import CV
from ..prompts import CV_READER_PROMPT


class CVReaderService:
    """Read CV sources and extract facts using an injected model."""

    def __init__(self, llm: HelloAgentsLLM) -> None:
        self._llm = llm

    @staticmethod
    def read_source(path: Path) -> str:
        """Read a nonempty UTF-8 Markdown CV, retaining its physical lines."""
        if path.suffix.lower() != ".md":
            raise ValueError("简历输入必须为 Markdown (.md)")
        text = path.read_text(encoding="utf-8-sig")
        if not text.strip():
            raise ValueError("简历文件为空")
        return text

    def run(
        self,
        source: str,
        text: str,
        *,
        correction: tuple[CV, ValueError] | None = None,
    ) -> CV:
        """Format numbered CV lines as dynamic context and return validated facts."""
        prompt = build_prompt(
            CV,
            CV_READER_PROMPT,
            {
                "source": source,
                "lines": [
                    {"line": i, "text": line}
                    for i, line in enumerate(text.splitlines(), 1)
                ],
            },
            correction=correction,
        )
        return ask(self._llm, "cv_reader", CV, prompt)
