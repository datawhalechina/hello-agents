const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const state = { source: 'sample', mode: 'demo', health: null, sample: null, run: null, busy: false, pollTimer: null, pollGeneration: 0, fileGeneration: 0, code: '', toastTimer: null };
const stageNames = { ingest: '读取设计', import: '导入设计', fetch: '获取设计', parse: '解析设计', normalize: '规范化设计', design: '理解设计', analyze: '分析设计', analysis: '分析设计', plan: '制定实现计划', planning: '制定实现计划', generate: '生成代码', codegen: '生成代码', coding: '生成代码', review: '审查代码', verify: '检查结果', repair: '修复问题', export: '整理项目', complete: '生成完成', validate: '校验输入' };
const fieldNames = { summary: '概述', description: '说明', warnings: '注意事项', limitations: '能力边界', issues: '发现的问题', checks: '检查项', status: '状态', passed: '通过', name: '名称', title: '标题', type: '类型', node_id: '节点 ID', node_count: '设计节点数', total_nodes: '设计节点数', text_count: '文本数', total_texts: '文本总数', covered_nodes: '已覆盖节点', covered_texts: '已覆盖文本', text_coverage: '文本覆盖度', structure_coverage: '结构覆盖度', coverage: '结构覆盖度', coverage_ratio: '结构覆盖度', duration_ms: '耗时（毫秒）', iterations: '修复轮数', repair_count: '修复次数', mode: '生成模式', score: '结构检查得分', components: '组件', layout: '布局', style: '样式', styles: '样式', colors: '颜色', typography: '字体', responsive: '响应式', files: '文件', file_count: '文件数', path: '文件路径', size: '大小', missing_nodes: '未覆盖节点', missing_texts: '缺失文本', unsupported_nodes: '暂不支持的节点', framework: '实现方案', steps: '实现步骤', tasks: '任务', evidence: '检查依据', result: '结果', message: '详情', priority: '优先级', reason: '原因', action: '建议', recommendations: '建议', brief: '补充要求', width: '宽度', height: '高度', target: '目标', notes: '备注', assets: '素材', node_ids: '节点 ID', component_name: '组件名', design_name: '设计名称', generated_nodes: '生成节点数', total_duration_ms: '总耗时（毫秒）' };
Object.assign(fieldNames, { llm_calls: '模型调用次数', llm_latency_ms: '模型总耗时（毫秒）', input_chars: '输入字符数', output_chars: '输出字符数', input_chars_note: '输入统计说明', context_omitted_nodes: '上下文省略节点数', truncated_context_calls: '上下文截断次数', token_usage: 'Token 用量', estimated_cost_usd: '模型费用（美元）', cost_note: '费用统计说明', files_count: '生成文件数', node_coverage_percent: '节点结构覆盖率', coverage_note: '覆盖率说明', calls: '模型调用记录', runner: '运行方式', rendered_node_count: '匹配节点数', scope: '检查范围', repair_applied: '已执行修复', model_review: '模型审查', model_review_note: '模型审查说明', observations: '设计观察', detail: '详情', severity: '严重程度', source: '来源', role: '角色', input: '输入', output: '输出', tag: 'HTML 标签', component: '组件名', rationale: '选择依据', responsive_strategy: '响应式策略', context_truncated: '上下文已截断', omitted_nodes: '省略节点数' });

function el(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = String(value);
  return node;
}

function notify(message) {
  clearTimeout(state.toastTimer);
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  state.toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3200);
}

