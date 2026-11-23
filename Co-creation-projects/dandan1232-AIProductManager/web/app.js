"use strict";

const $ = (id) => document.getElementById(id);
const fields = [
  ["title", "产品名称"], ["target_users", "目标用户"], ["problem", "要解决的问题"],
  ["scenario", "使用场景"], ["core_features", "核心功能"], ["exclusions", "本次不做"],
  ["constraints", "资源与限制"], ["success_criteria", "成功标准"],
];
let project = null;
let health = {};
let activeTab = "brief";
let pollTimer = null;
let dirty = false;
let requestBusy = false;
const welcome = $("conversation").firstElementChild.cloneNode(true);

function node(tag, text = "", className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function showError(error) {
  $("global-error").textContent = error.message || String(error);
  $("global-error").hidden = false;
}

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Requested-With": "AIProductManager" },
    body: JSON.stringify(body),
  });
  let result;
  try { result = await response.json(); }
  catch { throw new Error("服务没有返回有效结果，请检查本地服务是否仍在运行。"); }
  if (!response.ok) throw new Error(result.error || "请求失败，请稍后重试。");
  return result;
}

function setTab(name, focus = false) {
  activeTab = name;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const selected = button.dataset.tab === name;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
    $("panel-" + button.dataset.tab).hidden = !selected;
    if (selected && focus) button.focus();
  });
}

function updateConnection() {
  $("connection-dot").classList.toggle("connected", Boolean(health.ready));
  $("connection-label").textContent = health.ready ? "模型已配置" : "连接设置";
  $("setup-notice").hidden = Boolean(health.ready);
  $("setup-text").textContent = health.framework_installed
    ? "开始之前，连接你使用的模型服务。"
    : "AI 访谈需要安装项目依赖并配置模型连接。";
  $("search-hint").textContent = health.search_configured ? "会查询公开资料，并保留来源链接。" : "尚未配置搜索密钥；也可以取消勾选，只分析已确认需求。";
}

async function refreshProjects() {
  const items = await api("/api/projects");
  const select = $("project-select");
  select.replaceChildren(new Option("当前：新想法", ""));
  for (const item of items) select.add(new Option(item.title, item.id));
  select.value = project?.id || "";
}

function renderBrief() {
  const confirmed = Boolean(project?.confirmed_brief);
  $("document-title").textContent = project?.brief?.title || "还没命名的想法";
  $("brief-status").textContent = confirmed ? "已确认" : project ? "待你确认" : "等待输入";
  $("brief-status").classList.toggle("confirmed", confirmed);
  $("brief-help").textContent = confirmed ? "这份需求是后续分析的依据。修改后需要重新生成分析和文档。"
    : "聊过的内容会整理在这里。你可以随时检查，确认前也可以直接修改。";
  if (!dirty) {
    fields.forEach(([key]) => { $("brief-" + key).value = project?.brief?.[key] || ""; });
  }
  fields.forEach(([key]) => { $("brief-" + key).disabled = !project || project.busy || confirmed || requestBusy; });
  $("confirm").hidden = confirmed;
  $("confirm").disabled = !project || project.busy || project.round < 1 || requestBusy;
  $("reopen").hidden = !confirmed;
  $("reopen").disabled = Boolean(project?.busy || requestBusy);
  $("save-hint").textContent = dirty ? "有尚未确认的修改。确认后会保存这份需求。" : "确认后，后续分析会以这份需求为准。";
  $("assumptions").replaceChildren();
  $("assumptions").hidden = !project?.assumptions?.length || confirmed;
  if (!$("assumptions").hidden) {
    $("assumptions").append(node("strong", "仍需你判断"));
    const list = node("ul");
    project.assumptions.forEach((item) => list.append(node("li", item)));
    $("assumptions").append(list);
  }
  $("generation-controls").hidden = !confirmed;
  $("generate").disabled = Boolean(project?.busy || requestBusy);
  $("generate").textContent = project?.report ? "重新生成分析与 PRD" : "生成分析与 PRD";
  $("online").disabled = Boolean(project?.busy || requestBusy);
}

