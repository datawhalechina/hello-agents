/** Isolated native-window test. Never attaches to or quits the user's running client. */
import { _electron as electron } from 'playwright';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { chooseCustomProvider } from './provider-settings-helpers.mjs';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { PNG } from 'pngjs';
import { runInNewContext } from 'node:vm';
import { assertMascotMotion } from './mascot-motion-checks.mjs';
import { assertClientTransitions } from './client-transition-checks.mjs';

const runFile = promisify(execFile);
const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(desktop);
const artifacts = path.join(root, '.test-artifacts', `bubble-${Date.now()}`);
const profile = path.join(artifacts, 'profile');
const workspace = path.join(artifacts, 'bubble-workspace');
const positionFile = path.join(profile, 'bubble-position.json');
const mainTitle = 'CodeAssistantAgent · 代码助手';
const bubbleTitle = 'CodeAssistantAgent · 菲比桌面助手';
const checks = [];
const errors = [];
const nativeExits = [];
let nativeStderr = '';
let application;
let mainPage;
let bubblePage;

await mkdir(profile, { recursive: true });
await mkdir(workspace, { recursive: true });
await writeFile(path.join(workspace, 'notes.md'), '# Floating launcher integration test\n');
// A disconnected monitor's saved position must never make the launcher inaccessible.
await writeFile(positionFile, JSON.stringify({ x: 1000000, y: 1000000 }));

const env = {
  ...process.env,
  CODE_ASSISTANT_HIDDEN: '1',
  CODE_ASSISTANT_ALLOW_MULTIPLE: '1',
  CODE_ASSISTANT_DISABLE_KEYRING: '1',
  CODE_ASSISTANT_DATA_DIR: path.join(artifacts, 'service'),
  CODE_ASSISTANT_USER_DATA_DIR: profile,
  LLM_API_KEY: '',
  LLM_BASE_URL: '',
  LLM_MODEL_ID: '',
  OPENAI_API_KEY: '',
};
delete env.ELECTRON_RUN_AS_NODE;
delete env.CODE_ASSISTANT_DEV_URL;
delete env.PYTHONHOME;
delete env.PYTHONPATH;

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function eventually(operation, message, timeout = 15000) {
  const deadline = Date.now() + timeout;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const result = await operation();
      if (result) return result;
    } catch (error) {
      lastError = error;
    }
    await pause(80);
  }
  throw new Error(`${message}${lastError ? `: ${lastError.message}` : ''}`);
}

async function nativeState() {
  return application.evaluate(
    ({ BrowserWindow, screen }, titles) => {
      const windows = BrowserWindow.getAllWindows();
      const main = windows.find((window) => window.getTitle() === titles.main);
      const bubble = windows.find((window) => window.getTitle() === titles.bubble);
      if (!main || !bubble) return null;
      const bounds = bubble.getBounds();
      return {
        mainId: main.webContents.id,
        mainVisible: main.isVisible(),
        mainMinimized: main.isMinimized(),
        mainOpacity: main.getOpacity(),
        mainZoom: main.webContents.getZoomFactor(),
        mainBounds: main.getBounds(),
        bubbleVisible: bubble.isVisible(),
        bubbleOpacity: bubble.getOpacity(),
        bubbleZoom: bubble.webContents.getZoomFactor(),
        bubbleBounds: bounds,
        workArea: screen.getDisplayMatching(bounds).workArea,
        alwaysOnTop: bubble.isAlwaysOnTop(),
        resizable: bubble.isResizable(),
        background: bubble.getBackgroundColor(),
        webPreferences: bubble.webContents.getLastWebPreferences(),
      };
    },
    { main: mainTitle, bubble: bubbleTitle },
  );
}

function assertWithinWorkArea(state) {
  const box = state.bubbleBounds;
  const area = state.workArea;
  const marginX = area.width >= box.width + 16 ? 8 : 0;
  const marginY = area.height >= box.height + 16 ? 8 : 0;
  assert.ok(box.x >= area.x + marginX, 'launcher left edge is visible');
  assert.ok(box.y >= area.y + marginY, 'launcher top edge is visible');
  assert.ok(
    box.x + box.width <= area.x + area.width - marginX,
    `launcher right edge is visible: ${JSON.stringify({ box, area })}`,
  );
  assert.ok(
    box.y + box.height <= area.y + area.height - marginY,
    `launcher bottom edge is visible: ${JSON.stringify({ box, area })}`,
  );
}

function assertClientBesideBubble(state) {
  const client = state.mainBounds;
  const bubble = state.bubbleBounds;
  const work = state.workArea;
  const tolerance = 3;
  assert.ok(client.x >= work.x - tolerance && client.y >= work.y - tolerance &&
    client.x + client.width <= work.x + work.width + tolerance &&
    client.y + client.height <= work.y + work.height + tolerance,
    'the client stays inside the mascot display work area');
  assert.ok(client.x >= bubble.x + bubble.width + 12 - tolerance ||
    client.x + client.width <= bubble.x - 12 + tolerance ||
    client.y >= bubble.y + bubble.height + 12 - tolerance ||
    client.y + client.height <= bubble.y - 12 + tolerance,
    'the client opens beside the mascot without covering it');
}

