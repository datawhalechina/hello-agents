import {
  ApiError,
  createApi,
  fromWareki,
  sanitizeUiState,
  toWareki,
} from "/assets/api.js";

const STORAGE_KEY = "resume-agent-ui-v1";
const LANGUAGE_LABELS = {
  zh: "中文简历",
  ja: "日文简历",
  en: "English Resume",
};
const LANGUAGE_ORDER = ["zh", "ja", "en"];
const DIMENSIONS = [
  ["context", "背景"],
  ["responsibility", "我的职责"],
  ["action", "具体行动"],
  ["method", "方法与工具"],
  ["result", "结果"],
  ["evidence", "证明与数据"],
];
const STYLE_CATALOG = {
  zh: ["藏青现代", "经典墨色", "清新青碧"],
  ja: ["藏青JIS", "墨黑JIS", "蓝灰JIS"],
  en: ["青灰Teal", "经典黑白", "现代蓝"],
};
const api = createApi();

function readState() {
  try {
    return {
      locale: "zh",
      tab: "chat",
      ...sanitizeUiState(JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}")),
    };
  } catch {
    return { locale: "zh", tab: "chat" };
  }
}

const state = readState();
let bases = [];
let currentBase = null;
let currentSession = null;
let versions = [];
let currentVersion = null;
let capabilitiesState = null;
let currentRendered = null;
let editMode = false;
let editorView = "visual";

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitizeUiState(state)));
}

function byId(id) {
  return document.getElementById(id);
}

function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function showToast(message) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toast.hideTimer);
  toast.hideTimer = setTimeout(() => toast.classList.remove("show"), 2400);
}

function setServiceStatus(capabilities) {
  const status = byId("service-status");
  const available = capabilities?.status === "ready";
  status.className = `service-status ${available ? "ready" : "offline"}`;
  status.lastElementChild.textContent = available ? "导师可用" : "仅离线功能";
}

function selectTab(name) {
  const selected = ["chat", "facts", "jd", "tools"].includes(name) ? name : "chat";
  for (const button of byId("primary-tabs").querySelectorAll("button")) {
    button.setAttribute("aria-selected", String(button.dataset.tab === selected));
  }
  for (const panel of document.querySelectorAll("[data-panel]")) {
    panel.hidden = panel.dataset.panel !== selected;
  }
  byId("chat-composer").hidden = selected !== "chat" || !currentBase;
  state.tab = selected;
  saveState();
}

function field(label, name, placeholder = "", value = "", type = "input") {
  const wrapper = element("label", "form-field");
  wrapper.append(element("span", "", label));
  const input = document.createElement(type);
  input.name = name;
  input.placeholder = placeholder;
  input.value = value;
  wrapper.append(input);
  return wrapper;
}

function replaceBase(updated) {
  const index = bases.findIndex((base) => base.id === updated.id);
  if (index >= 0) bases[index] = updated;
  else bases.push(updated);
  currentBase = updated;
}

function chooseBase(base) {
  const changedBase = state.factBaseId && state.factBaseId !== base.id;
  currentBase = base;
  state.factBaseId = base.id;
  const selected = base.experiences.find((item) => item.id === state.experienceId);
  state.experienceId = selected?.id || base.experiences.at(-1)?.id || "";
  if (changedBase) delete state.versionId;
  saveState();
}

async function loadVersions() {
  versions = currentBase ? await api.listVersions(currentBase.id) : [];
  currentVersion = versions.find((item) => item.id === state.versionId)
    || versions.find((item) => item.is_active && item.locale === state.locale)
    || versions.find((item) => item.locale === state.locale)
    || versions.find((item) => item.is_active)
    || versions.at(-1)
    || null;
  if (currentVersion) {
    state.versionId = currentVersion.id;
    state.locale = currentVersion.locale;
  } else {
    delete state.versionId;
  }
  saveState();
}

async function recoverSession() {
  currentSession = null;
  if (!currentBase || !state.experienceId) return;
  try {
    const sessions = await api.listSessions(currentBase.id, state.experienceId);
    currentSession = sessions.find((session) => session.id === state.sessionId)
      || sessions.at(-1)
      || null;
    if (currentSession) state.sessionId = currentSession.id;
    else delete state.sessionId;
    saveState();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "访谈记录读取失败");
  }
}

