"use strict";

const $ = (id) => document.getElementById(id);
const fields = [
  ["title", "产品名称"], ["target_users", "目标用户"], ["problem", "要解决的问题"],
  ["scenario", "使用场景"], ["core_features", "核心功能"], ["exclusions", "本次不做"],
  ["constraints", "资源与限制"], ["success_criteria", "成功标准"],
];
const reviewDecisions = { pending: "待确认", first_release: "首版做", later: "以后做" };
const acceptanceStatuses = { pending: "待验收", passed: "通过", needs_fix: "待修复" };
let project = null;
let health = {};
let activeTab = "brief";
let pollTimer = null;
let pollVersion = 0;
const pollInterval = 1200;
const pollTimeout = 8000;
const editedFields = new Set();
let questionsEdited = false;
let requestBusy = false;
let reviewTarget = null;
const welcome = $("conversation").firstElementChild.cloneNode(true);
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const activeMotions = new Set();
const tabIndicator = node("span", "", "tab-indicator");
tabIndicator.id = "tab-indicator";
tabIndicator.setAttribute("aria-hidden", "true");
document.querySelector(".tabs").prepend(tabIndicator);

function playMotion(element, frames, options) {
  element.getAnimations().forEach((animation) => animation.cancel());
  if (reducedMotion.matches) return;
  const animation = element.animate(frames, options);
  activeMotions.add(animation);
  animation.onfinish = animation.oncancel = () => activeMotions.delete(animation);
}

function revealContent(elements, direction = 1) {
  // Content is already complete and editable; only its presentation eases in.
  Array.from(elements).filter((element) => element.getClientRects().length).forEach((element, index) => {
    playMotion(element, [
      { opacity: 0, transform: `translateY(${8 * direction}px)` },
      { opacity: 1, transform: "translateY(0)" },
    ], { duration: 420, delay: Math.min(index * 45, 180), easing: "cubic-bezier(.22,1,.36,1)", fill: "backwards" });
  });
}

function moveTabIndicator(animate = true) {
  const indicator = $("tab-indicator");
  const tab = document.querySelector(`[data-tab="${activeTab}"]`);
  const track = tab.parentElement.getBoundingClientRect();
  const target = tab.getBoundingClientRect();
  const current = indicator.getBoundingClientRect();
  const x = target.left - track.left;
  const fromX = current.left - track.left;
  const width = target.width;
  if (!width) return;
  const bridgeX = Math.min(fromX, x);
  const bridgeWidth = Math.max(fromX + current.width, x + width) - bridgeX;
  const transform = (left, scale) => `translate(${left}px, -50%) scaleX(${scale})`;
  indicator.getAnimations().forEach((animation) => animation.cancel());
  indicator.style.width = width + "px";
  indicator.style.transform = transform(x, 1);
  if (animate && indicator.dataset.ready) {
    playMotion(indicator, [
      { transform: transform(fromX, current.width / width), offset: 0 },
      { transform: transform(bridgeX, bridgeWidth / width), offset: .42 },
      { transform: transform(x, 1), offset: 1 },
    ], { duration: 460, easing: "cubic-bezier(.22,1,.36,1)" });
  }
  indicator.dataset.ready = "true";
}

function refreshDocument(container, content) {
  const revision = JSON.stringify([project?.id, content]);
  if (container.dataset.revision === revision) return false;
  container.dataset.revision = revision;
  container.replaceChildren();
  return true;
}