// Walk the actual GIF container instead of trusting its extension or a frame-count comment.
// This also rejects truncated sub-blocks and image rectangles outside the logical canvas.
function inspectGif(bytes) {
  assert.ok(bytes.length >= 14, 'GIF has a complete header');
  assert.match(bytes.toString('ascii', 0, 6), /^GIF8[79]a$/);
  const width = bytes.readUInt16LE(6);
  const height = bytes.readUInt16LE(8);
  assert.ok(width > 0 && height > 0, 'GIF has a nonempty logical canvas');
  let offset = 13;
  const headerFlags = bytes[10];
  if (headerFlags & 0x80) offset += 3 * (1 << ((headerFlags & 7) + 1));
  const delays = [];
  const transparent = [];
  let pendingDelay = 0;
  let pendingTransparency = false;
  let repeat = null;
  let ended = false;
  const requireBytes = (length) => {
    assert.ok(offset + length <= bytes.length, 'GIF block is not truncated');
  };
  const readSubBlocks = () => {
    const blocks = [];
    while (true) {
      requireBytes(1);
      const size = bytes[offset++];
      if (size === 0) return blocks;
      requireBytes(size);
      blocks.push(bytes.subarray(offset, offset + size));
      offset += size;
    }
  };
  while (offset < bytes.length) {
    requireBytes(1);
    const marker = bytes[offset++];
    if (marker === 0x3b) {
      ended = true;
      break;
    }
    if (marker === 0x21) {
      requireBytes(1);
      const label = bytes[offset++];
      if (label === 0xf9) {
        requireBytes(6);
        assert.equal(bytes[offset], 4, 'GIF graphic-control extension has the correct size');
        pendingTransparency = !!(bytes[offset + 1] & 1);
        pendingDelay = bytes.readUInt16LE(offset + 2) * 10;
        assert.equal(bytes[offset + 5], 0, 'GIF graphic-control extension terminates');
        offset += 6;
      } else {
        const blocks = readSubBlocks();
        if (label === 0xff && /^(?:NETSCAPE2\.0|ANIMEXTS1\.0)$/.test(blocks[0]?.toString('ascii'))) {
          assert.ok(blocks[1]?.length >= 3 && blocks[1][0] === 1, 'GIF loop extension is valid');
          repeat = blocks[1].readUInt16LE(1);
        }
      }
      continue;
    }
    assert.equal(marker, 0x2c, 'GIF contains only valid extension, image, or trailer blocks');
    requireBytes(9);
    const x = bytes.readUInt16LE(offset);
    const y = bytes.readUInt16LE(offset + 2);
    const frameWidth = bytes.readUInt16LE(offset + 4);
    const frameHeight = bytes.readUInt16LE(offset + 6);
    const imageFlags = bytes[offset + 8];
    assert.ok(frameWidth > 0 && frameHeight > 0, 'each GIF frame has visible dimensions');
    assert.ok(x + frameWidth <= width && y + frameHeight <= height, 'GIF frames fit the canvas');
    offset += 9;
    if (imageFlags & 0x80) offset += 3 * (1 << ((imageFlags & 7) + 1));
    requireBytes(1);
    const lzwMinimumCodeSize = bytes[offset++];
    assert.ok(lzwMinimumCodeSize >= 2 && lzwMinimumCodeSize <= 8, 'GIF uses a valid LZW code size');
    readSubBlocks();
    delays.push(pendingDelay);
    transparent.push(pendingTransparency);
    pendingDelay = 0;
    pendingTransparency = false;
  }
  assert.ok(ended, 'GIF has its trailer');
  assert.ok(delays.length > 1, 'artwork is a real multi-frame GIF');
  assert.ok(
    delays.every((delay) => delay > 0),
    'animation frames have explicit nonzero delays',
  );
  assert.ok(transparent.every(Boolean), 'each animated frame preserves the transparent desktop');
  return {
    width,
    height,
    frames: delays.length,
    duration: delays.reduce((sum, delay) => sum + delay, 0),
    repeat,
  };
}

async function inspectMascotAssets() {
  const assetDirectory = path.join(desktop, 'electron', 'assets');
  const hover = inspectGif(await readFile(path.join(assetDirectory, 'phoebe-hover.gif')));
  const click = inspectGif(await readFile(path.join(assetDirectory, 'phoebe-click.gif')));
  const manifest = JSON.parse(await readFile(path.join(assetDirectory, 'phoebe-animation.json'), 'utf8'));
  assert.ok(manifest.hover.durationMs > 0, 'manifest documents the hover preview duration');
  assert.ok(manifest.click.durationMs > 0, 'manifest documents the click feedback duration');
  assert.equal(hover.duration, manifest.hover.durationMs, 'hover GIF timing matches its manifest');
  assert.equal(click.duration, manifest.click.durationMs, 'click GIF timing matches its manifest');
  assert.equal(hover.frames, manifest.hover.frameCount, 'manifest matches the hover frame count');
  assert.equal(click.frames, manifest.click.frameCount, 'manifest matches the click frame count');
  assert.equal(manifest.hover.loop, true);
  assert.equal(manifest.click.loop, false);
  assert.equal(hover.repeat, 0, 'hover GIF explicitly repeats indefinitely');
  assert.equal(click.repeat, null, 'click GIF has no loop extension and plays only once');
  assert.equal(click.width, hover.width, 'click and hover canvases have the same width');
  assert.equal(click.height, hover.height, 'click and hover canvases have the same height');
  const stills = [];
  for (const file of ['phoebe-idle.png', 'phoebe-hover-still.png', 'phoebe-click-still.png']) {
    const decoded = PNG.sync.read(await readFile(path.join(assetDirectory, file)));
    assert.equal(decoded.width, hover.width, `${file} uses the same animation canvas width`);
    assert.equal(decoded.height, hover.height, `${file} uses the same animation canvas height`);
    const alphas = decoded.data.filter((_, index) => index % 4 === 3);
    assert.ok(
      alphas.some((alpha) => alpha === 0),
      `${file} has a transparent background`,
    );
    assert.ok(
      alphas.some((alpha) => alpha > 0),
      `${file} includes visible character pixels`,
    );
    stills.push(decoded.data);
  }
  assert.ok(!stills[0].equals(stills[1]), 'hover is a different character pose from idle');
  assert.ok(!stills[0].equals(stills[2]), 'click is a different character pose from idle');
  assert.ok(!stills[1].equals(stills[2]), 'click is a different character pose from hover');
  const sandbox = { window: {} };
  runInNewContext(await readFile(path.join(assetDirectory, manifest.runtime.metadata), 'utf8'), sandbox);
  const metadata = sandbox.window.PHOEBE_POSES;
  const atlas = PNG.sync.read(await readFile(path.join(assetDirectory, manifest.runtime.atlas)));
  assert.equal(metadata.poses.length, manifest.runtime.poseIds.length, 'all registered runtime poses are present');
  assert.equal(metadata.clickDurationMs, manifest.clickDurationMs, 'runtime and preview agree on gesture duration');
  const groundLevels = [];
  for (const [index, pose] of metadata.poses.entries()) {
    assert.equal(pose.id, manifest.runtime.poseIds[index], 'atlas pose order matches its runtime manifest');
    const [left, top, width, height] = pose.rect;
    assert.ok(left >= 0 && top >= 0 && left + width <= atlas.width && top + height <= atlas.height,
      `${pose.id} fits inside the decoded atlas`);
    let visible = 0; let transparent = 0; let bottom = -1;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      const alpha = atlas.data[((top + y) * atlas.width + left + x) * 4 + 3];
      if (!alpha) transparent++;
      if (alpha >= 32) { visible++; bottom = Math.max(bottom, y); }
    }
    assert.ok(visible > 1200 && transparent > 1200, `${pose.id} has visible art and a transparent desktop`);
    groundLevels.push(bottom);
  }
  assert.ok(Math.max(...groundLevels) - Math.min(...groundLevels) <= 3,
    'normalized poses share a visible foot baseline before runtime deformation');
  checks.push(
    `registered ${metadata.poses.length}-pose transparent runtime atlas; valid hover and click GIF previews`,
  );
  return { hover, click, hoverDurationMs: manifest.hover.durationMs, clickDurationMs: manifest.click.durationMs };
}