async function request(url, options = {}, raw = false) {
  const response = await fetch(url, { ...options, headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try { const body = await response.json(); message = body.error || body.detail || body.message || message; } catch { /* Keep the HTTP error when the response is not JSON. */ }
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  return raw ? response.text() : response.json();
}

function setFormError(message) {
  $('#form-error').textContent = message || '';
  $('#form-error').hidden = !message;
}

function updateControls() {
  const liveAvailable = Boolean(state.health?.live_available);
  const figmaAvailable = Boolean(state.health?.figma_available);
  const serverReady = Boolean(state.health);
  $$('[data-mode]').forEach((button) => {
    const selected = button.dataset.mode === state.mode;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
    button.disabled = state.busy || (button.dataset.mode === 'live' && !liveAvailable);
    if (button.dataset.mode === 'live') button.title = liveAvailable ? '使用服务端配置的模型运行 Agent' : '服务端未配置模型凭据，暂不可用';
  });
  $('#mode-hint').textContent = state.mode === 'live' ? '模型分析设计并规划语义结构，生成后再审查。布局与样式由设计数据决定。' : liveAvailable ? '离线模式按设计数据生成；也可切换到在线 Agent。' : '离线模式可直接运行。在线 Agent 需在服务端配置模型凭据。';
  $('#figma-hint').textContent = figmaAvailable ? '已配置 Figma 凭据。请选择单个 Frame 的链接。' : '服务端未配置 Figma 凭据。请先配置 FIGMA_ACCESS_TOKEN，或使用样例 / JSON。';
  $('#run-button').disabled = state.busy || !serverReady || (state.source === 'figma' && !figmaAvailable);
  $('#run-button').classList.toggle('busy', state.busy);
  $('#run-label').textContent = state.busy ? '正在生成…' : state.run?.status === 'failed' ? '重新生成' : '生成代码';
  $('#run-caption').textContent = state.busy ? '可以切换结果视图查看进度，请等待当前任务完成。' : state.source === 'figma' && !figmaAvailable ? 'Figma 连接就绪后即可生成。' : '完整过程与检查结果会保留在本次任务中。';
}

function selectSource(source) {
  state.source = source;
  $$('[data-source]').forEach((button) => {
    const selected = button.dataset.source === source;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
    $(`#source-${button.dataset.source}`).hidden = !selected;
  });
  setFormError('');
  updateControls();
}

function selectView(view) {
  $$('[data-view]').forEach((button) => {
    const selected = button.dataset.view === view;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
    $(`#view-${button.dataset.view}`).hidden = !selected;
  });
}

function addTabKeyboard(selector, attribute, callback) {
  const tabs = $$(selector);
  tabs.forEach((button, index) => button.addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    callback(tabs[next].dataset[attribute]);
    tabs[next].focus();
  }));
}

function inspectSample(sample) {
  let root = sample?.document || sample?.design || sample?.root || sample;
  if (sample?.nodes && typeof sample.nodes === 'object') root = Object.values(sample.nodes)[0]?.document || root;
  let frame = null;
  const visit = (node) => {
    if (!node || typeof node !== 'object') return;
    if (!frame && node.type === 'FRAME') frame = node;
    (Array.isArray(node.children) ? node.children : []).forEach(visit);
  };
  visit(root);
  const design = frame || root;
  const countNodes = (node) => !node || typeof node !== 'object' ? 0 : 1 + (Array.isArray(node.children) ? node.children : []).reduce((sum, child) => sum + countNodes(child), 0);
  const count = countNodes(design);
  $('#sample-name').textContent = design?.name || sample?.name || '内置设计样例';
  const bounds = design?.absoluteBoundingBox || design?.bounds || design?.size;
  const dimensions = bounds?.width && bounds?.height ? `${Math.round(bounds.width)} × ${Math.round(bounds.height)}` : '';
  $('#sample-detail').textContent = [dimensions, count > 0 ? `${count} 个设计节点` : 'Figma 设计数据'].filter(Boolean).join(' · ');
}

async function loadFile(file) {
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) { setFormError('JSON 文件超过 2 MB，请只导出需要生成的 Frame。'); return; }
  try {
    const content = await file.text();
    const parsed = JSON.parse(content);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('文件顶层需要是 JSON 对象。');
    $('#json-input').value = content;
    $('#file-label').textContent = file.name;
    setFormError('');
  } catch (error) { setFormError(`无法读取 JSON：${error.message}`); }
}

