const API_BASE = "http://127.0.0.1:8000";
const USER_ID_STORAGE_KEY = "healthRecordAgent_userId";
const LAST_DIET_RUN_KEY = "healthRecordAgent_lastDietRunId";
const DEV_MODE_STORAGE_KEY = "healthRecordAgent_devMode";
/** 兼容旧版「技术详情」开关 */
const LEGACY_TECH_STORAGE_KEY = "healthRecordAgent_showTech";

function isDeveloperMode() {
    const el = document.getElementById("devModeToggle");
    return !!(el && el.checked);
}

function getUserIdOrEmpty() {
    return document.getElementById("userId")?.value?.trim() || "";
}

/** 体检分析进度：默认对用户显示中文步骤名 */
function getHealthProgressAgents() {
    if (isDeveloperMode()) {
        return [
            { key: "PlannerAgent", label: "PlannerAgent 规划" },
            { key: "HealthIndicatorAgent", label: "HealthIndicatorAgent 指标" },
            { key: "RiskAssessmentAgent", label: "RiskAssessmentAgent 风险" },
            { key: "AdviceAgent", label: "AdviceAgent 建议" },
            { key: "ReportAgent", label: "ReportAgent 报告" },
        ];
    }
    return [
        { key: "PlannerAgent", label: "规划" },
        { key: "HealthIndicatorAgent", label: "指标解读" },
        { key: "RiskAssessmentAgent", label: "风险评估" },
        { key: "AdviceAgent", label: "建议" },
        { key: "ReportAgent", label: "汇总报告" },
    ];
}

function getUserId() {
    const el = document.getElementById("userId");
    const raw = el ? el.value.trim() : "";
    if (!raw) {
        alert("请填写用户 ID");
        return null;
    }
    try {
        localStorage.setItem(USER_ID_STORAGE_KEY, raw);
    } catch (_) { /* ignore */ }
    return raw;
}