async function assertMascotInteractions(animation) {
  // CDP pointer input does not drive the physical system cursor. Hold it steady
  // during pose checks; native dragging is exercised separately below.
  await application.evaluate(({ screen }) => {
    global.__mascotSmokePhysicalCursor = screen.getCursorScreenPoint;
    const cursor = screen.getCursorScreenPoint();
    screen.getCursorScreenPoint = () => cursor;
  });
  try {
    await assertMascotMotion({
      bubblePage, application, nativeState, bubbleTitle, artifacts, checks, pause, eventually, animation,
    });
  } finally {
    await application.evaluate(({ screen }) => {
      screen.getCursorScreenPoint = global.__mascotSmokePhysicalCursor;
      delete global.__mascotSmokePhysicalCursor;
    });
  }
}

async function launch() {
  application = await electron.launch({ args: [desktop], cwd: desktop, env, timeout: 60000 });
  const child = application.process();
  child.once('exit', (code, signal) => nativeExits.push({ pid: child.pid, code, signal, at: Date.now() }));
  child.stderr?.on('data', (chunk) => { nativeStderr = (nativeStderr + chunk.toString()).slice(-65536); });
  await application.evaluate(({ app, BrowserWindow, Menu }, logFile) => {
    const fs = process.getBuiltinModule('node:fs');
    const record = (kind, details = {}) => fs.appendFileSync(logFile,
      `${JSON.stringify({ at: Date.now(), kind, ...details, stack: new Error().stack })}\n`);
    // QA uses real menu templates and callbacks below, but never presents a second
    // identical native menu over the user's production bubble on the shared desktop.
    Menu.prototype.popup = function () {
      record('native-menu-presentation-suppressed', { labels: this.items.map((item) => item.label) });
    };
    for (const method of ['quit', 'exit']) {
      const original = app[method];
      app[method] = function (...args) {
        record(`app.${method}`, { args });
        return Reflect.apply(original, this, args);
      };
    }
    for (const method of ['close', 'destroy']) {
      const original = BrowserWindow.prototype[method];
      BrowserWindow.prototype[method] = function (...args) {
        record(`window.${method}`, { title: this.getTitle(), id: this.id });
        return Reflect.apply(original, this, args);
      };
    }
    app.on('before-quit', () => record('before-quit'));
    const isolated = new WeakSet();
    const isolateWindow = (window) => {
      if (isolated.has(window)) return;
      isolated.add(window);
      // Keep native visibility/focus/drag behavior observable to CDP without
      // displaying QA windows or intercepting the user's physical pointer.
      window.setOpacity(0);
      window.setIgnoreMouseEvents(true);
      window.on('close', () => record('window-close-event', { id: window.id, title: window.getTitle() }));
    };
    app.on('browser-window-created', (_event, window) => isolateWindow(window));
    for (const window of BrowserWindow.getAllWindows()) isolateWindow(window);
  }, path.join(artifacts, 'native-lifecycle.jsonl'));
  await eventually(
    async () => {
      const pages = application.windows();
      for (const page of pages) {
        const title = await page.title();
        if (title === mainTitle) mainPage = page;
        if (title === bubbleTitle) bubblePage = page;
      }
      return mainPage && bubblePage;
    },
    'Both renderer windows must be created',
    60000,
  );
  for (const page of [mainPage, bubblePage]) {
    page.setDefaultTimeout(20000);
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (entry) => {
      if (entry.type() === 'error') errors.push(entry.text());
    });
  }
  await mainPage.waitForFunction(() => !!window.codeAssistant);
  await mainPage.locator('.project-drop:not(:disabled)').waitFor();
  await bubblePage.waitForFunction(() => !!window.assistantBubble);
  await bubblePage.getByRole('button').first().waitFor({ state: 'attached' });
  return eventually(nativeState, 'Native windows must be available');
}

async function showBubble() {
  await application.evaluate(({ BrowserWindow }, title) => {
    BrowserWindow.getAllWindows()
      .find((window) => window.getTitle() === title)
      .show();
  }, bubbleTitle);
}

async function clickBubble() {
  // CDP dispatches renderer input directly. With physical mouse passthrough enabled,
  // explicitly perform the native activation that a real pointer press would cause.
  await application.evaluate(({ BrowserWindow }, title) => {
    BrowserWindow.getAllWindows().find((window) => window.getTitle() === title).focus();
  }, bubbleTitle);
  await eventually(() => application.evaluate(({ BrowserWindow }, title) =>
    BrowserWindow.getAllWindows().find((window) => window.getTitle() === title).isFocused(),
  bubbleTitle), 'The native bubble must be active before a synthetic pointer tap');
  await bubblePage.evaluate(() => new Promise((resolve) =>
    requestAnimationFrame(() => requestAnimationFrame(resolve))));
  // A synthetic tap does not move the OS cursor. Freeze it for this tap so a user's
  // concurrent physical mouse movement cannot turn the test click into a native drag.
  await application.evaluate(({ screen }) => {
    global.__tapRealCursor = screen.getCursorScreenPoint;
    const point = screen.getCursorScreenPoint();
    screen.getCursorScreenPoint = () => ({ ...point });
  });
  try {
    await bubblePage.getByRole('button').first().click();
  } finally {
    await application.evaluate(({ screen }) => {
      screen.getCursorScreenPoint = global.__tapRealCursor;
      delete global.__tapRealCursor;
    });
  }
}

