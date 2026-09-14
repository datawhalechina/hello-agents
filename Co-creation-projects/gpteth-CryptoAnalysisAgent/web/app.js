const form = document.querySelector("#analyze-form");
const symbolInput = document.querySelector("#symbol");
const runButton = document.querySelector("#run");
const recordBox = document.querySelector("#record");
const reportEl = document.querySelector("#report");
const metricsEl = document.querySelector("#metrics");
const historyEl = document.querySelector("#history");
const healthEl = document.querySelector("#health");
const agentItems = [...document.querySelectorAll("#agent-list li")];

const STAGES = ["technical", "onchain", "sentiment", "coordinator"];
let stageTimer = null;

function setHealth(text, ok = true) {
  healthEl.textContent = text;
  healthEl.style.color = ok ? "" : "var(--bad)";
}

function setBusy(busy) {
  runButton.disabled = busy;
  runButton.textContent = busy ? "分析中…" : "开始分析";
  form.setAttribute("aria-busy", String(busy));
  if (!busy) {
    clearInterval(stageTimer);
    stageTimer = null;
    agentItems.forEach((li) => {
      li.classList.remove("active");
      li.classList.add("done");
    });
  }
}

function startStages() {
  agentItems.forEach((li) => li.classList.remove("active", "done"));
  let i = 0;
  const tick = () => {
    agentItems.forEach((li, idx) => {
      li.classList.toggle("active", idx === i);
      li.classList.toggle("done", idx < i);
    });
    i = (i + 1) % STAGES.length;
  };
  tick();
  stageTimer = setInterval(tick, 2800);
}

function renderMarkdown(markdown) {
  const html = window.marked.parse(markdown || "");
  return window.DOMPurify.sanitize(html);
}

function renderMetrics(data) {
  const evaln = data.evaluation || {};
  const metrics = data.metrics || {};
  const gate = data.gate_passed;
  const grounding = evaln.grounding || {};
  metricsEl.hidden = false;
  metricsEl.innerHTML = `
    <div class="metric"><span>质量门禁</span><strong>${gate ? "通过" : "未通过"}</strong></div>
    <div class="metric"><span>耗时</span><strong>${Number(metrics.elapsed_seconds || 0).toFixed(1)}s</strong></div>
    <div class="metric"><span>工具调用</span><strong>${Object.values(data.tool_counts || {}).reduce((a, b) => a + b, 0)}</strong></div>
    <div class="metric"><span>数字溯源</span><strong>${grounding.grounding_rate != null ? Math.round(grounding.grounding_rate * 100) + "%" : "—"}</strong></div>
  `;
}

function showReport(markdown, appendix) {
  const extra = appendix ? `\n\n---\n\n${appendix}` : "";
  reportEl.innerHTML = renderMarkdown(markdown + extra);
}

function showError(message) {
  metricsEl.hidden = true;
  reportEl.innerHTML = `<p class="error">${message}</p>`;
}

async function loadHistory() {
  const rows = await fetch("/api/reports").then((r) => r.json());
  if (!rows.length) {
    historyEl.innerHTML = `<li class="fine">还没有本地报告</li>`;
    return;
  }
  historyEl.innerHTML = rows.map((row) => `
    <li>
      <button type="button" data-file="${row.filename}">
        <div class="name">
          <strong>${row.symbol}</strong>
          <span class="pill ${row.passed ? "" : "bad"}">${row.passed ? "通过" : "未通过"}</span>
        </div>
        <div class="meta">${row.stamp.replace("_", " ")}</div>
      </button>
    </li>
  `).join("");
}

async function openReport(filename) {
  const data = await fetch(`/api/reports/${encodeURIComponent(filename)}`).then((r) => {
    if (!r.ok) throw new Error("无法读取报告");
    return r.json();
  });
  metricsEl.hidden = true;
  showReport(data.report, data.appendix);
}

async function analyze(symbol) {
  setBusy(true);
  startStages();
  reportEl.innerHTML = `<div class="empty"><h2>正在分析 ${symbol}</h2><p>三位分析师并行工作，随后由协调员交叉验证。请稍候。</p></div>`;
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, record: recordBox.checked }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "分析失败");
    renderMetrics(data);
    showReport(data.report);
    reportEl.scrollIntoView({ behavior: "smooth", block: "start" });
    await loadHistory();
  } catch (err) {
    showError(err.message || "分析失败");
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const symbol = symbolInput.value.trim().toUpperCase();
  if (!symbol) {
    symbolInput.focus();
    return;
  }
  analyze(symbol);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
    chip.setAttribute("aria-pressed", "true");
    symbolInput.value = chip.dataset.symbol;
    symbolInput.focus();
  });
});

historyEl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-file]");
  if (button) openReport(button.dataset.file);
});

async function boot() {
  try {
    const health = await fetch("/api/health").then((r) => r.json());
    setHealth(health.llm_configured ? "本地就绪 · LLM 已配置" : "未检测到 LLM_API_KEY", health.llm_configured);
    await loadHistory();
    const first = historyEl.querySelector("button[data-file]");
    if (first) openReport(first.dataset.file);
  } catch {
    setHealth("无法连接本地服务", false);
  }
}

boot();
