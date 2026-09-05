"""HelloAgents Code Agent TUI - Main Logic.

TUI entry point and main application class.
Styles and utilities are in utils/tui_ui.py.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Iterable, Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Header, Input, RichLog, ListView, ListItem, Static, Collapsible

from core.config import Config, AVAILABLE_MODELS
from core.exceptions import HelloAgentsException
from core.llm import HelloAgentsLLM
from code_agent.agentic import CodeAgent
from code_agent.executors.apply_patch_executor import ApplyPatchExecutor, PatchApplyError
from utils.env import env_flag, env_flag_true, env_lower, env_str, env_stripped
from utils.observability import log_event
from utils.tui_ui import (
    TUI_CSS,
    extract_patch,
    normalize_patch,
    load_events,
    summarize_session,
    export_session,
)


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
CONFIRM_TOOL_RE = re.compile(r"\[\[CONFIRM_TOOL\]\]([\s\S]*?)\[\[/CONFIRM_TOOL\]\]")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text or "")
class _StreamingTUIWriter(io.TextIOBase):
    """A stdout/stderr-like stream that forwards output to the TUI in near-real-time.

    Why: `RichLog` can only append new lines, so we buffer partial writes and flush
    on newlines (or when the buffer grows / stalls), to avoid UI freezing and avoid
    dumping everything at the end.
    """

    def __init__(self, app: "CodeAgentTUI", kind: str) -> None:
        super().__init__()
        self._app = app
        self._kind = kind  # "stdout" | "stderr"
        self._buf: str = ""
        self._last_emit_ts = 0.0

    def writable(self) -> bool:  # pragma: no cover
        return True

    def isatty(self) -> bool:  # pragma: no cover
        return False

    def write(self, s: str) -> int:  # type: ignore[override]
        if not s:
            return 0
        self._buf += s
        self._drain_lines()
        self._maybe_emit_partial()
        return len(s)

    def flush(self) -> None:  # type: ignore[override]
        # Many libraries call flush very frequently (e.g. token streaming).
        # We treat flush as a "maybe" signal to update, not a hard boundary.
        self._drain_lines()
        self._maybe_emit_partial()

    def finish(self) -> None:
        """Force emit all remaining buffered content (call at turn end)."""
        self._drain_lines()
        self._emit(self._buf)
        self._buf = ""

    def _drain_lines(self) -> None:
        while "\n" in self._buf:
            line, rest = self._buf.split("\n", 1)
            self._buf = rest
            self._emit(line)

    def _maybe_emit_partial(self) -> None:
        if not self._buf:
            return
        now = time.time()
        # Emit partial buffer only if it is large or has been waiting for a while.
        if len(self._buf) >= 800 or (now - self._last_emit_ts) >= 1.0:
            self._emit(self._buf)
            self._buf = ""

    def _emit(self, chunk: str) -> None:
        if chunk is None:
            return
        chunk = _strip_ansi(chunk)
        if chunk == "":
            # Keep blank lines (progress separators).
            payload = ""
        else:
            payload = chunk.rstrip("\r")
        self._last_emit_ts = time.time()

        def _do() -> None:
            self._app._write_stream(payload, kind=self._kind)

        # If we're inside a background thread, schedule to UI thread.
        try:
            self._app.call_from_thread(_do)  # type: ignore[attr-defined]
        except Exception:
            _do()


class SuggestionItem(ListItem):
    """Custom list item that stores the suggestion value and optional description."""

    def __init__(self, value: str, description: str = "") -> None:
        super().__init__()
        self.value = value
        self.description = description

    def compose(self) -> ComposeResult:
        if self.description:
            # Two-column layout: command + description
            yield Static(f"[cyan]{self.value:<20}[/cyan] [dim]{self.description}[/dim]", markup=True)
        else:
            yield Static(self.value)


# Available commands with descriptions
COMMANDS = [
    ("/model", "查看或切换模型"),
    ("/plan", "生成执行计划 (--save 保存)"),
    ("/stats", "查看会话统计"),
    ("/export", "导出会话数据"),
    ("/clear", "清空输出"),
    ("/quit", "退出"),
]


class CodeAgentTUI(App):
    """Main TUI application for HelloAgents Code Agent."""

    CSS = TUI_CSS
    TITLE = "神秘奇奶龙--你的code管家"
    ENABLE_COMMAND_PALETTE = False  # 移除右下角 palette 提示

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("ctrl+l", "toggle_logo", "Logo", show=False),
        Binding("ctrl+t", "toggle_trace", "Trace", show=False),
        Binding("tab", "complete", "Complete", show=False),
        Binding("up", "suggestion_up", "Up", show=False),
        Binding("down", "suggestion_down", "Down", show=False),
        Binding("escape", "hide_suggestions", "Hide", show=False),
    ]

    def __init__(self, repo_root: Path, project: str | None = None):
        super().__init__()
        # TUI 默认静默：避免启动时刷屏（需要时可在环境变量里显式关闭）
        os.environ.setdefault("CODE_AGENT_QUIET", "1")
        self.repo_root = repo_root.resolve()
        self.project = project or self.repo_root.name
        self.config = Config.from_env()
        self.llm = HelloAgentsLLM()
        self.agent = CodeAgent(repo_root=self.repo_root, llm=self.llm, config=self.config)
        self.patch_executor = ApplyPatchExecutor(repo_root=self.repo_root)
        self.session_id = uuid.uuid4().hex
        os.environ["CODE_AGENT_SESSION_ID"] = self.session_id
        self.turns = 0

        self.pending_patch_text: str | None = None
        self.pending_user_input: str | None = None
        self.pending_tool_name: str | None = None
        self.pending_tool_input: str | None = None
        self.pending_tool_user_input: str | None = None
        self.pending_bang_command: str | None = None

        self._completion_start: Optional[int] = None
        self._completion_tag: Optional[str] = None
        self._suggestions: list[str] = []
        self._busy: bool = False
        self._logo_frames: list[Text] = []
        self._logo_frame_idx: int = 0
        self._logo_timer = None
        self._logo_visibility: str = env_lower("CODE_AGENT_LOGO_VISIBILITY", "once") or "once"
        if self._logo_visibility not in {"always", "once", "never"}:
            self._logo_visibility = "once"
        self._logo_splash_timer = None
        self._trace_offset: int = 0
        self._trace_path: Path | None = None
        self._trace_enabled: bool = env_flag_true("CODE_AGENT_TRACE_ENABLED", default=True)
        self._thought_log: RichLog | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("", id="logo")
            yield RichLog(id="trace", wrap=True, markup=True)
            yield VerticalScroll(id="output")
            yield ListView(id="suggestions")
        with Vertical(id="input_area"):
            yield Static("", id="input_line_top")
            with Horizontal(id="input_row"):
                yield Static(">", id="input_prompt")
                # placeholder 过长 + focus 样式在部分终端会呈现“色块/乱码”，这里缩短文案降低渲染风险
                yield Input(placeholder="输入消息（/命令，@引用）", id="input_bar")
            yield Static("", id="input_line_bottom")
        # 不显示底部快捷键栏（用户不需要 q quit）

    def on_mount(self) -> None:
        log_event(
            "session_start",
            {
                "project": self.project,
                "workspace": str(self.repo_root),
                "model": self.llm.model,
                "provider": self.llm.provider,
            },
        )
        # 首次 layout 完成后再渲染横线，保证长度等于终端宽度
        try:
            self.call_after_refresh(self._update_input_lines)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.set_timer(0, self._update_input_lines)  # type: ignore[attr-defined]
            except Exception:
                self._update_input_lines()

        # 启动 Logo（像项目 banner 一样，每次启动最开始显示）
        if self._logo_visibility != "never":
            self._write_logo()
            self._maybe_auto_hide_logo()
        else:
            self._set_logo_visible(False)

        # Trace timeline：从 events.jsonl 增量读取当前会话事件
        if self._trace_enabled:
            self._init_trace_timeline()

        # 输出文案：TUI 更强调可读性（用户能快速定位 user/assistant/过程日志）
        self._write_rule(
            "欢迎使用：神秘奇奶龙--你的 code 管家",
            border_style="#7aa2f7",
            title_style="bold #7aa2f7",
        )
        self._write("")
        self._write_kv("  工作根目录", str(self.repo_root))
        self._write("")
        model_type = "多模态" if self.llm.is_multimodal else "文本"
        self._write_kv("  当前模型", f"{self.llm.model} ({model_type})")
        self._write("")
        self._write_kv("  状态保存目录", Path(self.config.helloagents_dir).as_posix())
        self._write("")

        self._write_rule("提示:命令以 / 开头；引用文件、目录用 @（空格分隔）", border_style="#e0af68", title_style="bold #e0af68")

        self._write("")

        # Focus input
        self.query_one("#input_bar", Input).focus()

    def action_toggle_logo(self) -> None:
        """Toggle logo visibility (Ctrl+L)."""
        logo = self.query_one("#logo", Static)
        self._set_logo_visible(not bool(getattr(logo, "display", True)))

    def action_toggle_trace(self) -> None:
        """Toggle trace panel visibility (Ctrl+T)."""
        trace = self.query_one("#trace", RichLog)
        trace.display = not bool(getattr(trace, "display", True))

    def _init_trace_timeline(self) -> None:
        log_dir = env_str("CODE_AGENT_LOG_DIR") or str(self.repo_root / ".helloagents" / "logs")
        self._trace_path = (Path(log_dir).expanduser().resolve() / "events.jsonl")
        self._trace_offset = 0
        trace = self.query_one("#trace", RichLog)
        trace.clear()
        trace.write(Text("Trace Timeline（Ctrl+T 展开/折叠）", style="dim"))

        def _poll() -> None:
            self._poll_trace_events()

        try:
            self.set_interval(0.5, _poll)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _poll_trace_events(self) -> None:
        if not self._trace_path:
            return
        try:
            if not self._trace_path.exists():
                return
            with self._trace_path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._trace_offset)
                chunk = f.read()
                self._trace_offset = f.tell()
        except Exception:
            return

        if not chunk:
            return

        trace = self.query_one("#trace", RichLog)
        for line in chunk.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                import json as _json

                e = _json.loads(line)
            except Exception:
                continue
            if e.get("session_id") != self.session_id:
                continue

            et = e.get("type")
            ts = (e.get("ts") or "")[-12:-1]  # HH:MM:SS.mmm approx
            if et == "tool":
                ok = "✓" if e.get("ok", True) else "✗"
                tool = e.get("tool")
                ms = e.get("ms")
                call_id = e.get("tool_call_id") or ""
                inp = e.get("input_preview") or e.get("input")
                outp = e.get("output_preview")
                header = Text(
                    f"{ts}  {ok} tool  {tool}  ({ms} ms)  #{call_id}",
                    style="#7aa2f7" if ok == "✓" else "red",
                )
                trace.write(header)
                if inp:
                    trace.write(Text(f"  in: {str(inp)[:240]}", style="dim"))
                if outp:
                    trace.write(Text(f"  out: {str(outp)[:240]}", style="dim"))
            elif et == "llm":
                ok = "✓" if e.get("ok", True) else "✗"
                ms = e.get("ms")
                model = e.get("model")
                pt = e.get("prompt_tokens") or e.get("prompt_tokens_est")
                ct = e.get("completion_tokens") or e.get("completion_tokens_est")
                trace.write(
                    Text(
                        f"{ts}  {ok} llm   {model}  ({ms} ms)  tokens≈{pt}/{ct}",
                        style="#bb9af7" if ok == "✓" else "red",
                    )
                )
            elif et in {"patch_apply", "verify"}:
                ok = "✓" if e.get("ok", True) else "✗"
                ms = e.get("ms")
                trace.write(
                    Text(
                        f"{ts}  {ok} {et}  ({ms} ms)  {e.get('summary','')}",
                        style="green" if ok == "✓" else "red",
                    )
                )
            else:
                if et in {"context_base", "session_start", "session_end"}:
                    trace.write(Text(f"{ts}  • {et}", style="dim"))

    def _set_logo_visible(self, visible: bool) -> None:
        logo = self.query_one("#logo", Static)
        logo.display = visible
        # If hidden, stop animation timer to avoid wasting CPU.
        if not visible:
            try:
                if self._logo_timer is not None:
                    self._logo_timer.stop()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._logo_timer = None

    def _maybe_auto_hide_logo(self) -> None:
        """If visibility=once, auto-hide logo after a short splash."""
        if self._logo_visibility != "once":
            return
        sec_s = env_stripped("CODE_AGENT_LOGO_SPLASH_SECONDS", "")
        try:
            sec = float(sec_s) if sec_s else 2.0
        except Exception:
            sec = 2.0
        sec = max(0.2, min(10.0, sec))

        def _hide() -> None:
            self._set_logo_visible(False)

        try:
            self._logo_splash_timer = self.set_timer(sec, _hide)  # type: ignore[attr-defined]
        except Exception:
            # If timers are unavailable, just leave it visible.
            self._logo_splash_timer = None

    def on_resize(self) -> None:
        # Keep gradient lines aligned with terminal width
        self._update_input_lines()

    def on_unmount(self) -> None:
        log_event(
            "session_end",
            {
                "reason": "user_exit",
                "exit_code": 0,
                "turns": self.turns,
                "project": self.project,
                "workspace": str(self.repo_root),
                "model": self.llm.model,
                "provider": self.llm.provider,
            },
        )

    def _update_input_lines(self) -> None:
        """Render cyan 'gradient' lines like iflow (via Rich Text segments)."""
        # Always match terminal width; keep 1 char margin to avoid wrapping.
        width = max(10, (self.size.width or 0) - 1)
        chars = "─" * width
        # Make lines brighter/whiter (user wants white lines)
        colors = ["#ffffff", "#e6f7ff", "#b3f5ff", "#e6f7ff", "#ffffff"]
        seg = max(1, width // len(colors))

        line = Text()
        i = 0
        for idx, c in enumerate(colors):
            # last segment takes remainder
            if idx == len(colors) - 1:
                chunk = chars[i:]
            else:
                chunk = chars[i : i + seg]
            i += len(chunk)
            if chunk:
                line.append(chunk, style=c)

        self.query_one("#input_line_top", Static).update(line)
        self.query_one("#input_line_bottom", Static).update(line)

    # ============================================================
    # Output helpers
    # ============================================================

    def _write(self, text: str, style: str | None = None, *, markup: bool = False) -> None:
        """写入输出区（可交互：支持折叠、点击等）。"""
        renderable = Text.from_markup(text if text is not None else "", style=style) if markup else Text(text if text is not None else "", style=style)
        self._mount_output(Static(renderable))

    def _write_rule(
        self,
        title: str,
        *,
        border_style: str = "#202637",
        title_style: str = "bold",
    ) -> None:
        self._mount_output(
            Static(
                Panel(
                    Text(title, style=title_style),
                    box=box.ROUNDED,
                    border_style=border_style,
                    padding=(0, 1),
                )
            )
        )

    def _write_logo(self) -> None:
        """在启动时输出一个“项目 Logo”。

        优先级：
        1) 环境变量 `CODE_AGENT_LOGO` 指定的图片路径
        2) repo 内可提交的常见路径（如 images/ 或 assets/）
        3) 兜底：内置 ASCII art
        """

        def _candidate_paths() -> list[Path]:
            candidates: list[Path] = []
            env_logo = env_stripped("CODE_AGENT_LOGO", "")
            if env_logo:
                candidates.append(Path(env_logo).expanduser())
            # common defaults
            candidates.extend(
                [
                    self.repo_root / "assets" / "logo.png",
                    self.repo_root / "assets" / "logo.jpg",
                    self.repo_root / "assets" / "logo.gif",
                    self.repo_root / "images" / "logo.png",
                    self.repo_root / "images" / "logo.jpg",
                    self.repo_root / "images" / "logo.gif",
                    self.repo_root / "images" / "nailong.png",
                    self.repo_root / "images" / "nailong.jpg",
                    self.repo_root / "images" / "nailong.gif",
                ]
            )
            return candidates

        def _render_image_to_text(img_rgb, width: int) -> Text | None:
            try:
                from PIL import Image  # type: ignore
            except Exception:
                return None
            img = img_rgb
            if not isinstance(img, Image.Image):
                return None

            w0, h0 = img.size
            if w0 <= 0 or h0 <= 0:
                return None

            # Render with upper-half blocks: each char represents 2 vertical pixels.
            # We scale height in pixels by ~2 so the final character aspect looks OK.
            height_px = max(2, int(h0 / w0 * width * 2))
            if height_px % 2 == 1:
                height_px += 1
            img = img.resize((width, height_px))
            px = img.load()
            if px is None:
                return None

            out = Text()
            for y in range(0, height_px, 2):
                for x in range(width):
                    r1, g1, b1 = px[x, y]
                    r2, g2, b2 = px[x, y + 1]
                    style = f"#{r1:02x}{g1:02x}{b1:02x} on #{r2:02x}{g2:02x}{b2:02x}"
                    out.append("▀", style=style)
                out.append("\n")
            return out

        def _render_image_to_dots(img_rgb, width_chars: int) -> Text | None:
            """彩色点阵渲染：把图片压到字符网格，用彩色 '•' 表达像素点。"""
            try:
                from PIL import Image  # type: ignore
            except Exception:
                return None
            img = img_rgb
            if not isinstance(img, Image.Image):
                return None

            w0, h0 = img.size
            if w0 <= 0 or h0 <= 0:
                return None

            width_chars = max(2, int(width_chars))
            # 字符格通常“高于宽”，用一个经验系数避免看起来被拉长
            aspect = float(env_str("CODE_AGENT_LOGO_DOT_ASPECT", "0.55"))
            height_chars = max(1, int(h0 / w0 * width_chars * aspect))

            img = img.resize((width_chars, height_chars)).convert("RGB")
            px = img.load()
            if px is None:
                return None

            dot_char = env_str("CODE_AGENT_LOGO_DOT_CHAR", "•")
            out = Text()
            for y in range(height_chars):
                for x in range(width_chars):
                    r, g, b = px[x, y]
                    out.append(dot_char, style=f"#{r:02x}{g:02x}{b:02x}")
                out.append("\n")
            return out

        def _fit_width_no_upscale(w0: int, h0: int, *, mode: str) -> int:
            """尽量保持原图尺寸：不放大，仅在超出可用区域时等比缩小。

            说明：终端显示是“字符格”，无法真正按原始像素大小展示；这里的“原图尺寸”
            指尽量少做缩小，只要终端放得下就不缩。
            """
            # 可用宽度（字符格）
            max_w = max(10, (self.size.width or 80) - 8)

            # 默认：尽量给 logo 更多空间（只要终端高度允许）
            # 也可用环境变量覆盖
            env_max_h = env_stripped("CODE_AGENT_LOGO_MAX_HEIGHT", "")
            if env_max_h.isdigit():
                max_h_lines = max(6, int(env_max_h))
            else:
                # 预留若干行给 output/input；剩余尽量给 logo
                reserved = 14
                max_h_lines = max(8, min(40, max(8, (self.size.height or 40) - reserved)))

            target_w = min(w0, max_w)  # 不放大
            target_w = max(2, target_w)

            # 高度约束（可关闭）：不同模式的“每列宽度对应的行数”不同
            # halfblock: height_lines ≈ h0/w0 * target_w
            # dot:       height_lines ≈ h0/w0 * target_w * aspect(默认 0.55)
            disable_h_limit = env_flag("CODE_AGENT_LOGO_DISABLE_HEIGHT_LIMIT", default=False)
            if not disable_h_limit and h0 > 0:
                if mode == "dot":
                    try:
                        aspect = float(env_str("CODE_AGENT_LOGO_DOT_ASPECT", "0.55"))
                    except Exception:
                        aspect = 0.55
                    aspect = max(0.2, min(2.0, aspect))
                    height_lines_per_w = (h0 / w0) * aspect
                else:
                    height_lines_per_w = (h0 / w0)
                if height_lines_per_w > 0:
                    max_w_by_h = int(max_h_lines / height_lines_per_w)
                    if max_w_by_h > 0:
                        target_w = min(target_w, max_w_by_h)

            # 允许强制指定宽度（不推荐过大，可能溢出）
            env_w = env_stripped("CODE_AGENT_LOGO_WIDTH", "")
            if env_w.isdigit():
                forced = int(env_w)
                if forced > 0:
                    target_w = min(max_w, forced)

            return max(2, target_w)

        # 如果之前有动画 timer，先停掉
        try:
            if self._logo_timer is not None:
                self._logo_timer.stop()  # type: ignore[attr-defined]
        except Exception:
            pass
        self._logo_timer = None
        self._logo_frames = []
        self._logo_frame_idx = 0

        # 三种模式（由环境变量控制）：
        # - image: 渲染静态图片（即使输入是 gif，也只取首帧）
        # - gif:   渲染 gif 动图（若输入非动图则退化为 image）
        # - dot:   彩色点阵（即使输入是 gif，也只取首帧）
        logo_mode = env_lower("CODE_AGENT_LOGO_MODE", "image")
        if logo_mode not in {"image", "gif", "dot"}:
            logo_mode = "image"
        animate = env_flag_true("CODE_AGENT_LOGO_ANIMATE", default=True)

        def _set_logo(renderable) -> None:
            # Rich 的居中对齐（配合 #logo 的 content-align 更稳）
            self.query_one("#logo", Static).update(Align.center(renderable))

        for p in _candidate_paths():
            if not p.exists() or not p.is_file():
                continue
            try:
                from PIL import Image, ImageSequence  # type: ignore
            except Exception:
                break

            try:
                img = Image.open(p)
            except Exception:
                continue

            # 以第一帧尺寸计算目标宽度（尽量保持原图尺寸，不放大）
            try:
                w0, h0 = img.size
                width_chars = _fit_width_no_upscale(int(w0), int(h0), mode=logo_mode)
            except Exception:
                width_chars = max(24, min(72, (self.size.width or 80) - 10))

            is_gif = (getattr(img, "format", "") or "").upper() == "GIF"
            is_animated = bool(getattr(img, "is_animated", False)) or (getattr(img, "n_frames", 1) or 1) > 1

            # 模式2：gif 动图（仅在 logo_mode=gif 时启用；否则一律按静态图处理）
            if logo_mode == "gif" and animate and (is_gif or is_animated):
                frames: list[Text] = []
                duration_ms = int((img.info or {}).get("duration") or 90)
                duration_ms = max(50, min(500, duration_ms))

                try:
                    for frame in ImageSequence.Iterator(img):
                        rgb = frame.convert("RGB")
                        # gif 模式：默认回到“半块字符渲染”
                        t = _render_image_to_text(rgb, width=width_chars)
                        if t is not None:
                            frames.append(t)
                        if len(frames) >= 120:  # 防止超长 GIF 过重
                            break
                except Exception:
                    frames = []

                if frames:
                    self._logo_frames = frames
                    _set_logo(Panel(frames[0], box=box.ROUNDED, border_style="#202637", padding=(0, 1)))

                    def _advance() -> None:
                        if not self._logo_frames:
                            return
                        self._logo_frame_idx = (self._logo_frame_idx + 1) % len(self._logo_frames)
                        frame_t = self._logo_frames[self._logo_frame_idx]
                        _set_logo(Panel(frame_t, box=box.ROUNDED, border_style="#202637", padding=(0, 1)))

                    try:
                        self._logo_timer = self.set_interval(duration_ms / 1000.0, _advance)  # type: ignore[attr-defined]
                    except Exception:
                        self._logo_timer = None
                    return

            # 模式1/3：静态渲染（image / dot），以及 gif 输入但非 gif 模式时
            try:
                rgb0 = img.convert("RGB")
                if logo_mode == "dot":
                    t0 = _render_image_to_dots(rgb0, width_chars=width_chars)
                else:
                    # image 模式：默认回到“半块字符渲染”
                    t0 = _render_image_to_text(rgb0, width=width_chars)
            except Exception:
                t0 = None
            if t0 is not None:
                _set_logo(Panel(t0, box=box.ROUNDED, border_style="#202637", padding=(0, 1)))
                return

        # Fallback ASCII banner (always works).
        ascii_logo = Text(
            "\n".join(
                [
                    "   _   _       _           _                 ",
                    "  | \\ | | __ _(_)_ __   __| | ___  _ __   __ _",
                    "  |  \\| |/ _` | | '_ \\ / _` |/ _ \\| '_ \\ / _` |",
                    "  | |\\  | (_| | | | | | (_| | (_) | | | | (_| |",
                    "  |_| \\_|\\__,_|_|_| |_|\\__,_|\\___/|_| |_|\\__,_|",
                    "                 奶 龙 · CodeGamer             ",
                ]
            ),
            style="#7aa2f7",
        )
        _set_logo(Panel(ascii_logo, box=box.ROUNDED, border_style="#202637", padding=(0, 1)))

    def _write_kv(self, key: str, value: str) -> None:
        t = Text()
        t.append(f"{key}: ", style="bold #7aa2f7")
        t.append(value, style="#e8e8e8")
        self._mount_output(Static(t))

    def _write_dim(self, text: str) -> None:
        self._write(text, style="dim")

    def _write_user_message(self, user_in: str) -> None:
        # Highlight @references inside user text.
        t = Text()
        for part in user_in.split(" "):
            if part.startswith("@"):
                t.append(part, style="bold #7aa2f7")
            else:
                t.append(part)
            t.append(" ")
        # rich.text.Text.rstrip() 是原地修改并返回 None
        t.rstrip()
        ts = time.strftime("%H:%M:%S")
        self._mount_output(
            Static(
                Panel(
                    t,
                    title=f"😅 user · #{self.turns} · {ts}",
                    title_align="left",
                    box=box.ROUNDED,
                    border_style="#4FC3F7",
                    padding=(0, 1),
                )
            )
        )

    def _write_assistant_message(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self._mount_output(
            Static(
                Panel(
                    Text(text or ""),
                    title=f"奶浓认为是这样的：· {ts}",
                    title_align="left",
                    box=box.ROUNDED,
                    border_style="#E94560",
                    padding=(0, 1),
                )
            )
        )

    def _write_success(self, text: str) -> None:
        self._write(text, style="bold green")

    def _write_warning(self, text: str) -> None:
        self._write(text, style="bold yellow")

    def _write_error(self, text: str) -> None:
        self._write(text, style="bold red")

    def _write_stream(self, chunk: str, kind: str) -> None:
        """Write tool/agent intermediate logs with lighter weight."""
        # Preserve blank lines
        if chunk == "":
            self._write("")
            return

        # During a turn: stream logs into the collapsible thought panel by default.
        if self._thought_log is not None:
            self._thought_log.write(Text(chunk))
            return

        # Heuristic coloring for common log prefixes.
        style = "dim"
        if chunk.startswith("✅") or chunk.startswith("[OK]"):
            style = "green"
        elif chunk.startswith("❌") or chunk.startswith("[ERROR]"):
            style = "red"
        elif chunk.startswith("⚠️") or chunk.startswith("[WARNING]"):
            style = "yellow"
        elif chunk.startswith("🧠"):
            style = "#bb9af7"
        elif chunk.startswith("🔍") or chunk.startswith("📷"):
            style = "#7aa2f7"

        prefix = "· " if kind == "stdout" else "‼ "
        self._write(prefix + chunk, style=style)

    def _mount_output(self, widget: Widget) -> None:
        """Mount a widget into the scrollable output area and keep it scrolled to end."""
        out = self.query_one("#output", VerticalScroll)
        try:
            out.mount(widget)
        except Exception:
            return
        try:
            out.scroll_end(animate=False)
        except Exception:
            pass

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        input_widget = self.query_one("#input_bar", Input)
        input_widget.disabled = busy
        prompt = self.query_one("#input_prompt", Static)
        prompt.update("⏳" if busy else ">")
        try:
            header = self.query_one(Header)
            header.sub_title = "处理中…（过程日志会实时输出）" if busy else ""
        except Exception:
            pass

    # ============================================================
    # Path auto-completion
    # ============================================================

    def _update_suggestions(self, text: str) -> None:
        suggestions_view = self.query_one("#suggestions", ListView)
        suggestions_view.clear()
        
        # Check for command completion first (starts with /)
        if text.startswith("/"):
            cmd_prefix = text.lower()
            matching_cmds = [(cmd, desc) for cmd, desc in COMMANDS if cmd.startswith(cmd_prefix)]
            
            if matching_cmds:
                self._suggestions = [cmd for cmd, _ in matching_cmds]
                self._completion_start = 0
                self._completion_tag = "/"
                for cmd, desc in matching_cmds:
                    suggestions_view.append(SuggestionItem(cmd, desc))
                suggestions_view.display = True
                suggestions_view.index = 0
                return
        
        # Check for path completion (@)
        tag, prefix, replace_start = self._extract_completion_context(text)
        suggestions = self._get_path_suggestions(tag, prefix) if tag else []

        if suggestions:
            self._suggestions = suggestions
            for item in suggestions:
                suggestions_view.append(SuggestionItem(item))
            suggestions_view.display = True
            suggestions_view.index = 0
            self._completion_start = replace_start
            self._completion_tag = tag
        else:
            self._suggestions = []
            suggestions_view.display = False
            self._completion_start = None
            self._completion_tag = None

    def _extract_completion_context(self, text: str) -> tuple[str | None, str | None, Optional[int]]:
        """Extract @ completion context - simplified syntax: @path instead of @file(path)."""
        # Find the last @ that's not already completed (followed by space or end)
        idx = text.rfind("@")
        if idx == -1:
            return None, None, None
        
        # Get the part after @
        after_at = text[idx + 1:]
        
        # If there's a space after the path, this @ is already completed
        # Find where the current path ends (space marks end of path)
        space_idx = after_at.find(" ")
        if space_idx != -1:
            # Check if there's another @ after this one
            rest = after_at[space_idx:]
            next_at = rest.rfind("@")
            if next_at != -1:
                # Recalculate from the new @ position
                new_idx = idx + 1 + space_idx + next_at
                after_at = text[new_idx + 1:]
                idx = new_idx
                space_idx = after_at.find(" ")
                if space_idx != -1:
                    return None, None, None
            else:
                return None, None, None
        
        # The prefix is everything after @
        prefix = after_at.strip()
        replace_start = idx + 1
        return "@", prefix, replace_start

    def _get_path_suggestions(self, tag: str | None, prefix: str | None) -> list[str]:
        """Get path suggestions for @ completion - shows both files and folders."""
        if not tag or prefix is None:
            return []
        prefix = prefix.strip()
        if prefix.startswith("~"):
            prefix = os.path.expanduser(prefix)
        
        base_dir = self.repo_root
        needle = prefix
        path_prefix = ""
        
        if "/" in prefix:
            base_part = prefix.rsplit("/", 1)[0]
            needle = prefix.rsplit("/", 1)[1]
            path_prefix = base_part + "/"
            base_dir = (self.repo_root / base_part).resolve()

        if not base_dir.exists() or not base_dir.is_dir():
            return []

        def iter_entries() -> Iterable[Path]:
            try:
                # Sort: directories first, then files, both alphabetically
                entries = sorted(base_dir.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except Exception:
                return []
            ignored = {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}
            for entry in entries:
                if entry.name.startswith(".") and entry.name not in {".gitignore", ".env.example", ".env"}:
                    continue
                if entry.name in ignored:
                    continue
                yield entry

        results: list[str] = []
        for entry in iter_entries():
            if needle and not entry.name.lower().startswith(needle.lower()):
                continue
            suffix = "/" if entry.is_dir() else ""
            # Return full relative path from where user started typing
            results.append(path_prefix + entry.name + suffix)
            if len(results) >= 20:
                break
        return results

    def action_complete(self) -> None:
        """Apply first suggestion on Tab."""
        suggestions_view = self.query_one("#suggestions", ListView)
        if not suggestions_view.display or not self._suggestions:
            return
        idx = suggestions_view.index or 0
        if 0 <= idx < len(self._suggestions):
            self._apply_completion(self._suggestions[idx])

    def action_suggestion_up(self) -> None:
        """Move selection up in suggestions."""
        suggestions_view = self.query_one("#suggestions", ListView)
        if suggestions_view.display and self._suggestions:
            current = suggestions_view.index or 0
            suggestions_view.index = max(0, current - 1)

    def action_suggestion_down(self) -> None:
        """Move selection down in suggestions."""
        suggestions_view = self.query_one("#suggestions", ListView)
        if suggestions_view.display and self._suggestions:
            current = suggestions_view.index or 0
            suggestions_view.index = min(len(self._suggestions) - 1, current + 1)

    def action_hide_suggestions(self) -> None:
        """Hide suggestions list."""
        suggestions_view = self.query_one("#suggestions", ListView)
        suggestions_view.display = False

    def _apply_completion(self, value: str) -> None:
        input_widget = self.query_one("#input_bar", Input)
        text = input_widget.value
        if self._completion_start is None:
            return
        new_text = text[: self._completion_start] + value
        input_widget.value = new_text
        input_widget.cursor_position = len(new_text)
        suggestions_view = self.query_one("#suggestions", ListView)
        suggestions_view.display = False
        self._suggestions = []

    # ============================================================
    # Event handlers
    # ============================================================

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle suggestion selection via click or Enter."""
        if isinstance(event.item, SuggestionItem):
            self._apply_completion(event.item.value)
            # Refocus input
            self.query_one("#input_bar", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._busy:
            return
        self._update_suggestions(event.value)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        # In splash mode, hide logo on first real interaction to free space.
        if self._logo_visibility == "once":
            self._set_logo_visible(False)
        # First check if suggestions are visible and should be applied
        suggestions_view = self.query_one("#suggestions", ListView)
        if suggestions_view.display and self._suggestions:
            idx = suggestions_view.index or 0
            if 0 <= idx < len(self._suggestions):
                self._apply_completion(self._suggestions[idx])
                return

        user_in = event.value.strip()
        event.input.value = ""
        if not user_in:
            self._write("请提供具体指令或问题。")
            return

        # "!" 直通终端：用户自己执行命令，不走 agent
        if user_in.startswith("!"):
            cmd = user_in[1:].strip()
            if not cmd:
                self._write_warning("用法：!<command>  例如：!pwd")
                return
            await self._run_bang_command(cmd, allow_dangerous=False)
            return

        if self.pending_tool_name and self.pending_tool_input is not None:
            decision = user_in.lower()
            tool = self.pending_tool_name
            tool_input = self.pending_tool_input
            original = self.pending_tool_user_input or ""
            # clear first to avoid re-entrancy
            self.pending_tool_name = None
            self.pending_tool_input = None
            self.pending_tool_user_input = None
            if decision in {"y", "yes"}:
                # run tool, then feed result back to agent for next decision
                await self._run_tool_then_continue(tool, tool_input, original, approved=True)
            else:
                await self._run_tool_then_continue(tool, tool_input, original, approved=False)
            return

        # "! 命令" 的危险确认（只针对 bang 模式，不走 agent）
        if self.pending_bang_command:
            decision = user_in.lower()
            cmd = self.pending_bang_command
            self.pending_bang_command = None
            if decision in {"y", "yes"}:
                await self._run_bang_command(cmd, allow_dangerous=True)
            else:
                self._write_warning("已取消执行该命令。")
            return

        if self.pending_patch_text:
            if user_in.lower() in {"y", "yes"}:
                self._apply_patch(self.pending_user_input or "", self.pending_patch_text)
            else:
                self._write("已取消补丁应用。")
                # Feed back to agent so it can decide next step without manual re-typing.
                reject_prompt = (
                    "用户拒绝应用你生成的补丁。请解释原因/提供替代方案，或生成更小、更安全的补丁。"
                )
                self.turns += 1
                self._write("")
                self._write_user_message("（系统）用户拒绝应用补丁，继续决策")
                await self._run_turn_async(reject_prompt)
            self.pending_patch_text = None
            self.pending_user_input = None
            return

        if user_in in {"/q", "/quit", "quit", "exit"}:
            self._write("")
            self._write("没钱充token了，下次再见")
            self.exit()
            return

        if user_in.startswith("/stats"):
            self._handle_stats(user_in)
            return

        if user_in.startswith("/export"):
            self._handle_export(user_in)
            return

        # /verify 和 /fix 命令已移除，不再处理

        if user_in.startswith("/plan"):
            self._handle_plan(user_in)
            return

        if user_in.startswith("/model"):
            self._handle_model(user_in)
            return

        if user_in == "/clear":
            out = self.query_one("#output", VerticalScroll)
            # Remove all children
            for child in list(out.children):
                try:
                    child.remove()
                except Exception:
                    pass
            return

        self.turns += 1
        self._write("")
        self._write_user_message(user_in)
        await self._run_turn_async(user_in)

    # ============================================================
    # Command handlers
    # ============================================================

    def _handle_plan(self, user_in: str) -> None:
        raw = user_in[len("/plan") :].strip()
        save_plan = False
        if "--save" in raw:
            save_plan = True
            raw = raw.replace("--save", "").strip()
        goal = raw or "请为当前任务生成一个可执行计划"
        response = self.agent.registry.execute_tool("plan", goal)
        self._write("")
        self._write("🤖 plan")
        self._write(response)
        if save_plan:
            self.agent.note_tool.run(
                {
                    "action": "create",
                    "title": "Plan",
                    "content": f"Goal:\n{goal}\n\nPlan:\n\n{response}",
                    "note_type": "plan",
                    "tags": [self.project, "plan"],
                }
            )
            self._write("✅ 已保存到 notes")

    def _handle_model(self, user_in: str) -> None:
        arg = user_in[len("/model") :].strip()
        model_list = list(AVAILABLE_MODELS.items())
        if not arg:
            self._write("")
            model_type = "多模态" if self.llm.is_multimodal else "文本"
            self._write(f"当前模型: {self.llm.model} ({model_type})")
            self._write("")
            self._write("可用模型:")
            for i, (name, info) in enumerate(model_list, 1):
                mtype = "多模态" if info["multimodal"] else "文本"
                marker = "-> " if name == self.llm.model else "   "
                self._write(f"  {marker}[{i}] {name} [{mtype}]")
            self._write("")
            self._write("用法：/model <序号或模型名>")
            return

        target_model: Optional[str] = None
        if arg.isdigit():
            idx = int(arg) - 1
            if 0 <= idx < len(model_list):
                target_model = model_list[idx][0]
        elif arg in AVAILABLE_MODELS:
            target_model = arg

        if not target_model:
            self._write("未知模型，请输入序号或模型名。")
            return

        self.llm.switch_model(target_model)
        model_type = "多模态" if self.llm.is_multimodal else "文本"
        self._write(f"✓ 已切换到: {target_model} ({model_type})")

    def _handle_stats(self, user_in: str) -> None:
        arg = user_in[len("/stats") :].strip()
        log_dir = env_str("CODE_AGENT_LOG_DIR") or str(Path(".helloagents") / "logs")
        log_path = Path(log_dir) / "events.jsonl"
        events = load_events(log_path)
        if not events:
            self._write("暂无日志数据。")
            return

        current_id = env_str("CODE_AGENT_SESSION_ID")
        target_id = None
        if arg == "current" or not arg:
            target_id = current_id
        elif arg == "last":
            for e in reversed(events):
                if e.get("type") == "session_end":
                    target_id = e.get("session_id")
                    break
        else:
            target_id = arg

        if not target_id:
            self._write("未找到目标会话。")
            return

        session_events = [e for e in events if e.get("session_id") == target_id]
        if not session_events:
            self._write(f"未找到会话: {target_id}")
            return

        stats = summarize_session(session_events)
        self._write("")
        self._write("📊 会话统计")
        self._write(f"session_id: {target_id}")
        if stats["start_ts"]:
            self._write(f"start: {stats['start_ts']}")
        if stats["end_ts"]:
            self._write(f"end: {stats['end_ts']}")
        if stats["duration_ms"] is not None:
            self._write(f"duration: {stats['duration_ms']} ms")
        self._write(f"turns: {stats['turns']}")
        self._write(f"tool_calls: {stats['tool_calls']} (errors: {stats['tool_errors']})")
        self._write(f"llm_calls: {stats['llm_calls']} (errors: {stats['llm_errors']})")
        if stats["prompt_tokens"] or stats["completion_tokens"]:
            self._write(f"tokens: prompt={stats['prompt_tokens']} completion={stats['completion_tokens']}")
        self._write(f"tokens_est: prompt≈{stats['prompt_tokens_est']} completion≈{stats['completion_tokens_est']}")

    def _handle_export(self, user_in: str) -> None:
        arg = user_in[len("/export") :].strip()
        log_dir = env_str("CODE_AGENT_LOG_DIR") or str(Path(".helloagents") / "logs")
        log_path = Path(log_dir) / "events.jsonl"
        events = load_events(log_path)
        if not events:
            self._write("暂无日志数据。")
            return

        current_id = env_str("CODE_AGENT_SESSION_ID")
        target_id = None
        if arg == "current" or not arg:
            target_id = current_id
        elif arg == "last":
            for e in reversed(events):
                if e.get("type") == "session_end":
                    target_id = e.get("session_id")
                    break
        else:
            target_id = arg

        if not target_id:
            self._write("未找到目标会话。")
            return

        session_events = [e for e in events if e.get("session_id") == target_id]
        if not session_events:
            self._write(f"未找到会话: {target_id}")
            return

        export_dir = Path(log_dir).parent / "exports"
        export_path = export_session(target_id, session_events, export_dir)
        self._write("✅ 已导出会话信息")
        self._write(f"path: {export_path}")

    # ============================================================
    # Agent interaction
    # ============================================================

    async def _run_turn_async(self, user_in: str) -> None:
        """Run one agent turn without blocking the UI.

        - The agent runs in a background thread.
        - stdout/stderr are streamed into the output panel.
        - At the end, we render the assistant final message in a readable panel.
        """
        self._set_busy(True)

        # Create a collapsible "thinking" panel for this turn (collapsed by default).
        thought_log = RichLog(wrap=True, markup=True)
        self._thought_log = thought_log
        self._mount_output(
            Collapsible(
                thought_log,
                title="奶浓思考ing...",
                collapsed=True,
                collapsed_symbol="▶",
                expanded_symbol="▼",
            )
        )
        stream_out = _StreamingTUIWriter(self, kind="stdout")
        stream_err = _StreamingTUIWriter(self, kind="stderr")

        def _run() -> str:
            with contextlib.redirect_stdout(stream_out), contextlib.redirect_stderr(stream_err):
                return self.agent.run_turn(user_in)

        try:
            response = await asyncio.to_thread(_run)
        except FileNotFoundError as e:
            stream_out.finish()
            stream_err.finish()
            self._write_error(f"文件不存在：{e}")
            self._write_dim("提示：使用 @ 引用文件/目录，例如 @main.py @src/ 请分析")
            return
        except HelloAgentsException as e:
            stream_out.finish()
            stream_err.finish()
            self._write_error(f"LLM 调用失败: {e}")
            return
        finally:
            # Flush any remaining partial output.
            try:
                stream_out.finish()
                stream_err.finish()
            except Exception:
                pass
            # Stop routing stream output into thought log
            self._thought_log = None
            self._set_busy(False)

        # Render the assistant's final answer (high-contrast, easy to scan).
        self._write("")
        self._write_assistant_message(response)

        # Tool confirmation marker interception (Cursor-like gating)
        m = CONFIRM_TOOL_RE.search(response or "")
        if m:
            try:
                payload = json.loads(m.group(1))
                tool = payload.get("tool") or "terminal"
                tool_input = payload.get("tool_input") or ""
                # store pending tool request
                self.pending_tool_name = str(tool)
                self.pending_tool_input = str(tool_input)
                self.pending_tool_user_input = user_in

                self._write("")
                self._write_rule("需要确认执行命令/工具", border_style="#e0af68", title_style="bold #e0af68")
                self._write_kv("tool", str(tool))
                self._write_kv("input", str(tool_input)[:400])
                self._write_warning("是否允许运行？(y/n)")
            except Exception:
                pass
            return

        patch_text = extract_patch(response)
        if not patch_text:
            return
        patch_text = normalize_patch(patch_text)
        if patch_text.strip() == "*** Begin Patch\n*** End Patch":
            return

        # Cursor-like gating: always require confirmation before applying patch.
        self.pending_patch_text = patch_text
        self.pending_user_input = user_in
        self._write("")
        self._write_rule("即将应用补丁", border_style="#e0af68", title_style="bold #e0af68")
        # stats (parse blocks so Add File shows meaningful +lines)
        lines = patch_text.splitlines()
        files: list[str] = []
        created = updated = deleted = 0
        add = sub = 0

        current_op: str | None = None  # "add" | "update" | "delete"
        in_hunk = False
        for l in lines:
            if l.startswith("*** Add File:"):
                files.append(l.replace("*** ", "").strip())
                created += 1
                current_op = "add"
                in_hunk = False
                continue
            if l.startswith("*** Update File:"):
                files.append(l.replace("*** ", "").strip())
                updated += 1
                current_op = "update"
                in_hunk = False
                continue
            if l.startswith("*** Delete File:"):
                files.append(l.replace("*** ", "").strip())
                deleted += 1
                current_op = "delete"
                in_hunk = False
                continue
            if l.startswith("@@"):
                in_hunk = True
                continue
            if l.strip() == "*** End Patch":
                break

            # Count changes
            if current_op == "add":
                # Add File blocks should be treated as additions even if the model forgot '+' prefixes.
                if l.startswith("+") and not l.startswith("+++"):
                    add += 1
                elif l.startswith(("***", "@@")):
                    continue
                else:
                    # Non-empty content line counts as an added line
                    if l != "":
                        add += 1
                continue

            if current_op == "update" and in_hunk:
                if l.startswith("+") and not l.startswith("+++"):
                    add += 1
                elif l.startswith("-") and not l.startswith("---"):
                    sub += 1
                continue

        if files:
            self._write_kv("files", ", ".join(files[:8]) + (" ..." if len(files) > 8 else ""))
        self._write_kv("ops", f"add={created} update={updated} delete={deleted}")
        self._write_kv("diff", f"+{add} / -{sub}")
        self._write_warning("是否应用？(y/n)")
        return

    async def _run_tool_then_continue(self, tool: str, tool_input: str, original_user_in: str, approved: bool) -> None:
        """Run a pending tool (if approved) and continue agent decision."""
        self._set_busy(True)

        if not approved:
            self._write_warning(f"已拒绝执行：{tool}")
            prompt = (
                f"用户拒绝执行工具/命令：{tool}\n"
                f"拟执行输入：{tool_input}\n\n"
                "请基于现有信息继续决策（不要再要求执行同一命令），给出替代取证方式或直接结论。"
            )
            self._set_busy(False)
            self.turns += 1
            self._write("")
            self._write_user_message("（系统）拒绝执行命令后继续")
            await self._run_turn_async(prompt)
            return

        # approved: execute tool and feed result back to agent
        # 对齐 Claude Code/OpenCode：用户点 y 后，这次执行应当真正放行（而不是被工具内部硬白名单再拒绝）
        # 我们通过向 terminal 工具注入 `user_approved=true` 来实现“本次/一次性 token”。
        effective_input = tool_input
        if tool == "terminal":
            try:
                obj = json.loads(tool_input)
                if isinstance(obj, dict):
                    obj["user_approved"] = True
                    # 用户已在 UI 二次确认：允许 terminal 将该次执行视为已授权（等价一次性 token）
                    effective_input = json.dumps(obj, ensure_ascii=False)
            except Exception:
                # 非结构化输入保持原样
                effective_input = tool_input

        def _run() -> str:
            return self.agent.registry.execute_tool(tool, effective_input)

        try:
            out = await asyncio.to_thread(_run)
            self._write_success(f"已执行：{tool}")
            self._write(out)
            prompt = (
                f"用户允许执行工具/命令：{tool}\n"
                f"输入：{effective_input}\n\n"
                f"输出：\n{out}\n\n"
                "请基于该输出继续下一步（不要重复执行同一命令）。"
            )
        finally:
            self._set_busy(False)

        self.turns += 1
        self._write("")
        self._write_user_message("（系统）命令结果已获取，继续决策")
        await self._run_turn_async(prompt)


    async def _run_bang_command(self, command: str, *, allow_dangerous: bool) -> None:
        """Run a user-requested shell command directly (no agent)."""
        self._write("")
        self._write_rule("用户终端（!）", border_style="#4FC3F7", title_style="bold #4FC3F7")
        self._write_kv("command", command)

        self._set_busy(True)

        def _run() -> str:
            payload = json.dumps(
                {"command": command, "allow_dangerous": allow_dangerous, "shell_mode": True},
                ensure_ascii=False,
            )
            return self.agent.registry.execute_tool("terminal", payload)

        try:
            out = await asyncio.to_thread(_run)
        finally:
            self._set_busy(False)

        # If terminal asks for dangerous confirmation, do it in UI instead of blocking stdin.
        if isinstance(out, str) and "allow_dangerous=true" in out and not allow_dangerous:
            self.pending_bang_command = command
            self._write_warning("该命令需要确认（可能包含写盘/命令替换/非白名单）。是否继续？(y/n)")
            return

        # Show result
        self._write(out if isinstance(out, str) else str(out))

    def _apply_patch(self, user_in: str, patch_text: str) -> None:
        try:
            start = time.time()
            res = self.patch_executor.apply(patch_text)
            self._write("")
            self._write("✅ Patch applied")
            self._write(f"files: {', '.join(res.files_changed) if res.files_changed else '(none)'}")
            if res.backups:
                self._write(f"backups: {len(res.backups)} (in .helloagents/backups/...)")
            log_event(
                "patch_apply",
                {
                    "ok": True,
                    "ms": int((time.time() - start) * 1000),
                    "summary": f"{len(res.files_changed or [])} files",
                    "files_changed": res.files_changed,
                },
            )
            self.agent.note_tool.run(
                {
                    "action": "create",
                    "title": "Patch applied",
                    "content": f"User input:\n{user_in}\n\nPatch:\n\n```text\n{patch_text}\n```\n\nFiles:\n"
                    + "\n".join([f"- {p}" for p in res.files_changed]),
                    "note_type": "action",
                    "tags": [self.project, "patch_applied"],
                }
            )
        except PatchApplyError as e:
            self._write("")
            self._write(f"❌ Patch failed: {e}")
            log_event(
                "patch_apply",
                {
                    "ok": False,
                    "ms": 0,
                    "summary": "PatchApplyError",
                    "error": str(e),
                },
            )
            self.agent.note_tool.run(
                {
                    "action": "create",
                    "title": "Patch failed",
                    "content": f"Error: {e}\n\nUser input:\n{user_in}\n\nPatch:\n\n```text\n{patch_text}\n```\n",
                    "note_type": "blocker",
                    "tags": [self.project, "patch_failed"],
                }
            )


# ============================================================
# Entry point
# ============================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HelloAgents Code Agent TUI")
    parser.add_argument("--repo", type=str, default=".", help="Repository root (workspace). Default: .")
    parser.add_argument("--project", type=str, default=None, help="Project name (default: repo folder name)")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo).resolve()
    load_dotenv(dotenv_path=repo_root / ".env", override=False)

    app = CodeAgentTUI(repo_root=repo_root, project=args.project)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
