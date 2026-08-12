"""Plot styling helpers for publication-quality static charts."""

from __future__ import annotations

import logging
import re
import textwrap
import unicodedata
import warnings
from pathlib import Path
from typing import Iterable, Sequence


def configure_plotting_backend():
    """Configure a non-interactive matplotlib backend and return plotting modules."""

    import matplotlib

    current_backend = matplotlib.get_backend().lower()
    if "agg" not in current_backend:
        matplotlib.use("Agg", force=True)

    logging.getLogger("matplotlib.category").setLevel(logging.WARNING)

    import matplotlib.pyplot as plt
    import seaborn as sns

    return plt, sns


def get_plot_font_family() -> str:
    """Return the best available CJK-capable font family for the local machine."""

    configure_plotting_backend()
    from matplotlib import font_manager

    preferred_families = [
        "Microsoft YaHei",
        "Noto Sans SC",
        "SimHei",
        "SimSun",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for family in preferred_families:
        if family in available:
            return family
    return "DejaVu Sans"


def apply_publication_style():
    """Apply a consistent scientific plotting style with Chinese-safe fonts."""

    plt, sns = configure_plotting_backend()
    font_family = get_plot_font_family()

    sns.set_theme(context="talk", style="whitegrid", palette="deep")
    plt.rcParams.update(
        {
            "figure.figsize": (10.5, 6.2),
            "figure.dpi": 140,
            # Keep layout control conservative here; save_figure() owns final save-time fallback.
            "figure.constrained_layout.use": False,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "axes.facecolor": "#FAFAFA",
            "axes.edgecolor": "#2F2F2F",
            "axes.labelcolor": "#1F1F1F",
            "axes.titleweight": "bold",
            "axes.titlesize": 16,
            "axes.labelsize": 12,
            "axes.linewidth": 1.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.alpha": 0.18,
            "grid.linestyle": "--",
            "grid.linewidth": 0.8,
            "legend.frameon": False,
            "legend.fontsize": 10,
            "legend.title_fontsize": 11,
            "lines.linewidth": 2.2,
            "lines.markersize": 6,
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "font.family": "sans-serif",
            "font.sans-serif": [font_family, "Microsoft YaHei", "Noto Sans SC", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
        }
    )
    return plt, sns


def ensure_ascii_text(value: object, fallback: str = "label") -> str:
    """Convert labels to ASCII-only text when a fully ASCII figure is desired."""

    text = str(value).strip()
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    compact_text = " ".join(ascii_text.split()).strip()
    return compact_text or fallback


def ensure_ascii_sequence(values: Iterable[object], prefix: str = "label") -> list[str]:
    """Convert a sequence of labels to ASCII-only strings."""

    converted: list[str] = []
    for index, value in enumerate(values, start=1):
        converted.append(ensure_ascii_text(value, fallback=f"{prefix}_{index}"))
    return converted


def prepare_month_index(values: Sequence[object]):
    """Convert Chinese or ISO-like month labels to a stable datetime index when possible."""

    import pandas as pd

    normalized_values = []
    for value in values:
        text = str(value).strip()
        normalized_text = text.replace("年", "-").replace("月", "").replace("/", "-")
        match = re.fullmatch(r"(\d{4})-(\d{1,2})", normalized_text)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            normalized_values.append(f"{year:04d}-{month:02d}-01")
        else:
            normalized_values.append(text)

    parsed = pd.to_datetime(normalized_values, errors="coerce", format="%Y-%m-%d")
    if getattr(parsed, "notna", None) is not None and parsed.notna().all():
        return parsed
    return list(values)


def wrap_text(value: object, width: int = 16) -> str:
    """Wrap long text labels for cleaner legends and axis ticks."""

    text = str(value)
    if len(text) <= width:
        return text
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False))


def beautify_axes(
    ax,
    *,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    rotate_xticks: int = 25,
    wrap_xticks: bool = False,
    wrap_width: int = 14,
    legend: bool = True,
):
    """Apply consistent axis-level polish to reduce overlap and improve readability."""

    if title:
        ax.set_title(title, pad=14)
    if xlabel:
        ax.set_xlabel(xlabel, labelpad=10)
    if ylabel:
        ax.set_ylabel(ylabel, labelpad=10)

    if wrap_xticks:
        tick_labels = [wrap_text(label.get_text(), width=wrap_width) for label in ax.get_xticklabels()]
        ax.set_xticklabels(tick_labels)

    for label in ax.get_xticklabels():
        label.set_rotation(rotate_xticks)
        label.set_horizontalalignment("right" if rotate_xticks else "center")

    ax.tick_params(axis="x", pad=6)
    ax.tick_params(axis="y", pad=6)
    ax.margins(x=0.02)

    if legend and ax.get_legend() is not None:
        ax.legend(loc="best", frameon=False)

    return ax


def _resolve_save_figure_args(*args):
    """Support the new single-argument API and a minimal backward-compatible path."""

    plt, _ = configure_plotting_backend()
    if len(args) == 1:
        return plt.gcf(), args[0]
    if len(args) == 2 and hasattr(args[0], "savefig"):
        return args[0], args[1]
    raise TypeError("save_figure() expects save_figure(output_path) as the standard API.")


def _is_layout_conflict(exc: Exception) -> bool:
    message = str(exc).lower()
    keywords = (
        "layout engine",
        "tight_layout",
        "constrained_layout",
        "colorbar layout",
    )
    return any(keyword in message for keyword in keywords)


def _attempt_figure_save(fig, destination: Path) -> None:
    fig.savefig(destination, dpi=300, bbox_inches="tight", facecolor="white")


def save_figure(*args) -> Path:
    """Save the current figure defensively.

    Standard API:
        save_figure(output_path)

    A minimal backward-compatible path for save_figure(fig, output_path) is kept
    internally, but prompt/tooling should only expose the single-argument form.
    """

    fig, output_path = _resolve_save_figure_args(*args)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*figure layout has changed to tight.*")
        try:
            _attempt_figure_save(fig, destination)
        except Exception as exc:
            if not _is_layout_conflict(exc):
                raise

            # Defensive fallback: disable layout engines and retry without throwing
            # the common matplotlib heatmap/colorbar conflict back to the agent.
            try:
                if hasattr(fig, "set_layout_engine"):
                    fig.set_layout_engine(None)
            except Exception:
                pass

            try:
                if hasattr(fig, "set_constrained_layout"):
                    fig.set_constrained_layout(False)
            except Exception:
                pass

            try:
                fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
            except Exception:
                pass

            _attempt_figure_save(fig, destination)

    return destination
