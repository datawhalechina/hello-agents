from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from finance_agent.acceptance_rule_engine import write_json
from finance_agent.report_constants import REQUIRED_CALCULATED_DATA_KEYS, REQUIRED_ROW_KEYS

if TYPE_CHECKING:
    from finance_agent.report_agents import AgentNode


def parse_llm_json(raw_output: str, agent_name: str) -> dict[str, Any]:
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_output, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {
        "agent": agent_name,
        "status": "llm_output_parse_error",
        "raw_output": raw_output,
        "next_input": {},
    }


def normalize_agent_output(agent_name: str, parsed_output: dict[str, Any], input_json: dict[str, Any]) -> dict[str, Any]:
    calculated_data = input_json.get("calculated_data", {})
    next_input = input_json.get("next_input", {})
    validate_calculated_data(agent_name, calculated_data)
    validate_llm_reported_data_shape(agent_name, parsed_output, calculated_data)

    normalized = dict(parsed_output)
    normalized["agent"] = agent_name
    normalized.setdefault("status", "ok")
    normalized["data"] = calculated_data
    normalized["next_input"] = next_input
    return normalized


def validate_llm_reported_data_shape(
    agent_name: str,
    parsed_output: dict[str, Any],
    calculated_data: dict[str, Any],
) -> None:
    llm_data = parsed_output.get("data")
    if llm_data is None:
        return
    if not isinstance(llm_data, dict):
        raise ValueError(f"{agent_name} LLM output data must be a JSON object when present.")

    illegal_keys = sorted(set(llm_data) - set(calculated_data))
    if illegal_keys:
        raise ValueError(f"{agent_name} LLM output data contains illegal keys: {', '.join(illegal_keys)}")

    for (row_agent, field_name), row_keys in REQUIRED_ROW_KEYS.items():
        if row_agent != agent_name or field_name not in llm_data:
            continue
        rows = llm_data[field_name]
        if not isinstance(rows, list):
            raise ValueError(f"{agent_name} LLM output data.{field_name} must be a list.")
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ValueError(f"{agent_name} LLM output data.{field_name}[{index}] must be a JSON object.")
            calculated_rows = calculated_data.get(field_name, [])
            calculated_row_keys = set()
            if isinstance(calculated_rows, list) and calculated_rows and isinstance(calculated_rows[0], dict):
                calculated_row_keys = set(calculated_rows[0])
            allowed_row_keys = row_keys | calculated_row_keys
            illegal_row_keys = sorted(set(row) - allowed_row_keys)
            missing_row_keys = sorted(row_keys - set(row))
            if illegal_row_keys or missing_row_keys:
                details = []
                if illegal_row_keys:
                    details.append(f"illegal keys: {', '.join(illegal_row_keys)}")
                if missing_row_keys:
                    details.append(f"missing keys: {', '.join(missing_row_keys)}")
                raise ValueError(f"{agent_name} LLM output data.{field_name}[{index}] has invalid shape ({'; '.join(details)}).")


def validate_calculated_data(agent_name: str, calculated_data: Any) -> None:
    if not isinstance(calculated_data, dict):
        raise ValueError(f"{agent_name} calculated_data must be a JSON object.")

    required_keys = REQUIRED_CALCULATED_DATA_KEYS.get(agent_name, set())
    missing_keys = sorted(required_keys - calculated_data.keys())
    if missing_keys:
        raise ValueError(f"{agent_name} calculated_data is missing required keys: {', '.join(missing_keys)}")

    for (row_agent, field_name), row_keys in REQUIRED_ROW_KEYS.items():
        if row_agent != agent_name or field_name not in calculated_data:
            continue
        rows = calculated_data[field_name]
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise ValueError(f"{agent_name}.{field_name} must be a list.")
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ValueError(f"{agent_name}.{field_name}[{index}] must be a JSON object.")
            missing_row_keys = sorted(row_keys - row.keys())
            if missing_row_keys:
                raise ValueError(
                    f"{agent_name}.{field_name}[{index}] is missing required keys: "
                    f"{', '.join(missing_row_keys)}"
                )


def extract_agent_data(agent_output: dict[str, Any]) -> dict[str, Any]:
    if isinstance(agent_output.get("data"), dict):
        return agent_output["data"]
    return agent_output.get("next_input") or agent_output


def save_agent_run(
    path: Path,
    agent: AgentNode,
    input_json: dict[str, Any],
    raw_output: str,
    parsed_output: dict[str, Any] | str,
) -> None:
    write_json(
        {
            "agent": agent.name,
            "prompt": agent.prompt,
            "input_json": input_json,
            "output_format": agent.output_format,
            "raw_output": raw_output,
            "parsed_output": parsed_output,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        path,
    )


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