async function activateBase(base) {
  chooseBase(base);
  await Promise.all([recoverSession(), loadVersions()]);
  renderConversation();
  await renderFactBase();
  renderJdTab();
  renderToolsTab();
  await renderDocument();
}

function renderOnboarding() {
  currentSession = null;
  const panel = byId("chat-panel");
  panel.replaceChildren();
  const heading = element("div", "section-heading");
  heading.append(
    element("h2", "", "先建立一份档案"),
    element("p", "", "填三项即可开始，后面的内容由导师逐步追问。"),
  );

  const form = element("form", "onboarding-form");
  form.id = "onboarding-form";
  form.append(
    field("目标岗位", "role", "例如：数据分析师"),
    field("目标国家或地区（可选）", "country", "例如：日本"),
    field("公司、学校或项目", "organization", "例如：星河科技"),
    field("你当时的角色", "experienceRole", "例如：数据分析实习生"),
  );
  const submit = element("button", "primary", "创建档案并开始");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", handleOnboarding);
  panel.append(heading, form);
  byId("chat-composer").hidden = true;
}

async function handleOnboarding(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const role = String(form.get("role") || "").trim();
  const country = String(form.get("country") || "").trim();
  const organization = String(form.get("organization") || "").trim();
  const experienceRole = String(form.get("experienceRole") || "").trim();
  if (!role || !organization || !experienceRole) {
    showToast("请填写目标岗位、经历名称和角色");
    return;
  }
  const submit = event.currentTarget.querySelector("button[type=submit]");
  submit.disabled = true;
  try {
    let base = await api.createFactBase({
      role,
      country,
      languages: ["zh", "ja", "en"],
    });
    base = await api.addExperience(base.id, { organization, role: experienceRole });
    await activateBase(base);
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "档案创建失败");
    submit.disabled = false;
  }
}

function experienceSelector() {
  const wrapper = element("label", "compact-field");
  wrapper.append(element("span", "", "当前经历"));
  const select = document.createElement("select");
  select.id = "experience-select";
  for (const experience of currentBase.experiences) {
    const option = document.createElement("option");
    option.value = experience.id;
    option.textContent = `${experience.organization} · ${experience.role}`;
    option.selected = experience.id === state.experienceId;
    select.append(option);
  }
  select.addEventListener("change", async () => {
    state.experienceId = select.value;
    delete state.sessionId;
    saveState();
    await recoverSession();
    renderConversation();
  });
  wrapper.append(select);
  return wrapper;
}

function renderPendingProposal(proposal) {
  const card = element("article", "proposal-card");
  const dimensionLabel = DIMENSIONS.find(([key]) => key === proposal.dimension)?.[1]
    || proposal.dimension;
  card.append(
    element("strong", "", "待确认事实"),
    element("span", "proposal-dimension", dimensionLabel),
  );
  const list = element("ul", "proposal-values");
  for (const value of proposal.values) {
    const item = element("li", "", value.text);
    if (value.confidence === "estimated") item.append(element("span", "badge", "估算"));
    if (value.sensitive) item.append(element("span", "badge warning", "敏感"));
    list.append(item);
  }
  card.append(list);
  const actions = element("div", "proposal-actions");
  const confirm = element("button", "primary", "确认事实并继续");
  const reject = element("button", "", "这不是我的意思");
  confirm.type = reject.type = "button";
  confirm.addEventListener("click", () => confirmFact(proposal.id));
  reject.addEventListener("click", () => rejectFact(proposal.id));
  actions.append(confirm, reject);
  card.append(actions);
  return card;
}