function emptyDocument(title, description) {
  const box = node("div", "", "empty-document");
  box.append(node("div", "", "empty-rule"), node("h2", title), node("p", description));
  return box;
}

function sourceLink(source) {
  const link = node("a", `${source.id} · ${source.title || "查看来源"}`, "source-link");
  // The API already validates sources; keep this boundary safe for restored/corrupted records too.
  try {
    const url = new URL(source.url);
    if (!["https:", "http:"].includes(url.protocol)) return node("span", "来源地址无效");
    link.href = url.href;
  } catch { return node("span", "来源地址无效"); }
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}

function renderResearch() {
  const container = $("research-content");
  container.replaceChildren();
  if (!project?.sources?.length && !project?.notices?.length) {
    container.append(emptyDocument("先确定问题，再看竞品", "确认需求后，系统会查询相关产品。每条竞品结论都会附上搜索资料的来源。"));
    return;
  }
  container.append(node("p", "公开资料 / 查询记录", "eyebrow"), node("h2", "竞品与参考资料"));
  project.notices.forEach((notice) => container.append(node("p", notice, "notice")));
  if (project.research_summary) container.append(node("p", project.research_summary, "document-help"));
  for (const item of project.competitors) {
    const card = node("article", "", "research-item");
    card.append(node("h3", item.name), node("p", item.positioning), node("p", "相关功能：" + item.features), node("p", "差异与局限：" + item.difference));
    for (const id of item.source_ids) {
      const source = project.sources.find((s) => s.id === id);
      if (source) card.append(sourceLink(source));
    }
    container.append(card);
  }
  for (const source of project.sources) {
    const item = node("div", "", "source-item");
    item.append(sourceLink(source), node("p", "查询时间：" + new Date(source.retrieved_at).toLocaleString("zh-CN")));
    const details = node("details");
    details.append(node("summary", "查看搜索摘录"), node("div", source.content, "source-excerpt"));
    item.append(details);
    container.append(item);
  }
}

function renderReport() {
  const container = $("report-content");
  container.replaceChildren();
  if (!project?.report) {
    container.append(emptyDocument("从想法到一份产品文档", "访谈与分析完成后，这里会出现 PRD 草稿，包含功能范围、实现条件和可检查的验收标准。"));
    return;
  }
  if (project.conflicts.length) container.append(node("p", "一致性检查发现问题：请先检查报告中的冲突，修改需求或重新生成。", "notice error"));
  const article = node("article", "", "report-body");
  // Deliberately render a small safe Markdown subset. Never inject model text as HTML.
  for (const line of project.report.split("\n")) {
    if (!line.trim()) continue;
    if (line.startsWith("### ")) article.append(node("h4", line.slice(4)));
    else if (line.startsWith("## ")) article.append(node("h3", line.slice(3)));
    else if (line.startsWith("# ")) article.append(node("h2", line.slice(2)));
    else if (line.startsWith("> ")) article.append(node("p", line.slice(2), "report-quote"));
    else if (line.startsWith("- ")) article.append(node("p", "• " + line.slice(2), "report-list"));
    else article.append(node("p", line.replace(/^\*\*(.*)\*\*$/, "$1")));
  }
  container.append(article);
}

