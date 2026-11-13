/** Full Electron -> IPC -> Python -> HelloAgents -> local SSE provider smoke test. */
import { _electron as electron } from 'playwright';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { access, cp, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chooseCustomProvider } from './provider-settings-helpers.mjs';

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(desktop, '..');
const artifacts = path.join(root, '.test-artifacts', `desktop-${Date.now()}`);
const workspace = path.join(artifacts, 'calculator-demo');
await mkdir(artifacts, { recursive: true });
await cp(path.join(root, 'examples/buggy-calculator'), workspace, { recursive: true });
const original = (await readFile(path.join(workspace, 'calculator.py'), 'utf8')).replace(
  'return left - right',
  'return left + right',
);
await writeFile(path.join(workspace, 'calculator.py'), original);
await writeFile(path.join(workspace, 'notes.md'), '# 项目备注\n');
const originalTests = await readFile(path.join(workspace, 'test_calculator.py'), 'utf8');
const originalConfig = await readFile(path.join(workspace, 'pytest.ini'), 'utf8');
const originalEntries = await readdir(workspace);
const annotationSkill = (
  await readFile(path.join(root, 'skills/annotate-project-zh/SKILL.md'), 'utf8')
).replace(/\r\n/g, '\n');
const updated =
  [
    '# 代码用途：提供两个整数相加的示例函数，供计算调用和测试验证。',
    '# 输入文件：无。',
    '# 输入说明：调用方通过内存传入待相加的两个整数。',
    '# 输出文件：无。',
    '# 输出说明：返回两个整数的和，不写入文件。',
    '',
  ].join('\n') +
  original.replace(
    'def add(',
    [
      '# 函数用途：计算两个整数的和，保留原有加法逻辑。',
      '# 输入说明：left：左侧加数；right：右侧加数，均为调用方传入的整数。',
      '# 输出说明：返回 left 与 right 相加得到的整数。',
      'def add(',
    ].join('\n'),
  );
const updatedTests =
  [
    '# 代码用途：使用 pytest（自动发现并运行断言的 Python 测试框架）检查加法函数的正数和负数输入。',
    '# 输入文件：无。',
    '# 输入说明：使用代码中的整数样例调用内存中的 add 函数。',
    '# 输出文件：无。',
    '# 输出说明：断言不符合预期时抛出异常，供外部测试框架报告结果。',
    '',
  ].join('\n') +
  originalTests
    .replace(
      'def test_add_positive(',
      [
        '# 函数用途：检查两个正整数的加法结果。',
        '# 输入说明：无。',
        '# 输出说明：返回 None；结果不等于 5 时触发断言异常。',
        'def test_add_positive(',
      ].join('\n'),
    )
    .replace(
      'def test_add_negative(',
      [
        '# 函数用途：检查两个负整数的加法结果。',
        '# 输入说明：无。',
        '# 输出说明：返回 None；结果不等于 -5 时触发断言异常。',
        'def test_add_negative(',
      ].join('\n'),
    );
const updatedConfig =
  [
    '# 代码用途：限定 pytest（自动发现并运行断言的 Python 测试框架）的样例测试搜索范围。',
    '# 输入文件：运行时确定（由测试启动目录决定当前目录中的 test_calculator.py）。',
    '# 输入说明：testpaths 指定搜索当前目录，python_files 指定测试文件名。',
    '# 输出文件：无。',
    '# 输出说明：为外部测试框架提供文件发现规则，本配置不执行测试或写入文件。',
    '',
  ].join('\n') + originalConfig;
const documentation =
  '# 计算器项目说明\n\n本项目提供整数加法函数 `add(left, right)`。\n\n' +
  '## 项目概述\n用于演示整数加法及 pytest 断言。\n\n' +
  '## 主要功能\n计算两个整数的和，包含正数与负数测试。\n\n' +
  '## 技术栈与架构\nPython 源码与 pytest 测试；调用方调用 calculator.py 的 add。\n\n' +
  '![系统架构](docs/diagrams/architecture.png)\n\n' +
  '## 快速开始\n先按原项目依赖清单安装环境。\n\n' +
  '## 配置说明\npytest.ini 指定测试发现范围；本示例无需额外密钥。\n\n' +
  '## 使用示例\n调用 `add(2, 3)` 返回 `5`。\n\n' +
  '## 项目结构\ncalculator.py 实现函数，test_calculator.py 保存测试，pytest.ini 保存测试配置。\n\n' +
  '## 验证方式\n测试命令：`python -m pytest -q`；本次解析未执行测试。\n\n' +
  '## 当前边界\n只有整数加法示例，未实现外部服务。\n\n' +
  '## 作者与许可证\n以目标项目已有文件为准，未确认的信息不作推断。\n\n' +
  '[流程图](docs/diagrams/workflow.png) · [时序图](docs/diagrams/sequence.png) · [图示说明](docs/diagrams/README.md)\n';