function renderConversation() {
  if (!currentBase) {
    renderOnboarding();
    return;
  }
  const panel = byId("chat-panel");
  panel.replaceChildren();
  panel.append(experienceSelector());

  const actions = element("div", "panel-actions");
  const pending = currentSession
    ? Object.values(currentSession.pending_proposals || {})
    : [];
  const hasQuestion = Boolean(currentSession?.current_question);
  let startLabel = "开始访谈";
  if (pending.length) startLabel = "请先确认事实";
  else if (hasQuestion) startLabel = "请回答当前问题";
  else if (currentSession) startLabel = "下一轮提问";
  const start = element(
    "button",
    "primary",
    startLabel,
  );
  start.type = "button";
  start.id = "start-interview";
  start.disabled = pending.length > 0 || hasQuestion;
  start.addEventListener("click", startInterview);
  actions.append(start);
  panel.append(actions);

  const messages = element("div", "chat-messages");
  messages.id = "chat-messages";
  if (!currentSession) {
    const experience = currentBase.experiences.find((item) => item.id === state.experienceId);
    messages.append(element(
      "div",
      "message system-message",
      experience
        ? `当前经历：${experience.organization} · ${experience.role}。导师会一次问一个问题。`
        : "先添加一段经历，再开始访谈。",
    ));
  } else {
    for (const message of currentSession.messages) {
      messages.append(element(
        "div",
        `message ${message.role === "user" ? "user-message" : "assistant-message"}`,
        message.content,
      ));
    }
    if (pending.length) messages.append(renderPendingProposal(pending.at(-1)));
    if (currentSession.current_question && !pending.length) {
      const unknown = element("button", "text-button", "暂时想不到");
      unknown.type = "button";
      unknown.addEventListener("click", recordUnknown);
      messages.append(unknown);
    }
  }
  panel.append(messages);
  byId("chat-composer").hidden = state.tab !== "chat";
  messages.scrollTop = messages.scrollHeight;
}

async function ensureSession() {
  if (currentSession) return currentSession;
  currentSession = await api.createSession(currentBase.id, state.experienceId);
  state.sessionId = currentSession.id;
  saveState();
  return currentSession;
}

async function startInterview() {
  const button = byId("start-interview");
  button.disabled = true;
  try {
    const session = await ensureSession();
    await api.currentQuestion(session.id);
    currentSession = await api.getSession(session.id);
    renderConversation();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "访谈启动失败");
    button.disabled = false;
  }
}

async function submitAnswer(event) {
  event.preventDefault();
  if (!currentBase) return;
  const input = byId("chat-input");
  const message = input.value.trim();
  if (!message) return;
  const submit = event.currentTarget.querySelector("button[type=submit]");
  submit.disabled = true;
  try {
    const session = await ensureSession();
    await api.answer(session.id, message);
    input.value = "";
    currentSession = await api.getSession(session.id);
    renderConversation();
  } catch (error) {
    if (error instanceof ApiError && error.category === "unavailable") {
      showToast("回答已保存，导师暂时无法提炼；稍后可以继续");
      currentSession = state.sessionId ? await api.getSession(state.sessionId) : currentSession;
      renderConversation();
      input.value = "";
    } else {
      showToast(error instanceof ApiError ? error.message : "回答发送失败");
    }
  } finally {
    submit.disabled = false;
  }
}

async function confirmFact(proposalId) {
  try {
    await api.confirmProposal(currentSession.id, proposalId);
    const [base, session] = await Promise.all([
      api.getFactBase(currentBase.id),
      api.getSession(currentSession.id),
    ]);
    replaceBase(base);
    currentSession = session;
    renderConversation();
    await renderFactBase();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "事实确认失败");
  }
}

async function rejectFact(proposalId) {
  try {
    currentSession = await api.rejectProposal(currentSession.id, proposalId);
    renderConversation();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "事实退回失败");
  }
}

async function recordUnknown() {
  const question = currentSession?.current_question;
  if (!question) return;
  try {
    await api.recordUnknown(currentSession.id, question.dimension);
    await api.currentQuestion(currentSession.id);
    currentSession = await api.getSession(currentSession.id);
    renderConversation();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "暂时无法跳过这个问题");
  }
}

function profileForm() {
  const form = element("form", "profile-form");
  const profile = currentBase.profile || {};
  form.append(
    field("姓名", "name", "", profile.name || ""),
    field("邮箱", "email", "", profile.email || ""),
    field("电话", "phone", "", profile.phone || ""),
    field("所在地", "location", "", profile.location || ""),
    field("个人链接（每行一个）", "links", "", (profile.links || []).join("\n"), "textarea"),
  );
  const save = element("button", "primary", "保存基本信息");
  save.type = "submit";
  form.append(save);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    save.disabled = true;
    try {
      const updated = await api.updateProfile(currentBase.id, {
        name: String(data.get("name") || "").trim(),
        email: String(data.get("email") || "").trim(),
        phone: String(data.get("phone") || "").trim(),
        location: String(data.get("location") || "").trim(),
        links: String(data.get("links") || "").split("\n").map((item) => item.trim()).filter(Boolean),
      });
      replaceBase(updated);
      showToast("基本信息已保存");
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : "基本信息保存失败");
    } finally {
      save.disabled = false;
    }
  });
  return form;
}