function node(tag, text = "", className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function showError(error, target = "global-error") {
  $(target).textContent = error.message || String(error);
  $(target).hidden = false;
}

async function api(path, body, signal) {
  const response = await fetch(path, body === undefined ? { signal } : {
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
  const previous = activeTab;
  if (previous !== name) $("panel-" + previous).getAnimations({ subtree: true }).forEach((animation) => animation.cancel());
  activeTab = name;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const selected = button.dataset.tab === name;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
    $("panel-" + button.dataset.tab).hidden = !selected;
    if (selected && focus) button.focus();
  });
  moveTabIndicator();
  if (previous !== name) {
    const order = ["brief", "research", "report"];
    const panel = $("panel-" + name);
    const elements = name === "brief" ? panel.children : $(`${name}-content`).children;
    revealContent(elements, order.indexOf(name) > order.indexOf(previous) ? 1 : -1);
  }
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

function hasDraftEdits() {
  return editedFields.size > 0 || questionsEdited;
}

function clearDraftEdits() {
  editedFields.clear();
  questionsEdited = false;
}

function editedQuestions() {
  const value = $("pending-questions").value;
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function draftPayload() {
  const edits = Object.fromEntries([...editedFields].map((key) => [key, $("brief-" + key).value]));
  return { edits, ...(questionsEdited ? { pending_questions: editedQuestions() } : {}) };
}

function updateDraftFeedback() {
  const hasEdits = hasDraftEdits();
  const hint = hasEdits ? "草稿有未保存的修改。" : "确认后，后续分析会以这份需求为准。";
  if ($("save-hint").textContent !== hint) $("save-hint").textContent = hint;
  $("save-draft").disabled = !hasEdits || Boolean(project?.busy || requestBusy);
}

function renderSuggestion(key, disabled) {
  const suggestion = project?.draft_suggestions?.[key];
  const visible = Boolean(suggestion && !project?.confirmed_brief && suggestion !== $("brief-" + key).value.trim());
  $("suggestion-" + key).hidden = !visible;
  $("suggestion-text-" + key).textContent = visible ? suggestion : "";
  $("adopt-" + key).disabled = disabled;
}

function renderBrief() {
  const confirmed = Boolean(project?.confirmed_brief);
  const disabled = !project || project.busy || confirmed || requestBusy;
  $("document-title").textContent = project?.brief?.title || "还没命名的想法";
  $("brief-status").textContent = confirmed ? "已确认" : project ? "待你确认" : "等待输入";
  $("brief-status").classList.toggle("confirmed", confirmed);
  $("brief-help").textContent = confirmed ? "这份需求是后续分析的依据。修改后需要重新生成分析和文档。"
    : "聊过的内容会整理在这里。你可以随时检查，确认前也可以直接修改。";
  const changed = [];
  fields.forEach(([key]) => {
    const input = $("brief-" + key);
    if (!editedFields.has(key)) {
      const value = project?.brief?.[key] || "";
      if (input.value !== value) {
        input.value = value;
        if (value) changed.push(input.parentElement);
      }
    }
    input.disabled = disabled;
    renderSuggestion(key, disabled);
  });
  revealContent(changed);
  $("confirm").hidden = confirmed;
  $("confirm").disabled = !project || project.busy || project.round < 1 || requestBusy;
  $("reopen").hidden = !confirmed;
  $("reopen").disabled = Boolean(project?.busy || requestBusy);
  $("save-draft").hidden = !project || confirmed;
  updateDraftFeedback();
  const pending = project?.pending_questions ?? project?.assumptions ?? [];
  const questions = project?.confirmed_questions ?? project?.assumptions ?? [];
  $("question-editor").hidden = !project || confirmed;
  $("pending-questions").disabled = disabled;
  if (!questionsEdited) $("pending-questions").value = pending.join("\n");
  $("confirmed-questions").hidden = !confirmed || !questions.length;
  $("confirmed-question-list").replaceChildren(...(confirmed ? questions.map((item) => node("li", item)) : []));
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
  const researching = project?.busy && project.retry_action === "generate" && !project.report;
  if (!refreshDocument(container, [project?.sources, project?.notices, project?.competitors, project?.research_summary, researching])) return;
  if (!project?.sources?.length && !project?.notices?.length) {
    container.append(researching
      ? emptyDocument("正在生成分析", "分析和文档完成后，资料会显示在这里。")
      : emptyDocument("先确定问题，再看竞品", "确认需求后，系统会查询相关产品。每条竞品结论都会附上搜索资料的来源。"));
    revealContent(container.children);
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
  revealContent(container.children);
}

function renderReport() {
  const requirements = project?.report ? project.prd?.requirements ?? [] : [];
  const reviews = project?.prd_reviews ?? {};
  const firstRelease = requirements.filter((_, index) => reviews[index]?.decision === "first_release").length;
  const busy = requestBusy || Boolean(project?.busy);
  renderReviews(requirements, reviews, firstRelease, busy);
  renderAcceptance(firstRelease, busy);
  const container = $("report-content");
  if (!refreshDocument(container, [project?.report, project?.conflicts])) return;
  if (!project?.report) {
    container.append(emptyDocument("从想法到一份产品文档", "访谈与分析完成后，这里会出现 PRD 草稿，包含功能范围、实现条件和可检查的验收标准。"));
    revealContent(container.children);
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
  revealContent(article.children);
}

function renderReviews(requirements, reviews, firstRelease, busy) {
  $("reviews").hidden = !requirements.length;
  if (!requirements.length) $("reviews").open = false;
  $("export-checklist").disabled = !firstRelease || busy;
  $("release-checklist-hint").textContent = firstRelease
    ? `${firstRelease} 项功能标为「首版做」`
    : "将功能标为「首版做」后可导出。";
  const items = $("review-items");
  if (refreshDocument(items, [project?.report_id, requirements, reviews])) {
    let decided = 0;
    requirements.forEach((requirement, index) => {
      const decision = reviews[index]?.decision ?? "pending";
      if (decision !== "pending") decided++;
      const status = node("span", reviewDecisions[decision] ?? reviewDecisions.pending, "badge review-status");
      status.dataset.decision = decision;
      const summary = node("div", "", "review-summary");
      summary.append(node("strong", requirement.name), status);
      const button = node("button", "评审", "button secondary compact");
      button.type = "button";
      button.dataset.reviewIndex = String(index);
      button.setAttribute("aria-label", "评审 " + requirement.name);
      button.addEventListener("click", () => openReview(index));
      const item = node("li");
      item.append(summary, button);
      items.append(item);
    });
    $("review-progress").textContent = `${decided} / ${requirements.length} 项已决定`;
  }
  for (const button of items.querySelectorAll("[data-review-index]")) {
    button.disabled = busy;
  }
}

function renderAcceptance(firstRelease, busy) {
  const workspace = $("acceptance-workspace");
  const items = $("acceptance-cases");
  const hasReport = Boolean(project?.report);
  const suite = hasReport ? project.acceptance_suite : null;
  const cases = suite?.cases ?? [];
  const acceptanceTask = project?.retry_action === "generate_acceptance";
  const generating = acceptanceTask && project.busy;
  workspace.hidden = !hasReport;
  if (!hasReport) workspace.open = false;
  $("generate-acceptance").hidden = Boolean(suite);
  $("generate-acceptance").disabled = !hasReport || !firstRelease || busy;
  $("export-acceptance").hidden = !suite;
  $("export-acceptance").disabled = !suite || busy;

  let hint = "将功能标为「首版做」后可生成验收用例。";
  if (generating) hint = "正在生成用例。生成完成后，请按步骤手动验收。";
  else if (suite) hint = "请按步骤手动检查，并记录实际验收结果。";
  else if (acceptanceTask && project.error) hint = project.error;
  else if (firstRelease) hint = "根据首版功能的验收条件生成检查步骤和预期结果。";
  if ($("acceptance-hint").textContent !== hint) $("acceptance-hint").textContent = hint;

  const passed = cases.filter((testCase) => testCase.status === "passed").length;
  $("acceptance-progress").textContent = generating ? "生成中" : cases.length ? `${passed} / ${cases.length} 项通过` : "";
  if (refreshDocument(items, suite?.id)) {
    $("acceptance-error").hidden = true;
    cases.forEach((testCase, index) => items.append(acceptanceCase(suite.id, testCase, index)));
  }
  items.querySelectorAll("select").forEach((select, index) => {
    select.value = cases[index].status;
    select.disabled = busy;
  });
}

function acceptanceCase(suiteId, testCase, index) {
  const item = node("li", "", "acceptance-case");
  const header = node("div", "", "acceptance-case-heading");
  const title = `${testCase.requirement_id} ${testCase.name}`;
  const status = node("select", "", "acceptance-status");
  status.id = `acceptance-status-${index}`;
  const caption = node("label", `${title}的验收状态`, "sr-only");
  caption.htmlFor = status.id;
  for (const [value, label] of Object.entries(acceptanceStatuses)) status.add(new Option(label, value));
  status.addEventListener("change", async () => {
    const hadFocus = document.activeElement === status;
    await mutate("mark-acceptance", {
      suite_id: suiteId, requirement_id: testCase.requirement_id, status: status.value,
    }, "acceptance-error");
    if (hadFocus && document.activeElement === document.body) status.focus();
  });
  header.append(node("h3", title), caption, status);
  const steps = node("ol", "", "acceptance-steps");
  testCase.steps.forEach((step) => steps.append(node("li", step)));
  item.append(header, node("h4", "原验收条件"), node("p", testCase.acceptance),
              node("h4", "检查步骤"), steps, node("h4", "预期结果"), node("p", testCase.expected));
  return item;
}

function openReview(index) {
  const requirement = project.prd.requirements[index];
  const review = project.prd_reviews?.[index];
  reviewTarget = { index, report_id: project.report_id ?? null };
  $("review-title").textContent = requirement.name;
  $("review-description").textContent = requirement.description;
  $("review-decision").value = review?.decision ?? "pending";
  $("review-acceptance").value = review?.acceptance ?? requirement.acceptance;
  $("review-error").hidden = true;
  $("review-dialog").showModal();
}

function renderGenerationNotice() {
  const showingPrevious = project?.report && project.retry_action === "generate";
  const message = showingPrevious && project.busy && project.stage !== "done"
    ? "正在生成新版，当前显示上次生成的内容。"
    : showingPrevious && project.error ? "新版生成失败，仍可查看和导出上次生成的报告。" : "";
  for (const id of ["research-version", "report-version"]) {
    const notice = $(id);
    notice.hidden = !message;
    if (notice.textContent !== message) notice.textContent = message;
  }
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
      const choice = node("div", "", "option-choice");
      const button = node("button", text, "option");
      button.type = "button";
      button.title = "填入输入框，可修改后发送";
      button.addEventListener("click", () => { $("message").value = text; $("message").focus(); });
      const send = node("button", "", "option-send");
      send.type = "button";
      send.title = "直接发送";
      send.setAttribute("aria-label", "直接发送：" + text);
      const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      icon.setAttribute("viewBox", "0 0 24 24");
      icon.setAttribute("aria-hidden", "true");
      icon.setAttribute("focusable", "false");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13");
      icon.append(path);
      send.append(icon);
      send.addEventListener("click", () => {
        if ($("message").disabled || requestBusy) return;
        $("message").value = text;
        $("message-form").requestSubmit();
      });
      choice.append(button, send);
      $("options").append(choice);
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
  renderBrief(); renderResearch(); renderReport(); renderGenerationNotice(); updateConnection();
}

function rememberProject() {
  try { if (project) localStorage.setItem("aipm-project", project.id); else localStorage.removeItem("aipm-project"); }
  catch { /* Application works when browser storage is unavailable. */ }
}

function schedulePoll() {
  clearTimeout(pollTimer);
  const version = ++pollVersion;
  if (!project?.busy) return;
  const id = project.id;
  const isCurrent = () => version === pollVersion && project?.id === id;

  function schedule(delay) {
    pollTimer = setTimeout(async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), pollTimeout);
      let next;
      try {
        next = await api("/api/projects/" + id, undefined, controller.signal);
      } catch {
        if (!isCurrent()) return;
        $("activity-text").textContent = "暂时无法读取进度，正在重新连接…";
        schedule(Math.min(delay * 2, pollTimeout));
        return;
      } finally {
        clearTimeout(timeout);
      }

      if (!isCurrent()) return;
      const changed = next.updated_at !== project.updated_at || next.busy !== project.busy;
      project = next;
      if (changed) {
        if (!next.busy && next.stage === "done" && !next.error) setTab("report");
        render();
      } else if (delay > pollInterval) {
        $("activity-text").textContent = next.activity;
      }
      if (next.busy) schedule(pollInterval);
      else refreshProjects().catch(showError);
    }, delay);
  }

  schedule(pollInterval);
}

async function mutate(action, data = {}, errorTarget = "global-error") {
  if (!project || requestBusy) return false;
  requestBusy = true;
  $("draft-error").hidden = true;
  $("global-error").hidden = true;
  $("acceptance-error").hidden = true;
  $(errorTarget).hidden = true;
  render();
  try {
    project = await api(`/api/projects/${project.id}/${action}`, data);
    if (["draft", "answer", "confirm"].includes(action)) clearDraftEdits();
    if (["generate", "retry"].includes(action) && !project.busy && project.stage === "done" && !project.error) {
      setTab("report");
    }
    await refreshProjects().catch(showError);
    return true;
  } catch (error) {
    showError(error, errorTarget);
    return false;
  } finally {
    requestBusy = false;
    render();
    schedulePoll();
  }
}

fields.forEach(([key, label], index) => {
  const wrapper = node("div", "", "brief-field");
  const caption = node("label"); caption.htmlFor = "brief-" + key;
  caption.append(node("span", String(index + 1).padStart(2, "0"), "field-index"), document.createTextNode(label));
  const input = node("textarea"); input.id = "brief-" + key; input.rows = key === "title" ? 1 : 2;
  input.maxLength = 6000; input.placeholder = "等待访谈补充"; input.disabled = true;
  function trackFieldEdit() {
    if (input.value === (project?.brief?.[key] || "")) editedFields.delete(key);
    else editedFields.add(key);
    renderSuggestion(key, input.disabled);
    updateDraftFeedback();
  }
  input.addEventListener("input", trackFieldEdit);
  const suggestion = node("div", "", "draft-suggestion"); suggestion.id = "suggestion-" + key;
  suggestion.hidden = true;
  const preview = node("p"); preview.id = "suggestion-text-" + key;
  const adopt = node("button", "采用建议", "text-button"); adopt.id = "adopt-" + key;
  adopt.type = "button";
  adopt.setAttribute("aria-label", "采用关于" + label + "的建议");
  adopt.addEventListener("click", () => {
    input.value = project.draft_suggestions[key];
    trackFieldEdit();
    input.focus();
  });
  suggestion.append(node("strong", "AI 建议"), preview, adopt);
  wrapper.append(caption, input, suggestion); $("brief-fields").append(wrapper);
});

$("pending-questions").addEventListener("input", () => {
  const pending = project?.pending_questions ?? project?.assumptions ?? [];
  questionsEdited = JSON.stringify(editedQuestions()) !== JSON.stringify(pending);
  updateDraftFeedback();
});

$("message-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (requestBusy) return;
  if (!health.ready) { openSettings(); return; }
  const value = $("message").value.trim();
  if (!value) return;
  if (project) {
    if (await mutate("answer", { answer: value, ...draftPayload() })) $("message").value = "";
    return;
  }
  requestBusy = true; render(); $("global-error").hidden = true;
  try {
    project = await api("/api/projects", { idea: value });
    $("message").value = ""; rememberProject(); await refreshProjects();
  } catch (error) { showError(error); }
  finally { requestBusy = false; render(); schedulePoll(); }
});

$("save-draft").addEventListener("click", async () => {
  if (await mutate("draft", draftPayload(), "draft-error")) {
    $("save-hint").textContent = "草稿已保存。你可以继续访谈或确认需求。";
  }
});
$("brief-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const values = Object.fromEntries(fields.map(([key]) => [key, $("brief-" + key).value]));
  mutate("confirm", { brief: values, ...(questionsEdited ? { pending_questions: editedQuestions() } : {}) }, "draft-error");
});
$("reopen").addEventListener("click", () => {
  if (window.confirm("修改需求会使已有的竞品分析和 PRD 失效，之后需要重新生成。继续修改吗？")) mutate("reopen");
});
$("generate").addEventListener("click", async () => {
  if (await mutate("generate", { online: $("online").checked }) && project?.busy) setTab("research");
});
$("retry").addEventListener("click", () => mutate("retry"));
$("export").addEventListener("click", () => {
  if (project?.report && !project.busy) window.location.assign(`/api/projects/${project.id}/export`);
});
$("export-checklist").addEventListener("click", () => {
  if (project && !$("export-checklist").disabled) window.location.assign(`/api/projects/${project.id}/release-checklist`);
});
$("generate-acceptance").addEventListener("click", () => mutate("generate-acceptance", {}, "acceptance-error"));
$("export-acceptance").addEventListener("click", () => {
  if (project && !$("export-acceptance").disabled) window.location.assign(`/api/projects/${project.id}/acceptance-export`);
});