function collectInput() {
  const input = { source: state.source, mode: state.mode };
  const brief = $('#brief').value.trim();
  if (brief) input.brief = brief;
  if (state.source === 'json') {
    const raw = $('#json-input').value.trim();
    if (!raw) throw new Error('请上传或粘贴 Figma JSON。');
    try { input.payload = JSON.parse(raw); } catch { throw new Error('JSON 格式有误，请检查引号、逗号和括号。'); }
    if (!input.payload || Array.isArray(input.payload) || typeof input.payload !== 'object') throw new Error('JSON 顶层需要是一个对象。');
  }
  if (state.source === 'figma') {
    const value = $('#figma-url').value.trim();
    let url;
    try { url = new URL(value); } catch { throw new Error('请输入完整的 Figma 设计链接。'); }
    if (url.protocol !== 'https:' || !['www.figma.com', 'figma.com'].includes(url.hostname)) throw new Error('请使用 https://www.figma.com/ 开头的设计链接。');
    if (!/^\/(design|file)\/[^/]+/.test(url.pathname)) throw new Error('请选择 Figma design 或 file 设计链接。');
    input.figma_url = value;
    if ($('#node-id').value.trim()) input.node_id = $('#node-id').value.trim();
  }
  if (new TextEncoder().encode(JSON.stringify(input)).byteLength > 2 * 1024 * 1024) throw new Error('完整请求超过 2 MB，请缩小设计 JSON 或减少补充要求。');
  return input;
}

function setRunStatus(status) {
  const names = { queued: '等待执行', running: '正在执行', completed: '生成完成', failed: '执行失败' };
  $('#run-status').className = `run-status ${['queued', 'running', 'completed', 'failed'].includes(status) ? status : ''}`;
  $('#run-status-label').textContent = names[status] || '尚未运行';
}

function resetResult() {
  state.code = '';
  state.fileGeneration += 1;
  $('#preview-frame').removeAttribute('src');
  $('#preview-shell').hidden = true;
  $('#preview-canvas').classList.remove('has-preview');
  $('#preview-empty').hidden = false;
  $('#empty-title').textContent = '正在把设计变成代码';
  $('#empty-description').textContent = '当前阶段与执行结果会实时记录在下方。生成完成后，页面预览将显示在这里。';
  $('#preview-name').textContent = '正在生成';
  $('#preview-note').textContent = '预览将在隔离环境中展示';
  $('#file-select').replaceChildren(el('option', '', '正在生成项目文件…'));
  $('#file-select').disabled = true;
  $('#copy-button').disabled = true;
  $('#copy-label').textContent = '复制代码';
  $('#code-content').hidden = true;
  $('#code-placeholder').hidden = false;
  $('#file-code').textContent = '';
  $('#report-content').replaceChildren();
  $('#report-content').hidden = true;
  $('#report-placeholder').hidden = false;
  const download = $('#download-button');
  download.removeAttribute('href');
  download.classList.add('disabled');
  download.setAttribute('aria-disabled', 'true');
  download.tabIndex = -1;
  $('#event-list').replaceChildren();
  delete $('#event-list').dataset.fingerprint;
  $('#activity-empty').hidden = false;
  $('#activity-empty').textContent = '正在创建任务…';
  $('#event-count').textContent = '0 条记录';
}

function renderEvents(events = []) {
  const container = $('#event-list');
  const body = $('#activity-body');
  const nearBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 65;
  const items = Array.isArray(events) ? events : [];
  const fingerprint = JSON.stringify(items);
  if (container.dataset.fingerprint === fingerprint) return;
  container.dataset.fingerprint = fingerprint;
  container.replaceChildren();
  $('#activity-empty').hidden = items.length > 0;
  $('#activity-empty').textContent = '任务已创建，正在等待执行记录…';
  items.forEach((event) => {
    const status = String(event.status || '');
    const known = ['completed', 'success', 'passed', 'running', 'started', 'failed', 'error'].includes(status) ? status : 'pending';
    const item = el('li', `event-item ${known}`);
    item.append(el('span', 'event-marker', ['completed', 'success', 'passed'].includes(status) ? '✓' : ['failed', 'error'].includes(status) ? '!' : '•'));
    const description = el('div', 'event-description');
    description.append(el('strong', '', stageNames[event.stage] || event.stage || '执行阶段'));
    if (event.message) description.append(el('p', '', event.message));
    item.append(description);
    if (Number.isFinite(event.duration_ms)) item.append(el('span', 'event-duration', event.duration_ms >= 1000 ? `${(event.duration_ms / 1000).toFixed(1)} s` : `${Math.round(event.duration_ms)} ms`));
    container.append(item);
  });
  $('#event-count').textContent = `${items.length} 条记录`;
  if (nearBottom) body.scrollTop = body.scrollHeight;
}