function render() {
  const busy = Boolean(project?.busy || requestBusy);
  $("new-project").disabled = requestBusy;
  $("project-select").disabled = requestBusy;
  const confirmed = Boolean(project?.confirmed_brief);
  $("round-label").textContent = project ? `第 ${project.round} / 6 轮` : "由你的想法开始";
  $("conversation").replaceChildren();
  if (!project) $("conversation").append(welcome.cloneNode(true));
  else {
    for (const message of project.messages) {
      const item = node("div", "", "message " + message.role);
      item.append(node("div", message.role === "user" ? "你" : "AI 产品经理", "message-author"), node("p", message.content, "message-content"));
      $("conversation").append(item);
    }
    $("conversation").scrollTop = $("conversation").scrollHeight;
  }
  $("activity").hidden = !project?.busy;
  $("activity-text").textContent = project?.activity || "";
  $("task-error").hidden = !project?.error;
  $("task-error-text").textContent = project?.error || "";
  $("retry").disabled = busy;
  $("options").replaceChildren();
  if (project && !busy && !confirmed && !project.ready && !project.error) {
    project.options.forEach((text) => {
      const button = node("button", text, "option");
      button.type = "button";
      button.addEventListener("click", () => { $("message").value = text; $("message").focus(); });
      $("options").append(button);
    });
  }
  $("message-label").textContent = project ? "补充你的回答" : "描述你的产品想法";
  $("message").placeholder = project ? "说说你的选择和考虑，也可以直接说暂时不确定。" : "我想做一个……主要帮助……解决……";
  $("message").disabled = busy || confirmed || Boolean(project?.ready || project?.error);
  $("send").disabled = $("message").disabled;
  $("send").textContent = project ? "发送回答" : "开始梳理";
  $("composer-hint").textContent = confirmed ? "需求已确认，可在右侧开始分析" : project?.ready ? "请检查右侧草稿并确认需求" : "你的回答会成为需求的依据";
  $("export").disabled = !project?.report || busy;
  const stages = { interview: 0, confirm: 1, confirmed: 1, research: 2, assess: 2, writing: 3, audit: 3, done: 3 };
  const step = stages[project?.stage] || 0;
  document.querySelectorAll(".steps li").forEach((li, index) => {
    li.classList.toggle("current", index === step);
    li.classList.toggle("complete", index < step);
    if (index === step) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
  });
  renderBrief(); renderResearch(); renderReport(); updateConnection();
}

function rememberProject() {
  try { if (project) localStorage.setItem("aipm-project", project.id); else localStorage.removeItem("aipm-project"); }
  catch { /* Application works when browser storage is unavailable. */ }
}

function schedulePoll() {
  clearTimeout(pollTimer);
  if (!project?.busy) return;
  const id = project.id;
  pollTimer = setTimeout(async () => {
    try {
      const next = await api("/api/projects/" + id);
      if (project?.id !== id) return;
      const changed = next.updated_at !== project.updated_at || next.busy !== project.busy;
      project = next;
      if (changed) {
        if (project.stage === "done") setTab("report");
        render();
      }
      if (!project.busy) await refreshProjects();
      schedulePoll();
    } catch (error) { showError(error); }
  }, 1200);
}

async function mutate(action, data = {}) {
  if (!project || requestBusy) return;
  requestBusy = true;
  $("global-error").hidden = true;
  render();
  try {
    project = await api(`/api/projects/${project.id}/${action}`, data);
    dirty = false;
    rememberProject();
    await refreshProjects();
  } catch (error) { showError(error); }
  finally { requestBusy = false; render(); schedulePoll(); }
}

fields.forEach(([key, label], index) => {
  const wrapper = node("div", "", "brief-field");
  const caption = node("label"); caption.htmlFor = "brief-" + key;
  caption.append(node("span", String(index + 1).padStart(2, "0"), "field-index"), document.createTextNode(label));
  const input = node("textarea"); input.id = "brief-" + key; input.rows = key === "title" ? 1 : 2;
  input.maxLength = 6000; input.placeholder = "等待访谈补充"; input.disabled = true;
  input.addEventListener("input", () => { dirty = true; $("save-hint").textContent = "有尚未确认的修改。确认后会保存这份需求。"; });
  wrapper.append(caption, input); $("brief-fields").append(wrapper);
});

$("message-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (requestBusy) return;
  if (!health.ready) { openSettings(); return; }
  const value = $("message").value.trim();
  if (!value) return;
  if (dirty && !window.confirm("继续访谈会根据回答更新草稿。要放弃尚未确认的手动修改吗？")) return;
  dirty = false;
  if (project) {
    await mutate("answer", { answer: value });
    if (project?.messages.at(-1)?.content === value || project?.busy) $("message").value = "";
    return;
  }
  requestBusy = true; render(); $("global-error").hidden = true;
  try {
    project = await api("/api/projects", { idea: value });
    $("message").value = ""; rememberProject(); await refreshProjects();
  } catch (error) { showError(error); }
  finally { requestBusy = false; render(); schedulePoll(); }
});

