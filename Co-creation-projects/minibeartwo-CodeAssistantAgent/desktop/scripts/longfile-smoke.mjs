import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { _electron as electron } from 'playwright';

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const artifacts = await mkdtemp(path.join(os.tmpdir(), 'code-assistant-longfile-ui-'));
const project = path.join(artifacts, 'project');
await mkdir(project);
const sourcePath = path.join(project, 'large.py');
const original = '"""Preserve this module documentation."""\n\n' + Array.from({ length: 15 }, (_, i) =>
  `def calculate_${i}(value, *, scale=1):\n    subtotal = value * scale\n` +
  Array.from({ length: 40 }, (_, j) => `    # Source context ${i}/${j}: ${'padding '.repeat(10)}\n`).join('') +
  '    return subtotal\n\n').join('');
assert.ok(original.length > 51000);
await writeFile(sourcePath, original);
const units = [], rendererErrors = [];
let calls = 0, providerFailure, app, page;
const provider = createServer(async (request, response) => {
  try {
    const pieces = [];
    for await (const piece of request) pieces.push(piece);
    const input = JSON.parse(Buffer.concat(pieces).toString());
    calls++;
    const context = JSON.parse(input.messages[1].content);
    let action;
    if (context.client_mode === 'annotation_unit') {
      const unit = context.annotation_unit;
      assert.equal(await readFile(sourcePath, 'utf8'), original, 'no partial draft may write the source');
      assert.deepEqual(input.tools[0].function.parameters.properties.action.enum, ['annotate_unit']);
      assert.equal(input.messages.length, 2, 'a unit request does not carry old whole-file pages');
      units.push(unit);
      const documentation = { purpose: `说明 ${unit.name} 的比例计算用途。`,
        inputs: unit.parameters.map((name) => `${name.replace(/^\*+/, '')}：调用方传入的参数`).join('；') || '无。',
        outputs: '返回原实现计算的数值，不改变代码行为。' };
      if (unit.kind === 'header') Object.assign(documentation, { input_files: '无。', output_files: '无。' });
      action = { action: 'annotate_unit', args: { path: unit.path, base_hash: unit.base_hash,
        target_id: unit.target_id, documentation }, summary: `描述 ${unit.name}` };
    } else {
      assert.equal(units.length, 16);
      assert.notEqual(await readFile(sourcePath, 'utf8'), original);
      action = { action: 'final', args: { message: '所有函数草稿已汇总，完整文件校验通过。' }, summary: '结束注释' };
    }
    const argumentsText = JSON.stringify(action);
    response.writeHead(200, { 'Content-Type': 'text/event-stream', Connection: 'close' });
    response.write(`data: ${JSON.stringify({ choices: [{ index: 0, delta: { tool_calls: [{ index: 0,
      id: `longfile-call-${calls}`, type: 'function', function: { name: 'submit_action', arguments: argumentsText } }] },
      finish_reason: null }] })}\n\n`);
    response.end('data: {"choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}\n\ndata: [DONE]\n\n');
  } catch (error) {
    providerFailure = error;
    if (!response.headersSent) response.writeHead(500);
    response.end('Local test assertion failed.');
  }
});
await new Promise((resolve) => provider.listen(0, '127.0.0.1', resolve));
const baseUrl = `http://127.0.0.1:${provider.address().port}/v1`;
const env = { ...process.env, CODE_ASSISTANT_HIDDEN: '1', CODE_ASSISTANT_ALLOW_MULTIPLE: '1',
  CODE_ASSISTANT_DISABLE_KEYRING: '1', CODE_ASSISTANT_DATA_DIR: path.join(artifacts, 'service'),
  CODE_ASSISTANT_USER_DATA_DIR: path.join(artifacts, 'profile'), LLM_API_KEY: '', LLM_MODEL_ID: '', LLM_BASE_URL: '' };