function readable(value, key = '') {
  if (value === null || value === undefined) return '未提供';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'number' && key === 'node_coverage_percent') return `${value}%`;
  if (typeof value === 'number' && /coverage/.test(key) && value >= 0 && value <= 1) return `${Math.round(value * 100)}%`;
  if (key === 'mode') return value === 'demo' ? '离线演示' : value === 'live' ? '在线 Agent' : String(value);
  if (key === 'status') return ({ passed: '通过', passed_with_advisories: '通过，有待人工复核建议', failed: '未通过', completed: '已完成', running: '执行中' })[value] || String(value);
  if (key === 'name') return ({ required_files: '必备文件', node_coverage: '节点结构覆盖', manifest_json: '节点映射文件', basic_accessibility: '基础可访问性' })[value] || String(value);
  if (key === 'runner') return ({ deterministic_demo: '离线规则生成', 'hello_agents.SimpleAgent': 'HelloAgents SimpleAgent', injected_test_runner: '测试替身（非真实模型）' })[value] || String(value);
  return String(value);
}

function renderValue(value, depth = 0) {
  const wrapper = el('div', 'report-data');
  if (depth > 5) { wrapper.append(el('p', '', typeof value === 'object' ? JSON.stringify(value) : readable(value))); return wrapper; }
  if (Array.isArray(value)) {
    if (!value.length) { wrapper.textContent = '无'; return wrapper; }
    const list = el('ul', value.some((item) => item && typeof item === 'object') ? 'report-list' : '');
    value.forEach((item) => { const li = el('li'); li.append(renderValue(item, depth + 1)); list.append(li); });
    wrapper.append(list);
  } else if (value && typeof value === 'object') {
    const list = el('dl');
    Object.entries(value).forEach(([key, content]) => {
      list.append(el('dt', '', fieldNames[key] || key));
      const detail = el('dd');
      if (content && typeof content === 'object') detail.append(renderValue(content, depth + 1));
      else detail.textContent = readable(content, key);
      list.append(detail);
    });
    wrapper.append(list);
  } else { wrapper.append(el('p', '', readable(value))); }
  return wrapper;
}

function renderReport(result) {
  const report = $('#report-content');
  report.replaceChildren();
  report.className = 'report-content';
  const reviewFailed = result.review?.passed === false || result.review?.status === 'failed';
  const summary = el('div', reviewFailed ? 'report-summary needs-review' : 'report-summary');
  summary.append(el('h2', '', reviewFailed ? '代码已生成，存在待修复问题' : '生成结果已就绪'), el('p', '', '以下审查基于设计结构与输出代码。结构检查通过不代表像素级还原，请结合页面预览核对字体、间距和素材。'));
  report.append(summary);
  const appendSection = (title, value) => {
    if (value === undefined || value === null) return;
    const section = el('section', 'report-section');
    section.append(el('h3', '', title), renderValue(value));
    report.append(section);
  };
  if (result.metrics && typeof result.metrics === 'object') {
    const section = el('section', 'report-section');
    section.append(el('h3', '', '运行与结构指标'));
    const grid = el('div', 'metric-grid');
    const headlineMetrics = ['node_coverage_percent', 'node_count', 'files_count', 'llm_calls', 'duration_ms', 'input_chars', 'output_chars'];
    Object.entries(result.metrics).filter(([key, value]) => headlineMetrics.includes(key) && typeof value === 'number').forEach(([key, value]) => {
      const item = el('div', 'metric-item');
      item.append(el('strong', '', readable(value, key)), el('span', '', fieldNames[key] || key));
      grid.append(item);
    });
    section.append(grid, el('p', 'report-note', '仅展示本次任务实际返回的指标；覆盖度衡量结构或文本，不衡量视觉相似度。'));
    const extraMetrics = Object.fromEntries(Object.entries(result.metrics).filter(([key]) => !headlineMetrics.includes(key)));
    if (Object.keys(extraMetrics).length) {
      const details = el('details', 'metrics-details');
      details.append(el('summary', '', '查看调用明细与费用说明'), renderValue(extraMetrics));
      section.append(details);
    }
    report.append(section);
  }
  const warnings = result.warnings || result.design?.warnings;
  if (warnings && (!Array.isArray(warnings) || warnings.length)) {
    const warning = el('section', 'warning-block');
    warning.append(el('h3', '', '设计导入注意事项'), renderValue(warnings));
    report.append(warning);
  }
  appendSection('代码审查', result.review);
  appendSection('设计分析', result.analysis);
  appendSection('实现计划', result.plan);
  if (!result.analysis && !result.plan && !result.review && !result.metrics) report.append(el('p', 'report-note', '本次任务没有返回详细审查数据，请直接查看源代码与预览。'));
  report.hidden = false;
  $('#report-placeholder').hidden = true;
}