$("brief-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const values = Object.fromEntries(fields.map(([key]) => [key, $("brief-" + key).value]));
  mutate("confirm", { brief: values });
});
$("reopen").addEventListener("click", () => {
  if (window.confirm("修改需求会使已有的竞品分析和 PRD 失效，之后需要重新生成。继续修改吗？")) mutate("reopen");
});
$("generate").addEventListener("click", () => { setTab("research"); mutate("generate", { online: $("online").checked }); });
$("retry").addEventListener("click", () => mutate("retry"));
$("export").addEventListener("click", () => {
  if (project?.report && !project.busy) window.location.assign(`/api/projects/${project.id}/export`);
});

function allowSwitch() { return !dirty || window.confirm("有尚未确认的修改。要放弃这些修改并切换项目吗？"); }
function newProject() {
  if (!allowSwitch()) return;
  clearTimeout(pollTimer); project = null; dirty = false; $("message").value = "";
  $("global-error").hidden = true; rememberProject(); setTab("brief"); render();
  $("project-select").value = ""; $("message").focus();
}
$("new-project").addEventListener("click", newProject);
$("project-select").addEventListener("change", async () => {
  const id = $("project-select").value;
  if (!allowSwitch()) { $("project-select").value = project?.id || ""; return; }
  if (!id) { dirty = false; newProject(); return; }
  try {
    const next = await api("/api/projects/" + id);
    clearTimeout(pollTimer); project = next; dirty = false; $("message").value = "";
    rememberProject(); setTab(project.report ? "report" : "brief"); render(); schedulePoll();
  } catch (error) { showError(error); }
});
document.querySelectorAll("[data-tab]").forEach((button, index, buttons) => {
  button.addEventListener("click", () => setTab(button.dataset.tab));
  button.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? 2 : (index + (event.key === "ArrowRight" ? 1 : -1) + 3) % 3;
    setTab(buttons[next].dataset.tab, true);
  });
});

function openSettings() {
  $("model").value = health.model || "";
  $("base-url").value = health.base_url || "https://api.openai.com/v1";
  $("api-key").value = ""; $("search-key").value = "";
  $("api-key").placeholder = health.llm_configured ? "已经保存；留空保留现有密钥" : "填写服务商提供的密钥";
  $("search-key").placeholder = health.search_configured ? "已经保存；留空保留现有密钥" : "联网竞品研究时使用";
  $("settings-error").hidden = true;
  $("framework-note").hidden = Boolean(health.framework_installed);
  $("framework-note").textContent = "当前 Python 缺少 HelloAgents。请在项目目录运行 python -m pip install -r requirements.txt，然后重启服务。";
  $("settings-dialog").showModal();
}
$("settings-open").addEventListener("click", openSettings);
$("setup-open").addEventListener("click", openSettings);
$("settings-close").addEventListener("click", () => $("settings-dialog").close());
$("settings-dialog").addEventListener("close", () => { $("api-key").value = ""; $("search-key").value = ""; });
$("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  try {
    health = await api("/api/settings", Object.fromEntries(new FormData(event.target)));
    $("settings-dialog").close(); updateConnection();
  } catch (error) { $("settings-error").textContent = error.message; $("settings-error").hidden = false; }
  finally { button.disabled = false; }
});
window.addEventListener("beforeunload", (event) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });

async function init() {
  render();
  try {
    health = await api("/api/health"); updateConnection();
    let saved;
    try { saved = localStorage.getItem("aipm-project"); } catch { saved = null; }
    if (saved) {
      try { project = await api("/api/projects/" + encodeURIComponent(saved)); }
      catch { project = null; rememberProject(); }
    }
    await refreshProjects(); render(); schedulePoll();
  } catch (error) { showError(error); }
}
init();