function setTab(name) {
    const tabs = ["analysis", "diet", "history"];
    const n = tabs.includes(name) ? name : "analysis";
    tabs.forEach((t) => {
        const panel = document.getElementById(`tab-${t}`);
        if (panel) panel.classList.toggle("hidden", t !== n);
    });
    document.querySelectorAll(".tab-segment [role='tab']").forEach((btn) => {
        const on = btn.dataset.tab === n;
        btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    if (`#${n}` !== location.hash) {
        history.replaceState(null, "", `#${n}`);
    }
    if (n === "diet") {
        refreshReflectRunOptions();
    }
}

function tabFromHash() {
    const h = (location.hash || "").replace(/^#/, "").toLowerCase();
    if (h === "diet" || h === "history" || h === "analysis") return h;
    return "analysis";
}

document.addEventListener("DOMContentLoaded", () => {
    const el = document.getElementById("userId");
    if (el) {
        try {
            const saved = localStorage.getItem(USER_ID_STORAGE_KEY);
            if (saved) el.value = saved;
        } catch (_) { /* ignore */ }
    }

    setTab(tabFromHash());
    window.addEventListener("hashchange", () => setTab(tabFromHash()));

    document.querySelectorAll(".tab-segment [data-tab]").forEach((btn) => {
        btn.addEventListener("click", () => setTab(btn.dataset.tab || "analysis"));
    });

    const devCb = document.getElementById("devModeToggle");
    if (devCb) {
        try {
            const dm = localStorage.getItem(DEV_MODE_STORAGE_KEY);
            const legacy = localStorage.getItem(LEGACY_TECH_STORAGE_KEY);
            if (dm === "1" || legacy === "1") devCb.checked = true;
        } catch (_) { /* ignore */ }
        devCb.addEventListener("change", () => {
            try {
                localStorage.setItem(DEV_MODE_STORAGE_KEY, devCb.checked ? "1" : "0");
            } catch (_) { /* ignore */ }
            refreshReflectRunOptions();
        });
    }

    const dlg = document.getElementById("reflectPromptDialog");
    const go = document.getElementById("reflectDialogGo");
    const later = document.getElementById("reflectDialogLater");
    if (go) {
        go.addEventListener("click", () => {
            if (dlg && typeof dlg.close === "function") dlg.close();
            focusFeedbackSection();
        });
    }
    if (later) {
        later.addEventListener("click", () => {
            if (dlg && typeof dlg.close === "function") dlg.close();
        });
    }

    document.querySelectorAll('input[name="reflectFollowedChoice"]').forEach((el) => {
        el.addEventListener("change", syncReflectReasonVisibility);
    });
    syncReflectReasonVisibility();
});

/** 选「否」时展示未执行原因；选「是」时隐藏并清空原因（后端会将 reason 置为 executed_ok）。 */
function syncReflectReasonVisibility() {
    const yes = document.getElementById("reflectFollowedYes");
    const no = document.getElementById("reflectFollowedNo");
    const block = document.getElementById("reflectReasonBlock");
    const sel = document.getElementById("reflectReasonCode");
    const detail = document.getElementById("reflectDetail");
    if (!block || !sel) return;
    if (no?.checked) {
        block.classList.remove("hidden");
    } else {
        block.classList.add("hidden");
        sel.value = "";
        if (detail) detail.value = "";
    }
}

/** 拉取近期饮食推荐，填充「反馈」下拉的选项；preferredRunId 优先选中（如刚生成的一条）。 */
async function refreshReflectRunOptions(preferredRunId) {
    const sel = document.getElementById("reflectRunSelect");
    if (!sel) return;

    const userId = getUserIdOrEmpty();
    sel.innerHTML = "";

    const addPlaceholder = (text, disabled = true) => {
        const o = document.createElement("option");
        o.value = "";
        o.textContent = text;
        if (disabled) o.disabled = true;
        o.selected = true;
        sel.appendChild(o);
    };

    if (!userId) {
        addPlaceholder("请先填写用户 ID");
        return;
    }

    try {
        const res = await fetch(
            `${API_BASE}/api/diet/users/${encodeURIComponent(userId)}/runs?limit=20`
        );
        const data = await res.json().catch(() => ({}));
        const items = data.items || [];
        if (!items.length) {
            addPlaceholder("暂无推荐记录，请先生成一次饮食推荐");
            return;
        }

        const dev = isDeveloperMode();
        items.forEach((row) => {
            const o = document.createElement("option");
            o.value = row.run_id;
            let label = "";
            try {
                const t = row.created_at
                    ? new Date(row.created_at).toLocaleString("zh-CN", {
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                      })
                    : "";
                const tp =
                    row.total_protein != null
                        ? `约 ${row.total_protein} g 蛋白`
                        : "饮食推荐";
                label = t ? `${t} · ${tp}` : tp;
                if (dev) label += ` · ${row.run_id}`;
            } catch (_) {
                label = row.run_id;
            }
            o.textContent = label;
            sel.appendChild(o);
        });

        const pick =
            preferredRunId ||
            (() => {
                try {
                    return localStorage.getItem(LAST_DIET_RUN_KEY);
                } catch (_) {
                    return null;
                }
            })();
        if (pick && Array.from(sel.options).some((opt) => opt.value === pick)) {
            sel.value = pick;
        }
    } catch (e) {
        console.error(e);
        addPlaceholder("加载推荐列表失败，请稍后重试");
    }
}

function openReflectPromptDialog() {
    const dlg = document.getElementById("reflectPromptDialog");
    if (dlg && typeof dlg.showModal === "function") {
        dlg.showModal();
    } else {
        focusFeedbackSection();
    }
}

function focusFeedbackSection() {
    const h = document.getElementById("feedbackSectionTitle");
    h?.scrollIntoView({ behavior: "smooth", block: "start" });
    const first = document.getElementById("reflectRunSelect");
    if (first) {
        setTimeout(() => first.focus(), 400);
    }
}

function renderMealPlan(mp) {
    if (!mp) return "<p>（无 meal_plan）</p>";
    const tips = Array.isArray(mp.tips) ? mp.tips.filter(Boolean).join("；") : "";
    let h = `<p><strong>估算总蛋白</strong>：${mp.total_est_protein_g ?? "—"} g</p><ul class="meal-plan-list">`;
    (mp.items || []).forEach((it) => {
        h += `<li><strong>${escapeHtml(it.name || "")}</strong> — ${escapeHtml(it.portion || "")}`;
        if (it.est_protein_g != null) h += `（约 <strong>${it.est_protein_g}</strong> g 蛋白）`;
        if (it.why) h += `<br><span class="muted-why">${escapeHtml(it.why)}</span>`;
        h += "</li>";
    });
    h += "</ul>";
    if (tips) h += `<p class="meal-tips"><strong>提示</strong>：${escapeHtml(tips)}</p>`;
    return h;
}

function escapeHtml(s) {
    if (!s) return "";
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
}

async function recommendDiet() {
    const userId = getUserId();
    if (!userId) return;

    const statusEl = document.getElementById("dietStatus");
    const outEl = document.getElementById("dietResult");
    if (!statusEl || !outEl) return;

    statusEl.textContent = isDeveloperMode()
        ? "⏳ 正在调用 Planning + ReAct（可能需多次 LLM，请稍候）…"
        : "⏳ 正在生成推荐，请稍候…";
    outEl.classList.add("hidden");
    outEl.innerHTML = "";

    const foodLog = document.getElementById("dietFoodLog")?.value?.trim() || "";
    if (!foodLog) {
        statusEl.textContent = "⚠️ 请先填写今天吃了什么";
        return;
    }

    const body = {
        user_id: userId,
        context: {
            today_food_log_text: foodLog,
            goal: document.getElementById("dietGoal")?.value || "muscle_gain",
            channels: ["convenience_store", "delivery"],
            activity_context: document.getElementById("dietActivityContext")?.value?.trim() || "",
            free_notes: document.getElementById("dietNotes")?.value?.trim() || "",
        },
    };

    try {
        const res = await fetch(`${API_BASE}/api/diet/recommend`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data.detail ? JSON.stringify(data.detail) : `HTTP ${res.status}`);
        }

        const runId = data.run_id;
        try {
            localStorage.setItem(LAST_DIET_RUN_KEY, runId);
        } catch (_) { /* ignore */ }
        const planning = data.planning || {};
        const ver = data.schema_version || "1";
        const mode = data.pipeline_mode || "legacy";
        const tech = isDeveloperMode();

        let html = "";
        if (tech) {
            html += `<p><strong>run_id</strong>：<code>${escapeHtml(runId)}</code> &nbsp; <small>schema=${escapeHtml(String(ver))} / ${escapeHtml(String(mode))}</small></p>`;
        }
        if (data.degraded) {
            html += tech
                ? `<p class="banner banner-warning"><strong>降级</strong>：部分阶段使用规则/模板兜底，请查看 <code>errors</code>。</p>`
                : `<p class="banner banner-warning"><strong>说明</strong>：部分内容由规则自动补齐，请以列表中的可执行项为准。</p>`;
        }
        if (planning.reasoning) {
            html += tech
                ? `<p><strong>Planning（Nutritionist 摘要）</strong>：${escapeHtml(planning.reasoning)}</p>`
                : `<p><strong>营养分析摘要</strong>：${escapeHtml(planning.reasoning)}</p>`;
        }
        const ns = data.nutrition_summary || {};
        if (!tech) {
            html += `<p><strong>今日营养估算</strong>：蛋白 ${escapeHtml(String(ns.protein_g ?? 0))}g，碳水 ${escapeHtml(String(ns.carb_g ?? 0))}g，脂肪 ${escapeHtml(String(ns.fat_g ?? 0))}g，热量 ${escapeHtml(String(ns.calories_kcal ?? 0))} kcal</p>`;
        } else {
            html += `<details class="diet-trace"><summary>食物解析与营养估算</summary><pre style="white-space:pre-wrap;max-height:220px;overflow:auto;">${escapeHtml(JSON.stringify({ food_parse: data.food_parse, nutrition_summary: data.nutrition_summary }, null, 2))}</pre></details>`;
        }
        const hx = data.habit_extras;
        if (hx && hx.reflect_alignment) {
            html += tech
                ? `<p><strong>Habit · Reflect 对齐</strong>：${escapeHtml(hx.reflect_alignment)}</p>`
                : `<p><strong>与历史反馈对齐</strong>：${escapeHtml(hx.reflect_alignment)}</p>`;
            if (hx.execution_hints && hx.execution_hints.length) {
                html += `<p><strong>执行提示</strong>：${escapeHtml(hx.execution_hints.join("；"))}</p>`;
            }
        }
        html += `<h4>推荐方案</h4>${renderMealPlan(data.meal_plan)}`;

        if (tech) {
            if (data.errors && data.errors.length) {
                html += `<details class="diet-trace"><summary>错误记录（${data.errors.length}）</summary><pre style="white-space:pre-wrap;max-height:200px;overflow:auto;">${escapeHtml(JSON.stringify(data.errors, null, 2))}</pre></details>`;
            }
            if (data.reflect_memory_used) {
                html += `<details class="diet-trace"><summary>已注入的 Reflect 记忆摘要</summary><pre style="white-space:pre-wrap;">${escapeHtml(String(data.reflect_memory_used))}</pre></details>`;
            }
            if (data.react_trace && data.react_trace.length) {
                html += `<details class="diet-trace"><summary>流水线轨迹（${data.react_trace.length} 段）</summary><pre style="white-space:pre-wrap;max-height:280px;overflow:auto;">${escapeHtml(JSON.stringify(data.react_trace, null, 2))}</pre></details>`;
            }
        }

        outEl.innerHTML = html;
        outEl.classList.remove("hidden");
        statusEl.textContent = data.degraded
            ? tech
                ? "⚠️ 推荐完成（含降级，已写入 diet_runs）"
                : "⚠️ 推荐已保存（部分内容已自动处理）"
            : tech
              ? "✅ 推荐完成（已写入 diet_runs）"
              : "✅ 推荐已保存";

        await refreshReflectRunOptions(runId);
        openReflectPromptDialog();
    } catch (e) {
        console.error(e);
        statusEl.textContent = "❌ 请求失败";
        outEl.innerHTML = `<p class="banner-error">${escapeHtml(e.message || String(e))}</p>`;
        outEl.classList.remove("hidden");
    }
}

async function submitDietReflect() {
    const userId = getUserId();
    if (!userId) return;

    const runId = document.getElementById("reflectRunSelect")?.value?.trim();
    if (!runId) {
        alert("请先在列表里选择一条要反馈的推荐，或先生成一次饮食推荐");
        return;
    }

    const yes = document.getElementById("reflectFollowedYes")?.checked;
    const no = document.getElementById("reflectFollowedNo")?.checked;
    if (!yes && !no) {
        alert("请先选择「是否按这条推荐执行」");
        return;
    }
    const followed = !!yes;
    let reasonCode = null;
    let detail = null;
    if (followed) {
        reasonCode = null;
        detail = null;
    } else {
        reasonCode = document.getElementById("reflectReasonCode")?.value?.trim() || null;
        if (!reasonCode) {
            alert("请选择未执行的主要原因");
            return;
        }
        detail = document.getElementById("reflectDetail")?.value?.trim() || null;
    }

    const statusEl = document.getElementById("dietStatus");
    if (statusEl) statusEl.textContent = "⏳ 正在保存反馈…";

    try {
        const res = await fetch(`${API_BASE}/api/diet/reflect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: userId,
                diet_run_id: runId,
                followed,
                reason_code: reasonCode,
                reason_detail: detail,
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data.detail ? JSON.stringify(data.detail) : `HTTP ${res.status}`);
        }
        if (statusEl) {
            statusEl.textContent = isDeveloperMode()
                ? `✅ Reflect 已保存（id=${data.reflect_id}），下次推荐会读取`
                : "✅ 反馈已保存，将在下次推荐时参考";
        }
        await loadDietHistory();
    } catch (e) {
        console.error(e);
        if (statusEl) statusEl.textContent = "❌ 保存失败：" + (e.message || e);
    }
}

async function loadDietHistory() {
    const userId = getUserId();
    if (!userId) return;

    const pre = document.getElementById("dietHistoryPre");
    const hint = document.getElementById("historyEmptyHint");
    const summaryEl = document.getElementById("historySummary");
    const rawDetails = document.getElementById("historyRawDetails");
    if (!pre) return;

    if (hint) hint.classList.add("hidden");
    if (summaryEl) {
        summaryEl.classList.remove("hidden");
        summaryEl.textContent = "加载中…";
    }
    if (rawDetails) {
        rawDetails.classList.add("hidden");
        rawDetails.open = false;
    }
    pre.textContent = "";

    try {
        const [r1, r2] = await Promise.all([
            fetch(`${API_BASE}/api/diet/users/${encodeURIComponent(userId)}/runs?limit=15`).then((r) => r.json()),
            fetch(`${API_BASE}/api/diet/users/${encodeURIComponent(userId)}/reflect_history?limit=15`).then((r) => r.json()),
        ]);
        const n1 = (r1.items || []).length;
        const n2 = (r2.items || []).length;
        if (summaryEl) {
            summaryEl.textContent = `已加载 ${n1} 条饮食推荐记录、${n2} 条反馈记录。`;
        }
        pre.textContent = JSON.stringify({ diet_runs: r1, reflect: r2 }, null, 2);
        if (rawDetails) {
            if (isDeveloperMode()) {
                rawDetails.classList.remove("hidden");
            } else {
                rawDetails.classList.add("hidden");
            }
        }
    } catch (e) {
        if (summaryEl) {
            summaryEl.textContent = "加载失败：" + (e.message || e);
        }
        pre.textContent = "";
    }
}
/**
 * 显示 / 更新多 Agent 进度。仅在 agents 数量变化时重建 DOM，轮询时只更新状态文案，避免整表闪烁。
 */
function showAgentProgress(agentContainer, agents, statusFunc) {
    const getStatus =
        typeof statusFunc === "function" ? statusFunc : () => statusFunc;
    const needRebuild =
        agentContainer.children.length !== agents.length ||
        agents.some((a, i) => agentContainer.children[i]?.dataset?.agentKey !== a.key);

    if (needRebuild) {
        agentContainer.innerHTML = "";
        agents.forEach((agent) => {
            const li = document.createElement("li");
            li.dataset.agentKey = agent.key;
            const labelSpan = document.createElement("span");
            labelSpan.className = "agent-progress-label";
            labelSpan.textContent = agent.label;
            const statusSpan = document.createElement("span");
            statusSpan.className = "agent-progress-status";
            statusSpan.textContent = getStatus(agent.key);
            li.appendChild(labelSpan);
            li.appendChild(document.createTextNode("："));
            li.appendChild(statusSpan);
            agentContainer.appendChild(li);
        });
        return;
    }

    agents.forEach((agent, i) => {
        const li = agentContainer.children[i];
        const statusSpan = li?.querySelector?.(".agent-progress-status");
        if (statusSpan) statusSpan.textContent = getStatus(agent.key);
    });
}

// 公共函数：提交任务并轮询状态
async function submitAndPollTask(url, body, agents, resultCard, reportDiv, analysisDiv, progressList, loadingText, doneText, errorText) {
    reportDiv.innerHTML = "";
    analysisDiv.innerText = loadingText;
    progressList.classList.remove("hidden");
    showAgentProgress(progressList, agents, () => "⏳ 执行中...");
    resultCard.classList.add("hidden");

    try {
        const response = await fetch(url, body);
        if (!response.ok) throw new Error(`服务器返回错误状态：${response.status}`);

        const data = await response.json();
        const taskId = data.task_id;

        let taskStatus = await fetch(`${API_BASE}/api/health/task_status/${taskId}`).then(r => r.json());
        while (taskStatus.state !== "completed") {
            showAgentProgress(progressList, agents, agentKey => taskStatus.agents?.[agentKey] ?? "⏳ 执行中...");
            await new Promise(res => setTimeout(res, 1000));
            taskStatus = await fetch(`${API_BASE}/api/health/task_status/${taskId}`).then(r => r.json());
        }
        // 任务完成后刷新一次 agent 状态，保证 ReportAgent 也显示 completed
        showAgentProgress(progressList, agents, agentKey => taskStatus.agents?.[agentKey] ?? "⏳ 执行中...");
        // 显示最终报告
        const summary = taskStatus.report?.report?.summary || "<p>❌ 未返回报告内容</p>";
        reportDiv.innerHTML = typeof summary === "string" ? summary : JSON.stringify(summary, null, 2);
        analysisDiv.innerText = doneText;
        resultCard.classList.remove("hidden");

    } catch (error) {
        const errorMessage = error?.message || JSON.stringify(error);
        console.error("任务提交或轮询出错:", errorMessage);
        reportDiv.innerHTML = `<p>❌ ${errorText}: ${errorMessage}</p>`;
        analysisDiv.innerText = `❌ ${errorText}`;
        progressList.innerHTML = "";
    }
}

// 文本报告分析
async function analyze() {
    const userId = getUserId();
    if (!userId) return;

    const reportText = document.getElementById("reportText").value;
    if (!reportText) {
        alert("请输入体检报告内容");
        return;
    }

    const resultCard = document.getElementById("resultCard");
    const reportDiv = document.getElementById("report");
    const analysisDiv = document.getElementById("analysis");
    const progressList = document.getElementById("progressList");

    const agents = getHealthProgressAgents();

    await submitAndPollTask(
        `${API_BASE}/api/health/analysis`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ report_text: reportText, user_id: userId })
        },
        agents,
        resultCard,
        reportDiv,
        analysisDiv,
        progressList,
        isDeveloperMode() ? "⏳ 正在分析文本报告，请稍候…" : "⏳ 正在分析，请稍候…",
        "✅ 分析完成",
        "报告生成失败"
    );
}

// PDF报告分析
async function uploadPDF() {
    const userId = getUserId();
    if (!userId) return;

    const fileInput = document.getElementById("pdfFile");
    const file = fileInput.files[0];
    if (!file) {
        alert("请选择PDF文件");
        return;
    }

    const formData = new FormData();
    formData.append("user_id", userId);
    formData.append("file", file);

    const resultCard = document.getElementById("resultCard");
    const reportDiv = document.getElementById("report");
    const analysisDiv = document.getElementById("analysis");
    const progressList = document.getElementById("progressList");

    const agents = getHealthProgressAgents();

    await submitAndPollTask(
        `${API_BASE}/api/health/analysis/pdf`,
        { method: "POST", body: formData },
        agents,
        resultCard,
        reportDiv,
        analysisDiv,
        progressList,
        isDeveloperMode() ? "⏳ 正在分析 PDF 报告，请稍候…" : "⏳ 正在分析 PDF，请稍候…",
        "✅ 分析完成",
        "上传失败"
    );
}