async function loadCode(path) {
  if (!state.run || !path) return;
  const generation = ++state.fileGeneration;
  const runId = state.run.id;
  $('#copy-button').disabled = true;
  $('#copy-label').textContent = '复制代码';
  $('#file-code').textContent = '正在读取文件…';
  $('#code-placeholder').hidden = true;
  $('#code-content').hidden = false;
  state.code = '';
  try {
    const content = await request(`/api/runs/${encodeURIComponent(runId)}/files?path=${encodeURIComponent(path)}`, {}, true);
    if (generation !== state.fileGeneration || state.run?.id !== runId) return;
    state.code = content;
    $('#file-code').textContent = content;
    $('#copy-button').disabled = false;
  } catch (error) {
    if (generation !== state.fileGeneration) return;
    $('#file-code').textContent = `文件读取失败：${error.message}`;
  }
}

function renderCompleted(run) {
  const result = run.result || {};
  const base = `/api/runs/${encodeURIComponent(run.id)}`;
  $('#preview-empty').hidden = true;
  $('#preview-shell').hidden = false;
  $('#preview-canvas').classList.add('has-preview');
  $('#preview-frame').src = `${base}/preview`;
  $('#preview-name').textContent = result.design?.name || result.design?.root?.name || '生成页面';
  $('#preview-note').textContent = `${result.mode === 'live' ? '在线 Agent' : '离线演示'}生成 · 脚本已在预览中禁用`;
  const download = $('#download-button');
  download.href = `${base}/download`;
  download.setAttribute('download', `framecraft-${run.id}.zip`);
  download.classList.remove('disabled');
  download.setAttribute('aria-disabled', 'false');
  download.tabIndex = 0;
  const files = Array.isArray(result.files) ? result.files : [];
  const select = $('#file-select');
  select.replaceChildren();
  files.forEach((file) => {
    const path = typeof file === 'string' ? file : file.path;
    if (!path) return;
    const option = el('option', '', path);
    option.value = path;
    select.append(option);
  });
  select.disabled = select.options.length === 0;
  if (Array.from(select.options).some((option) => option.value === 'src/App.tsx')) select.value = 'src/App.tsx';
  if (select.options.length) void loadCode(select.value);
  else select.append(el('option', '', '本次任务没有返回项目文件'));
  renderReport(result);
}

function renderFailure(message) {
  $('#empty-title').textContent = '这次生成没有完成';
  $('#empty-description').textContent = message || '请查看执行记录，检查输入后重新生成。';
  $('#preview-name').textContent = '执行失败';
  $('#file-select').replaceChildren(el('option', '', '任务失败，暂无项目文件'));
  setFormError(message || '生成失败，请检查输入后重试。');
}

async function pollRun(id, generation) {
  if (generation !== state.pollGeneration) return;
  try {
    const run = await request(`/api/runs/${encodeURIComponent(id)}`);
    if (generation !== state.pollGeneration) return;
    state.run = run;
    renderEvents(run.events);
    setRunStatus(run.status);
    if (run.status === 'completed' || run.status === 'failed') {
      state.busy = false;
      state.pollTimer = null;
      if (run.status === 'completed') renderCompleted(run);
      else renderFailure(run.error || '生成失败，请查看执行记录后重试。');
      updateControls();
      return;
    }
    state.pollTimer = setTimeout(() => void pollRun(id, generation), 800);
  } catch (error) {
    if (generation !== state.pollGeneration) return;
    state.busy = false;
    state.run = { ...state.run, status: 'failed' };
    setRunStatus('failed');
    renderFailure(`无法获取任务状态：${error.message}。任务可能仍在服务端运行，可恢复连接后重新生成。`);
    updateControls();
  }
}

