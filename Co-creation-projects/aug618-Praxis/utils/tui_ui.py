"""TUI UI 工具（CSS 样式与公共工具引用）。

与 cli_ui 的职责保持一致：仅提供样式与可复用的轻量工具入口。
"""

from __future__ import annotations

# 复用 CLI/TUI 共用的补丁与会话工具，避免重复实现
from utils.patch_utils import extract_patch, normalize_patch, patch_requires_confirmation
from utils.session_utils import load_events, summarize_session, export_session


# ============================================================
# CSS Styles for Textual App
# ============================================================

TUI_CSS = """
Screen {
    layout: vertical;
    background: #0f1115;
}

Header {
    background: #141824;
    color: #e8e8e8;
}

/* Footer widget removed; we use a minimal footer_bar */

#logo {
    height: auto;
    max-height: 100;
    background: #0f1115;
    margin: 1 2 0 2;
    content-align: center middle;
}

#trace {
    height: auto;
    max-height: 12;
    background: #0f1115;
    border: tall #202637;
    margin: 0 2;
    padding: 0 1;
    display: none;
}

#output {
    height: 1fr;
    background: #0f1115;
    border: tall #202637;
    padding: 1 2;
    scrollbar-gutter: stable;
    overflow-y: auto;
}

Collapsible {
    border: tall #202637;
    margin: 0 2;
}

#suggestions {
    height: auto;
    max-height: 10;
    background: #141824;
    border: tall #202637;
    margin: 0 2;
    display: none;
}

#suggestions > ListItem {
    padding: 0 2;
    background: #141824;
}

#suggestions > ListItem:hover {
    background: #202637;
}

#suggestions > ListItem.-highlight {
    background: #4c7dff;
    color: #0f1115;
}

#input_area {
    dock: bottom;
    height: 3;
    background: #0f1115;
    width: 1fr;
}

#input_line_top, #input_line_bottom {
    height: 1;
    /* Textual CSS 不支持 linear-gradient；渐变线由代码用 Rich Text 渲染 */
    background: #0f1115;
    width: 1fr;
    content-align: left middle;
}

#input_row {
    height: 1;
    background: #0f1115;
    padding: 0 2;
}

#input_prompt {
    width: 2;
    color: #7aa2f7;
    text-style: bold;
    content-align: left middle;
}

#input_bar {
    background: #0f1115;
    border: none;
    padding: 0;
    height: 1;
}

Input {
    background: #0f1115;
    border: none;
    color: #e8e8e8;
}

Input:focus {
    border: none;
}

/* Cursor shape is terminal-dependent; we can only style colors here */
Input > .input--cursor {
    background: #00ffff;
    /* 某些终端/渲染环境可能不会正确绘制 cursor 的 background，
       若此时把 cursor 字符设为深色，会导致“光标所在字符消失”，看起来像输入乱码/缺字。
       这里用高对比亮色，保证无论背景是否生效都可见。 */
    color: #e8e8e8;
}

/* 在部分终端里，Input 聚焦时的选区/占位符默认样式会显得像“乱码色块”。
   这里显式设置占位符与选区颜色，避免高对比的黄色块。 */
Input.-placeholder {
    color: #565f89;
}

Input > .input--selection {
    background: #202637;
    color: #e8e8e8;
}

/* footer_bar removed */
"""