async function ownBackend() {
  const parent = application.process().pid;
  let children;
  if (process.platform === 'win32') {
    const { stdout } = await runFile(
      'powershell.exe',
      [
        '-NoProfile',
        '-NonInteractive',
        '-Command',
        'Get-CimInstance Win32_Process -Filter "Name LIKE \'python%\'" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress',
      ],
      { windowsHide: true, maxBuffer: 1024 * 1024 },
    );
    const value = JSON.parse(stdout.trim() || '[]');
    children = (Array.isArray(value) ? value : [value]).map((entry) => ({
      pid: entry.ProcessId,
      command: entry.CommandLine || '',
    }));
  } else {
    const { stdout } = await runFile('ps', ['-Ao', 'pid=,ppid=,args=']);
    children = stdout.split('\n').flatMap((line) => {
      const match = line.trim().match(/^(\d+)\s+(\d+)\s+(.*)$/);
      return match && Number(match[2]) === parent
        ? [{ pid: Number(match[1]), command: match[3] }]
        : [];
    });
  }
  const child = children.find((entry) => {
    const command = entry.command.replaceAll('"', '');
    return (
      /(?:^|\s)-m\s+backend(?:\s|$)/.test(command) &&
      command.toLowerCase().includes(env.CODE_ASSISTANT_DATA_DIR.toLowerCase())
    );
  });
  assert.ok(child, 'the test owns a separate Python sidecar');
  const port = Number(child.command.replaceAll('"', '').match(/--port\s+(\d+)/)?.[1]);
  assert.ok(port > 0, 'sidecar port is discoverable without exposing its credential');
  return { pid: child.pid, endpoint: `http://127.0.0.1:${port}` };
}

async function openModelFromMenu() {
  await application.evaluate(({ Menu }) => {
    global.__settingsMenuPopup = Menu.prototype.popup;
    global.__settingsMenu = null;
    Menu.prototype.popup = function () { global.__settingsMenu = this; };
  });
  try {
    await bubblePage.getByRole('button').first().dispatchEvent('contextmenu');
    await eventually(() => application.evaluate(() => !!global.__settingsMenu),
      'Right-clicking Phoebe creates the native menu');
    const item = await application.evaluate(() => {
      const entry = global.__settingsMenu.items.find((item) => item.label === '配置模型');
      return entry ? { enabled: entry.enabled } : null;
    });
    assert.ok(item?.enabled, 'the native menu provides the model configuration action');
    await application.evaluate(() => {
      const item = global.__settingsMenu.items.find((item) => item.label === '配置模型');
      item.click(item, null, {});
    });
  } finally {
    await application.evaluate(({ Menu }) => {
      Menu.prototype.popup = global.__settingsMenuPopup;
      delete global.__settingsMenuPopup;
      delete global.__settingsMenu;
    });
  }
  await mainPage.getByRole('dialog', { name: '模型设置', exact: true }).waitFor();
}

async function assertModelConfigurationMenu() {
  const before = await nativeState();
  assert.equal(before.mainVisible, false);
  assert.equal(await mainPage.locator('.selected-project').count(), 0);
  await openModelFromMenu();
  await eventually(async () => (await nativeState()).mainVisible,
    'model configuration reveals the hidden client');
  assert.equal((await nativeState()).mainId, before.mainId);
  await chooseCustomProvider(mainPage, 'http://127.0.0.1:12345/v1');
  await mainPage.locator('input[name="model"]').fill('bubble-menu-model');
  await mainPage.getByRole('button', { name: '保存连接', exact: true }).click();
  await mainPage.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  assert.equal(await mainPage.evaluate(async () => (await window.codeAssistant.bootstrap()).settings.model),
    'bubble-menu-model');
  await mainPage.evaluate(() => window.codeAssistant.windowControl('minimize'));
  await eventually(async () => (await nativeState()).mainMinimized, 'client minimizes before menu restoration');
  await openModelFromMenu();
  await eventually(async () => !(await nativeState()).mainMinimized, 'model menu restores a minimized client');
  assert.equal(await mainPage.locator('input[name="model"]').inputValue(), 'bubble-menu-model');
  await mainPage.locator('input[name="model"]').fill('unsaved-menu-draft');
  const reopened = await nativeState();
  await openModelFromMenu();
  assert.equal(await mainPage.locator('.settings-dialog').count(), 1);
  assert.equal(await mainPage.locator('input[name="model"]').inputValue(), 'unsaved-menu-draft');
  assert.deepEqual((await nativeState()).mainBounds, reopened.mainBounds,
    'repeated menu selection preserves the visible client position');
  await mainPage.getByRole('button', { name: '取消', exact: true }).click();
  assert.equal(await mainPage.evaluate(async () => (await window.codeAssistant.bootstrap()).settings.model),
    'bubble-menu-model', 'cancel does not save the draft');
  await mainPage.evaluate(() => window.codeAssistant.windowControl('close'));
  await eventually(async () => !(await nativeState()).mainVisible, 'menu checks leave the client hidden');
  checks.push('Phoebe model menu opens settings without a project, saves shared configuration, restores minimized client and preserves repeated-open drafts');
}

async function assertBackendStopped(sidecar) {
  await eventually(
    async () => {
      try {
        const response = await fetch(`${sidecar.endpoint}/health`, {
          signal: AbortSignal.timeout(400),
        });
        if (response.ok) return false;
      } catch {
        /* The owned service has stopped listening. */
      }
      try {
        process.kill(sidecar.pid, 0);
        return false;
      } catch {
        return true;
      }
    },
    'Exiting must stop the owned Python sidecar',
    20000,
  );
}

async function closeThroughMenu() {
  // Intercept presentation only: still exercise the real renderer IPC and native menu callbacks.
  await application.evaluate(({ Menu }) => {
    global.__bubbleSmokePopup = Menu.prototype.popup;
    Menu.prototype.popup = function () {
      global.__bubbleSmokeMenu = this;
    };
  });
  await bubblePage.evaluate(() => window.assistantBubble.menu());
  await eventually(
    () => application.evaluate(() => !!global.__bubbleSmokeMenu),
    'Launcher menu must open',
  );
  const labels = await application.evaluate(() =>
    global.__bubbleSmokeMenu.items.map((item) => item.label),
  );
  assert.ok(
    labels.some((label) => /退出/.test(label)),
    'native menu includes exit',
  );
  const closed = application.waitForEvent('close', { timeout: 30000 });
  await application
    .evaluate(() => {
      const menu = global.__bubbleSmokeMenu;
      const exit = menu.items.find((item) => /退出/.test(item.label));
      exit.click(exit, null, {});
    })
    .catch((error) => {
      if (!/closed|destroyed/i.test(error.message)) throw error;
    });
  await closed;
  application = null;
}