async function startRun(event) {
  event.preventDefault();
  if (state.busy) return;
  let body;
  try { body = collectInput(); } catch (error) { setFormError(error.message); return; }
  clearTimeout(state.pollTimer);
  const generation = ++state.pollGeneration;
  state.busy = true;
  state.run = null;
  setFormError('');
  resetResult();
  setRunStatus('queued');
  updateControls();
  try {
    const run = await request('/api/runs', { method: 'POST', body: JSON.stringify(body) });
    if (generation !== state.pollGeneration) return;
    if (!run.id) throw new Error('服务未返回有效的任务 ID');
    state.run = run;
    $('#run-id-label').textContent = `任务 ${run.id}`;
    void pollRun(run.id, generation);
  } catch (error) {
    if (generation !== state.pollGeneration) return;
    state.busy = false;
    state.run = { status: 'failed' };
    setRunStatus('failed');
    renderFailure(error.message);
    $('#activity-empty').textContent = '任务未能创建，请检查上方错误信息。';
    updateControls();
  }
}

async function copyCode() {
  if (!state.code) return;
  try {
    await navigator.clipboard.writeText(state.code);
    $('#copy-label').textContent = '已复制';
    notify('代码已复制到剪贴板');
    setTimeout(() => { $('#copy-label').textContent = '复制代码'; }, 2400);
  } catch { notify('浏览器未允许复制，请在代码区手动选择并复制。'); }
}

async function initialize() {
  const results = await Promise.allSettled([request('/api/health'), request('/api/sample')]);
  if (results[0].status === 'fulfilled') {
    state.health = results[0].value;
    $('#connection-status').className = 'connection ready';
    $('#connection-label').textContent = '本地服务已连接';
  } else {
    $('#connection-status').className = 'connection failed';
    $('#connection-label').textContent = '服务未连接';
    setFormError('无法连接本地服务。请确认服务已启动，然后刷新页面。');
  }
  if (results[1].status === 'fulfilled') { state.sample = results[1].value; inspectSample(state.sample); }
  else { $('#sample-detail').textContent = '暂时无法读取样例，可尝试重新生成'; }
  updateControls();
}

$$('[data-source]').forEach((button) => button.addEventListener('click', () => selectSource(button.dataset.source)));
$$('[data-view]').forEach((button) => button.addEventListener('click', () => selectView(button.dataset.view)));
$$('[data-mode]').forEach((button) => button.addEventListener('click', () => { state.mode = button.dataset.mode; updateControls(); }));
addTabKeyboard('[data-source]', 'source', selectSource);
addTabKeyboard('[data-view]', 'view', selectView);
$$('[data-viewport]').forEach((button) => button.addEventListener('click', () => {
  const mobile = button.dataset.viewport === 'mobile';
  $$('[data-viewport]').forEach((option) => { const selected = option === button; option.classList.toggle('selected', selected); option.setAttribute('aria-pressed', String(selected)); });
  $('#preview-shell').classList.toggle('mobile', mobile);
  $('#viewport-label').textContent = mobile ? '手机画布 · 390px' : '自适应画布';
}));
$('#run-form').addEventListener('submit', startRun);
$('#json-file').addEventListener('change', (event) => void loadFile(event.target.files?.[0]));
$('#file-drop').addEventListener('dragover', (event) => { event.preventDefault(); $('#file-drop').classList.add('drag-over'); });
$('#file-drop').addEventListener('dragleave', () => $('#file-drop').classList.remove('drag-over'));
$('#file-drop').addEventListener('drop', (event) => { event.preventDefault(); $('#file-drop').classList.remove('drag-over'); void loadFile(event.dataTransfer.files?.[0]); });
$('#file-select').addEventListener('change', (event) => void loadCode(event.target.value));
$('#copy-button').addEventListener('click', () => void copyCode());
$('#download-button').addEventListener('click', (event) => { if ($('#download-button').getAttribute('aria-disabled') === 'true') event.preventDefault(); });
window.addEventListener('beforeunload', () => { clearTimeout(state.pollTimer); state.pollGeneration += 1; });
void initialize();