function factValue(value) {
  const row = element("li", "fact-value", value.text);
  if (value.confidence === "estimated") row.append(element("span", "badge", "估算"));
  if (value.sensitive) row.append(element("span", "badge warning", "敏感"));
  return row;
}

async function renderFactBase() {
  const root = byId("facts-content");
  root.className = "facts-content";
  root.replaceChildren();
  if (!currentBase) {
    root.className = "empty-state";
    root.textContent = "建立档案后可在这里查看经历证据。";
    return;
  }
  const profileDetails = element("details", "profile-details");
  profileDetails.open = false;
  profileDetails.append(element("summary", "", "候选人基本信息"), profileForm());
  root.append(profileDetails);

  const qualityReports = await Promise.all(currentBase.experiences.map(async (experience) => {
    try {
      return await api.experienceQuality(currentBase.id, experience.id);
    } catch {
      return null;
    }
  }));
  currentBase.experiences.forEach((experience, index) => {
    const card = element("article", "experience-card");
    card.append(element("h3", "", `${experience.organization} · ${experience.role}`));
    const quality = qualityReports[index];
    card.append(element(
      "p",
      "quality-caption",
      quality?.passes_gate
        ? "证据已达到可写门槛"
        : `已整理 ${quality?.present_dimensions || 0}/6 个证据维度`,
    ));
    const grid = element("div", "dimension-list");
    for (const [key, label] of DIMENSIONS) {
      const group = element("details", "dimension-group");
      const values = experience.statements?.[key] || [];
      group.append(element("summary", "", `${label} · ${values.length} 条`));
      if (!values.length) group.append(element("p", "empty-copy", "还没有确认事实"));
      else {
        const list = document.createElement("ul");
        for (const value of values) list.append(factValue(value));
        group.append(list);
      }
      grid.append(group);
    }
    const deepen = element("button", "", "继续访谈");
    deepen.type = "button";
    deepen.addEventListener("click", async () => {
      state.experienceId = experience.id;
      delete state.sessionId;
      selectTab("chat");
      await recoverSession();
      renderConversation();
    });
    card.append(grid, deepen);
    root.append(card);
  });
}

async function chooseVersion(versionId) {
  state.versionId = versionId;
  saveState();
  try {
    await api.activateVersion(versionId);
    await loadVersions();
    byId("language-button").textContent = LANGUAGE_LABELS[state.locale];
    renderJdTab();
    renderToolsTab();
    await renderDocument();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "版本切换失败");
  }
}

function versionMeta(version) {
  const language = LANGUAGE_LABELS[version.locale] || version.locale;
  const company = version.company || "通用公司";
  const role = version.target_role || "通用岗位";
  return `${company} · ${role} · ${language}`;
}

function renderJdTab() {
  const root = byId("jd-content");
  root.className = "jd-content";
  root.replaceChildren();
  if (!currentBase) {
    root.className = "empty-state";
    root.textContent = "建立档案后可以创建岗位版本。";
    return;
  }

  const createDetails = element("details", "version-create");
  createDetails.open = versions.length === 0;
  createDetails.append(element("summary", "", versions.length ? "新建岗位版本" : "创建第一个岗位版本"));
  const form = element("form", "version-form");
  form.append(
    field("版本名称", "name", "例如：东京数据分析师", `${currentBase.target?.role || "通用"}版本`),
    field("目标岗位", "targetRole", "职位名称", currentBase.target?.role || ""),
    field("目标公司（可选）", "company", "公司名称"),
    field("岗位描述 JD", "rawJd", "粘贴岗位职责和要求", "", "textarea"),
  );
  const experienceGroup = element("fieldset", "experience-choice");
  experienceGroup.append(element("legend", "", "用于此版本的经历"));
  for (const experience of currentBase.experiences) {
    const label = element("label", "check-row");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "experienceIds";
    checkbox.value = experience.id;
    checkbox.checked = true;
    label.append(checkbox, document.createTextNode(`${experience.organization} · ${experience.role}`));
    experienceGroup.append(label);
  }
  form.append(experienceGroup);
  const submit = element("button", "primary", "创建并预览");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const name = String(data.get("name") || "").trim();
    if (!name) {
      showToast("请填写版本名称");
      return;
    }
    submit.disabled = true;
    try {
      const version = await api.createVersion(currentBase.id, {
        name,
        target_role: String(data.get("targetRole") || "").trim(),
        company: String(data.get("company") || "").trim(),
        raw_jd: String(data.get("rawJd") || "").trim(),
        locale: state.locale,
        selected_experience_ids: data.getAll("experienceIds").map(String),
      });
      state.versionId = version.id;
      saveState();
      await chooseVersion(version.id);
      showToast("岗位版本已创建");
    } catch (error) {
      showToast(error instanceof ApiError ? error.message : "版本创建失败");
      submit.disabled = false;
    }
  });
  createDetails.append(form);
  root.append(createDetails);

  const list = element("div", "version-list");
  for (const version of versions) {
    const card = element("article", `version-card${version.id === currentVersion?.id ? " selected" : ""}`);
    const heading = element("div", "version-card-heading");
    heading.append(element("strong", "", version.name));
    if (version.id === currentVersion?.id) heading.append(element("span", "badge", "当前"));
    if (version.status === "stale") heading.append(element("span", "badge warning", "事实已更新"));
    card.append(heading, element("p", "", versionMeta(version)));
    const use = element("button", "", version.id === currentVersion?.id ? "正在使用" : "使用此版本");
    use.type = "button";
    use.disabled = version.id === currentVersion?.id;
    use.addEventListener("click", () => chooseVersion(version.id));
    card.append(use);
    list.append(card);
  }
  if (versions.length) root.append(list);
}