const documentationPaths = [
  '项目说明.md',
  'docs/diagrams/README.md',
  'docs/diagrams/architecture.png',
  'docs/diagrams/workflow.png',
  'docs/diagrams/sequence.png',
];
const diagramPackage = {
  architecture: {
    title: '计算器系统架构',
    description: '调用方通过 calculator.py 调用整数加法函数。',
    nodes: [
      { id: 'caller', label: '调用方' },
      { id: 'add', label: 'calculator.py · add' },
      { id: 'result', label: '整数结果' },
    ],
    edges: [
      { from: 'caller', to: 'add', label: 'left / right' },
      { from: 'add', to: 'result', label: '相加' },
    ],
  },
  workflow: {
    title: '加法执行流程',
    description: '传入两个数，计算总和并返回，不写入文件。',
    nodes: [
      { id: 'input', label: '接收 left 与 right' },
      { id: 'sum', label: '计算 left + right' },
      { id: 'return', label: '返回总和' },
    ],
    edges: [
      { from: 'input', to: 'sum' },
      { from: 'sum', to: 'return' },
    ],
  },
  sequence: {
    title: '加法调用时序',
    description: '调用方传入参数并读取同步返回值。',
    participants: [
      { id: 'caller', label: '调用方' },
      { id: 'calculator', label: 'calculator.add' },
    ],
    messages: [
      { from: 'caller', to: 'calculator', label: 'add(left, right)' },
      { from: 'calculator', to: 'caller', label: '返回 left + right', dashed: true },
    ],
  },
};
const resumePatchSummary = '续跑验证：已为加法函数添加中文注释，保留这条失败前进度。';
const resumeReadSummary = '续跑验证：重新读取已应用的源码，确认无需重复写入补丁。';
const loopReadSummary = '防循环验证：重复读取已经完成注释的加法函数。';
const loopResumeSummary = '防循环验证：继续原任务，读取尚未处理的测试文件。';
let modelCalls = 0;
let discoveryMode = 'ok';
const discoveryRequests = [];
const requests = [];
const provider = createServer(async (request, response) => {
  try {
    if (request.method === 'GET' && request.url.endsWith('/models')) {
      const mode = discoveryMode;
      discoveryRequests.push({ url: request.url, authorization: request.headers.authorization });
      if (mode === 'delayed') await new Promise((resolve) => setTimeout(resolve, 400));
      response.writeHead(mode === 'unauthorized' ? 401 : mode === 'unsupported' ? 404 : 200, {
        'Content-Type': 'application/json',
      });
      response.end(
        JSON.stringify(
          mode === 'unauthorized'
            ? { error: 'model-list-test-key' }
            : {
                data:
                  mode === 'empty'
                    ? []
                    : (mode === 'delayed'
                        ? ['stale-model']
                        : ['local-protocol-test', 'another-model', 'local-protocol-test']
                      ).map((id) => ({ id })),
              },
        ),
      );
      return;
    }
    let body = '';
    for await (const chunk of request) body += chunk;
    const input = JSON.parse(body);
    assert.equal(
      input.parallel_tool_calls,
      false,
      'the client requests one native tool call per round',
    );
    requests.push(input);
    const actions = [
      {
        action: 'inventory',
        args: { offset: 0 },
        summary: '建立完整项目文件清单，保留测试与配置范围。',
      },
      { action: 'read', args: { path: 'calculator.py' }, summary: '读取加法函数与文件版本。' },
      {
        action: 'read',
        args: { path: 'test_calculator.py' },
        summary: '读取全部测试函数，建立函数清单。',
      },
      {
        action: 'read',
        args: { path: 'pytest.ini' },
        summary: '读取测试发现配置，确认参数与实际用途。',
      },
      {
        action: 'propose_patch',
        args: {
          changes: [
            {
              path: 'calculator.py',
              base_hash: createHash('sha256').update(original).digest('hex'),
              content: updated,
            },
            {
              path: 'test_calculator.py',
              base_hash: createHash('sha256').update(originalTests).digest('hex'),
              content: updatedTests,
            },
            {
              path: 'pytest.ini',
              base_hash: createHash('sha256').update(originalConfig).digest('hex'),
              content: updatedConfig,
            },
          ],
        },
        summary: '为完整示例源码、测试与配置添加中文说明，保留原有逻辑，准备审阅。',
      },
      {
        action: 'final',
        args: {
          message:
            '已处理 3 个文件、3 个函数，保留原有逻辑并通过 Python 静态注释检查；跳过 Markdown 文档，未执行项目或测试。',
        },
        summary: '整理文件与函数覆盖数量、跳过项及静态检查结果。',
      },
      {
        action: 'read',
        args: { path: 'calculator.py' },
        summary: '读取项目入口，依据实际代码整理说明。',
      },
      {
        action: 'propose_documentation',
        args: {
          overview: documentation,
          diagrams: { ...diagramPackage, base_hashes: { '项目说明.md': 'forged-legacy-value' } },
        },
        summary: '生成项目说明和三张 PNG 设计图，校验后自动应用。',
      },
      {
        action: 'final',
        args: {
          message: '已生成项目说明.md 和 docs/diagrams/，说明项目用途、核心函数与三张设计图。',
        },
        summary: '整理项目解析结果。',
      },
      {
        action: 'read',
        args: { path: 'calculator.py' },
        summary: '续跑验证：读取撤销后的原始加法函数。',
      },
      {
        action: 'propose_patch',
        args: {
          changes: [
            {
              path: 'calculator.py',
              base_hash: createHash('sha256').update(original).digest('hex'),
              content: updated,
            },
          ],
        },
        summary: resumePatchSummary,
      },
      {
        status: 402,
        error: {
          message: 'Desktop smoke quota exhausted; replenish before resuming.',
          type: 'insufficient_quota',
        },
      },
      { action: 'read', args: { path: 'calculator.py', force: true }, summary: resumeReadSummary },
      {
        action: 'final',
        args: {
          message: '继续执行后已重新读取并确认 calculator.py 的中文注释，沿用原有已应用补丁。',
        },
        summary: '续跑验证：保留历史并完成剩余核实。',
      },
      {
        action: 'read',
        args: { path: 'calculator.py' },
        summary: '防循环验证：识别已经完整注释的文件。',
      },
      {
        action: 'read',
        args: { path: 99 },
        summary: '防循环验证：检查非法读取参数的真实错误反馈。',
      },
      ...Array.from({ length: 6 }, () => ({
        action: 'read',
        args: { path: 'calculator.py' },
        summary: loopReadSummary,
      })),
      { action: 'read', args: { path: 'test_calculator.py' }, summary: loopResumeSummary },
      {
        action: 'final',
        args: { message: '已停止重复扫描，并读取未完成的测试文件；其余注释留待后续处理。' },
        summary: '防循环验证：如实报告仍未覆盖的范围。',
      },
    ];
    const action = actions[modelCalls++] || actions.at(-1);
    const toolName = input.tools[0].function.name;
    const expectedToolName = 'submit_action';
    assert.equal(toolName, expectedToolName);
    assert.equal(input.tool_choice.function.name, expectedToolName);
    if (modelCalls === 8) {
      assert.deepEqual(input.tools[0].function.parameters.properties.args.required, [
        'overview',
        'diagrams',
      ]);
      assert.ok(!('baselines' in JSON.parse(input.messages[1].content).analysis_output));
      assert.ok(
        !input.tools[0].function.parameters.properties.args.properties.path,
        'the draft phase no longer exposes reads',
      );
      assert.deepEqual(input.tools[0].function.parameters.properties.action.enum, [
        'propose_documentation',
      ]);
    }
    if (action.status) {
      response.writeHead(action.status, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ error: action.error }));
      return;
    }
    const outputs = [
      {
        text: JSON.stringify(action),
        id: `smoke-call-${modelCalls}`,
      },
    ];
    if (modelCalls === 7) {
      outputs.push({
        text: JSON.stringify({
          action: 'read',
          args: { path: 'calculator.py' },
          summary: '重复读取应只返回原文件摘要。',
        }),
        id: `smoke-call-${modelCalls}-extra`,
      });
      outputs.push({
        text: JSON.stringify({
          action: 'read',
          args: { path: 'README.md' },
          summary: '明确读取项目说明。',
        }),
        id: `smoke-call-${modelCalls}-readme`,
      });
      outputs.push({
        text: JSON.stringify({
          action: 'read',
          args: { path: 'test_calculator.py' },
          summary: '读取测试依据。',
        }),
        id: `smoke-call-${modelCalls}-tests`,
      });
    }
    response.writeHead(200, { 'Content-Type': 'text/event-stream', Connection: 'close' });
    for (
      let offset = 0;
      offset < Math.max(...outputs.map((output) => output.text.length));
      offset += 50
    ) {
      const parts = [];
      for (const [index, output] of outputs.entries()) {
        if (offset >= output.text.length) continue;
        const part = { index, function: { arguments: output.text.slice(offset, offset + 50) } };
        if (offset === 0 || modelCalls === 8) {
          part.id = output.id;
          part.type = 'function';
          part.function.name = toolName;
        }
        parts.push(part);
      }
      response.write(
        `data: ${JSON.stringify({ id: 'local-smoke', object: 'chat.completion.chunk', created: 0, model: input.model, choices: [{ index: 0, delta: { content: '<result>ignored simulated observation</result>', tool_calls: parts }, finish_reason: null }] })}\n\n`,
      );
    }
    response.write(
      `data: ${JSON.stringify({ choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }] })}\n\n`,
    );
    response.end('data: [DONE]\n\n');
  } catch (error) {
    response.writeHead(500);
    response.end(String(error));
  }
});
await new Promise((resolve) => provider.listen(0, '127.0.0.1', resolve));
const baseUrl = `http://127.0.0.1:${provider.address().port}/v1`;
const env = {
  ...process.env,
  CODE_ASSISTANT_HIDDEN: '1',
  CODE_ASSISTANT_ALLOW_MULTIPLE: '1',
  CODE_ASSISTANT_DISABLE_KEYRING: '1',
  CODE_ASSISTANT_DATA_DIR: path.join(artifacts, 'service'),
  CODE_ASSISTANT_USER_DATA_DIR: path.join(artifacts, 'profile'),
  LLM_API_KEY: '',
  LLM_MODEL_ID: '',
  LLM_BASE_URL: '',
};
delete env.ELECTRON_RUN_AS_NODE;
delete env.CODE_ASSISTANT_DEV_URL;
delete env.PYTHONHOME;
delete env.PYTHONPATH;
let app;
const errors = [];
const homeChecks = [];
async function launch() {
  const instance = await electron.launch({ args: [desktop], cwd: desktop, env, timeout: 60000 });
  app = instance;
  await instance.evaluate(({ app, BrowserWindow }) => {
    const isolateWindow = (window) => {
      window.setOpacity(0);
      window.setIgnoreMouseEvents(true);
    };
    app.on('browser-window-created', (_event, window) => isolateWindow(window));
    for (const window of BrowserWindow.getAllWindows()) isolateWindow(window);
  });
  await instance.firstWindow({ timeout: 60000 });
  let page;
  const deadline = Date.now() + 60000;
  while (!page && Date.now() < deadline) {
    for (const candidate of instance.windows()) {
      if ((await candidate.title()) === 'CodeAssistantAgent · 代码助手') {
        page = candidate;
        break;
      }
    }
    if (!page) await new Promise((resolve) => setTimeout(resolve, 40));
  }
  assert.ok(page, 'the native client renderer is available independently of launcher load order');
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (entry) => {
    if (entry.type() === 'error') errors.push(entry.text());
  });
  page.setDefaultTimeout(20000);
  await page.waitForFunction(() => !!window.codeAssistant);
  await page.locator('.project-drop:not(:disabled)').waitFor();
  return { instance, page };
}

async function dropNativePath(page, nativePath) {
  await page.evaluate(() => {
    window.__dropEvents = [];
    if (window.__dropObserved) return;
    window.__dropObserved = true;
    for (const type of ['dragenter', 'dragover', 'drop'])
      document.addEventListener(
        type,
        (event) => {
          window.__dropEvents.push({
            type,
            target: event.target.tagName,
            files: event.dataTransfer.files.length,
            disabled: document.querySelector('.project-drop').disabled,
          });
        },
        true,
      );
  });
  const target = await page.locator('.project-drop').boundingBox();
  assert.ok(target, 'the project drop target is visible');
  const client = await page.context().newCDPSession(page);
  try {
    const data = { items: [], files: [nativePath], dragOperationsMask: 1 };
    for (const type of ['dragEnter', 'dragOver', 'drop']) {
      await client.send('Input.dispatchDragEvent', {
        type,
        x: target.x + target.width / 2,
        y: target.y + target.height / 2,
        data,
      });
    }
  } finally {
    await client.detach();
  }
  await page.waitForFunction(() =>
    window.__dropEvents.some((event) => event.type === 'drop' && event.files > 0),
  );
  await page.locator('.project-drop:not(:disabled)').waitFor();
  await writeFile(
    path.join(artifacts, `drop-${Date.now()}.json`),
    JSON.stringify(
      await page.evaluate(() => ({
        events: window.__dropEvents,
        text: document.querySelector('.project-drop').innerText,
      })),
      null,
      2,
    ),
  );
}

async function historyTaskIds(page) {
  const trigger = page.getByRole('button', { name: '历史任务', exact: true });
  await trigger.waitFor();
  if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
  const ids = await page
    .locator('.task-history-row')
    .evaluateAll((rows) => rows.map((row) => row.dataset.taskId));
  await trigger.press('Escape');
  return ids;
}

async function selectHistoryTask(page, id) {
  const trigger = page.getByRole('button', { name: '历史任务', exact: true });
  if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
  await page.locator(`.task-history-row[data-task-id="${id}"] .task-history-select`).click();
}

