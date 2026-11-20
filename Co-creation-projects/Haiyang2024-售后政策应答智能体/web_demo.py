# -*- coding: utf-8 -*-
"""本地演示界面：输入一条工单，同时查看三种模式的处理结果。

为什么用标准库而不是 Web 框架：
    本工程的定位是"自包含、依赖轻"。为了一个演示页面再引入 Web 框架并不划算，
    `http.server` 足够支撑"输入 → 运行 → 展示"这一件事，也不给评审者增加安装负担。

启动：
    python web_demo.py
然后浏览器打开：
    http://127.0.0.1:8848
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))  # 先读工作目录下的 .env，再向上查找

from src.agents import MODES, AgentRunner, require_llm_env  # noqa: E402
from src.retriever import PolicyRetriever  # noqa: E402
from src.tools import CATEGORY_RULE, check_red_lines  # noqa: E402

PORT = 8848

RETRIEVER = PolicyRetriever(ROOT / "data" / "knowledge_base")
RUNNER = AgentRunner(RETRIEVER, quiet=True)

#: 预填的示例工单，取自评测集 case_001
SAMPLE_TICKET = (
    "我买的蓝牙耳机订单 20260709001，到现在三天还没发货，客服也没人回。"
    "我现在很着急，能不能赶紧发货？"
)

# 注意：这里必须用原始字符串。页面脚本里有 '\n'、正则里的 \s 等 JS 转义，
# 若按普通字符串处理会被 Python 提前解释，导致整个页面脚本语法错误、按钮点了没反应。
PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>售后政策应答的多范式实证对比 · 本地演示</title>
<style>
  :root { --line:#e3e6ea; --ink:#1f2329; --muted:#6b7280; --brand:#2f6feb; --warn:#c0392b; }
  * { box-sizing:border-box; }
  body { margin:0; padding:32px 20px 64px; background:#f6f7f9; color:var(--ink);
         font:15px/1.7 -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
  .wrap { max-width:1100px; margin:0 auto; }
  h1 { font-size:22px; margin:0 0 6px; }
  .sub { color:var(--muted); margin-bottom:24px; }
  .panel { background:#fff; border:1px solid var(--line); border-radius:10px; padding:20px; margin-bottom:20px; }
  textarea { width:100%; min-height:92px; padding:12px; border:1px solid var(--line);
             border-radius:8px; font:inherit; resize:vertical; }
  .row { display:flex; flex-wrap:wrap; gap:18px; align-items:center; margin-top:14px; }
  label { display:flex; gap:6px; align-items:center; cursor:pointer; }
  button { padding:9px 22px; border:0; border-radius:8px; background:var(--brand); color:#fff;
           font:inherit; font-weight:600; cursor:pointer; }
  button:disabled { opacity:.55; cursor:not-allowed; }
  #status { margin-top:12px; color:var(--muted); min-height:22px; }
  .cards { display:grid; gap:16px; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); }
  .card { background:#fff; border:1px solid var(--line); border-radius:10px; padding:18px; }
  .card-title { font-size:16px; font-weight:600; margin:0 0 4px; }
  .meta { color:var(--muted); font-size:13px; margin-bottom:12px; }
  .answer { word-break:break-word; }
  /* Markdown 渲染样式：模型回复常带标题、加粗、列表、表格与代码块 */
  .md > :first-child { margin-top:0; }
  .md > :last-child { margin-bottom:0; }
  .md p { margin:8px 0; }
  .md h1, .md h2, .md h3, .md h4, .md h5, .md h6 { margin:14px 0 6px; font-size:15px; font-weight:600; }
  .md h1 { font-size:17px; }
  .md h2 { font-size:16px; }
  .md ul, .md ol { margin:8px 0; padding-left:20px; }
  .md li { margin:3px 0; }
  .md code { background:#f1f3f5; padding:1px 5px; border-radius:4px; font-size:13px;
             font-family:ui-monospace, SFMono-Regular, Menlo, monospace; }
  .md pre { background:#f6f8fa; padding:10px 12px; border-radius:8px; overflow-x:auto; margin:10px 0; }
  .md pre code { background:none; padding:0; }
  .md blockquote { margin:8px 0; padding:4px 12px; border-left:3px solid var(--line); color:var(--muted); }
  .md hr { border:0; border-top:1px solid var(--line); margin:12px 0; }
  .md table { border-collapse:collapse; margin:10px 0; font-size:14px; display:block; overflow-x:auto; }
  .md th, .md td { border:1px solid var(--line); padding:6px 10px; text-align:left; }
  .md th { background:#f6f7f9; font-weight:600; }
  .badge { display:inline-block; padding:2px 9px; border-radius:20px; font-size:12px;
           background:#eef4ff; color:var(--brand); margin-right:6px; }
  .badge.bad { background:#fdecea; color:var(--warn); }
  ul.risk { margin:8px 0 0; padding-left:18px; color:var(--warn); }
  .hint { color:var(--muted); font-size:13px; margin-top:10px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>售后政策应答的多范式实证对比</h1>
  <div class="sub">同一套政策库与提示词，只切换编排方式，观察三种模式的差别。三种模式串行执行，通常需要 30 到 60 秒。</div>

  <div class="panel">
    <textarea id="ticket" placeholder="粘贴一条客户诉求…"></textarea>
    <div class="row">
      <label><input type="checkbox" name="mode" value="A" checked> A 无检索直答</label>
      <label><input type="checkbox" name="mode" value="B" checked> B 单跳检索</label>
      <label><input type="checkbox" name="mode" value="C" checked> C 多步自治</label>
      <button id="run">运行</button>
      <button id="reset" style="background:#8a94a6">填入示例</button>
    </div>
    <div id="status">就绪：知识库共 __RULE_COUNT__ 条规则。</div>
    <div class="hint">提示：模式 A 不带工具，容易给不出依据；模式 B 会检索政策；模式 C 还会在定稿前自查合规红线。</div>
  </div>

  <div class="cards" id="cards"></div>
</div>

<script>
const SAMPLE = __SAMPLE__;

function setStatus(text) { document.getElementById('status').textContent = text; }

function esc(text) {
  return (text || '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
}

/* 行内元素：先转义再替换，顺序不能反，否则会把标签转义掉 */
function inline(text) {
  return text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

/* 轻量 Markdown 渲染：只覆盖模型实际会输出的语法，不引入任何前端依赖。
   输入必须是已转义文本，因此这里拼接的标签不会被用户内容注入破坏。 */
function mdToHtml(source) {
  const lines = esc(source || '').split('\n');
  const out = [];
  let index = 0;
  let listType = null;
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length) { out.push('<p>' + inline(paragraph.join('<br>')) + '</p>'); paragraph = []; }
  };
  const closeList = () => {
    if (listType) { out.push('</' + listType + '>'); listType = null; }
  };
  const parseRow = row => row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    // 围栏代码块
    if (trimmed.startsWith('```')) {
      flushParagraph(); closeList();
      const buffer = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        buffer.push(lines[index]); index += 1;
      }
      index += 1;
      out.push('<pre><code>' + buffer.join('\n') + '</code></pre>');
      continue;
    }

    // 表格：当前行含竖线，且下一行是分隔行（|---|---|）
    if (trimmed.includes('|') && index + 1 < lines.length
        && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[index + 1])) {
      flushParagraph(); closeList();
      const header = parseRow(trimmed);
      index += 2;
      const body = [];
      while (index < lines.length && lines[index].includes('|') && lines[index].trim() !== '') {
        body.push(parseRow(lines[index])); index += 1;
      }
      let table = '<table><thead><tr>' + header.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr></thead><tbody>';
      table += body.map(row => '<tr>' + row.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('');
      table += '</tbody></table>';
      out.push(table);
      continue;
    }

    // 标题
    const heading = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushParagraph(); closeList();
      const level = Math.min(heading[1].length, 6);
      out.push('<h' + level + '>' + inline(heading[2]) + '</h' + level + '>');
      index += 1;
      continue;
    }

    // 水平线
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flushParagraph(); closeList();
      out.push('<hr>');
      index += 1;
      continue;
    }

    // 引用。注意文本在进入本函数时已做 HTML 转义，行首的 ">" 已经是 "&gt;"，
    // 这里必须按转义后的形态匹配，否则引用块永远识别不到（测试已覆盖该用例）
    if (/^&gt;\s?/.test(trimmed)) {
      flushParagraph(); closeList();
      const buffer = [];
      while (index < lines.length && /^&gt;\s?/.test(lines[index].trim())) {
        buffer.push(lines[index].trim().replace(/^&gt;\s?/, ''));
        index += 1;
      }
      out.push('<blockquote>' + inline(buffer.join('<br>')) + '</blockquote>');
      continue;
    }

    // 有序 / 无序列表
    const ordered = trimmed.match(/^\d+[.)]\s+(.*)$/);
    const unordered = trimmed.match(/^[-*+]\s+(.*)$/);
    if (ordered || unordered) {
      flushParagraph();
      const wanted = ordered ? 'ol' : 'ul';
      if (listType !== wanted) { closeList(); out.push('<' + wanted + '>'); listType = wanted; }
      out.push('<li>' + inline((ordered || unordered)[1]) + '</li>');
      index += 1;
      continue;
    }

    // 空行：段落与列表的分隔
    if (trimmed === '') {
      flushParagraph(); closeList();
      index += 1;
      continue;
    }

    closeList();
    paragraph.push(line);
    index += 1;
  }

  flushParagraph(); closeList();
  return out.join('\n');
}

function renderCard(item) {
  const risks = (item.redlines && item.redlines.length)
    ? '<ul class="risk">' + item.redlines.map(r => '<li>' + esc(r) + '</li>').join('') + '</ul>'
    : '<div class="hint">未命中合规红线。</div>';
  const flag = (item.redlines && item.redlines.length)
    ? '<span class="badge bad">命中红线 ' + item.redlines.length + ' 处</span>'
    : '<span class="badge">合规通过</span>';
  return '<div class="card">'
    + '<div class="card-title">' + esc(item.mode) + ' · ' + esc(item.label) + '</div>'
    + '<div class="meta">' + esc(item.agent) + '<br>'
    + '耗时 ' + item.elapsed_ms + ' ms ｜ 模型调用 ' + item.llm_calls + ' 次 ｜ 工具调用 ' + item.tool_calls + ' 次</div>'
    + flag
    + '<div class="answer md">' + mdToHtml(item.answer || '（无回复）') + '</div>'
    + risks
    + (item.error ? '<div class="hint">提示：' + esc(item.error) + '</div>' : '')
    + '</div>';
}

async function run() {
  const ticket = document.getElementById('ticket').value.trim();
  const modes = [...document.querySelectorAll('input[name=mode]:checked')].map(el => el.value);
  if (!ticket) { setStatus('请先填写一条客户诉求。'); return; }
  if (!modes.length) { setStatus('请至少选择一种模式。'); return; }

  const button = document.getElementById('run');
  button.disabled = true;
  document.getElementById('cards').innerHTML = '';
  setStatus('运行中…三种模式串行执行，约需 30 到 60 秒，请不要关闭页面。');

  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticket, modes })
    });
    const data = await resp.json();
    if (data.error) { setStatus('运行失败：' + data.error); return; }
    document.getElementById('cards').innerHTML = data.results.map(renderCard).join('');
    setStatus('完成：已生成 ' + data.results.length + ' 个结果。');
  } catch (err) {
    setStatus('运行失败：' + err);
  } finally {
    button.disabled = false;
  }
}

document.getElementById('run').addEventListener('click', run);
document.getElementById('reset').addEventListener('click', () => {
  document.getElementById('ticket').value = SAMPLE;
  setStatus('已填入示例工单，点击"运行"开始。');
});
document.getElementById('ticket').value = SAMPLE;
</script>
</body>
</html>
"""