function configureExportLink(id, format, version) {
  const link = byId(id);
  if (!version) {
    link.removeAttribute("href");
    link.classList.add("disabled");
    link.setAttribute("aria-disabled", "true");
    return;
  }
  link.href = api.exportUrl(version.id, format);
  link.classList.remove("disabled");
  link.setAttribute("aria-disabled", "false");
}

function renderDocumentToolbar() {
  const switcher = byId("document-switcher");
  switcher.replaceChildren();
  const styleSelect = byId("style-select");
  styleSelect.replaceChildren();

  if (!currentVersion) {
    styleSelect.append(new Option("藏青现代"));
    styleSelect.disabled = true;
  } else {
    const versionSelect = document.createElement("select");
    versionSelect.setAttribute("aria-label", "岗位版本");
    for (const version of versions) {
      const option = new Option(version.name, version.id, false, version.id === currentVersion.id);
      versionSelect.append(option);
    }
    versionSelect.addEventListener("change", () => chooseVersion(versionSelect.value));
    versionSelect.disabled = editMode;
    switcher.append(versionSelect);
    if (currentVersion.locale === "ja") {
      const documentTypes = element("div", "document-types");
      const rirekisho = element("button", "selected", "履歴書");
      const workHistory = element("button", "", "職務経歴書");
      rirekisho.type = workHistory.type = "button";
      rirekisho.disabled = true;
      workHistory.addEventListener("click", () => showToast("当前导出会同时保留日文履历所需信息"));
      documentTypes.append(rirekisho, workHistory);
      switcher.append(documentTypes);
    }
    const styleNames = STYLE_CATALOG[currentVersion.locale] || STYLE_CATALOG.zh;
    const selectedStyle = currentVersion.styles?.[currentVersion.locale] || styleNames[0];
    for (const style of styleNames) {
      styleSelect.append(new Option(style, style, false, style === selectedStyle));
    }
    styleSelect.disabled = editMode;
    styleSelect.onchange = async () => {
      styleSelect.disabled = true;
      try {
        const updated = await api.setVersionStyle(currentVersion.id, styleSelect.value);
        versions = versions.map((item) => item.id === updated.id ? updated : item);
        currentVersion = updated;
        await renderDocument();
        showToast("版式已保存");
      } catch (error) {
        showToast(error instanceof ApiError ? error.message : "版式保存失败");
        styleSelect.disabled = false;
      }
    };
  }

  const editButton = byId("edit-button");
  editButton.disabled = !currentVersion;
  editButton.textContent = editMode ? "保存编辑" : "编辑";
  editButton.title = currentVersion ? "编辑当前简历草稿" : "请先创建岗位版本";
  const draftBadge = byId("draft-badge");
  draftBadge.hidden = !currentVersion?.manual_html && !currentVersion?.manual_markdown;
  configureExportLink("export-pdf", "pdf", currentVersion);
  configureExportLink("export-html", "html", currentVersion);
  configureExportLink("export-markdown", "md", currentVersion);
  configureExportLink("export-docx", "docx", currentVersion);
}