async function waitForNativeState(application, property, expected) {
  const deadline = Date.now() + 10000;
  let state;
  while (Date.now() < deadline) {
    state = await application.evaluate(({ BrowserWindow }) => {
      const window = BrowserWindow.getAllWindows().find(
        (entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手',
      );
      return { maximized: window.isMaximized(), minimized: window.isMinimized() };
    });
    if (state[property] === expected) return;
    await new Promise((resolve) => setTimeout(resolve, 40));
  }
  assert.equal(state[property], expected, `native ${property} changes after titlebar action`);
}

async function nativeScreenshot(application, name) {
  const image = await application.evaluate(async ({ BrowserWindow }) => {
    const main = BrowserWindow.getAllWindows().find(
      (entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手',
    );
    const capture = await main.webContents.capturePage();
    return { size: capture.getSize(), png: capture.toPNG().toString('base64') };
  });
  await writeFile(path.join(artifacts, name), Buffer.from(image.png, 'base64'));
  return image.size;
}

async function assertNoLegacyInterface(page) {
  assert.equal(
    await page
      .locator('.workspace-layout, .editor-area, .sidebar, .assistant-panel, .monaco-editor')
      .count(),
    0,
    'only the approved blue client and its feature dialogs are rendered',
  );
}

const exists = async (file) =>
  access(file).then(
    () => true,
    () => false,
  );
async function assertDocumentationFiles() {
  const overview = await readFile(path.join(workspace, '项目说明.md'), 'utf8');
  assert.match(overview, /计算器项目说明/);
  assert.match(overview, /add\(left, right\)/);
  assert.match(overview, /docs\/diagrams\/architecture\.png/);
  const diagramsReadme = await readFile(path.join(workspace, 'docs/diagrams/README.md'), 'utf8');
  for (const name of ['architecture', 'workflow', 'sequence']) {
    assert.ok(diagramsReadme.includes(`${name}.png`), 'diagram guide links to every generated PNG');
    const png = await readFile(path.join(workspace, `docs/diagrams/${name}.png`));
    assert.deepEqual(png.subarray(0, 8), Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
  }
}

async function inspectHome(page, application) {
  await assertNoLegacyInterface(page);
  const native = await application.evaluate(({ BrowserWindow, screen }) => {
    const windows = BrowserWindow.getAllWindows();
    const main = windows.find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手');
    const bubble = windows.find(
      (entry) => entry.getTitle() === 'CodeAssistantAgent · 菲比桌面助手',
    );
    return {
      bounds: main.getContentBounds(),
      zoom: main.webContents.getZoomFactor(),
      displayScale: screen.getDisplayMatching(main.getBounds()).scaleFactor,
      bubbleZoom: bubble.webContents.getZoomFactor(),
    };
  });
  // Windows may round both rectangle edges when converting fractional display scales.
  assert.ok(
    Math.abs(native.bounds.width - 650) <= 2,
    'the client opens at the requested width within display rounding',
  );
  assert.ok(
    Math.abs(native.bounds.height - 500) <= 2,
    'the client opens at the requested height within display rounding',
  );
  assert.equal(native.zoom, 0.65625, 'the whole client scales uniformly with its window');
  assert.equal(native.bubbleZoom, 1, 'client scaling does not change the desktop mascot');
  const title = await page.locator('.client-titlebar').innerText();
  assert.match(title, /代码助手/);
  assert.match(title, /CodeAssistantAgent/);
  assert.doesNotMatch(title, /菲比/);
  const layout = await page.evaluate(() => {
    const boxes = ['.project-drop', '.home-action-comment', '.home-action-analysis'].map(
      (selector) => {
        const { x, y, width, height } = document.querySelector(selector).getBoundingClientRect();
        return { x, y, width, height };
      },
    );
    return {
      width: innerWidth,
      height: innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      boxes,
    };
  });
  assert.ok(
    Math.abs(layout.width * native.zoom - native.bounds.width) < 1,
    'the renderer fits the native client width',
  );
  assert.ok(
    Math.abs(layout.height * native.zoom - native.bounds.height) < 1,
    'the renderer fits the native client height',
  );
  assert.ok(
    layout.scrollWidth <= layout.width && layout.scrollHeight <= layout.height,
    'the three home controls fit without scrolling',
  );
  const [drop, comment, analysis] = layout.boxes;
  assert.ok(drop.x + drop.width <= comment.x, 'drop panel is beside the action cards');
  assert.ok(comment.y + comment.height <= analysis.y, 'the action cards are vertically stacked');
  for (const box of layout.boxes) {
    assert.ok(
      box.x >= 0 &&
        box.y >= 0 &&
        box.x + box.width <= layout.width &&
        box.y + box.height <= layout.height,
      'every home control fits inside the window',
    );
  }
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(artifacts, 'home.png') });
  const capture = await nativeScreenshot(application, 'home-native.png');
  assert.ok(
    Math.abs(capture.width - native.bounds.width * native.displayScale) <= 1 &&
      Math.abs(capture.height - native.bounds.height * native.displayScale) <= 1,
    'native capture confirms the requested client size within physical-pixel rounding',
  );
  homeChecks.push('650×500 native client at 65.625% scale; mascot scale unchanged');
  await application.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .setSize(640, 480),
  );
  await page.waitForFunction(
    () => Math.abs(innerWidth * 0.65625 - 640) <= 2 && Math.abs(innerHeight * 0.65625 - 480) <= 2,
  );
  const minimumSize = await application.evaluate(({ BrowserWindow }) => {
    const { width, height } = BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .getContentBounds();
    return { width, height };
  });
  assert.ok(
    Math.abs(minimumSize.width - 640) <= 2 && Math.abs(minimumSize.height - 480) <= 2,
    'the resized native client reaches its supported minimum within display rounding',
  );
  const minimumFits = await page.evaluate(() => {
    const inside = (inner, outer) =>
      inner.left >= outer.left - 1 &&
      inner.top >= outer.top - 1 &&
      inner.right <= outer.right + 1 &&
      inner.bottom <= outer.bottom + 1;
    const viewport = { left: 0, top: 0, right: innerWidth, bottom: innerHeight };
    const controls = [...document.querySelectorAll('.project-drop, .home-action')];
    const texts = [
      ...document.querySelectorAll(
        '.drop-interior > strong, .drop-description, .action-copy strong, .action-copy > span',
      ),
    ];
    return (
      document.documentElement.scrollWidth <= innerWidth &&
      document.documentElement.scrollHeight <= innerHeight &&
      controls.every((element) => inside(element.getBoundingClientRect(), viewport)) &&
      texts.every((element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const card = element.closest('button').getBoundingClientRect();
        return [...range.getClientRects()].every((rect) => inside(rect, card));
      })
    );
  });
  assert.equal(
    minimumFits,
    true,
    'home controls and labels fit at the minimum supported window size',
  );
  await page.screenshot({ path: path.join(artifacts, 'home-min.png') });
  await application.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .setSize(650, 500),
  );
  await page.waitForFunction(
    () => Math.abs(innerWidth * 0.65625 - 650) <= 2 && Math.abs(innerHeight * 0.65625 - 500) <= 2,
  );
  homeChecks.push('minimum 640×480 native home keeps all controls and labels inside the window');
  const syntheticRejected = await page.evaluate(async () => {
    try {
      await window.codeAssistant.openDroppedProject(new File(['x'], 'fake.py'));
      return false;
    } catch {
      return true;
    }
  });
  assert.equal(syntheticRejected, true, 'a synthetic File cannot supply an arbitrary disk path');
  homeChecks.push('filesystem-backed drop bridge rejects synthetic files');
  await application.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .show(),
  );
  const restoreSize = await application.evaluate(({ BrowserWindow }) => {
    const { width, height } = BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .getContentBounds();
    return { width, height };
  });
  await page.getByRole('button', { name: '最大化或还原', exact: true }).click();
  await page.waitForFunction(({ width, height }) => innerWidth > width || innerHeight > height, {
    width: layout.width,
    height: layout.height,
  });
  await waitForNativeState(application, 'maximized', true);
  await page.getByRole('button', { name: '最大化或还原', exact: true }).click();
  await waitForNativeState(application, 'maximized', false);
  // Compare with the pre-maximize size: Windows rounds transparent-window bounds
  // again on restore at fractional display scales.
  await page.waitForFunction(
    ({ width, height }) =>
      Math.abs(innerWidth * 0.65625 - width) <= 2 && Math.abs(innerHeight * 0.65625 - height) <= 2,
    restoreSize,
  );
  await page.getByRole('button', { name: '最小化', exact: true }).click();
  await waitForNativeState(application, 'minimized', true);
  await application.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .restore(),
  );
  await waitForNativeState(application, 'minimized', false);
  homeChecks.push('custom titlebar maximizes, restores, and minimizes the native client');
}

