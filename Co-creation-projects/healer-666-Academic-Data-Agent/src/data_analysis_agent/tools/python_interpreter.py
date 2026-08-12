"""Python execution sandbox tool."""

from __future__ import annotations

import contextlib
import io
import json
import os
import traceback
import warnings
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from hello_agents.tools import Tool, ToolParameter

from ..plotting import (
    apply_publication_style,
    beautify_axes,
    configure_plotting_backend,
    ensure_ascii_sequence,
    ensure_ascii_text,
    get_plot_font_family,
    prepare_month_index,
    save_figure,
)
from ..tool_protocol import ToolErrorCode, ToolResponse


class PythonInterpreterTool(Tool):
    """Isolated Python execution sandbox for local data analysis."""

    def __init__(self):
        super().__init__(
            name="PythonInterpreterTool",
            description=(
                "This is a Python interpreter. You can use installed scientific libraries such as pandas, numpy, scipy, statsmodels, matplotlib, and related tooling when they are available in the local environment. "
                "Extremely important: you must use print() to display every result, statistic, file path, or conclusion you want to observe, otherwise you will receive no Observation. "
                "Each execution runs in a fresh isolated namespace, so your code must include every import and variable definition it depends on. "
                "The namespace already includes plotting helpers: plt, sns, apply_publication_style(), beautify_axes(), prepare_month_index(), get_plot_font_family(), ensure_ascii_text(), ensure_ascii_sequence(), and save_figure(). "
                "Use save_figure(output_path) as the only standard figure-saving API. Focus on plotting the data, then call save_figure(path) directly. "
                "Do not pass fig manually, do not call plt.tight_layout() manually, and do not redefine your own save_fig/save_plot helper unless absolutely necessary. "
                "If data_context warns that N < 30, prioritize non-parametric tests when appropriate and remain highly cautious about normality assumptions."
            ),
        )
        plt, sns = apply_publication_style()
        self._base_namespace = {
            "__builtins__": __builtins__,
            "__name__": "__main__",
            "pd": pd,
            "np": np,
            "json": json,
            "os": os,
            "Path": Path,
            "io": io,
            "warnings": warnings,
            "plt": plt,
            "sns": sns,
            "apply_publication_style": apply_publication_style,
            "beautify_axes": beautify_axes,
            "configure_plotting_backend": configure_plotting_backend,
            "ensure_ascii_text": ensure_ascii_text,
            "ensure_ascii_sequence": ensure_ascii_sequence,
            "get_plot_font_family": get_plot_font_family,
            "prepare_month_index": prepare_month_index,
            "save_figure": save_figure,
        }

    def _build_namespace(self) -> Dict[str, Any]:
        return dict(self._base_namespace)

    def execute(self, parameters: Dict[str, Any]) -> ToolResponse:
        code = parameters.get("code", parameters.get("input", ""))
        if not isinstance(code, str) or not code.strip():
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="PythonInterpreterTool expected a non-empty 'code' string.",
            )

        namespace = self._build_namespace()
        redirected_output = io.StringIO()
        redirected_error = io.StringIO()

        try:
            compiled_code = compile(code, "<python_interpreter_tool>", "exec")
            with warnings.catch_warnings(record=True) as captured_warnings:
                warnings.simplefilter("always")
                with contextlib.redirect_stdout(redirected_output), contextlib.redirect_stderr(redirected_error):
                    exec(compiled_code, namespace, namespace)
        except Exception:
            error_traceback = traceback.format_exc()
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=(
                    "Python execution failed. Full traceback:\n"
                    f"{error_traceback}"
                ),
                context={
                    "code": code,
                    "traceback": error_traceback,
                },
            )

        stdout_text = redirected_output.getvalue()
        stderr_text = redirected_error.getvalue()
        warning_messages = []
        for item in captured_warnings:
            warning_message = warnings.formatwarning(
                message=item.message,
                category=item.category,
                filename=item.filename,
                lineno=item.lineno,
                line=item.line,
            ).strip()
            if warning_message and warning_message not in warning_messages:
                warning_messages.append(warning_message)

        combined_output_parts = []
        if stdout_text.strip():
            combined_output_parts.append(stdout_text.strip())
        if stderr_text.strip():
            combined_output_parts.append(f"[stderr]\n{stderr_text.strip()}")
        if warning_messages:
            combined_output_parts.append("[warnings]\n" + "\n".join(warning_messages))

        combined_output = "\n\n".join(combined_output_parts).strip()
        data = {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "warnings": warning_messages,
        }

        if stdout_text.strip():
            return ToolResponse.success(text=combined_output, data=data, context={"code": code})

        if stderr_text.strip() or warning_messages:
            return ToolResponse.partial(
                text=(
                    f"{combined_output}\n\n"
                    "Code executed without stdout. Please use print() for every result you want returned in the Observation."
                ).strip(),
                data=data,
                context={"code": code},
            )

        return ToolResponse.partial(
            text=(
                "Code executed successfully, but no stdout was captured. "
                "Please use print() for every result you want returned in the Observation."
            ),
            data=data,
            context={"code": code},
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        return self.execute(parameters).to_json()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description=(
                    "Python code to execute. Include all required imports and use print() for every value, statistic, or conclusion you want returned in the Observation."
                ),
                required=True,
            )
        ]