async function inspectClientPlacement() {
  const controller = { exports: {} };
  runInNewContext(await readFile(path.join(desktop, 'electron/bubble-controller.cjs'), 'utf8'), {
    module: controller,
    require: () => ({}),
  });
  const client = { width: 650, height: 500 };
  const work = { x: 0, y: 0, width: 1536, height: 824 };
  const cases = [
    { name: 'preferred bottom-right mascot', work,
      anchor: { x: 800, y: 600, width: 96, height: 96 }, side: 'left', bottomAligned: true },
    { name: 'right edge', work, anchor: { x: 1416, y: 350, width: 96, height: 96 }, side: 'left' },
    { name: 'left edge', work, anchor: { x: 24, y: 350, width: 96, height: 96 }, side: 'right' },
    { name: 'top edge', work, anchor: { x: 1416, y: 8, width: 96, height: 96 } },
    { name: 'bottom edge', work, anchor: { x: 1416, y: 720, width: 96, height: 96 },
      side: 'left', bottomAligned: true },
    { name: 'negative monitor coordinates', work: { x: -1280, y: 100, width: 1280, height: 800 },
      anchor: { x: -1256, y: 300, width: 96, height: 96 }, side: 'right' },
    { name: 'monitor above primary', work: { x: 0, y: -900, width: 1600, height: 900 },
      anchor: { x: 1450, y: -120, width: 96, height: 96 } },
    { name: 'vertical fallback', work: { x: 0, y: 0, width: 1000, height: 900 },
      anchor: { x: 450, y: 12, width: 96, height: 96 }, side: 'below' },
  ];
  for (const fixture of cases) {
    const position = controller.exports.getClientPosition(fixture.anchor, client, fixture.work);
    const bounds = { ...position, ...client };
    assertClientBesideBubble({ mainBounds: bounds, bubbleBounds: fixture.anchor, workArea: fixture.work });
    assert.ok(bounds.x >= fixture.work.x + 8 && bounds.y >= fixture.work.y + 8 &&
      bounds.x + bounds.width <= fixture.work.x + fixture.work.width - 8 &&
      bounds.y + bounds.height <= fixture.work.y + fixture.work.height - 8,
      `${fixture.name}: keep clear of work-area edges`);
    if (fixture.side === 'left') assert.ok(bounds.x + bounds.width < fixture.anchor.x);
    if (fixture.side === 'right') assert.ok(bounds.x > fixture.anchor.x + fixture.anchor.width);
    if (fixture.side === 'below') assert.ok(bounds.y > fixture.anchor.y + fixture.anchor.height);
    if (fixture.bottomAligned) assert.equal(bounds.y + bounds.height,
      fixture.anchor.y + fixture.anchor.height, `${fixture.name}: align the two bottom edges`);
  }
  checks.push('client placement covers all edges, negative monitor coordinates, and vertical fallback');
}

async function assertNativeClientTransition() {
  // Insufficient space above must still leave Phoebe beside the client's bottom edge.
  await application.evaluate(({ BrowserWindow, screen }, title) => {
    const bubble = BrowserWindow.getAllWindows().find((entry) => entry.getTitle() === title);
    const work = screen.getDisplayMatching(bubble.getBounds()).workArea;
    bubble.setPosition(work.x + work.width - 120, work.y + 8, false);
  }, bubbleTitle);
  await application.evaluate(({ BrowserWindow, systemPreferences }, title) => {
    const window = BrowserWindow.getAllWindows().find((entry) => entry.getTitle() === title);
    const settings = systemPreferences.getAnimationSettings.bind(systemPreferences);
    global.__clientTransitionAnimationSettings = settings;
    systemPreferences.getAnimationSettings = () => ({ ...settings(), prefersReducedMotion: false });
    global.__clientTransitionFrames = [];
    for (const name of ['setOpacity', 'setPosition', 'show', 'hide']) {
      const original = window[name].bind(window);
      window[name] = (...args) => {
        const value = original(...args);
        global.__clientTransitionFrames.push({
          at: performance.now(), method: name, bounds: window.getBounds(), opacity: window.getOpacity(),
        });
        return value;
      };
    }
  }, mainTitle);
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await bubblePage.waitForFunction(() => document.getElementById('bubble').getAttribute('aria-expanded') === 'true');
  await pause(600);
  const opened = await nativeState();
  assert.equal(opened.mainVisible, true);
  assert.equal(opened.mainOpacity, 0, 'animation respects the invisible native QA window');
  assertClientBesideBubble(opened);
  assert.ok(opened.mainBounds.x + opened.mainBounds.width < opened.bubbleBounds.x,
    'the mascot defaults to the right of the client');
  assert.equal(opened.mainBounds.y + opened.mainBounds.height,
    opened.bubbleBounds.y + opened.bubbleBounds.height,
    'opening near the top edge adjusts the mascot to the client bottom');
  checks.push('click opens the client above-left with Phoebe bottom-aligned, even near the screen top');
  const frames = await application.evaluate(() => global.__clientTransitionFrames);
  await writeFile(path.join(artifacts, 'client-transition-frames.json'), JSON.stringify(frames, null, 2));
  const moved = frames.filter((frame) => frame.method === 'setPosition');
  assert.equal(moved.length, 1, 'native position is set once before show, with no movement during the fade');
  assert.ok(frames.indexOf(moved[0]) < frames.findIndex((frame) => frame.method === 'show'),
    'the client docks beside the mascot before it becomes visible');
  const opacityFrames = frames.filter((frame) => frame.method === 'setOpacity');
  assert.ok(opacityFrames.length >= 8, 'the native fade spans multiple opacity updates');
  assert.ok(opacityFrames.at(-1).at - opacityFrames[0].at >= 450,
    'the native entrance reveals gradually over about half a second');
  const shown = frames.findIndex((frame) => frame.method === 'show');
  assert.ok(frames.slice(shown).filter((frame) => frame.method === 'setOpacity').every((frame) =>
    frame.bounds.x === frames[shown].bounds.x && frame.bounds.y === frames[shown].bounds.y),
    'the window stays fixed throughout the native fade');
  assert.ok(frames.slice(shown).every((frame) =>
    frame.bounds.width === frames[shown].bounds.width && frame.bounds.height === frames[shown].bounds.height),
    'native animation never resizes or reflows the client');
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await bubblePage.waitForFunction(() => document.getElementById('bubble').getAttribute('aria-expanded') === 'false');
  await eventually(async () => !(await nativeState()).mainVisible, 'fade-out eventually hides the native window');
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await pause(48);
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await pause(16);
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await pause(600);
  assert.equal((await nativeState()).mainVisible, true, 'rapid native reopen cannot be hidden by an old timer');
  assertClientBesideBubble(await nativeState());
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await eventually(async () => !(await nativeState()).mainVisible, 'transition checks leave the client hidden');
  await writeFile(path.join(artifacts, 'client-transition-frames.json'), JSON.stringify(frames, null, 2));
  checks.push('real native client fades gradually in place, retains size and opacity limits, and reverses on rapid clicks');
}