for (const name of ['ELECTRON_RUN_AS_NODE', 'CODE_ASSISTANT_DEV_URL', 'PYTHONHOME', 'PYTHONPATH']) delete env[name];
try {
  app = await electron.launch({ args: [desktop], cwd: desktop, env, timeout: 60000 });
  await app.evaluate(({ app, BrowserWindow, dialog }, directory) => {
    const isolate = (window) => { window.setOpacity(0); window.setIgnoreMouseEvents(true); };
    app.on('browser-window-created', (_event, window) => isolate(window));
    BrowserWindow.getAllWindows().forEach(isolate);
    dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [directory] });
  }, project);
  await app.firstWindow({ timeout: 60000 });
  const deadline = Date.now() + 60000;
  while (!page && Date.now() < deadline) {
    for (const candidate of app.windows()) {
      if (await candidate.title() === 'CodeAssistantAgent · 代码助手') { page = candidate; break; }
    }
    if (!page) await new Promise((resolve) => setTimeout(resolve, 50));
  }
  assert.ok(page);
  page.setDefaultTimeout(20000);
  page.on('pageerror', (error) => rendererErrors.push(error.message));
  await page.waitForFunction(() => !!window.codeAssistant);
  await page.evaluate((url) => window.codeAssistant.request('PUT', '/api/settings', {
    base_url: url, model: 'local-longfile-test', max_steps: 50, api_key: '' }), baseUrl);
  await page.reload();
  await page.locator('.project-drop:not(:disabled)').click();
  await page.locator('.project-drop.is-ready').waitFor();
  await page.locator('.home-action-comment').click();
  await page.getByRole('button', { name: '开始注释', exact: true }).click();
  await page.locator('.task-status.completed').waitFor({ timeout: 90000 });
  if (providerFailure) throw providerFailure;
  const id = await page.getByRole('button', { name: '历史任务', exact: true }).getAttribute('data-task-id');
  const task = await page.evaluate((id) => window.codeAssistant.request('GET', `/api/tasks/${id}`), id);
  assert.equal(task.steps, 17);
  assert.equal(calls, 17);
  assert.equal(task.patches.length, 1);
  assert.equal(task.patches[0].status, 'applied');
  assert.equal(new Set(units.map((unit) => unit.target_id)).size, 16);
  assert.equal(units.filter((unit) => unit.kind === 'function').length, 15);
  assert.ok(units.every((unit) => JSON.stringify(unit).length <= 22000));
  assert.equal(await page.locator('.feature-activity li').filter({ hasText: '已保存 large.py' }).count(), 16);
  assert.equal(await page.locator('.feature-activity li').filter({ hasText: '检测到重复动作' }).count(), 0);
  await page.locator('.patch-review .patch-status.applied').waitFor();
  await page.locator('.feature-task').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(artifacts, 'completed.png') });
  const after = await readFile(sourcePath, 'utf8');
  assert.notEqual(after, original);
  assert.match(after, /# 代码用途/);
  assert.equal((after.match(/# 函数用途/g) || []).length, 15);
  await page.getByRole('button', { name: '撤销此补丁', exact: true }).click();
  await page.locator('.patch-status.reverted').waitFor();
  assert.equal(await readFile(sourcePath, 'utf8'), original);
  assert.deepEqual(rendererErrors, []);
  const result = { status: 'passed', sourceChars: original.length, units: units.length, calls,
    steps: task.steps, patches: 1, noPartialWrites: true, undoRestoredOriginal: true, rendererErrors };
  await writeFile(path.join(artifacts, 'result.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ ...result, artifacts }));
} catch (error) {
  if (page) {
    await page.screenshot({ path: path.join(artifacts, 'failure.png') }).catch(() => {});
    await writeFile(path.join(artifacts, 'failure.txt'), await page.locator('body').innerText()).catch(() => {});
  }
  console.error(`Long-file desktop check failed. Artifacts: ${artifacts}`);
  throw providerFailure || error;
} finally {
  if (app) await app.close();
  provider.closeAllConnections();
  await new Promise((resolve) => provider.close(resolve));
}
