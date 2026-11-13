const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { randomBytes } = require('node:crypto');
const { spawn, execFile } = require('node:child_process');
const { existsSync } = require('node:fs');
const { stat } = require('node:fs/promises');
const net = require('node:net');
const path = require('node:path');
const { createBubble } = require('./bubble-controller.cjs');

const root = path.resolve(__dirname, '../..');
const token = randomBytes(24).toString('hex');
let backend,
  endpoint,
  window,
  launcher,
  stopping = false;
let openWhenReady = false;
const subscriptions = new Map();
if (process.env.CODE_ASSISTANT_USER_DATA_DIR)
  app.setPath('userData', process.env.CODE_ASSISTANT_USER_DATA_DIR);
const ownsInstance =
  process.env.CODE_ASSISTANT_ALLOW_MULTIPLE === '1' || app.requestSingleInstanceLock();
if (!ownsInstance) app.quit();
app.on('second-instance', () => {
  openWhenReady = true;
  launcher?.show();
  launcher?.showClient();
});
const terminal = new Set([
  'completed',
  'failed',
  'cancelled',
  'interrupted',
  'budget_exhausted',
  'rejected',
]);

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

async function api(method, route, body) {
  if (!endpoint) throw new Error('本地服务尚未就绪。');
  const response = await fetch(endpoint + route, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(20000),
  });
  const value = await response.json();
  if (!response.ok)
    throw new Error(typeof value.detail === 'string' ? value.detail : JSON.stringify(value.detail));
  return value;
}

function allowed(method, route) {
  if (
    typeof route !== 'string' ||
    route.length > 5000 ||
    !route.startsWith('/api/') ||
    /[\r\n\\]/.test(route)
  )
    return false;
  const pathname = route.split('?')[0];
  const id = '[a-f0-9]{32}';
  const routes = {
    GET: [
      'settings',
      'connections',
      'workspaces',
      'sessions',
      `sessions/${id}/tasks`,
      `tasks/${id}`,
    ],
    PUT: ['settings'],
    DELETE: [`connections/${id}`, `tasks/${id}`],
    POST: ['models', 'connection-test', 'connections', `connections/${id}/activate`, 'tasks', `tasks/${id}/(cancel|resume)`, `patches/${id}/(review|undo)`],
  };
  return (routes[method] || []).some((pattern) => new RegExp(`^/api/${pattern}$`).test(pathname));
}

