import { ApiError, createApi, sanitizeUiState } from "/assets/api.js";

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
  currentBase = base;
  state.factBaseId = base.id;
  const selected = base.experiences.find((item) => item.id === state.experienceId);
  state.experienceId = selected?.id || base.experiences.at(-1)?.id || "";
  delete state.versionId;
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
  await recoverSession();
  renderConversation();
  await renderFactBase();
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

function cycleLanguage() {
  const index = LANGUAGE_ORDER.indexOf(state.locale);
  state.locale = LANGUAGE_ORDER[(index + 1) % LANGUAGE_ORDER.length];
  byId("language-button").textContent = LANGUAGE_LABELS[state.locale];
  saveState();
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
    setServiceStatus(capabilities);
    const base = bases.find((item) => item.id === state.factBaseId) || bases.at(-1) || null;
    if (base) await activateBase(base);
    else renderOnboarding();
  } catch (error) {
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
});
byId("settings-button").addEventListener("click", () => byId("settings-dialog").showModal());
byId("sample-button").addEventListener("click", createSample);
byId("language-button").addEventListener("click", cycleLanguage);
byId("chat-composer").addEventListener("submit", submitAnswer);

boot();