async function assertClientDragFollowing() {
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await pause(600);
  const before = await nativeState();
  assert.equal(before.mainVisible, true);
  const { mainBounds: client, bubbleBounds: anchor, workArea: work } = before;
  const clamp = (value, min, max) => Math.max(min, Math.min(value, max));
  const dx = clamp(-40, work.x + 8 - Math.min(client.x, anchor.x),
    work.x + work.width - 8 - Math.max(client.x + client.width, anchor.x + anchor.width));
  const dy = clamp(-32, work.y + 8 - Math.min(client.y, anchor.y),
    work.y + work.height - 8 - Math.max(client.y + client.height, anchor.y + anchor.height));
  await writeFile(path.join(artifacts, 'client-drag-start.json'), JSON.stringify({ before, dx, dy }, null, 2));
  assert.ok(Math.hypot(dx, dy) >= 6, 'the two-window group has room for a real drag');
  const opacityFrames = await application.evaluate(() =>
    global.__clientTransitionFrames.filter((frame) => frame.method === 'setOpacity').length);
  await application.evaluate(({ screen, BrowserWindow }, title) => {
    global.__followDragRealCursor = screen.getCursorScreenPoint;
    global.__followDragCursor = { x: 400, y: 400 };
    screen.getCursorScreenPoint = () => ({ ...global.__followDragCursor });
    BrowserWindow.getAllWindows().find((window) => window.getTitle() === title).focus();
  }, bubbleTitle);
  try {
    await eventually(() => application.evaluate(({ BrowserWindow }, title) =>
      BrowserWindow.getAllWindows().find((window) => window.getTitle() === title).isFocused(),
    bubbleTitle), 'The bubble receives focus before dragging the visible client');
    const button = bubblePage.locator('#bubble');
    const center = await button.boundingBox();
    const play = await button.getAttribute('data-play');
    await bubblePage.mouse.move(center.x + center.width / 2, center.y + center.height / 2);
    await bubblePage.mouse.down();
    await bubblePage.evaluate(() => window.assistantBubble.startDrag());
    await application.evaluate((_electron, { dx, dy }) => {
      global.__followDragCursor = { x: 400 + dx, y: 400 + dy };
    }, { dx, dy });
    await bubblePage.mouse.move(center.x + center.width / 2 + Math.sign(dx) * 12,
      center.y + center.height / 2 + Math.sign(dy) * 12, { steps: 3 });
    const moved = await eventually(async () => {
      const current = await nativeState();
      if (current.bubbleBounds.x === anchor.x && current.bubbleBounds.y === anchor.y) return false;
      assert.equal(current.mainBounds.x - client.x, current.bubbleBounds.x - anchor.x);
      assert.equal(current.mainBounds.y - client.y, current.bubbleBounds.y - anchor.y);
      return current;
    }, 'The visible client follows while the pointer is still held, with the same movement delta');
    assert.equal(moved.mainVisible, true);
    assert.equal(moved.mainId, before.mainId);
    assert.equal(moved.mainBounds.width, client.width);
    assert.equal(moved.mainBounds.height, client.height);
    assertClientBesideBubble(moved);
    await bubblePage.mouse.up();
    await eventually(() => button.getAttribute('data-pose').then((pose) => pose !== 'pressed'),
      'Releasing a linked drag releases pointer capture');
    assert.equal(await button.getAttribute('data-play'), play, 'linked dragging does not toggle or restart click feedback');
    assert.equal(await application.evaluate(() =>
      global.__clientTransitionFrames.filter((frame) => frame.method === 'setOpacity').length), opacityFrames,
    'linked dragging does not restart the fade animation');
    assert.equal(await mainPage.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
      'Keep this unsent draft while the client is tucked away.');
    checks.push('dragging the visible client and mascot preserves their offset, dimensions, renderer, draft, and opacity');

    await bubblePage.evaluate(() => window.assistantBubble.startDrag());
    await application.evaluate(() => { global.__followDragCursor = { x: -1000000, y: -1000000 }; });
    await bubblePage.evaluate(() => window.assistantBubble.moveDrag());
    assert.equal((await bubblePage.evaluate(() => window.assistantBubble.endDrag())).dragged, true);
    await eventually(async () => {
      const current = await nativeState();
      assertWithinWorkArea(current);
      assertClientBesideBubble(current);
      return true;
    }, 'A linked drag near a display edge keeps both windows visible without covering the mascot');
    assert.equal((await nativeState()).mainVisible, true);
    checks.push('linked dragging at display edges repositions the client inside the mascot display work area');
  } finally {
    await application.evaluate(({ screen }) => {
      screen.getCursorScreenPoint = global.__followDragRealCursor;
      delete global.__followDragRealCursor;
    });
  }
  await bubblePage.evaluate(() => window.assistantBubble.toggle());
  await eventually(async () => !(await nativeState()).mainVisible, 'Linked-drag checks finish with the client hidden');
}

