(function () {
  const STORAGE_KEY = "historical_review_web_v1";

  const $ = (id) => document.getElementById(id);

  function readForm() {
    return {
      api_key: $("cfg-api-key").value.trim(),
      base_url: $("cfg-base-url").value.trim(),
      model: $("cfg-model").value.trim(),
      debate_temperature: parseFloat($("cfg-debate-temp").value) || 0.72,
      synthesizer_temperature: parseFloat($("cfg-synth-temp").value) || 0.22,
      max_tokens: parseInt($("cfg-max-tokens").value, 10) || 4096,
      timeout: parseInt($("cfg-timeout").value, 10) || 180,
      use_evidence_bundle: $("cfg-use-evidence").checked,
    };
  }

  function applyForm(data) {
    if (!data) return;
    if (data.api_key != null) $("cfg-api-key").value = data.api_key;
    if (data.base_url != null) $("cfg-base-url").value = data.base_url;
    if (data.model != null) $("cfg-model").value = data.model;
    if (data.debate_temperature != null) $("cfg-debate-temp").value = data.debate_temperature;
    if (data.synthesizer_temperature != null) $("cfg-synth-temp").value = data.synthesizer_temperature;
    if (data.max_tokens != null) $("cfg-max-tokens").value = data.max_tokens;
    if (data.timeout != null) $("cfg-timeout").value = data.timeout;
    if (data.use_evidence_bundle != null) $("cfg-use-evidence").checked = data.use_evidence_bundle;
  }

  function loadStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      applyForm(data);
    } catch (_) {
      /* ignore */
    }
  }

  function saveStorage() {
    const data = readForm();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  function clearStorage() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function renderMarkdown(md) {
    const el = $("output-md");
    if (!md) {
      el.innerHTML = "";
      return;
    }
    if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
      el.textContent = md;
      return;
    }
    const raw = marked.parse(md, { mangle: false, headerIds: false });
    el.innerHTML = DOMPurify.sanitize(raw);
  }

  function setStatus(text) {
    $("status-text").textContent = text || "";
  }

  function setError(msg) {
    const box = $("output-error");
    if (!msg) {
      box.classList.add("hidden");
      box.textContent = "";
      return;
    }
    box.textContent = msg;
    box.classList.remove("hidden");
  }

  function padTime(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function nowTime() {
    const d = new Date();
    return `${padTime(d.getHours())}:${padTime(d.getMinutes())}:${padTime(d.getSeconds())}`;
  }

  function appendLog(text) {
    const log = $("progress-log");
    const line = document.createElement("div");
    line.className = "log-line";
    line.innerHTML = `<time>${nowTime()}</time>${escapeHtml(text)}`;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function setProgressBar(step, total) {
    const totalN = typeof total === "number" && total > 0 ? total : 15;
    const stepN = typeof step === "number" ? step : 0;
    const pct = Math.min(100, Math.round(((stepN + 1) / totalN) * 100));
    const fill = $("progress-fill");
    const track = $("progress-track");
    fill.style.width = pct + "%";
    track.setAttribute("aria-valuenow", String(pct));
    $("progress-meta").textContent = `进度约 ${pct}%（阶段 ${Math.min(stepN + 1, totalN)} / ${totalN}）`;
  }

  function resetProgressUi() {
    $("progress-log").innerHTML = "";
    $("progress-fill").style.width = "0%";
    $("progress-track").setAttribute("aria-valuenow", "0");
    $("progress-meta").textContent = "准备开始…";
  }

  function handleStreamEvent(ev, state) {
    const t = ev.total;
    const s = typeof ev.step === "number" ? ev.step : state.lastStep;

    switch (ev.event) {
      case "progress":
        appendLog(ev.message || "");
        setStatus(ev.message || "");
        if (typeof ev.step === "number") {
          state.lastStep = ev.step;
          setProgressBar(ev.step, ev.total);
        }
        break;
      case "evidence_done":
        appendLog(`考据附录已就绪（约 ${ev.chars || 0} 字）`);
        if (ev.preview) appendLog("附录预览：" + ev.preview.slice(0, 200).replace(/\s+/g, " ") + "…");
        setProgressBar(ev.step, t);
        break;
      case "round1_start":
      case "round2_start":
      case "digest_start":
      case "synthesis_start":
        appendLog(ev.message || `${ev.event} · ${ev.role || ""}`);
        setStatus(ev.message || "调用模型中…");
        if (typeof ev.step === "number") {
          state.lastStep = ev.step;
          setProgressBar(ev.step, t);
        }
        break;
      case "round1_end":
      case "round2_end":
      case "digest_end":
      case "synthesis_end":
        if (ev.markdown_section) {
          state.md += ev.markdown_section;
          renderMarkdown(state.md);
        }
        appendLog(`✓ 已完成：${ev.role ? ev.role : ev.event.replace("_end", "")}`);
        if (typeof ev.step === "number") {
          state.lastStep = ev.step;
          setProgressBar(ev.step, t);
        }
        break;
      case "complete":
        state.completed = true;
        if (ev.markdown) {
          state.md = ev.markdown;
          renderMarkdown(state.md);
        }
        setProgressBar((t || 15) - 1, t || 15);
        $("progress-meta").textContent = "全部完成";
        setStatus("完成");
        appendLog(ev.message || "全部完成");
        break;
      case "error":
        setError(ev.message || "未知错误");
        setStatus("");
        appendLog("错误：" + (ev.message || ""));
        break;
      default:
        break;
    }
  }

  async function consumeSseStream(response, state) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const block of parts) {
        const line = block.trim();
        if (!line.startsWith("data:")) continue;
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;
        let ev;
        try {
          ev = JSON.parse(jsonStr);
        } catch {
          continue;
        }
        handleStreamEvent(ev, state);
        if (ev.event === "error") return false;
      }
    }
    return !!state.completed;
  }

  async function runDebate() {
    const topic = $("topic-input").value.trim();
    if (!topic) {
      setError("请先填写历史议题。");
      return;
    }

    const cfg = readForm();
    $("btn-run").disabled = true;
    setError("");
    resetProgressUi();
    renderMarkdown("");
    setStatus("连接服务器…");
    appendLog("已提交议题，等待流式响应…");

    const body = {
      topic,
      api_key: cfg.api_key || null,
      base_url: cfg.base_url || null,
      model: cfg.model || null,
      debate_temperature: cfg.debate_temperature,
      synthesizer_temperature: cfg.synthesizer_temperature,
      max_tokens: cfg.max_tokens,
      timeout: cfg.timeout,
      use_evidence_bundle: cfg.use_evidence_bundle,
    };

    const state = { md: "", lastStep: 0, completed: false };
    const ac = new AbortController();
    const to = setTimeout(() => ac.abort(), 920000);

    try {
      const res = await fetch("/api/debate/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ac.signal,
      });

      if (!res.ok) {
        const text = await res.text();
        setError("HTTP " + res.status + " " + text.slice(0, 200));
        setStatus("");
        return;
      }

      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("text/event-stream")) {
        setError("服务器未返回事件流，请重启 Web 服务后重试。");
        setStatus("");
        return;
      }

      const ok = await consumeSseStream(res, state);
      state.completed = ok;
      if (!ok && !$("output-error").textContent) {
        setError("流式输出意外结束，请查看日志或重试。");
      }
    } catch (e) {
      const msg = e.name === "AbortError" ? "等待超时，请重试或缩小议题。" : String(e);
      setError(msg);
      setStatus("");
      appendLog(msg);
    } finally {
      clearTimeout(to);
      $("btn-run").disabled = false;
    }
  }

  $("btn-run").addEventListener("click", runDebate);

  $("btn-save-config").addEventListener("click", () => {
    if ($("cfg-remember").checked) {
      saveStorage();
      setStatus("已保存到本机浏览器");
    } else {
      setStatus("请勾选「记住配置」后再保存，或仅使用当前页面临时配置");
    }
  });

  $("btn-clear-config").addEventListener("click", () => {
    clearStorage();
    $("cfg-api-key").value = "";
    setStatus("已清除本地保存的配置");
  });

  $("btn-toggle-config").addEventListener("click", () => {
    const panel = $("config-panel");
    const collapsed = panel.classList.toggle("collapsed");
    $("btn-toggle-config").setAttribute("aria-expanded", String(!collapsed));
    $("btn-toggle-config").textContent = collapsed ? "展开配置" : "收起配置";
  });

  loadStorage();
})();