async function renderDocument() {
  renderDocumentToolbar();
  const empty = byId("preview-empty");
  const frame = byId("preview-frame");
  const warnings = byId("preview-warnings");
  byId("preview-editor-bar").hidden = !editMode;
  byId("markdown-editor").hidden = true;
  warnings.replaceChildren();
  currentRendered = null;
  frame.hidden = true;
  frame.removeAttribute("srcdoc");
  empty.hidden = false;
  const placeholder = empty.querySelector(".paper-placeholder span");
  if (!currentVersion) {
    placeholder.textContent = "创建岗位版本后，简历会显示在这里。";
    return;
  }

  const requestedId = currentVersion.id;
  placeholder.textContent = "正在生成预览…";
  try {
    const rendered = await api.previewVersion(requestedId);
    if (currentVersion?.id !== requestedId) return;
    currentRendered = rendered;
    for (const warning of rendered.warnings || []) {
      warnings.append(element("div", "preview-warning", warning.message));
    }
    frame.srcdoc = rendered.html;
    empty.hidden = true;
    frame.hidden = false;
  } catch (error) {
    placeholder.textContent = error instanceof ApiError ? error.message : "预览生成失败";
  }
}

function setEditorView(view) {
  editorView = view === "markdown" ? "markdown" : "visual";
  const frame = byId("preview-frame");
  const markdown = byId("markdown-editor");
  const visualButton = byId("visual-editor-button");
  const markdownButton = byId("markdown-editor-button");
  frame.hidden = editorView !== "visual";
  markdown.hidden = editorView !== "markdown";
  visualButton.classList.toggle("selected", editorView === "visual");
  markdownButton.classList.toggle("selected", editorView === "markdown");
  if (frame.contentDocument) {
    frame.contentDocument.designMode = editMode && editorView === "visual" ? "on" : "off";
  }
}

function beginEditor() {
  if (!currentVersion || !currentRendered) {
    showToast("预览尚未准备好");
    return;
  }
  editMode = true;
  editorView = "visual";
  byId("markdown-editor").value = currentRendered.markdown;
  byId("preview-editor-bar").hidden = false;
  renderDocumentToolbar();
  setEditorView("visual");
  showToast("可以直接修改右侧文字，也可以编辑 Markdown");
}

function editedHtml() {
  const documentRoot = byId("preview-frame").contentDocument?.documentElement;
  return documentRoot ? `<!DOCTYPE html>\n${documentRoot.outerHTML}` : currentRendered?.html || "";
}

async function saveEditor() {
  const button = byId("edit-button");
  button.disabled = true;
  try {
    const updated = await api.setVersionDraft(currentVersion.id, {
      markdown: byId("markdown-editor").value,
      html: editedHtml(),
    });
    versions = versions.map((item) => item.id === updated.id ? updated : item);
    currentVersion = updated;
    editMode = false;
    await renderDocument();
    renderToolsTab();
    showToast("编辑稿已保存到服务端");
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "编辑稿保存失败");
    button.disabled = false;
  }
}

async function resetDraft() {
  if (!currentVersion) return;
  const button = byId("reset-draft-button");
  button.disabled = true;
  try {
    const updated = await api.setVersionDraft(currentVersion.id, { markdown: "", html: "" });
    versions = versions.map((item) => item.id === updated.id ? updated : item);
    currentVersion = updated;
    editMode = false;
    await renderDocument();
    renderToolsTab();
    showToast("已恢复为事实库自动生成的版本");
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "恢复失败");
    button.disabled = false;
  }
}

function toolExportLink(label, format) {
  const link = element("a", "button-link", label);
  if (currentVersion) link.href = api.exportUrl(currentVersion.id, format);
  else {
    link.classList.add("disabled");
    link.setAttribute("aria-disabled", "true");
  }
  return link;
}