try {
  await assertClientTransitions(desktop, checks);
  await inspectClientPlacement();
  const animation = await inspectMascotAssets();
  let state = await launch();
  const initialMainId = state.mainId;
  assert.equal(state.mainVisible, false, 'client starts hidden');
  assert.equal(state.bubbleVisible, false, 'QA hidden mode hides the bubble as well');
  assert.equal(state.mainOpacity, 0, 'the QA client never appears on the shared desktop');
  assert.equal(state.bubbleOpacity, 0, 'the QA launcher never appears on the shared desktop');
  assert.equal(state.mainZoom, 0.65625, 'the client keeps its compact scale');
  assert.equal(state.bubbleZoom, 1, 'the mascot retains its independent native scale');
  assert.equal(state.bubbleBounds.width, 96);
  assert.equal(state.bubbleBounds.height, 96);
  assert.equal(state.resizable, false);
  // getBackgroundColor() reports RGB without alpha on Windows.
  assert.match(state.background.toLowerCase(), /^#000000(?:00)?$/);
  assert.equal(state.webPreferences.contextIsolation, true);
  assert.equal(state.webPreferences.nodeIntegration, false);
  assert.equal(state.webPreferences.sandbox, true);
  assertWithinWorkArea(state);
  checks.push(
    'hidden startup; 96 DIP transparent, isolated, always-on-top launcher; stale position clamping',
  );
  const sidecar = await ownBackend();

  await showBubble();
  await eventually(async () => (await nativeState()).alwaysOnTop,
    'The visible native launcher must remain always on top');
  await assertNativeClientTransition();
  await assertMascotInteractions(animation);
  await assertModelConfigurationMenu();
  await clickBubble();
  await eventually(
    async () => (await nativeState()).mainVisible,
    'Clicking the bubble must open the client',
  );
  await eventually(async () => {
    assertClientBesideBubble(await nativeState());
    return true;
  }, 'The client must open beside Phoebe rather than at the desktop center');
  checks.push('native client opens beside Phoebe and stays within the same display work area');
  await application.evaluate(({ dialog }, folder) => {
    dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [folder] });
  }, workspace);
  await mainPage.getByRole('button', { name: '导入项目', exact: true }).click();
  await mainPage.locator('.selected-project').filter({ hasText: 'bubble-workspace' }).waitFor();
  await mainPage.locator('.home-action-comment').click();
  await mainPage.getByRole('dialog', { name: '代码注释', exact: true }).waitFor();
  assert.equal(await mainPage.locator('.workspace-layout, .editor-area, .sidebar, .assistant-panel, .monaco-editor').count(), 0);
  await mainPage.locator('.feature-dialog').getByRole('button', { name: '模型设置', exact: true }).click();
  await chooseCustomProvider(mainPage, 'http://127.0.0.1:12345/v1');
  await mainPage.locator('input[name="model"]').fill('bubble-state-test');
  await mainPage.getByRole('button', { name: '保存连接', exact: true }).click();
  await mainPage.getByRole('dialog', { name: '模型设置', exact: true }).waitFor({ state: 'hidden' });
  assert.equal(await mainPage.evaluate(async () => (await window.codeAssistant.bootstrap()).settings.model), 'bubble-state-test');
  assert.match(await mainPage.locator('.feature-dialog').getByRole('button', { name: '模型设置', exact: true }).innerText(), /bubble-state-test/);
  await mainPage
    .getByRole('textbox', { name: '任务需求', exact: true })
    .fill('Keep this unsent draft while the client is tucked away.');
  await openModelFromMenu();
  assert.equal(await mainPage.locator('input[name="model"]').inputValue(), 'bubble-state-test');
  await mainPage.getByRole('button', { name: '取消', exact: true }).click();
  assert.equal(await mainPage.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
    'Keep this unsent draft while the client is tucked away.');
  checks.push('model configuration from the native menu preserves the active project and task draft');
  await clickBubble();
  await eventually(
    async () => !(await nativeState()).mainVisible,
    'Second bubble click must hide the client',
  );
  await clickBubble();
  await eventually(
    async () => (await nativeState()).mainVisible,
    'Bubble must reopen the same client',
  );
  assert.equal((await nativeState()).mainId, initialMainId);
  await eventually(async () => { assertClientBesideBubble(await nativeState()); return true; },
    'Reopening settles beside the mascot after its transition');
  assert.equal(
    await mainPage.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
    'Keep this unsent draft while the client is tucked away.',
  );
  assert.match(await mainPage.locator('.selected-project').innerText(), /bubble-workspace/);
  assert.equal(await mainPage.evaluate(async () => (await window.codeAssistant.bootstrap()).settings.model), 'bubble-state-test');
  assert.match(await mainPage.locator('.feature-dialog').getByRole('button', { name: '模型设置', exact: true }).innerText(), /bubble-state-test/);
  assert.equal(await mainPage.locator('.workspace-layout, .editor-area, .sidebar, .assistant-panel, .monaco-editor').count(), 0);
  checks.push(
    'bubble clicks toggle the client while preserving project, model settings, and unsent draft',
  );

  await mainPage.getByRole('button', { name: '关闭窗口', exact: true }).click();
  state = await eventually(async () => {
    const current = await nativeState();
    return current.mainVisible ? false : current;
  }, 'The close button finishes the native fade-out');
  assert.equal(state.mainVisible, false);
  assert.equal(state.bubbleVisible, true);
  assert.equal(state.mainId, initialMainId, 'close hides rather than destroys the renderer');
  assert.equal((await fetch(`${sidecar.endpoint}/health`)).status, 200);
  await clickBubble();
  await eventually(
    async () => (await nativeState()).mainVisible,
    'Client must reopen after its close button',
  );
  assert.equal(
    await mainPage.getByRole('textbox', { name: '任务需求', exact: true }).inputValue(),
    'Keep this unsent draft while the client is tucked away.',
  );
  checks.push('client close hides its window and keeps the Python service and draft alive');

  // Playwright's synthetic pointer events do not move the OS cursor. Supply deterministic
  // screen coordinates while exercising the actual renderer pointer handlers and IPC.
  await application.evaluate(({ screen }) => {
    global.__bubbleSmokeRealCursor = screen.getCursorScreenPoint;
    global.__bubbleSmokeCursor = { x: 300, y: 300 };
    screen.getCursorScreenPoint = () => ({ ...global.__bubbleSmokeCursor });
  });
  await clickBubble();
  await eventually(
    async () => !(await nativeState()).mainVisible,
    'Client must be hidden before drag',
  );
  // Synthetic input does not activate a native window as a physical mouse press does.
  // Focus it explicitly and wait for activation before beginning a drag: otherwise a
  // delayed blur from hiding the client legitimately cancels the captured gesture.
  await application.evaluate(({ BrowserWindow }, title) => {
    BrowserWindow.getAllWindows()
      .find((window) => window.getTitle() === title)
      .focus();
  }, bubbleTitle);
  await eventually(
    () =>
      application.evaluate(
        ({ BrowserWindow }, title) =>
          BrowserWindow.getAllWindows()
            .find((window) => window.getTitle() === title)
            .isFocused(),
        bubbleTitle,
      ),
    'The native bubble must be active before synthetic dragging',
  );
  const beforeHiddenDrag = await nativeState();
  const beforeDrag = beforeHiddenDrag.bubbleBounds;
  const beforeDragPlay = await bubblePage.locator('#bubble').getAttribute('data-play');
  const center = await bubblePage.getByRole('button').first().boundingBox();
  assert.ok(center);
  await bubblePage.mouse.move(center.x + center.width / 2, center.y + center.height / 2);
  await bubblePage.evaluate(() => { window.__mascotTrace.length = 0; });
  await bubblePage.mouse.down();
  assert.equal(await bubblePage.locator('#bubble').getAttribute('data-pose'), 'pressed');
  // This invoke is an ordered IPC barrier after the renderer's pointerdown handler.
  await bubblePage.evaluate(() => window.assistantBubble.startDrag());
  await application.evaluate(() => {
    global.__bubbleSmokeCursor = { x: 240, y: 240 };
  });
  await bubblePage.mouse.move(center.x + center.width / 2 - 12, center.y + center.height / 2 - 12, {
    steps: 3,
  });
  await eventually(async () => {
    const moved = (await nativeState()).bubbleBounds;
    return moved.x !== beforeDrag.x || moved.y !== beforeDrag.y;
  }, 'Dragging must move the native bubble');
  const movedBounds = (await nativeState()).bubbleBounds;
  await application.evaluate(() => {
    global.__bubbleSmokeCursor = { x: 220, y: 220 };
  });
  await bubblePage.mouse.up();
  await eventually(async () => {
    const released = (await nativeState()).bubbleBounds;
    return released.x < movedBounds.x && released.y < movedBounds.y;
  }, 'Pointer release must sample the final native cursor position');
  state = await nativeState();
  assert.equal(state.mainVisible, false, 'releasing a drag must not also toggle the client');
  assert.deepEqual(state.mainBounds, beforeHiddenDrag.mainBounds,
    'dragging the mascot alone does not move the hidden client');
  await eventually(() => bubblePage.locator('#bubble').getAttribute('data-pose').then((pose) => pose !== 'pressed'),
    'Releasing a drag restores the character pose');
  assert.equal(await bubblePage.locator('#bubble').getAttribute('data-play'), beforeDragPlay,
    'dragging never accepts a new click feedback gesture');
  assert.ok((await bubblePage.evaluate(() => window.__mascotTrace)).every((entry) => entry.play === beforeDragPlay),
    'releasing a drag can continue prior feedback but never starts a new playback');
  assertWithinWorkArea(state);
  await eventually(async () => {
    const saved = JSON.parse(await readFile(positionFile, 'utf8'));
    return saved.x === state.bubbleBounds.x && saved.y === state.bubbleBounds.y;
  }, 'Drag position must be persisted');
  await application.evaluate(({ screen }) => {
    screen.getCursorScreenPoint = global.__bubbleSmokeRealCursor;
  });
  checks.push(
    'renderer drag moves the native window, persists coordinates, and suppresses accidental toggle',
  );
  await assertClientDragFollowing();

  await application.evaluate(({ BrowserWindow }, title) => {
    BrowserWindow.getAllWindows()
      .find((window) => window.getTitle() === title)
      .setPosition(1000000, 1000000);
  }, bubbleTitle);
  // Windows applies native position changes asynchronously. Model a later display event.
  await pause(150);
  await application.evaluate(({ screen }) => {
    screen.emit('display-metrics-changed', {}, screen.getPrimaryDisplay(), ['workArea']);
  });
  state = await eventually(async () => {
    const current = await nativeState();
    assertWithinWorkArea(current);
    assert.equal(
      current.bubbleBounds.width,
      96,
      'DPI changes must preserve the 96 DIP launcher width',
    );
    assert.equal(
      current.bubbleBounds.height,
      96,
      'DPI changes must preserve the 96 DIP launcher height',
    );
    return current;
  }, 'Display changes must clamp the launcher');
  assertWithinWorkArea(state);
  const remembered = { x: state.bubbleBounds.x, y: state.bubbleBounds.y };
  await bubblePage.screenshot({ path: path.join(artifacts, 'bubble.png'), omitBackground: true });
  checks.push('display change reclamps the full bubble within the work area');

  await closeThroughMenu();
  await assertBackendStopped(sidecar);
  checks.push('native menu exit shuts down the application and its owned Python sidecar');
  mainPage = null;
  bubblePage = null;
  state = await launch();
  assert.deepEqual({ x: state.bubbleBounds.x, y: state.bubbleBounds.y }, remembered);
  const restartedSidecar = await ownBackend();
  await showBubble();
  await clickBubble();
  await mainPage.locator('.home-action-comment').click();
  await mainPage.getByRole('dialog', { name: '代码注释', exact: true }).waitFor();
  assert.match(await mainPage.locator('.selected-project').innerText(), /bubble-workspace/);
  assert.equal(await mainPage.evaluate(async () => (await window.codeAssistant.bootstrap()).settings.model), 'bubble-state-test');
  assert.match(await mainPage.locator('.feature-dialog').getByRole('button', { name: '模型设置', exact: true }).innerText(), /bubble-state-test/);
  assert.equal(await mainPage.locator('.workspace-layout, .editor-area, .sidebar, .assistant-panel, .monaco-editor').count(), 0);
  await application.close();
  application = null;
  await assertBackendStopped(restartedSidecar);
  checks.push('restart restores the remembered bubble position, project, and model settings');
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(artifacts, 'result.json'),
    JSON.stringify({ status: 'passed', checks, errors, nativeExits }, null, 2),
  );
  console.log(`Bubble smoke passed. Artifacts: ${artifacts}`);
} catch (error) {
  const failedNativeState = await nativeState().catch(() => null);
  await writeFile(path.join(artifacts, 'native-failure-state.json'), JSON.stringify(failedNativeState, null, 2)).catch(() => {});
  await writeFile(path.join(artifacts, 'electron-stderr.log'), nativeStderr).catch(() => {});
  if (bubblePage && !bubblePage.isClosed()) {
    await writeFile(path.join(artifacts, 'mascot-failure-state.json'), JSON.stringify(
      await bubblePage.evaluate(() => ({
        snapshot: window.__mascotMotion?.snapshot(),
        trace: window.__mascotTrace,
        samples: window.__mascotSamples,
        attributes: { ...document.getElementById('bubble').dataset },
      })), null, 2,
    )).catch(() => {});
  }
  for (const [name, page] of [
    ['client', mainPage],
    ['bubble', bubblePage],
  ]) {
    if (page && !page.isClosed()) {
      await page.screenshot({ path: path.join(artifacts, `${name}-failure.png`) }).catch(() => {});
      await writeFile(
        path.join(artifacts, `${name}-failure.txt`),
        await page.locator('body').innerText(),
      ).catch(() => {});
    }
  }
  await writeFile(
    path.join(artifacts, 'result.json'),
    JSON.stringify(
      { status: 'failed', checks, errors, nativeExits, error: error.stack || String(error) },
      null,
      2,
    ),
  );
  throw error;
} finally {
  if (application) await application.close().catch(() => {});
}