async function inspectImportedProject(page, application) {
  await page.locator('.project-drop.is-ready').waitFor();
  assert.equal(await page.locator('.project-drop [role="status"]').innerText(), '项目已就绪');
  await page.locator('.is-celebrating .project-success-badge').waitFor();
  await page.waitForTimeout(350);
  await nativeScreenshot(application, 'project-import-success.png');
  await page.locator('.home-grid.is-celebrating').waitFor({ state: 'detached' });
  const animations = await page
    .locator('.project-drop')
    .evaluate(
      (element) =>
        element
          .getAnimations({ subtree: true })
          .filter((animation) => animation.playState === 'running').length,
    );
  assert.equal(animations, 0, 'the success animation settles rather than looping');
  for (const [width, height] of [
    [650, 500],
    [640, 480],
  ]) {
    await application.evaluate(
      ({ BrowserWindow }, size) =>
        BrowserWindow.getAllWindows()
          .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
          .setSize(size.width, size.height),
      { width, height },
    );
    await page.waitForFunction(
      ({ width, height }) =>
        Math.abs(innerWidth * 0.65625 - width) <= 2 &&
        Math.abs(innerHeight * 0.65625 - height) <= 2,
      { width, height },
    );
    const fits = await page.locator('.project-drop').evaluate((card) => {
      const bounds = card.getBoundingClientRect();
      return (
        [
          ...card.querySelectorAll(
            '.project-ready-art, strong, .selected-project, .drop-description, .project-ready-hint, .project-replace-hint',
          ),
        ].every((element) => {
          const box = element.getBoundingClientRect();
          return (
            box.left >= bounds.left &&
            box.right <= bounds.right &&
            box.top >= bounds.top &&
            box.bottom <= bounds.bottom
          );
        }) &&
        document.documentElement.scrollWidth <= innerWidth &&
        document.documentElement.scrollHeight <= innerHeight
      );
    });
    assert.ok(fits, `success illustration and labels fit at ${width}×${height}`);
    await nativeScreenshot(application, `project-ready-${width}.png`);
  }
  await application.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()
      .find((entry) => entry.getTitle() === 'CodeAssistantAgent · 代码助手')
      .setSize(650, 500),
  );
  homeChecks.push(
    'project import changes illustration, success badge, headline and name; finite motion fits normal and minimum client sizes',
  );

  await application.evaluate(({ dialog }) => {
    dialog.showOpenDialog = async () => ({ canceled: true, filePaths: [] });
  });
  await page.getByRole('button', { name: '导入项目', exact: true }).click();
  await page.locator('.project-drop.is-ready').waitFor();
  assert.equal(
    await page.locator('.home-grid.is-celebrating').count(),
    0,
    'cancelling selection does not replay success',
  );
  await application.evaluate(
    ({ dialog }, missing) => {
      dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [missing] });
    },
    path.join(artifacts, 'missing-project'),
  );
  await page.getByRole('button', { name: '导入项目', exact: true }).click();
  await page.locator('.error-banner').waitFor();
  await page.locator('.project-drop.is-ready').waitFor();
  assert.match(await page.locator('.selected-project').innerText(), /calculator-demo/);
  assert.equal(
    await page.locator('.home-grid.is-celebrating').count(),
    0,
    'failed import preserves the previous project without a new success pulse',
  );
  await page.getByRole('button', { name: '关闭错误提示', exact: true }).click();
  homeChecks.push(
    'cancelled or failed replacement preserves the selected project without claiming new import success',
  );

  await page.emulateMedia({ reducedMotion: 'reduce' });
  await dropNativePath(page, workspace);
  await page.locator('.project-drop.is-ready').waitFor();
  await page.waitForFunction(() =>
    document
      .querySelector('.home-grid')
      .getAnimations({ subtree: true })
      .every((animation) => animation.playState !== 'running'),
  );
  const reducedAnimations = await page
    .locator('.home-grid')
    .evaluate(
      (element) =>
        element
          .getAnimations({ subtree: true })
          .filter((animation) => animation.playState === 'running').length,
    );
  assert.equal(reducedAnimations, 0, 'reduced motion keeps the success state static');
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.locator('.home-grid.is-celebrating').waitFor({ state: 'detached' });
  await dropNativePath(page, workspace);
  await page.locator('.is-celebrating .project-success-badge').waitFor();
  homeChecks.push(
    'reimporting the same folder replays success; reduced motion retains clear static confirmation',
  );
}

async function inspectProviderSelection(page, application) {
  const before = await page.evaluate(async () => (await window.codeAssistant.bootstrap()).settings);
  const provider = page.getByRole('combobox', { name: 'API 服务商', exact: true });
  await provider.selectOption('deepseek');
  assert.equal(
    await page.locator('.provider-address > span').innerText(),
    'https://api.deepseek.com',
  );
  await page.locator('input[name="model"]').fill('deepseek-draft-model');
  await page.locator('input[name="api_key"]').fill('deepseek-draft-key');
  await provider.selectOption('kimi');
  assert.equal(
    await page.locator('.provider-address > span').innerText(),
    'https://api.moonshot.cn/v1',
  );
  assert.equal(await page.locator('input[name="model"]').inputValue(), '');
  assert.equal(await page.locator('input[name="api_key"]').inputValue(), '');
  await page.locator('input[name="model"]').fill('kimi-draft-model');
  await provider.selectOption('custom');
  const popup = page.getByRole('dialog', { name: '自定义服务商', exact: true });
  await popup.waitFor();
  await page.waitForFunction(() => document.activeElement.id === 'custom-api-address');
  await popup.locator('input[name="base_url"]').fill('ftp://invalid.example/v1');
  await popup.getByRole('button', { name: '使用此地址', exact: true }).click();
  await popup.getByRole('alert').filter({ hasText: 'HTTP(S)' }).waitFor();
  await page.keyboard.press('Escape');
  await popup.waitFor({ state: 'hidden' });
  assert.equal(await page.getByRole('dialog', { name: '模型设置', exact: true }).count(), 1);
  assert.equal(
    await provider.inputValue(),
    'kimi',
    'cancelling custom input preserves the previous provider',
  );
  assert.equal(await page.locator('input[name="model"]').inputValue(), 'kimi-draft-model');
  await chooseCustomProvider(page, '  ' + baseUrl + '/draft/  ');
  assert.equal(await provider.inputValue(), 'custom');
  assert.equal(await page.locator('.provider-address > span').innerText(), baseUrl + '/draft');
  await page.getByRole('button', { name: '编辑地址', exact: true }).click();
  await popup.waitFor();
  assert.equal(await popup.locator('input[name="base_url"]').inputValue(), baseUrl + '/draft');
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await nativeScreenshot(application, 'custom-provider-native.png');
  await popup.locator('input[name="base_url"]').fill(baseUrl + '/not-confirmed');
  await popup.getByRole('button', { name: '取消', exact: true }).click();
  assert.equal(await page.locator('.provider-address > span').innerText(), baseUrl + '/draft');
  await provider.selectOption('deepseek');
  await provider.selectOption('custom');
  await popup.waitFor();
  assert.equal(await popup.locator('input[name="base_url"]').inputValue(), baseUrl + '/draft');
  await popup.getByRole('button', { name: '取消', exact: true }).click();
  assert.equal(await provider.inputValue(), 'deepseek');
  assert.deepEqual(
    await page.evaluate(async () => (await window.codeAssistant.bootstrap()).settings),
    before,
    'provider selection remains a draft until saving',
  );
  await chooseCustomProvider(page, baseUrl);
  homeChecks.push(
    'provider dropdown presets, custom popup validation and Escape, cancelled edits and custom address recall preserve unsaved settings',
  );
}

async function inspectModelDiscovery(page, application) {
  const before = await page.evaluate(async () => (await window.codeAssistant.bootstrap()).settings);
  await chooseCustomProvider(page, baseUrl);
  await page.locator('input[name="api_key"]').fill('model-list-test-key');
  await page.locator('input[name="model"]').fill('');
  await page.getByRole('button', { name: '测试连接', exact: true }).click();
  await page.locator('.api-connection-status.is-success').filter({ hasText: '连接成功' }).waitFor();
  assert.match(await page.locator('.api-connection-status').innerText(), /毫秒/);
  assert.equal(
    await page.locator('.model-name-row select').count(),
    0,
    'testing the API does not replace the model entry or require a model name',
  );
  assert.deepEqual(
    await page.evaluate(async () => (await window.codeAssistant.bootstrap()).settings),
    before,
  );
  discoveryMode = 'unauthorized';
  await page.getByRole('button', { name: '测试连接', exact: true }).click();
  await page.locator('.api-connection-status.is-error').filter({ hasText: 'API Key' }).waitFor();
  assert.doesNotMatch(
    await page.locator('.api-connection-status').innerText(),
    /model-list-test-key/,
  );
  discoveryMode = 'unsupported';
  await page.getByRole('button', { name: '测试连接', exact: true }).click();
  await page
    .locator('.api-connection-status.is-warning')
    .filter({ hasText: '尚未确认调用权限' })
    .waitFor();
  discoveryMode = 'delayed';
  const connectionRequests = discoveryRequests.length;
  await page.getByRole('button', { name: '测试连接', exact: true }).click();
  const connectionDeadline = Date.now() + 5000;
  while (discoveryRequests.length === connectionRequests && Date.now() < connectionDeadline)
    await new Promise((resolve) => setTimeout(resolve, 25));
  assert.ok(discoveryRequests.length > connectionRequests);
  await page.locator('input[name="api_key"]').fill('changed-draft-key');
  await page.waitForTimeout(600);
  assert.equal(
    await page.locator('.api-connection-status').innerText(),
    '',
    'a late connection result cannot validate edited credentials',
  );
  await page.locator('input[name="api_key"]').fill('model-list-test-key');
  discoveryMode = 'ok';
  await page.getByRole('button', { name: '测试连接', exact: true }).click();
  await page.locator('.api-connection-status.is-success').waitFor();
  homeChecks.push(
    'API test button uses draft credentials without a model or save, shows elapsed time and handles auth, unsupported detection and stale results',
  );
  await page.getByRole('button', { name: '获取模型列表', exact: true }).click();
  const selector = page.getByRole('combobox', { name: '模型名称', exact: true });
  await selector.waitFor();
  assert.equal(await selector.locator('option').count(), 3, 'duplicate provider IDs are removed');
  assert.equal(discoveryRequests.at(-1).authorization, 'Bearer model-list-test-key');
  assert.equal(discoveryRequests.at(-1).url, '/v1/models');
  assert.deepEqual(
    await page.evaluate(async () => (await window.codeAssistant.bootstrap()).settings),
    before,
    'fetching with draft credentials does not save the configuration',
  );
  await selector.selectOption('local-protocol-test');
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await nativeScreenshot(application, 'model-list-native.png');
  await page.getByRole('button', { name: '手动填写', exact: true }).click();
  assert.equal(await page.locator('input[name="model"]').inputValue(), 'local-protocol-test');
  await page.getByRole('button', { name: '从列表选择', exact: true }).click();
  assert.equal(await selector.inputValue(), 'local-protocol-test');
  discoveryMode = 'empty';
  await page.getByRole('button', { name: '获取模型列表', exact: true }).click();
  await page.locator('.model-fetch-status').filter({ hasText: '未返回可用模型' }).waitFor();
  assert.equal(await page.locator('input[name="model"]').inputValue(), 'local-protocol-test');
  discoveryMode = 'unauthorized';
  await page.getByRole('button', { name: '获取模型列表', exact: true }).click();
  await page.locator('.model-fetch-error').filter({ hasText: 'API Key' }).waitFor();
  assert.doesNotMatch(await page.locator('.model-fetch-error').innerText(), /model-list-test-key/);
  discoveryMode = 'unsupported';
  await page.getByRole('button', { name: '获取模型列表', exact: true }).click();
  await page.locator('.model-fetch-error').filter({ hasText: '不支持' }).waitFor();
  discoveryMode = 'delayed';
  const previousRequests = discoveryRequests.length;
  await page.getByRole('button', { name: '获取模型列表', exact: true }).click();
  const deadline = Date.now() + 5000;
  while (discoveryRequests.length === previousRequests && Date.now() < deadline)
    await new Promise((resolve) => setTimeout(resolve, 25));
  assert.ok(discoveryRequests.length > previousRequests);
  await chooseCustomProvider(page, baseUrl + '/changed');
  await page.waitForTimeout(600);
  assert.equal(
    await page.locator('.model-name-row select').count(),
    0,
    'late responses cannot populate a changed provider',
  );
  assert.equal(await page.locator('.model-fetch-status').innerText(), '');
  assert.equal(
    await page.locator('input[name="model"]').inputValue(),
    '',
    'changing a provider endpoint clears the previous model selection',
  );
  discoveryMode = 'ok';
  await page.locator('input[name="api_key"]').fill('');
  await chooseCustomProvider(page, baseUrl);
  assert.equal(modelCalls, 0, 'model discovery never starts a generation task');
  homeChecks.push(
    'draft model discovery uses the native IPC and HTTP route, deduplicates IDs, selects models and supports manual input without saving',
  );
  homeChecks.push(
    'empty, unsupported and unauthorized model lists preserve manual input; stale provider responses are ignored',
  );
}