def run_modes(ticket: str, modes: list[str]) -> list[dict]:
    """串行执行选中的模式，并把红线复核结果一并返回。"""
    results: list[dict] = []
    for mode in modes:
        if mode not in MODES:
            continue
        outcome = RUNNER.run(ticket, mode)
        results.append(
            {
                "mode": mode,
                "label": MODES[mode]["label"],
                "agent": MODES[mode]["agent"],
                "answer": outcome.answer,
                "elapsed_ms": outcome.elapsed_ms,
                "llm_calls": outcome.llm_calls,
                "tool_calls": outcome.tool_calls,
                "redlines": [
                    f"{category}（{CATEGORY_RULE.get(category, '')}）：{matched}"
                    for category, matched in check_red_lines(outcome.answer)
                ],
                "error": outcome.error,
            }
        )
    return results


class Handler(BaseHTTPRequestHandler):
    server_version = "AfterSalesPolicyAgentDemo"

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - 标准库要求的命名
        if self.path == "/favicon.ico":
            # 浏览器会自动请求图标。返回 204 而不是 404，避免控制台里出现与业务无关的
            # 报错噪音——排查问题时这种噪音很容易被误判成接口异常
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if self.path not in ("/", "/index.html"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        page = (
            PAGE.replace("__RULE_COUNT__", str(len(RETRIEVER.list_rules())))
            .replace("__SAMPLE__", json.dumps(SAMPLE_TICKET, ensure_ascii=False))
        )
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - 标准库要求的命名
        if self.path != "/api/run":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")

            ticket = str(payload.get("ticket") or "").strip()
            if not ticket:
                raise ValueError("客户诉求不能为空")

            # 参数校验必须在入口做完。否则字符串形式的 modes 会被逐字符拆成模式，
            # 而全部非法时会静默返回空结果，页面只显示"已生成 0 个结果"，用户看不出问题
            modes_raw = payload.get("modes")
            if modes_raw is None:
                modes_raw = list(MODES)
            if not isinstance(modes_raw, list):
                raise ValueError("modes 必须是模式代号数组，例如 [\"A\", \"C\"]")

            modes = [str(mode).strip() for mode in modes_raw if str(mode).strip() in MODES]
            if not modes:
                raise ValueError(f"没有可运行的模式，可选：{'、'.join(MODES)}")

            body = json.dumps({"results": run_modes(ticket, modes)}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except Exception as exc:  # noqa: BLE001 - 演示服务：把错误如实返回给页面
            body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:
        # 默认会往终端刷访问日志，这里只保留最简信息，避免干扰
        sys.stderr.write("[web_demo] %s\n" % (fmt % args))


def main() -> None:
    # 启动前校验：宁可现在报错，也不要启动后每次都返回空回答
    require_llm_env()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    stats = RETRIEVER.stats()
    print("=" * 60)
    print("售后政策应答的多范式实证对比 · 本地演示")
    print("=" * 60)
    print(f"知识库：{stats['规则条数']} 条规则 / {stats['片段总数']} 个片段")
    print(f"模型：{os.environ.get('LLM_MODEL_ID', '(未配置)')}")
    print(f"打开地址：http://127.0.0.1:{port}")
    print("停止服务：按 Ctrl+C")
    print("=" * 60)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
