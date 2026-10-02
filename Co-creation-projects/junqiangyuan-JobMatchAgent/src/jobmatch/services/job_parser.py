"""CSV source parsing and job qualification extraction."""

import csv
from pathlib import Path

from hello_agents import HelloAgentsLLM

from ..agents import ask, build_prompt
from ..contracts import JobRow, ParsedJobs
from ..prompts import JOB_PARSER_PROMPT

COLUMNS = ("岗位名称", "工作职责", "任职资格", "公司名字", "公司地址")


class JobParserService:
    """Parse CSV sources and extract qualifications using an injected model."""

    def __init__(self, llm: HelloAgentsLLM) -> None:
        self._llm = llm

    @staticmethod
    def read_source(path: Path) -> list[JobRow]:
        """Parse UTF-8 CSV, retaining order and physical multiline record identities."""
        if path.suffix.lower() != ".csv":
            raise ValueError("职位输入必须为 CSV (.csv)")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            headers = next(reader, [])
            if len(headers) != len(COLUMNS) or set(headers) != set(COLUMNS):
                raise ValueError(f"CSV 表头必须包含 {','.join(COLUMNS)}")
            rows = []
            next_line = reader.line_num + 1
            for values in reader:
                start_line = next_line
                next_line = reader.line_num + 1
                if not values:
                    continue
                if len(values) != len(headers):
                    raise ValueError(f"CSV 第 {start_line} 行列数错误")
                rows.append(JobRow(start_line, dict(zip(headers, values))))
        if not rows:
            raise ValueError("CSV 没有职位行")
        return rows

    def run(
        self,
        source: str,
        rows: list[JobRow],
        *,
        correction: tuple[ParsedJobs, ValueError] | None = None,
    ) -> ParsedJobs:
        """Format CSV records as dynamic context and return validated qualifications."""
        prompt = build_prompt(
            ParsedJobs,
            JOB_PARSER_PROMPT,
            {"source": source, "rows": [{"row": row.row, **row.fields} for row in rows]},
            correction=correction,
        )
        return ask(self._llm, "job_opportunities_parser", ParsedJobs, prompt)