async function launchBackend() {
  const python =
    process.env.CODE_ASSISTANT_PYTHON ||
    path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!existsSync(python))
    throw new Error('未找到项目 Python 环境。请先在项目目录执行 setup.ps1。');
  const port = await freePort();
  endpoint = `http://127.0.0.1:${port}`;
  const env = {
    ...process.env,
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
    CODE_ASSISTANT_TOKEN: token,
  };
  delete env.PYTHONHOME;
  delete env.PYTHONPATH;
  const args = [
    '-E',
    '-X',
    'utf8',
    '-m',
    'backend',
    '--port',
    String(port),
    '--token',
    token,
    '--data-dir',
    process.env.CODE_ASSISTANT_DATA_DIR || path.join(app.getPath('userData'), 'service'),
  ];
  backend = spawn(python, args, {
    cwd: root,
    env,
    windowsHide: true,
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  let errors = '';
  backend.stderr.on('data', (data) => {
    errors = (errors + data.toString()).slice(-6000);
  });
  let exit = null;
  backend.once('error', (error) => {
    exit = error.message;
  });
  backend.once('exit', (code) => {
    exit = `Python 服务退出 (${code})\n${errors}`;
  });
  for (let attempt = 0; attempt < 150; attempt++) {
    if (exit !== null) throw new Error(exit);
    try {
      const response = await fetch(endpoint + '/health', { signal: AbortSignal.timeout(400) });
      if (response.ok && (await response.json()).service === 'CodeAssistantAgent') return;
    } catch {
      /* Wait for the owned sidecar. */
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error('本地服务启动超时。\n' + errors);
}

async function watch(sender, taskId, after) {
  const controller = new AbortController();
  subscriptions.set(taskId, controller);
  let cursor = after,
    retries = 0;
  try {
    while (!controller.signal.aborted && !sender.isDestroyed()) {
      try {
        const response = await fetch(`${endpoint}/api/tasks/${taskId}/events?after=${cursor}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('事件流连接失败。');
        const decoder = new TextDecoder();
        let buffer = '';
        for await (const bytes of response.body) {
          buffer += decoder.decode(bytes, { stream: true }).replace(/\r\n/g, '\n');
          let index;
          while ((index = buffer.indexOf('\n\n')) >= 0) {
            const frame = buffer.slice(0, index);
            buffer = buffer.slice(index + 2);
            const data = frame
              .split('\n')
              .filter((line) => line.startsWith('data: '))
              .map((line) => line.slice(6))
              .join('\n');
            if (!data) continue;
            const event = JSON.parse(data);
            if (event.id > cursor && !sender.isDestroyed()) {
              cursor = event.id;
              sender.send('assistant:event', event);
            }
          }
        }
        if (terminal.has((await api('GET', `/api/tasks/${taskId}`)).status)) break;
        retries = 0;
      } catch (error) {
        if (controller.signal.aborted) break;
        if (++retries > 5) {
          if (!sender.isDestroyed())
            sender.send('assistant:event', {
              task_id: taskId,
              kind: 'connection.error',
              data: { message: '服务连接中断，请重新打开任务或重启客户端。' },
            });
          break;
        }
      }
      await new Promise((resolve) => setTimeout(resolve, Math.min(500 * 2 ** retries, 5000)));
    }
  } finally {
    if (subscriptions.get(taskId) === controller) subscriptions.delete(taskId);
  }
}

function registerHandlers() {
  const trust = (event) => {
    if (!window || event.sender !== window.webContents) throw new Error('未知的客户端。');
  };
  ipcMain.handle('assistant:bootstrap', async (event) => {
    trust(event);
    return {
      version: app.getVersion(),
      settings: await api('GET', '/api/settings'),
      workspaces: await api('GET', '/api/workspaces'),
    };
  });
  ipcMain.handle('assistant:open-workspace', async (event) => {
    trust(event);
    const choice = await dialog.showOpenDialog(window, {
      title: '打开项目文件夹',
      properties: ['openDirectory'],
    });
    return choice.canceled ? null : api('POST', '/api/workspaces', { path: choice.filePaths[0] });
  });
  ipcMain.handle('assistant:open-dropped-workspace', async (event, droppedPath) => {
    trust(event);
    if (
      typeof droppedPath !== 'string' ||
      droppedPath.length > 32768 ||
      droppedPath.includes('\0') ||
      !path.isAbsolute(droppedPath)
    )
      throw new Error('请拖入本地项目文件夹或代码文件。');
    let entry;
    try {
      entry = await stat(droppedPath);
    } catch {
      throw new Error('无法读取拖入的项目，请确认文件仍然存在且可以访问。');
    }
    if (!entry.isDirectory() && !entry.isFile())
      throw new Error('请拖入项目文件夹或普通代码文件。');
    const projectPath = entry.isDirectory() ? droppedPath : path.dirname(droppedPath);
    return {
      workspace: await api('POST', '/api/workspaces', { path: projectPath }),
      selectedFile: entry.isFile() ? path.basename(droppedPath) : null,
    };
  });
  ipcMain.handle('assistant:window-state', (event) => {
    trust(event);
    return { maximized: window.isMaximized() };
  });
  ipcMain.handle('assistant:window-control', (event, action) => {
    trust(event);
    if (action === 'minimize') window.minimize();
    else if (action === 'maximize') {
      if (window.isMaximized()) window.unmaximize();
      else window.maximize();
    } else if (action === 'close') window.close();
    else throw new Error('未知的窗口操作。');
    return { maximized: window.isMaximized() };
  });
  ipcMain.handle('assistant:request', async (event, request) => {
    trust(event);
    if (
      !request ||
      !allowed(request.method, request.path) ||
      JSON.stringify(request.body || '').length > 1_000_000
    )
      throw new Error('此请求不在客户端接口范围内。');
    const result = await api(request.method, request.path, request.body);
    if (request.method === 'DELETE' && /^\/api\/tasks\/[a-f0-9]{32}$/.test(request.path)) {
      const taskId = request.path.split('/').at(-1);
      subscriptions.get(taskId)?.abort();
      subscriptions.delete(taskId);
    }
    return result;
  });
  ipcMain.handle('assistant:watch', (event, { taskId, after }) => {
    trust(event);
    if (!/^[a-f0-9]{32}$/.test(taskId) || !Number.isSafeInteger(after) || after < 0)
      throw new Error('任务标识无效。');
    if (!subscriptions.has(taskId) || subscriptions.get(taskId).signal.aborted)
      void watch(event.sender, taskId, after);
  });
  ipcMain.handle('assistant:unwatch', (event, taskId) => {
    trust(event);
    subscriptions.get(taskId)?.abort();
  });
}

function stopBackend() {
  for (const controller of subscriptions.values()) controller.abort();
  if (backend && backend.exitCode === null) {
    if (process.platform === 'win32')
      execFile(
        'taskkill',
        ['/PID', String(backend.pid), '/T', '/F'],
        { windowsHide: true },
        () => {},
      );
    else backend.kill('SIGTERM');
  }
}

app.whenReady().then(async () => {
  if (!ownsInstance) return;
  try {
    await launchBackend();
    window = new BrowserWindow({
      width: 650,
      height: 500,
      minWidth: 640,
      minHeight: 480,
      frame: false,
      thickFrame: false,
      transparent: true,
      roundedCorners: true,
      show: false,
      skipTaskbar: true,
      backgroundColor: '#00000000',
      title: 'CodeAssistantAgent · 代码助手',
      webPreferences: {
        preload: path.join(__dirname, 'preload.cjs'),
        zoomMode: 'isolated',
        zoomFactor: 0.65625,
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    });
    window.setMenu(null);
    registerHandlers();
    window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    window.webContents.on('will-navigate', (event) => event.preventDefault());
    window.on('close', (event) => {
      if (!stopping) {
        event.preventDefault();
        launcher?.hideClient();
      }
    });
    launcher = createBubble({
      mainWindow: window,
      userData: app.getPath('userData'),
      hidden: process.env.CODE_ASSISTANT_HIDDEN === '1',
      onQuit: () => {
        if (!stopping) app.quit();
      },
    });
    if (process.env.CODE_ASSISTANT_DEV_URL)
      await window.loadURL(process.env.CODE_ASSISTANT_DEV_URL);
    else await window.loadFile(path.join(__dirname, '../dist/index.html'));
    launcher.setReady(true);
    if (openWhenReady) launcher.showClient();
  } catch (error) {
    if (stopping) return;
    stopBackend();
    dialog.showErrorBox('代码助手启动失败', error.message);
    app.quit();
  }
});
app.on('before-quit', () => {
  if (!stopping) {
    stopping = true;
    launcher?.dispose();
    stopBackend();
  }
});
app.on('window-all-closed', () => {
  if (stopping) app.quit();
});