function renderToolsTab() {
  const root = byId("tools-content");
  root.className = "tools-content";
  root.replaceChildren();

  const service = element("section", "tool-card");
  service.append(
    element("h3", "", "运行状态"),
    element("p", "", capabilitiesState?.status === "ready"
      ? "导师访谈与事实提炼可用。"
      : "导师当前离线，事实库、版本与导出仍可使用。"),
  );
  root.append(service);

  const exports = element("section", "tool-card");
  exports.append(element("h3", "", "当前版本导出"));
  const exportActions = element("div", "tool-actions");
  exportActions.append(
    toolExportLink("HTML", "html"),
    toolExportLink("Markdown", "md"),
    toolExportLink("DOCX", "docx"),
    toolExportLink("PDF", "pdf"),
  );
  exports.append(exportActions);
  root.append(exports);

  const wareki = element("section", "tool-card");
  wareki.append(element("h3", "", "和暦换算"));
  const form = element("form", "wareki-form");
  const western = field("公历日期", "western", "2019-05-01");
  const japanese = field("和暦日期", "japanese", "平成31年4月30日");
  const result = element("output", "conversion-result", "输入一侧日期后换算");
  const actions = element("div", "tool-actions");
  const toJapanese = element("button", "", "转为和暦");
  const toWestern = element("button", "", "转为公历");
  toJapanese.type = toWestern.type = "button";
  toJapanese.addEventListener("click", () => {
    result.textContent = toWareki(western.querySelector("input").value) || "日期格式不正确";
  });
  toWestern.addEventListener("click", () => {
    result.textContent = fromWareki(japanese.querySelector("input").value) || "和暦格式或日期不正确";
  });
  actions.append(toJapanese, toWestern);
  form.append(western, japanese, actions, result);
  wareki.append(form);
  root.append(wareki);
}

async function createSample() {
  byId("sample-button").disabled = true;
  try {
    let base = await api.createFactBase({
      role: "数据分析师",
      country: "日本",
      languages: ["zh", "ja", "en"],
    });
    base = await api.addExperience(base.id, {
      organization: "星河科技",
      role: "数据分析实习生",
    });
    selectTab("chat");
    await activateBase(base);
    showToast("已创建示例档案");
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "示例档案创建失败");
  } finally {
    byId("sample-button").disabled = false;
  }
}

async function cycleLanguage() {
  const index = LANGUAGE_ORDER.indexOf(state.locale);
  state.locale = LANGUAGE_ORDER[(index + 1) % LANGUAGE_ORDER.length];
  byId("language-button").textContent = LANGUAGE_LABELS[state.locale];
  saveState();
  if (!currentBase) return;
  try {
    let version = versions.find((item) => item.locale === state.locale);
    if (!version) {
      const role = currentBase.target?.role || "通用";
      version = await api.createVersion(currentBase.id, {
        name: `${LANGUAGE_LABELS[state.locale]} · ${role}`,
        target_role: role,
        company: "",
        raw_jd: "",
        locale: state.locale,
        selected_experience_ids: currentBase.experiences.map((item) => item.id),
      });
    }
    await chooseVersion(version.id);
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "语言版本切换失败");
  }
}

async function boot() {
  byId("language-button").textContent = LANGUAGE_LABELS[state.locale];
  selectTab(state.tab);
  try {
    const [, capabilities, loadedBases] = await Promise.all([
      api.health(),
      api.capabilities(),
      api.listFactBases(),
    ]);
    bases = loadedBases;
    capabilitiesState = capabilities;
    setServiceStatus(capabilities);
    const base = bases.find((item) => item.id === state.factBaseId) || bases.at(-1) || null;
    if (base) await activateBase(base);
    else renderOnboarding();
  } catch (error) {
    capabilitiesState = null;
    setServiceStatus(null);
    renderOnboarding();
    showToast(error instanceof ApiError ? error.message : "页面初始化失败");
  }
}

byId("primary-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) return;
  selectTab(button.dataset.tab);
  if (button.dataset.tab === "facts") renderFactBase();
  if (button.dataset.tab === "jd") renderJdTab();
  if (button.dataset.tab === "tools") renderToolsTab();
});
byId("settings-button").addEventListener("click", () => byId("settings-dialog").showModal());
byId("sample-button").addEventListener("click", createSample);
byId("language-button").addEventListener("click", cycleLanguage);
byId("chat-composer").addEventListener("submit", submitAnswer);
byId("edit-button").addEventListener("click", () => {
  if (editMode) saveEditor();
  else beginEditor();
});
byId("visual-editor-button").addEventListener("click", () => setEditorView("visual"));
byId("markdown-editor-button").addEventListener("click", () => setEditorView("markdown"));
byId("reset-draft-button").addEventListener("click", resetDraft);
byId("preview-frame").addEventListener("load", () => {
  if (editMode && editorView === "visual") setEditorView("visual");
});

boot();
