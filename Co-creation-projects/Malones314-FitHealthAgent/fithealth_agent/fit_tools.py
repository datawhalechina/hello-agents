"""fit_tools.py

Agent tools for editing parsed FIT workout sets:
  - UpdateSetTool      edit name / weight / reps
  - MergeSetsTool      merge sets with HR recomputation
  - DeleteSetTool      remove one erroneous active set
  - UndoLastEditTool / RestoreParsedSourceTool  recover pending edits
"""

from __future__ import annotations

from typing import Any

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from . import workout_store


class UpdateSetTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="update_set",
            description=(
                "Modify a training set: category name, weight_kg, or repetitions. "
                "Use index to identify which set to change."
            ),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="index",
                type="integer",
                description="Set index (1-based)",
                required=True,
            ),
            ToolParameter(
                name="category",
                type="string",
                description="New exercise name in Chinese, e.g. wotui or shenzun",
                required=False,
            ),
            ToolParameter(
                name="weight_kg",
                type="number",
                description="New weight in kg",
                required=False,
            ),
            ToolParameter(
                name="repetitions",
                type="integer",
                description="New repetition count",
                required=False,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        index = parameters.get("index")
        if not isinstance(index, int) or index < 1:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="index must be a positive integer",
            )
        result = workout_store.update_set(
            index=index,
            category=parameters.get("category"),
            weight_kg=parameters.get("weight_kg"),
            repetitions=parameters.get("repetitions"),
        )
        if "error" in result:
            return ToolResponse.error(code="UPDATE_FAILED", message=result["error"])
        return ToolResponse.success(
            text=(
                "Updated set "
                + str(index)
                + ": "
                + str(result["category"])
                + " "
                + str(result["weight_kg"])
                + "kg x "
                + str(result["repetitions"])
            ),
            data=result,
        )


class MergeSetsTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="merge_sets",
            description=(
                "Merge multiple training sets into one. Automatically recomputes avg_hr/max_hr "
                "from raw HR data over the merged time window. Use when the watch auto-paused "
                "and split one continuous set. Rest segments between the selected active sets "
                "are removed and included in the merged duration. reps=sum, weight=max, name=most frequent."
            ),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="indices",
                type="array",
                description="List of set indices to merge, e.g. [2, 3]",
                required=True,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        indices = parameters.get("indices")
        if not isinstance(indices, list) or len(indices) < 2:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="indices must be a list of at least 2 integers",
            )
        try:
            indices = [int(i) for i in indices]
        except (TypeError, ValueError):
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="indices must contain integers",
            )
        result = workout_store.merge_sets(indices)
        if "error" in result:
            return ToolResponse.error(code="MERGE_FAILED", message=result["error"])

        hr_info = ""
        if result.get("avg_hr") is not None:
            hr_info = (
                ", HR avg=" + str(result["avg_hr"])
                + " max=" + str(result["max_hr"]) + " bpm"
            )
        note = result.get("hr_note", "")
        return ToolResponse.success(
            text=(
                "Merged sets "
                + str(indices)
                + " into set "
                + str(result["index"])
                + ": "
                + str(result["category"])
                + " "
                + str(result["weight_kg"])
                + "kg x "
                + str(result["repetitions"])
                + hr_info
                + ". "
                + note
            ),
            data=result,
        )


class DeleteSetTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="delete_set",
            description=(
                "Delete one erroneous active strength-training set from the pending FIT workout. "
                "Use undo_last_edit if the deletion was mistaken."
            ),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="index",
                type="integer",
                description="Set index (1-based)",
                required=True,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        index = parameters.get("index")
        if not isinstance(index, int) or index < 1:
            return ToolResponse.error(
                code="INVALID_PARAM", message="index must be a positive integer"
            )
        result = workout_store.delete_set(index)
        if "error" in result:
            return ToolResponse.error(code="DELETE_FAILED", message=result["error"])
        return ToolResponse.success(
            text=f"Deleted set {index}. You can undo this edit if needed.", data=result
        )


class UndoLastEditTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="undo_last_edit",
            description="Undo the most recent pending FIT workout edit.",
        )

    def get_parameters(self) -> list[ToolParameter]:
        return []

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        result = workout_store.undo_last_edit()
        if "error" in result:
            return ToolResponse.error(code="UNDO_FAILED", message=result["error"])
        return ToolResponse.success(text="Undid the last training edit.", data=result)


class RestoreParsedSourceTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="restore_parsed_source",
            description=(
                "Restore the pending workout to the original parsed FIT result, discarding all pending edits."
            ),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return []

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        result = workout_store.restore_parsed_source()
        if "error" in result:
            return ToolResponse.error(code="RESTORE_FAILED", message=result["error"])
        return ToolResponse.success(
            text="Restored the original parsed FIT workout.", data=result
        )