async function inspectSavedConnections(page, application) {
  const current = await page.evaluate(
    async () => (await window.codeAssistant.bootstrap()).settings,
  );
  const originalId = current.connection_id;
  const open = async () => {
    await page
      .locator('.feature-dialog')
      .getByRole('button', { name: '模型设置', exact: true })
      .click();
    await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor();
    await page.getByRole('button', { name: '新建配置', exact: true }).waitFor({ state: 'visible' });
    await page.waitForFunction(
      () => !document.querySelector('.connection-presets-heading button').disabled,
    );
  };
  await open();
  const list = page.getByRole('combobox', { name: '配置列表', exact: true });
  assert.equal(await list.inputValue(), originalId);
  await page.getByRole('textbox', { name: '配置名称', exact: true }).fill('日常代码助手');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  await open();
  assert.equal(
    await list.locator('option').count(),
    2,
    'editing a saved configuration does not duplicate it',
  );
  await page.getByRole('button', { name: '新建配置', exact: true }).click();
  assert.equal(await list.inputValue(), '');
  assert.equal(await page.locator('input[name="model"]').inputValue(), '');
  assert.equal(await page.locator('input[name="api_key"]').inputValue(), '');
  assert.equal(
    await page.getByRole('combobox', { name: 'API 服务商', exact: true }).inputValue(),
    '',
  );
  assert.equal(
    await page.evaluate(
      async () => (await window.codeAssistant.bootstrap()).settings.connection_id,
    ),
    originalId,
    'creating a draft does not change the active connection',
  );
  await chooseCustomProvider(page, baseUrl);
  await page.getByRole('textbox', { name: '配置名称', exact: true }).fill('备用配置');
  await page.locator('input[name="model"]').fill('alternate-local-model');
  await page.locator('input[name="api_key"]').fill('secondary-test-key');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  const second = await page.evaluate(async () => (await window.codeAssistant.bootstrap()).settings);
  assert.notEqual(second.connection_id, originalId);
  await open();
  assert.equal(await list.locator('option').count(), 3);
  await list.selectOption(originalId);
  await page.waitForFunction(
    () => document.querySelector('input[name="model"]').value === 'local-protocol-test',
  );
  assert.equal(
    await page.evaluate(
      async () => (await window.codeAssistant.bootstrap()).settings.connection_id,
    ),
    originalId,
  );
  await list.selectOption(second.connection_id);
  await page.waitForFunction(
    () => document.querySelector('input[name="model"]').value === 'alternate-local-model',
  );
  assert.equal(await page.locator('input[name="api_key"]').inputValue(), '');
  await page.getByRole('button', { name: '测试连接', exact: true }).click();
  await page.locator('.api-connection-status.is-success').waitFor();
  assert.equal(
    discoveryRequests.at(-1).authorization,
    'Bearer secondary-test-key',
    'selecting a saved connection restores its separate key without exposing it to the renderer',
  );
  await list.selectOption(originalId);
  await page.waitForFunction(
    () => document.querySelector('input[name="model"]').value === 'local-protocol-test',
  );
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  await nativeScreenshot(application, 'saved-connections-native.png');
  await page.getByRole('button', { name: '新建配置', exact: true }).click();
  await page.getByRole('textbox', { name: '配置名称', exact: true }).fill('未保存的新配置');
  assert.equal(
    await page.getByRole('button', { name: '删除配置', exact: true }).isDisabled(),
    true,
  );
  await chooseCustomProvider(page, baseUrl);
  await page.locator('input[name="model"]').fill('temporary-delete-model');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  await open();
  assert.equal(await list.locator('option').count(), 4);
  await page.getByRole('button', { name: '删除配置', exact: true }).click();
  await page.waitForFunction(
    (id) => document.querySelector('#saved-connection').value === id,
    originalId,
  );
  assert.equal(await list.locator('option').count(), 3);
  assert.equal(await page.locator('input[name="model"]').inputValue(), 'local-protocol-test');
  assert.equal(
    await page.evaluate(
      async () => (await window.codeAssistant.bootstrap()).settings.connection_id,
    ),
    originalId,
  );
  await nativeScreenshot(application, 'delete-connection-native.png');
  await page.getByRole('button', { name: '新建配置', exact: true }).click();
  await page.getByRole('textbox', { name: '配置名称', exact: true }).fill('未保存的新配置');
  await page.getByRole('button', { name: '取消', exact: true }).click();
  assert.equal(
    await page.evaluate(
      async () => (await window.codeAssistant.bootstrap()).settings.connection_id,
    ),
    originalId,
  );
  homeChecks.push(
    'saved connection list edits in place, creates separate profiles, switches active models and keys immediately, and cancels unsaved new drafts',
  );
  homeChecks.push(
    'delete configuration uses native IPC, removes the saved entry, restores the remaining active configuration and is disabled for unsaved drafts',
  );
}

