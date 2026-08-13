import { ApiError, createApi, sanitizeUiState } from "/assets/api.js";

const STORAGE_KEY = "resume-agent-ui-v1";
const LANGUAGE_LABELS = {
  zh: "中文简历",
  ja: "日文简历",
  en: "English Resume",
};
const LANGUAGE_ORDER = ["zh", "ja", "en"];
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

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitizeUiState(state)));
}

function byId(id) {
  return document.getElementById(id);
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
  byId("chat-composer").hidden = selected !== "chat";
  state.tab = selected;
  saveState();
}

function field(label, name, placeholder = "", value = "") {
  const wrapper = document.createElement("label");
  wrapper.className = "form-field";
  const text = document.createElement("span");
  text.textContent = label;
  const input = document.createElement("input");
  input.name = name;
  input.placeholder = placeholder;
  input.value = value;
  wrapper.append(text, input);
  return wrapper;
}

function renderOnboarding() {
  const panel = byId("chat-panel");
  panel.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "section-heading";
  const title = document.createElement("h2");
  title.textContent = "先建立一份档案";
  const note = document.createElement("p");
  note.textContent = "填三项即可开始，后面的内容由导师逐步追问。";
  heading.append(title, note);

  const form = document.createElement("form");
  form.id = "onboarding-form";
  form.className = "onboarding-form";
  form.append(
    field("目标岗位", "role", "例如：数据分析师"),
    field("目标国家或地区（可选）", "country", "例如：日本"),
    field("公司、学校或项目", "organization", "例如：星河科技"),
    field("你当时的角色", "experienceRole", "例如：数据分析实习生"),
  );
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "primary";
  submit.textContent = "创建档案并开始";
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
    base = await api.addExperience(base.id, {
      organization,
      role: experienceRole,
    });
    bases.push(base);
    chooseBase(base);
    renderCurrentBase();
  } catch (error) {
    showToast(error instanceof ApiError ? error.message : "档案创建失败");
    submit.disabled = false;
  }
}

function chooseBase(base) {
  currentBase = base;
  state.factBaseId = base.id;
  state.experienceId = base.experiences.at(-1)?.id || "";
  delete state.sessionId;
  delete state.versionId;
  saveState();
}

function renderCurrentBase() {
  if (!currentBase) {
    renderOnboarding();
    return;
  }
  const panel = byId("chat-panel");
  panel.replaceChildren();
  const actions = document.createElement("div");
  actions.className = "panel-actions";
  const start = document.createElement("button");
  start.id = "start-interview";
  start.type = "button";
  start.className = "primary";
  start.textContent = "开始访谈";
  actions.append(start);

  const message = document.createElement("div");
  message.className = "message system-message";
  const experience = currentBase.experiences.find((item) => item.id === state.experienceId)
    || currentBase.experiences[0];
  message.textContent = experience
    ? `当前经历：${experience.organization} · ${experience.role}。点击“开始访谈”，导师会一次问一个问题。`
    : "先添加一段经历，再开始访谈。";
  const messages = document.createElement("div");
  messages.id = "chat-messages";
  messages.className = "chat-messages";
  messages.append(message);
  panel.append(actions, messages);
  byId("chat-composer").hidden = false;
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
    bases.push(base);
    chooseBase(base);
    selectTab("chat");
    renderCurrentBase();
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
    currentBase = bases.find((base) => base.id === state.factBaseId) || bases.at(-1) || null;
    if (currentBase) chooseBase(currentBase);
    renderCurrentBase();
  } catch (error) {
    setServiceStatus(null);
    renderOnboarding();
    showToast(error instanceof ApiError ? error.message : "页面初始化失败");
  }
}

byId("primary-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (button) selectTab(button.dataset.tab);
});
byId("settings-button").addEventListener("click", () => byId("settings-dialog").showModal());
byId("sample-button").addEventListener("click", createSample);
byId("language-button").addEventListener("click", cycleLanguage);
byId("chat-composer").addEventListener("submit", (event) => {
  event.preventDefault();
  showToast("请先点击“开始访谈”");
});

boot();
