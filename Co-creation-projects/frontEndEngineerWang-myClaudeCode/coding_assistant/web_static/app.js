const $ = (selector) => document.querySelector(selector);
const state = { conversations: [], current: null, activeTab: 'chat', poll: null };

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function formatTime(value) {
  if (!value) return '';
  try { return new Date(value).toLocaleString('zh-CN', {month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit'}); } catch { return ''; }
}
async function api(url, options = {}) {
  const response = await fetch(url, {headers: {'Content-Type':'application/json'}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `${response.status}`);
  return data;
}
function contentText(content) {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return JSON.stringify(content, null, 2);
  return content.map(block => {
    if (typeof block === 'string') return block;
    if (block.type === 'text') return block.text || '';
    if (block.type === 'tool_use') return `⚙ ${block.name}\n${JSON.stringify(block.input || {}, null, 2)}`;
    if (block.type === 'tool_result') return `↳ tool_result\n${typeof block.content === 'string' ? block.content : JSON.stringify(block.content, null, 2)}`;
    return JSON.stringify(block, null, 2);
  }).join('\n\n');
}
function renderConversations() {
  $('#conversation-list').innerHTML = state.conversations.length ? state.conversations.map(item => `
    <div class="conversation-item ${state.current?.id === item.id ? 'active' : ''}" data-id="${escapeHtml(item.id)}">
      <div class="name">${escapeHtml(item.title || '新对话')}</div>
      <div class="meta"><span>${item.message_count || 0} 条消息</span><span>${formatTime(item.updated_at)}</span></div>
    </div>`).join('') : '<div class="sidebar-label">暂无对话</div>';
  document.querySelectorAll('.conversation-item').forEach(el => el.addEventListener('click', () => selectConversation(el.dataset.id)));
}
function renderStatus() {
  if (!state.current) return;
  const status = state.current.status || 'idle';
  const pill = $('#status-pill');
  pill.className = `status ${status}`;
  pill.textContent = status === 'running' ? '处理中' : status === 'error' ? '出错' : '空闲';
  $('#send').disabled = status === 'running';
  $('#conversation-title').textContent = state.current.title || '新对话';
  $('#workdir').value = state.current.workdir || '';
  $('#debug-count').textContent = (state.current.debug_events || []).length;
}
function renderMessages() {
  const messages = state.current?.messages || [];
  if (!messages.length) {
    $('#messages').innerHTML = '<div class="empty-state"><div class="empty-icon">◌</div><h2>开始一段新的协作</h2><p>告诉 Agent 你想完成什么，它会在当前工作目录中读取、修改和验证代码。</p></div>';
    return;
  }
  $('#messages').innerHTML = messages.map(message => {
    const role = message.role === 'user' ? 'user' : 'assistant';
    const text = contentText(message.content);
    return `<article class="message ${role}"><div class="avatar">${role === 'user' ? '你' : '✦'}</div><div class="bubble">${escapeHtml(text)}</div></article>`;
  }).join('');
  const box = $('#messages'); box.scrollTop = box.scrollHeight;
}
function formatNumber(value) { return Number(value || 0).toLocaleString(); }
function renderTokenMetrics() {
  const usage = state.current?.token_usage || {};
  $('#token-metrics').innerHTML = `
    <div><span>LLM 请求轮次</span><strong>${formatNumber(usage.request_count)}</strong></div>
    <div><span>输入 Token</span><strong>${formatNumber(usage.input_tokens)}</strong></div>
    <div><span>输出 Token</span><strong>${formatNumber(usage.output_tokens)}</strong></div>`;
}

// Sidebar summary for an llm_request event: hides the giant messages payload
// behind an expandable so the trace panel stays readable.
function summarizeLlmRequest(data) {
  const toolNames = data?.tool_names || (data?.tools || []).map(tool => tool.name || '').filter(Boolean);
  const messages = Array.isArray(data?.messages) ? data.messages : [];
  const toolList = toolNames.length ? toolNames.join(', ') : '（无）';
  return {
    model: data?.model || 'unknown',
    message_count: Number(data?.message_count || messages.length || 0),
    tool_list: toolList,
    messages,
  };
}

function renderLlmRequestBody(data) {
  const summary = summarizeLlmRequest(data);
  const header = `<div class="debug-summary"><div><span>model</span><strong>${escapeHtml(summary.model)}</strong></div><div><span>messages</span><strong>${formatNumber(summary.message_count)}</strong></div><div><span>tools</span><strong>${escapeHtml(summary.tool_list)}</strong></div></div>`;
  const messagesJson = JSON.stringify(summary.messages, null, 2);
  return `${header}<details class="debug-sub"><summary>查看最终发送给大模型的 messages</summary><pre>${escapeHtml(messagesJson)}</pre></details>`;
}

function renderDebug() {
  const events = (state.current?.debug_events || []).filter(event => event.type !== 'llm_usage');
  if (!events.length) { $('#debug-events').innerHTML = '<div class="debug-empty">发送消息后，这里会显示完整的模型调用和工具执行链路。</div>'; return; }
  const lastIndex = events.length - 1;
  $('#debug-events').innerHTML = events.map((event, index) => {
    const body = event.type === 'llm_request'
      ? renderLlmRequestBody(event.data || {})
      : `<pre>${escapeHtml(JSON.stringify(event.data ?? {}, null, 2))}</pre>`;
    const size = JSON.stringify(event.data ?? {}).length.toLocaleString();
    return `<details class="debug-event" ${index === lastIndex ? 'open' : ''}><summary><span class="event-type">${escapeHtml(event.type)}</span><span class="event-time">${escapeHtml(formatTime(event.at))}</span><span class="event-size">${size} chars</span></summary>${body}</details>`;
  }).join('');
}
function render() { renderConversations(); renderStatus(); renderMessages(); renderTokenMetrics(); renderDebug(); }
async function refreshList() {
  const result = await api('/api/conversations'); state.conversations = result.conversations || [];
  if (!state.current && state.conversations.length) await selectConversation(state.conversations[0].id, false); else renderConversations();
}
async function selectConversation(id, updateList = true) {
  state.current = await api(`/api/conversations/${encodeURIComponent(id)}`);
  if (updateList) await refreshList(); else render();
  render();
  startPolling();
}
async function createConversation() {
  try {
    const record = await api('/api/conversations', {method:'POST', body:JSON.stringify({workdir: $('#workdir').value || undefined})});
    state.current = record; await refreshList(); render(); $('#prompt').focus();
  } catch (error) { alert(error.message); }
}
function startPolling() {
  clearInterval(state.poll);
  state.poll = setInterval(async () => {
    if (!state.current) return;
    try {
      const latest = await api(`/api/conversations/${encodeURIComponent(state.current.id)}`);
      const changed = latest.updated_at !== state.current.updated_at || latest.status !== state.current.status;
      state.current = latest;
      if (changed) { render(); await refreshList(); }
      if (latest.status === 'running') { renderStatus(); }
    } catch (error) { console.warn(error); }
  }, 900);
}
async function sendMessage(event) {
  event.preventDefault();
  if (!state.current) await createConversation();
  const prompt = $('#prompt').value.trim(); if (!prompt || !state.current) return;
  $('#prompt').value = ''; $('#send').disabled = true;
  try {
    state.current = await api(`/api/conversations/${encodeURIComponent(state.current.id)}/messages`, {method:'POST', body:JSON.stringify({content:prompt})});
    render(); startPolling();
  } catch (error) { $('#prompt').value = prompt; alert(error.message); render(); }
}
async function saveSettings() {
  if (!state.current) return;
  try {
    state.current = await api(`/api/conversations/${encodeURIComponent(state.current.id)}`, {method:'PATCH', body:JSON.stringify({workdir:$('#workdir').value, title:$('#conversation-title').textContent})});
    render(); await refreshList();
  } catch (error) { alert(error.message); }
}
function setup() {
  $('#new-chat').addEventListener('click', createConversation);
  $('#composer').addEventListener('submit', sendMessage);
  $('#save-settings').addEventListener('click', saveSettings);
  $('#refresh-debug').addEventListener('click', async () => { if (state.current) { state.current = await api(`/api/conversations/${encodeURIComponent(state.current.id)}`); renderDebug(); renderStatus(); } });
  $('#prompt').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('#composer').requestSubmit(); } });
  document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => { document.querySelectorAll('.tab').forEach(item => item.classList.remove('active')); document.querySelectorAll('.view').forEach(item => item.classList.remove('active')); tab.classList.add('active'); $(`#${tab.dataset.tab}-view`).classList.add('active'); state.activeTab = tab.dataset.tab; }));
  refreshList().catch(error => alert(error.message));
}
setup();