try {
  let opened = await launch();
  app = opened.instance;
  let page = opened.page;
  await inspectHome(page, app);
  await app.evaluate(({ dialog }, folder) => {
    global.__nativeFolderSelections = 0;
    dialog.showOpenDialog = async () => {
      global.__nativeFolderSelections++;
      return { canceled: false, filePaths: [folder] };
    };
  }, workspace);
  await page.getByRole('button', { name: '导入项目', exact: true }).click();
  await page.locator('.selected-project').filter({ hasText: 'calculator-demo' }).waitFor();
  assert.equal(await app.evaluate(() => global.__nativeFolderSelections), 1);
  homeChecks.push('native folder picker imports the project on the blue client');
  await inspectImportedProject(page, app);
  await app.evaluate(({ dialog }) => {
    global.__clearChooserCalls = 0;
    dialog.showOpenDialog = async () => {
      global.__clearChooserCalls++;
      return { canceled: true, filePaths: [] };
    };
  });
  await page.getByRole('button', { name: '清除当前项目', exact: true }).click();
  await page.locator('.project-drop:not(.is-ready)').waitFor();
  assert.equal(await page.locator('.project-drop [role="status"]').innerText(), '将项目拖入这里');
  assert.equal(
    await page.locator('.project-clear, .selected-project, .home-grid.is-celebrating').count(),
    0,
  );
  assert.equal(
    await app.evaluate(() => global.__clearChooserCalls),
    0,
    'the separate clear button never opens the project picker',
  );
  assert.equal(
    await readFile(path.join(workspace, 'calculator.py'), 'utf8'),
    original,
    'clearing the selection leaves project files unchanged',
  );
  await nativeScreenshot(app, 'project-cleared.png');
  homeChecks.push(
    'clear button resets the drop panel during success feedback without opening the picker or deleting files',
  );
  await dropNativePath(page, workspace);
  await page.locator('.selected-project').filter({ hasText: 'calculator-demo' }).waitFor();
  await page.locator('.home-action-comment').click();
  await page.getByRole('dialog', { name: '代码注释', exact: true }).waitFor();
  await assertNoLegacyInterface(page);
  assert.match(
    await page.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
    /中文.*注释|注释/,
  );
  assert.equal(
    await page.getByRole('checkbox', { name: '允许此任务运行测试', exact: true }).count(),
    0,
    'the annotation skill offers no authorization to execute the target project',
  );
  assert.equal(await page.getByRole('textbox', { name: '授权测试命令', exact: true }).count(), 0);
  assert.equal(modelCalls, 0, 'choosing an action prepares the task without sending it');
  homeChecks.push(
    'native folder drop opens the Chinese annotation dialog without a legacy workbench',
  );
  await page
    .getByRole('textbox', { name: '任务需求', exact: true })
    .fill('保留这份未发送的任务草稿。');
  await page.getByRole('button', { name: '关闭任务面板', exact: true }).click();
  await assertNoLegacyInterface(page);
  await page.getByRole('button', { name: '继续任务', exact: true }).click();
  assert.equal(
    await page.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
    '保留这份未发送的任务草稿。',
  );
  homeChecks.push('closing a feature panel and continuing preserves an unsent task draft');
  await page.getByRole('button', { name: '关闭任务面板', exact: true }).click();
  await dropNativePath(page, path.join(workspace, 'calculator.py'));
  await page.locator('.home-action-analysis').click();
  await page.getByRole('dialog', { name: '项目解析', exact: true }).waitFor();
  await assertNoLegacyInterface(page);
  assert.match(
    await page.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
    /说明文档|解析|分析/,
  );
  assert.equal(modelCalls, 0);
  homeChecks.push('native code-file drop prepares documentation inside the blue client');
  await page.getByRole('button', { name: '关闭任务面板', exact: true }).click();
  await page.locator('.home-action-comment').click();
  await page
    .locator('.feature-dialog')
    .getByRole('button', { name: '模型设置', exact: true })
    .click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor();
  await inspectProviderSelection(page, app);
  await inspectModelDiscovery(page, app);
  await chooseCustomProvider(page, baseUrl);
  await page.locator('input[name="model"]').fill('local-protocol-test');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  await inspectSavedConnections(page, app);
  await page
    .getByRole('textbox', { name: '任务需求', exact: true })
    .fill('按绑定技能为完整项目添加五项文件头和逐函数三项中文注释，保留原有逻辑，仅静态检查。');
  assert.equal(
    await page.getByRole('checkbox', { name: '允许此任务运行测试', exact: true }).count(),
    0,
  );
  await page.getByRole('button', { name: '开始注释', exact: true }).click();
  await page.locator('.task-status.completed').waitFor({ timeout: 60000 });
  assert.equal(await page.getByRole('button', { name: '接受并应用', exact: true }).count(), 0);
  assert.match(await page.locator('.patch-review').innerText(), /calculator\.py|中文/);
  await assertNoLegacyInterface(page);
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), updated);
  assert.equal(await readFile(path.join(workspace, 'test_calculator.py'), 'utf8'), updatedTests);
  assert.equal(await readFile(path.join(workspace, 'pytest.ini'), 'utf8'), updatedConfig);
  assert.deepEqual(
    await readdir(workspace),
    originalEntries,
    'annotation modifies existing project files without generating reports or execution artifacts',
  );
  assert.equal(
    await page.getByLabel('运行输出', { exact: true }).count(),
    0,
    'the annotation task does not run the target project or pytest',
  );
  const annotationTaskId = await page
    .getByRole('button', { name: '历史任务', exact: true })
    .getAttribute('data-task-id');
  assert.ok(annotationTaskId, 'the annotation task is available in persisted history');
  const savedTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    annotationTaskId,
  );
  assert.equal(
    savedTask.skill,
    'annotate-project-zh',
    'the annotation button creates a skill-bound task',
  );
  assert.equal(
    savedTask.selected_file,
    null,
    'a single-file drop must not narrow the annotation scope',
  );
  assert.deepEqual(savedTask.test_argv, [], 'skill-bound tasks never authorize project execution');
  assert.equal(
    savedTask.patches[0].changes.length,
    3,
    'the annotation includes project tests and configuration',
  );
  assert.match(
    savedTask.result,
    /客户端实际进度：(Python\s+)?静态注释格式通过 2 个文件/,
    'the final result includes actual static coverage rather than only the model summary',
  );
  assert.equal(modelCalls, 6);
  assert.equal(requests[0].stream, true);
  assert.ok(
    requests[1].messages.some(
      (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-1',
    ),
    'real observations use the original native call ID',
  );
  assert.ok(
    !JSON.stringify(requests).includes('ignored simulated observation'),
    'model-generated tool observations never enter conversation evidence',
  );
  for (const request of requests) {
    const system = request.messages.find((message) => message.role === 'system').content;
    assert.ok(system.includes(annotationSkill), 'every model step receives the full bundled skill');
    assert.match(system, /函数用途、输入说明、输出说明/);
    assert.match(system, /完整项目/);
    assert.doesNotMatch(system, /test: \{\}/, 'the annotation model is not offered a test action');
    const context = JSON.parse(request.messages[1].content);
    assert.equal(context.skill, 'annotate-project-zh');
    assert.equal(context.selected_file, null);
    assert.deepEqual(context.authorized_test, []);
    assert.equal(
      path.resolve(context.workspace_root),
      workspace,
      'the pinned context identifies the full imported workspace',
    );
  }
  await nativeScreenshot(app, 'annotation-native.png');
  homeChecks.push(
    'annotation automatically applies validated source, function and configuration comments with Diff and undo records',
  );
  await page.getByRole('button', { name: '撤销此补丁', exact: true }).click();
  await page.locator('.patch-status').filter({ hasText: '已撤销' }).waitFor();
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), original);
  assert.equal(await readFile(path.join(workspace, 'test_calculator.py'), 'utf8'), originalTests);
  assert.equal(await readFile(path.join(workspace, 'pytest.ini'), 'utf8'), originalConfig);
  homeChecks.push('annotation undo restores all original project source, tests and configuration');
  await writeFile(
    path.join(workspace, 'README.md'),
    '# 计算器示例\n\n提供 add 函数，示例包含预留的算术错误。\n',
    'utf8',
  );
  await page.getByRole('button', { name: '关闭任务面板', exact: true }).click();
  await page.locator('.home-action-analysis').click();
  await page.getByRole('dialog', { name: '项目解析', exact: true }).waitFor();
  await page.getByRole('button', { name: '新建任务', exact: true }).click();
  await page
    .getByRole('textbox', { name: '任务需求', exact: true })
    .fill('依据实际代码生成项目说明.md 和 docs/diagrams/，说明项目用途、核心函数及测试方式。');
  assert.equal(
    await page.getByRole('checkbox', { name: '允许此任务运行测试', exact: true }).count(),
    0,
  );
  await page.getByRole('button', { name: '开始解析', exact: true }).click();
  await page.locator('.task-status.completed').waitFor({ timeout: 60000 });
  assert.equal(await page.getByRole('button', { name: '接受并应用', exact: true }).count(), 0);
  for (const name of documentationPaths) {
    assert.equal(
      await exists(path.join(workspace, name)),
      true,
      'the full document package is applied without a review click',
    );
  }
  assert.match(await page.locator('.patch-review').innerText(), /项目说明\.md/);
  const architecturePreview = page.locator('.patch-file').filter({
    has: page.locator('summary').filter({ hasText: 'docs/diagrams/architecture.png' }),
  });
  await architecturePreview.locator('summary').click();
  const previewImage = architecturePreview.getByRole('img', {
    name: 'docs/diagrams/architecture.png 修改后 PNG 预览',
    exact: true,
  });
  await previewImage.waitFor();
  await previewImage.evaluate((image) => image.decode());
  assert.ok(await previewImage.evaluate((image) => image.naturalWidth > 0));
  assert.equal(
    await architecturePreview.locator('.patch-diff').count(),
    0,
    'PNG bytes are never shown as source text',
  );
  await assertNoLegacyInterface(page);
  await assertDocumentationFiles();
  const analysisTaskId = await page
    .getByRole('button', { name: '历史任务', exact: true })
    .getAttribute('data-task-id');
  assert.ok(analysisTaskId && analysisTaskId !== annotationTaskId);
  const analysisTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    analysisTaskId,
  );
  assert.equal(
    analysisTask.skill,
    'analyze-project-zh',
    'project analysis creates a dedicated static documentation task',
  );
  assert.equal(analysisTask.selected_file, null);
  assert.deepEqual(analysisTask.test_argv, []);
  assert.equal(
    analysisTask.patches[0].changes.length,
    5,
    'automatic application writes the five output files',
  );
  assert.equal(
    analysisTask.patches[0].changes.filter(
      (change) => change.encoding === 'base64' && change.mime_type === 'image/png',
    ).length,
    3,
  );
  assert.equal(modelCalls, 9);
  assert.equal(analysisTask.steps, 3, 'a native read batch uses one model round');
  const batchResults = requests[7].messages.filter((message) => message.role === 'tool');
  assert.deepEqual(
    batchResults.map((message) => message.tool_call_id),
    ['smoke-call-7', 'smoke-call-7-extra', 'smoke-call-7-readme', 'smoke-call-7-tests'],
  );
  assert.deepEqual(
    batchResults.map((message) => JSON.parse(message.content).path),
    ['calculator.py', 'calculator.py', 'README.md', 'test_calculator.py'],
  );
  homeChecks.push(
    'project analysis accepts a provider returning multiple read calls despite parallel_tool_calls:false and returns each real result with its original ID',
  );
  homeChecks.push(
    'cached reads retain their original path; documentation phases keep submit_action stable and merge repeated stream metadata before automatic application',
  );
  assert.ok(
    requests[8].messages.some((message) =>
      message.tool_calls?.some((call) => call.id === 'smoke-call-8'),
    ),
    'repeated document call IDs are not concatenated in history',
  );
  assert.ok(
    !requests[6].messages
      .find((message) => message.role === 'system')
      .content.includes(annotationSkill),
    'documentation is not subject to the annotation-only skill',
  );
  await nativeScreenshot(app, 'analysis-native.png');
  homeChecks.push(
    'project analysis binds static documentation skill and automatically applies 项目说明.md plus three PNG diagrams, with actual image previews',
  );
  await page.getByRole('button', { name: '关闭任务面板', exact: true }).click();
  await dropNativePath(page, path.join(workspace, 'notes.md'));
  await page.locator('.home-action-analysis').click();
  await page.getByRole('dialog', { name: '项目解析', exact: true }).waitFor();
  assert.match(await page.locator('.feature-project').innerText(), /解析范围：整个项目/);
  assert.equal(
    await page.locator('.task-status, .patch-review').count(),
    0,
    'a newly dropped file starts a fresh task rather than relabeling the previous task',
  );
  assert.equal(
    await page.getByRole('textbox', { name: '任务需求', exact: true }).isEditable(),
    true,
  );
  assert.equal(
    (await historyTaskIds(page)).length,
    2,
    'importing a file keeps both previous tasks in history',
  );
  assert.equal(modelCalls, 9, 'importing another file does not send a new model request');
  await assertNoLegacyInterface(page);
  homeChecks.push(
    'importing another file in the same project clears the active result and retains task history',
  );
  await app.close();
  app = null;
  opened = await launch();
  app = opened.instance;
  page = opened.page;
  await assertNoLegacyInterface(page);
  await page.locator('.project-drop.is-ready').waitFor();
  assert.equal(
    await page.locator('.home-grid.is-celebrating').count(),
    0,
    'restoring an existing project after restart does not pretend a new drop occurred',
  );
  await page.locator('.home-action-comment').click();
  await selectHistoryTask(page, annotationTaskId);
  await page.locator('.task-status.completed').waitFor();
  assert.match(await page.locator('.patch-status').innerText(), /已撤销/);
  const restoredAnnotationTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    annotationTaskId,
  );
  assert.equal(
    restoredAnnotationTask.skill,
    'annotate-project-zh',
    'the skill binding survives application restart',
  );
  assert.equal(restoredAnnotationTask.selected_file, null);
  assert.deepEqual(restoredAnnotationTask.test_argv, []);
  assert.equal(
    await page.getByRole('checkbox', { name: '允许此任务运行测试', exact: true }).count(),
    0,
  );
  await selectHistoryTask(page, analysisTaskId);
  await page.getByRole('dialog', { name: '项目解析', exact: true }).waitFor();
  await page.locator('.task-status.completed').waitFor();
  assert.match(await page.locator('.patch-review').innerText(), /项目说明\.md/);
  assert.match(await page.locator('.patch-status').innerText(), /已应用/);
  await assertDocumentationFiles();
  await assertNoLegacyInterface(page);
  await page
    .locator('.feature-dialog')
    .getByRole('button', { name: '模型设置', exact: true })
    .click();
  assert.equal(await page.locator('input[name="model"]').inputValue(), 'local-protocol-test');
  assert.equal(
    await page.getByRole('combobox', { name: 'API 服务商', exact: true }).inputValue(),
    'custom',
  );
  assert.equal(await page.locator('.provider-address > span').innerText(), baseUrl);
  await page.waitForFunction(() => !document.querySelector('#saved-connection').disabled);
  assert.equal(
    await page.getByRole('combobox', { name: '配置列表', exact: true }).locator('option').count(),
    3,
    'both saved connections survive application restart',
  );
  assert.equal(
    await page.getByRole('textbox', { name: '配置名称', exact: true }).inputValue(),
    '日常代码助手',
  );
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  homeChecks.push(
    'restart restores annotation and documentation history plus the saved model connection',
  );
  await page.getByRole('button', { name: '关闭任务面板', exact: true }).click();
  await page.getByRole('button', { name: '清除当前项目', exact: true }).click();
  await page.locator('.project-drop:not(.is-ready)').waitFor();
  assert.equal(
    await page.getByRole('button', { name: '继续任务', exact: true }).count(),
    0,
    'clearing a project also clears its active task and unsent context',
  );
  await app.close();
  app = null;
  opened = await launch();
  app = opened.instance;
  page = opened.page;
  assert.equal(await page.locator('.project-drop [role="status"]').innerText(), '将项目拖入这里');
  assert.equal(
    await page.locator('.project-clear, .selected-project').count(),
    0,
    'a cleared project stays cleared across restart',
  );
  await dropNativePath(page, workspace);
  await page.locator('.project-drop.is-ready').waitFor();
  await page.locator('.home-action-comment').click();
  const retainedTasks = await historyTaskIds(page);
  assert.ok(
    retainedTasks.includes(annotationTaskId) && retainedTasks.includes(analysisTaskId),
    'reimporting after clear restores the existing task history',
  );
  await assertDocumentationFiles();
  homeChecks.push(
    'cleared selection persists after restart; reimport restores project history and leaves generated files intact',
  );
  await selectHistoryTask(page, annotationTaskId);
  await page.locator('.task-status.completed').waitFor();
  await page.getByRole('button', { name: '历史任务', exact: true }).click();
  const analysisRow = page.locator(`.task-history-row[data-task-id="${analysisTaskId}"]`);
  await analysisRow.locator('.task-history-delete').click();
  await analysisRow.waitFor({ state: 'detached' });
  assert.equal(
    await page.getByRole('button', { name: '历史任务', exact: true }).getAttribute('data-task-id'),
    annotationTaskId,
    'deleting another row preserves the current selection',
  );
  const annotationRow = page.locator(`.task-history-row[data-task-id="${annotationTaskId}"]`);
  await annotationRow.locator('.task-history-delete').click();
  await annotationRow.waitFor({ state: 'detached' });
  assert.equal(
    await page.locator('.task-status, .patch-review').count(),
    0,
    'deleting the selected task clears its progress and Diff',
  );
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), original);
  await assertDocumentationFiles();
  await nativeScreenshot(app, 'history-deleted-native.png');
  await app.close();
  app = null;
  opened = await launch();
  app = opened.instance;
  page = opened.page;
  await page.locator('.project-drop.is-ready').waitFor();
  await page.locator('.home-action-comment').click();
  assert.deepEqual(await historyTaskIds(page), [], 'deleted records remain absent after restart');
  await assertDocumentationFiles();
  homeChecks.push(
    'per-row history deletion clears selected and other records, persists after restart, and preserves project files',
  );

  await page
    .getByRole('textbox', { name: '任务需求', exact: true })
    .fill('为 calculator.py 添加中文注释；服务额度恢复后继续同一任务，重新读取并核实已应用修改。');
  await page.getByRole('button', { name: '开始注释', exact: true }).click();
  await page.locator('.task-status.failed').waitFor({ timeout: 60000 });
  const resumableTaskId = await page
    .getByRole('button', { name: '历史任务', exact: true })
    .getAttribute('data-task-id');
  assert.ok(resumableTaskId && ![annotationTaskId, analysisTaskId].includes(resumableTaskId));
  const failedTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    resumableTaskId,
  );
  assert.equal(failedTask.skill, 'annotate-project-zh');
  assert.equal(failedTask.steps, 3, 'a failed provider request retains its consumed step');
  assert.match(failedTask.result, /402|insufficient_quota/);
  assert.equal(failedTask.patches.length, 1);
  assert.equal(failedTask.patches[0].status, 'applied');
  const appliedPatchId = failedTask.patches[0].id;
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), updated);
  assert.equal(modelCalls, 12, 'the simulated quota error stops without an automatic retry');
  const firstRead = requests[10].messages.find(
    (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-10',
  );
  assert.equal(
    JSON.parse(firstRead.content).content,
    original,
    'the new annotation task reads the original file restored by the earlier undo',
  );
  await page.getByRole('button', { name: '继续执行', exact: true }).waitFor();
  await page.getByRole('button', { name: '继续执行', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(artifacts, 'annotation-failed.png') });
  await nativeScreenshot(app, 'annotation-failed-native.png');

  await app.close();
  app = null;
  opened = await launch();
  app = opened.instance;
  page = opened.page;
  await page.locator('.project-drop.is-ready').waitFor();
  await page.locator('.home-action-comment').click();
  await selectHistoryTask(page, resumableTaskId);
  await page.locator('.task-status.failed').waitFor();
  await page.locator('.feature-activity .activity-error').waitFor();
  assert.equal(
    modelCalls,
    12,
    'restarting and selecting failed history never sends a model request',
  );
  assert.deepEqual(await historyTaskIds(page), [resumableTaskId]);
  assert.equal(
    await page.getByText(resumePatchSummary, { exact: true }).count(),
    1,
    'persisted progress replays once when the failed history is opened',
  );
  assert.equal(await page.locator('.patch-status.applied').count(), 1);

  await page
    .locator('.feature-dialog')
    .getByRole('button', { name: '模型设置', exact: true })
    .click();
  await page.getByRole('spinbutton', { name: '单任务最大执行步数', exact: true }).fill('3');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  assert.equal(
    await page.getByRole('button', { name: '继续执行', exact: true }).isDisabled(),
    true,
  );
  assert.match(
    await page.locator('.feature-resume-hint').innerText(),
    /达到执行步数上限.*提高步数/,
  );
  assert.equal(modelCalls, 12, 'changing the task budget does not itself execute the task');
  await page
    .locator('.feature-dialog')
    .getByRole('button', { name: '模型设置', exact: true })
    .click();
  await page.getByRole('spinbutton', { name: '单任务最大执行步数', exact: true }).fill('5');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  assert.equal(await page.getByRole('button', { name: '继续执行', exact: true }).isEnabled(), true);
  const priorProgress = await page.locator('.feature-activity li').allTextContents();
  await page.getByRole('button', { name: '继续执行', exact: true }).click();
  await page.locator('.task-status.completed').waitFor({ timeout: 60000 });
  await page.getByText(resumeReadSummary, { exact: true }).waitFor();
  assert.equal(
    await page.getByRole('button', { name: '历史任务', exact: true }).getAttribute('data-task-id'),
    resumableTaskId,
  );
  const resumedTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    resumableTaskId,
  );
  assert.equal(resumedTask.id, failedTask.id, 'resume continues the existing persisted task');
  assert.equal(
    resumedTask.session_id,
    failedTask.session_id,
    'resume retains the same conversation',
  );
  assert.equal(resumedTask.steps, 5, 'resume adds two steps to the existing three-step budget');
  assert.match(await page.locator('.feature-step-count').innerText(), /5\s*\/\s*5\s*步/);
  assert.equal(resumedTask.patches.length, 1, 'resume never replays the already applied patch');
  assert.equal(resumedTask.patches[0].id, appliedPatchId);
  assert.equal(resumedTask.patches[0].status, 'applied');
  assert.equal(await page.locator('.patch-status.applied').count(), 1);
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), updated);
  assert.equal(await readFile(path.join(workspace, 'test_calculator.py'), 'utf8'), originalTests);
  assert.equal(await readFile(path.join(workspace, 'pytest.ini'), 'utf8'), originalConfig);
  assert.equal(modelCalls, 14);
  const restoredRead = requests[12].messages.find(
    (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-10',
  );
  assert.equal(
    JSON.parse(restoredRead.content).content,
    original,
    'the original read observation survives restart and resume',
  );
  const restoredPatch = requests[12].messages.find(
    (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-11',
  );
  assert.equal(JSON.parse(restoredPatch.content).patch_id, appliedPatchId);
  assert.equal(JSON.parse(restoredPatch.content).status, 'applied');
  assert.ok(
    requests[12].messages.some(
      (entry) => entry.role === 'user' && entry.content.includes('用户点击“继续执行”'),
    ),
  );
  const currentRead = requests[13].messages.find(
    (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-13',
  );
  assert.equal(
    JSON.parse(currentRead.content).content,
    updated,
    'the resumed model receives a fresh observation of the actual applied source',
  );
  const resumedProgress = await page.locator('.feature-activity li').allTextContents();
  assert.deepEqual(
    resumedProgress.slice(0, priorProgress.length),
    priorProgress,
    'resuming retains the displayed progress instead of replacing it',
  );
  assert.ok(
    resumedProgress.length > priorProgress.length,
    'the resumed SSE stream delivers new progress',
  );
  assert.equal(
    await page.getByText(resumePatchSummary, { exact: true }).count(),
    1,
    'reconnecting SSE never duplicates progress from before the failure',
  );
  assert.equal(await page.getByText(resumeReadSummary, { exact: true }).count(), 1);
  assert.equal(
    await page.getByRole('button', { name: '继续执行', exact: true }).count(),
    0,
    'completed annotation tasks cannot be resumed',
  );
  assert.deepEqual(
    await historyTaskIds(page),
    [resumableTaskId],
    'resume creates no extra history row',
  );
  await page.locator('.feature-step-count').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(artifacts, 'annotation-resumed.png') });
  await nativeScreenshot(app, 'annotation-resumed-native.png');
  homeChecks.push(
    'annotation quota failure preserves applied code; restart and history restore the same task, steps, observations and Diff',
  );
  homeChecks.push(
    'resume is disabled at the step limit; raising the limit continues the same task from 3 to 5 steps with one applied patch and deduplicated live progress',
  );

  await page
    .locator('.feature-dialog')
    .getByRole('button', { name: '模型设置', exact: true })
    .click();
  await page.getByRole('spinbutton', { name: '单任务最大执行步数', exact: true }).fill('12');
  await page.getByRole('button', { name: '保存连接', exact: true }).click();
  await page.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  await page.getByRole('button', { name: '新建任务', exact: true }).click();
  await page
    .getByRole('textbox', { name: '任务需求', exact: true })
    .fill('识别已完成注释的文件，遇到重复扫描时保留任务进度并暂停，继续执行后处理剩余范围。');
  await page.getByRole('button', { name: '开始注释', exact: true }).click();
  await page.locator('.task-status.interrupted').waitFor({ timeout: 60000 });
  const loopTaskId = await page
    .getByRole('button', { name: '历史任务', exact: true })
    .getAttribute('data-task-id');
  assert.ok(loopTaskId && loopTaskId !== resumableTaskId);
  const loopTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    loopTaskId,
  );
  assert.equal(
    loopTask.steps,
    8,
    'six identical reads without new evidence pause before the configured budget',
  );
  assert.match(loopTask.result, /持续重复动作或无进展/);
  assert.match(loopTask.result, /客户端实际进度/);
  assert.equal(loopTask.patches.length, 0, 'rechecking completed files never creates a patch');
  assert.equal(modelCalls, 22, 'the loop guard stops issuing provider calls after pausing');
  const verifiedRead = JSON.parse(
    requests[15].messages.find(
      (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-15',
    ).content,
  );
  assert.equal(verifiedRead.status, 'verified');
  assert.equal(verifiedRead.format_verified, true);
  assert.equal(
    verifiedRead.content,
    updated,
    'an existing complete Python source is still read once to check the meaning of its comments',
  );
  const repeatedRead = JSON.parse(
    requests[17].messages.find(
      (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-17',
    ).content,
  );
  assert.equal(repeatedRead.status, 'verified');
  assert.equal(repeatedRead.already_complete, true);
  assert.equal(
    repeatedRead.content,
    '',
    'completed Python reads avoid replaying already observed source contents',
  );
  const invalidRead = JSON.parse(
    requests[16].messages.find(
      (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-16',
    ).content,
  );
  assert.equal(invalidRead.status, 'error');
  assert.equal(invalidRead.action, 'read');
  assert.equal(invalidRead.error, 'ValueError');
  assert.match(invalidRead.recovery.instruction, /真实错误/);
  const warningObservation = JSON.parse(
    requests[19].messages.find(
      (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-19',
    ).content,
  );
  assert.match(
    warningObservation.loop_guard.message,
    /重复动作/,
    'the provider receives a real loop warning before the client pauses',
  );
  const loopWarnings = page
    .locator('.feature-activity li')
    .filter({ hasText: '检测到重复动作且没有新增读取范围或注释进展' });
  await loopWarnings.first().waitFor();
  assert.ok(
    (await loopWarnings.count()) >= 1,
    'loop warnings are visible in the desktop progress list',
  );
  assert.equal(await page.getByRole('button', { name: '继续执行', exact: true }).isEnabled(), true);
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), updated);
  await page.getByRole('button', { name: '继续执行', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(artifacts, 'annotation-loop-paused.png') });
  const warningsBeforeResume = await loopWarnings.count();
  await page.getByRole('button', { name: '继续执行', exact: true }).click();
  await page.locator('.task-status.completed').waitFor({ timeout: 60000 });
  await page.getByText(loopResumeSummary, { exact: true }).waitFor();
  const resumedLoopTask = await page.evaluate(
    (id) => window.codeAssistant.request('GET', `/api/tasks/${id}`),
    loopTaskId,
  );
  assert.equal(resumedLoopTask.id, loopTask.id);
  assert.equal(resumedLoopTask.session_id, loopTask.session_id);
  assert.equal(
    resumedLoopTask.steps,
    10,
    'continuing the paused task retains its eight consumed steps',
  );
  assert.equal(resumedLoopTask.patches.length, 0);
  assert.equal(modelCalls, 24);
  assert.match(resumedLoopTask.result, /客户端实际进度：(Python\s+)?静态注释格式通过 1 个文件/);
  assert.match(resumedLoopTask.result, /未完成 2 个文件/);
  assert.match(
    resumedLoopTask.result,
    /尚未覆盖整个项目/,
    'a final action cannot conceal the remaining annotation coverage',
  );
  assert.match(
    await page.getByLabel('处理结果', { exact: true }).innerText(),
    /test_calculator\.py/,
  );
  const resumedContext = JSON.parse(requests[22].messages[1].content);
  assert.equal(
    resumedContext.annotation_progress.counts.verified,
    1,
    'durable completed-file progress is pinned into the resumed model context',
  );
  const resumedPendingRead = JSON.parse(
    requests[23].messages.find(
      (entry) => entry.role === 'tool' && entry.tool_call_id === 'smoke-call-23',
    ).content,
  );
  assert.equal(resumedPendingRead.content, originalTests);
  assert.equal(
    await loopWarnings.count(),
    warningsBeforeResume,
    'resuming a loop pause does not replay previous warning events',
  );
  assert.equal(await page.getByRole('button', { name: '继续执行', exact: true }).count(), 0);
  assert.deepEqual(
    new Set(await historyTaskIds(page)),
    new Set([loopTaskId, resumableTaskId]),
    'loop recovery retains one history row for each actual task',
  );
  assert.equal(await readFile(path.join(workspace, 'calculator.py'), 'utf8'), updated);
  assert.equal(await readFile(path.join(workspace, 'test_calculator.py'), 'utf8'), originalTests);
  assert.equal(await readFile(path.join(workspace, 'pytest.ini'), 'utf8'), originalConfig);
  await page.getByLabel('处理结果', { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(artifacts, 'annotation-loop-resumed.png') });
  homeChecks.push(
    'existing complete Python source is read once for semantic review, then returns verified without contents; invalid reads preserve structured errors and correction guidance',
  );
  homeChecks.push(
    'repeated reads emit visible loop warnings and pause; continuing preserves the task, eight used steps and durable coverage, then reports remaining files',
  );
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(artifacts, 'result.json'),
    JSON.stringify(
      {
        status: 'passed',
        modelCalls,
        checks: [
          ...homeChecks,
          'retired IDE elements remain absent throughout both feature workflows',
        ],
        errors,
      },
      null,
      2,
    ),
  );
  console.log(`Desktop smoke passed. Artifacts: ${artifacts}`);
} catch (error) {
  console.error('Renderer errors:', errors);
  if (app) {
    const pages = app.windows();
    if (pages[0]) {
      await pages[0].screenshot({ path: path.join(artifacts, 'failure.png') }).catch(() => {});
      await writeFile(
        path.join(artifacts, 'failure.txt'),
        await pages[0].locator('body').innerText(),
      ).catch(() => {});
    }
  }
  throw error;
} finally {
  if (app) await app.close();
  provider.closeAllConnections();
  await new Promise((resolve) => provider.close(resolve));
}
