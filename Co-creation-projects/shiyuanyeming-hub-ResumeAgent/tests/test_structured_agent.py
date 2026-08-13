import pytest
from pydantic import BaseModel

from resume_agent.agents.structured import (
    AgentOutputError,
    extract_json_object,
    run_structured,
)


class Reply(BaseModel):
    question: str


class FakeRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def run(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def test_extracts_json_from_markdown_fence():
    result = extract_json_object('```json\n{"question": "What changed?"}\n```')

    assert result == {"question": "What changed?"}


def test_extracts_first_complete_object_from_surrounding_text():
    result = extract_json_object(
        'Here is the result: {"question": "What changed?"} Thank you.'
    )

    assert result == {"question": "What changed?"}


def test_invalid_output_retries_once_with_validation_feedback():
    runner = FakeRunner(['{"wrong": "field"}', '{"question": "What changed?"}'])

    result = run_structured(runner, "Write one question", Reply)

    assert result.question == "What changed?"
    assert len(runner.prompts) == 2
    assert "validation" in runner.prompts[1].lower()
    assert "question" in runner.prompts[1]


def test_two_invalid_outputs_raise_typed_error():
    runner = FakeRunner(["not json", '{"wrong": "again"}'])

    with pytest.raises(AgentOutputError) as error:
        run_structured(runner, "Write one question", Reply)

    assert error.value.attempts == 2
    assert len(runner.prompts) == 2