$("review-close").addEventListener("click", () => $("review-dialog").close());
$("review-dialog").addEventListener("cancel", (event) => { if (requestBusy) event.preventDefault(); });
$("review-dialog").addEventListener("close", () => {
  document.querySelector(`[data-review-index="${reviewTarget?.index}"]`)?.focus();
  reviewTarget = null;
});
$("review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!reviewTarget || requestBusy) return;
  const data = { ...reviewTarget, decision: $("review-decision").value, acceptance: $("review-acceptance").value };
  const controls = [$("review-close"), $("review-save"), $("review-decision"), $("review-acceptance")];
  controls.forEach((control) => { control.disabled = true; });
  try {
    if (await mutate("review", data, "review-error")) $("review-dialog").close();
  } finally {
    controls.forEach((control) => { control.disabled = false; });
  }
});

function allowSwitch() { return !hasDraftEdits() || window.confirm("草稿有未保存的修改。要放弃修改并切换项目吗？"); }
function newProject() {
  if (!allowSwitch()) return;
  project = null; schedulePoll(); clearDraftEdits(); $("message").value = "";
  $("global-error").hidden = true; $("draft-error").hidden = true;
  rememberProject(); setTab("brief"); render();
  $("project-select").value = ""; $("message").focus();
}
$("new-project").addEventListener("click", newProject);
$("project-select").addEventListener("change", async () => {
  const id = $("project-select").value;
  if (!allowSwitch()) { $("project-select").value = project?.id || ""; return; }
  if (!id) { clearDraftEdits(); newProject(); return; }
  try {
    const next = await api("/api/projects/" + id);
    project = next; clearDraftEdits(); $("message").value = "";
    $("draft-error").hidden = true;
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
window.addEventListener("beforeunload", (event) => {
  if (hasDraftEdits()) { event.preventDefault(); event.returnValue = ""; }
});

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
reducedMotion.addEventListener("change", () => {
  activeMotions.forEach((animation) => animation.cancel());
  moveTabIndicator(false);
});
new ResizeObserver(() => moveTabIndicator(false)).observe(document.querySelector(".tabs"));
document.fonts.ready.then(() => moveTabIndicator(false));
moveTabIndicator(false);
init();
