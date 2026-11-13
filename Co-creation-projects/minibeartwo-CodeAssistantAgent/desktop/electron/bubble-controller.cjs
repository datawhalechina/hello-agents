/** Native floating launcher: the renderer can only drag, toggle, or open its menu. */
const { BrowserWindow, Menu, ipcMain, screen, systemPreferences } = require('electron');
const { readFileSync, writeFileSync, mkdirSync } = require('node:fs');
const path = require('node:path');
const { createClientTransition } = require('./client-transition.cjs');

const SIZE = 96;

function getClientPosition(anchor, client, work) {
  const gap = 12;
  const marginX = work.width >= client.width + 16 ? 8 : 0;
  const marginY = work.height >= client.height + 16 ? 8 : 0;
  const left = work.x + marginX;
  const top = work.y + marginY;
  const right = Math.max(left, work.x + work.width - marginX - client.width);
  const bottom = Math.max(top, work.y + work.height - marginY - client.height);
  const centeredX = anchor.x + (anchor.width - client.width) / 2;
  const alignedBottomY = anchor.y + anchor.height - client.height;
  const candidates = [
    { x: anchor.x - client.width - gap, y: alignedBottomY },
    { x: anchor.x + anchor.width + gap, y: alignedBottomY },
    { x: centeredX, y: anchor.y + anchor.height + gap },
    { x: centeredX, y: anchor.y - client.height - gap },
  ].map((candidate, preference) => {
    const x = Math.max(left, Math.min(Math.round(candidate.x), right));
    const y = Math.max(top, Math.min(Math.round(candidate.y), bottom));
    const overlapWidth = Math.max(0,
      Math.min(x + client.width, anchor.x + anchor.width + gap) - Math.max(x, anchor.x - gap));
    const overlapHeight = Math.max(0,
      Math.min(y + client.height, anchor.y + anchor.height + gap) - Math.max(y, anchor.y - gap));
    return { x, y, overlap: overlapWidth * overlapHeight, preference };
  });
  // Open above and to the left, leaving the character at the client's bottom right.
  // Use another clear side only when the display cannot fit that arrangement.
  candidates.sort((a, b) => a.overlap - b.overlap || a.preference - b.preference);
  return { x: candidates[0].x, y: candidates[0].y };
}

function createBubble({ mainWindow, userData, hidden, onQuit }) {
  const positionFile = path.join(userData, 'bubble-position.json');
  let ready = false;
  let drag = null;
  let disposed = false;
  const clientTransition = createClientTransition({
    window: mainWindow,
    positionWindow: positionClient,
    reduceMotion: () => systemPreferences.getAnimationSettings().prefersReducedMotion,
    onState: notify,
  });
  const area = screen.getPrimaryDisplay().workArea;
  let initial = { x: area.x + area.width - SIZE - 24, y: area.y + area.height * 0.55 - SIZE / 2 };
  try {
    const saved = JSON.parse(readFileSync(positionFile, 'utf8'));
    if (
      Number.isSafeInteger(saved.x) &&
      Number.isSafeInteger(saved.y) &&
      Math.abs(saved.x) < 2_000_000_000 &&
      Math.abs(saved.y) < 2_000_000_000
    )
      initial = saved;
  } catch {
    // First launch and invalid preference files use the default desktop position.
  }

  function boundedPosition(point) {
    const rectangle = { x: Math.round(point.x), y: Math.round(point.y), width: SIZE, height: SIZE };
    const work = screen.getDisplayMatching(rectangle).workArea;
    const marginX = work.width >= SIZE + 16 ? 8 : 0;
    const marginY = work.height >= SIZE + 16 ? 8 : 0;
    return {
      x: Math.round(
        Math.max(work.x + marginX, Math.min(rectangle.x, work.x + work.width - SIZE - marginX)),
      ),
      y: Math.round(
        Math.max(work.y + marginY, Math.min(rectangle.y, work.y + work.height - SIZE - marginY)),
      ),
    };
  }

  const bubble = new BrowserWindow({
    ...boundedPosition(initial),
    width: SIZE,
    height: SIZE,
    title: 'CodeAssistantAgent · 桌面气泡',
    frame: false,
    thickFrame: false,
    transparent: true,
    backgroundColor: '#00000000',
    hasShadow: false,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'bubble-preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
      partition: 'floating-launcher',
    },
  });
  function maintainNativeBounds() {
    // Electron on Windows can ignore an explicit floating level before first show.
    if (process.platform === 'win32') {
      bubble.setAlwaysOnTop(true);
      if (!bubble.isAlwaysOnTop()) bubble.setAlwaysOnTop(true, 'screen-saver');
    } else bubble.setAlwaysOnTop(true, 'floating');
    const bounds = bubble.getBounds();
    if (bounds.width !== SIZE || bounds.height !== SIZE) {
      bubble.setBounds({ ...boundedPosition(bounds), width: SIZE, height: SIZE }, false);
    }
  }
  maintainNativeBounds();
  bubble.on('show', maintainNativeBounds);
  bubble.setMenu(null);
  bubble.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  bubble.webContents.on('will-navigate', (event) => event.preventDefault());
  // Prevent a client page's zoom setting from resizing the launcher on file://.
  bubble.webContents.on('did-finish-load', () => {
    bubble.webContents.setZoomFactor(1);
    notify();
    if (!hidden) bubble.showInactive();
  });
  bubble.loadFile(path.join(__dirname, 'bubble.html')).catch((error) => {
    console.error('Floating launcher failed to load:', error.message);
    onQuit();
  });

  function savePosition() {
    if (bubble.isDestroyed()) return;
    try {
      const { x, y } = bubble.getBounds();
      mkdirSync(userData, { recursive: true });
      writeFileSync(positionFile, JSON.stringify({ x, y }) + '\n', 'utf8');
    } catch (error) {
      console.error('Could not remember launcher position:', error.message);
    }
  }

  function notify() {
    if (!bubble.isDestroyed()) {
      bubble.webContents.send('bubble:state', {
        ready,
        clientVisible:
          !mainWindow.isDestroyed() && clientTransition.isOpen(),
      });
    }
  }

  function positionClient() {
    if (bubble.isDestroyed() || mainWindow.isDestroyed() ||
      mainWindow.isMaximized() || mainWindow.isFullScreen()) return;
    const anchor = bubble.getBounds();
    const work = screen.getDisplayMatching(anchor).workArea;
    const next = getClientPosition(anchor, mainWindow.getBounds(), work);
    mainWindow.setPosition(next.x, next.y, false);
    const client = mainWindow.getBounds();
    const beside = next.x + client.width <= anchor.x || next.x >= anchor.x + anchor.width;
    if (beside) {
      // If the client was clamped at the top edge, keep the mascot bottom-aligned.
      const aligned = boundedPosition({ x: anchor.x, y: next.y + client.height - SIZE });
      if (aligned.y !== anchor.y) {
        bubble.setBounds({ ...aligned, width: SIZE, height: SIZE }, false);
        savePosition();
      }
    }
  }

  function showClient() {
    if (!ready || mainWindow.isDestroyed()) return;
    clientTransition.show();
  }

  function hideClient() {
    if (mainWindow.isDestroyed()) return;
    clientTransition.hide();
  }

  function toggle() {
    if (clientTransition.isOpen()) hideClient();
    else showClient();
  }

  function menu() {
    if (drag?.moved) savePosition();
    drag = null;
    Menu.buildFromTemplate([
      {
        label: clientTransition.isOpen() ? '收起客户端' : '打开客户端',
        enabled: ready,
        click: toggle,
      },
      {
        label: '配置模型',
        enabled: ready,
        click: () => {
          if (!ready || mainWindow.isDestroyed()) return;
          showClient();
          mainWindow.webContents.send('assistant:open-settings');
        },
      },
      { type: 'separator' },
      { label: '退出代码助手', click: onQuit },
    ]).popup({ window: bubble });
  }

  function trust(event) {
    if (bubble.isDestroyed() || event.sender !== bubble.webContents) {
      throw new Error('未知的气泡窗口。');
    }
  }

  function followClient(anchor) {
    if (!drag?.clientOrigin || mainWindow.isDestroyed() || !clientTransition.isOpen() ||
      !mainWindow.isVisible() || mainWindow.isMinimized() ||
      mainWindow.isMaximized() || mainWindow.isFullScreen()) return;
    const client = mainWindow.getBounds();
    const work = screen.getDisplayMatching(anchor).workArea;
    const marginX = work.width >= client.width + 16 ? 8 : 0;
    const marginY = work.height >= client.height + 16 ? 8 : 0;
    let x = Math.max(work.x + marginX, Math.min(drag.clientOrigin.x + anchor.x - drag.origin.x,
      Math.max(work.x + marginX, work.x + work.width - client.width - marginX)));
    let y = Math.max(work.y + marginY, Math.min(drag.clientOrigin.y + anchor.y - drag.origin.y,
      Math.max(work.y + marginY, work.y + work.height - client.height - marginY)));
    // Keep the original offset while there is room; dock to another side at an edge.
    if (x < anchor.x + anchor.width + 12 && x + client.width > anchor.x - 12 &&
      y < anchor.y + anchor.height + 12 && y + client.height > anchor.y - 12) {
      ({ x, y } = getClientPosition(anchor, client, work));
    }
    if (x !== client.x || y !== client.y) mainWindow.setPosition(x, y, false);
  }

  function moveDrag() {
    if (!drag) return;
    const cursor = screen.getCursorScreenPoint();
    const dx = cursor.x - drag.cursor.x;
    const dy = cursor.y - drag.cursor.y;
    if (!drag.moved && Math.hypot(dx, dy) < 6) return;
    drag.moved = true;
    const next = boundedPosition({ x: drag.origin.x + dx, y: drag.origin.y + dy });
    bubble.setBounds({ ...next, width: SIZE, height: SIZE }, false);
    followClient({ ...next, width: SIZE, height: SIZE });
  }

  const handlers = {
    'bubble:toggle': (event) => {
      trust(event);
      toggle();
    },
    'bubble:drag-start': (event) => {
      trust(event);
      const follows = !mainWindow.isDestroyed() && clientTransition.isOpen() && mainWindow.isVisible() &&
        !mainWindow.isMinimized() && !mainWindow.isMaximized() && !mainWindow.isFullScreen();
      drag = { cursor: screen.getCursorScreenPoint(), origin: bubble.getBounds(), moved: false,
        clientOrigin: follows ? mainWindow.getBounds() : null };
    },
    'bubble:drag-end': (event) => {
      trust(event);
      moveDrag();
      const dragged = !!drag?.moved;
      drag = null;
      if (dragged) savePosition();
      return { dragged };
    },
  };
  const listeners = {
    'bubble:drag-move': (event) => {
      trust(event);
      moveDrag();
    },
    'bubble:menu': (event) => {
      trust(event);
      menu();
    },
  };
  for (const [name, handler] of Object.entries(handlers)) ipcMain.handle(name, handler);
  for (const [name, listener] of Object.entries(listeners)) ipcMain.on(name, listener);

  function keepOnScreen() {
    if (bubble.isDestroyed()) return;
    clientTransition.settle();
    const next = boundedPosition(bubble.getBounds());
    // Windows can change frameless bounds slightly during a monitor DPI transition.
    bubble.setBounds({ ...next, width: SIZE, height: SIZE }, false);
    savePosition();
    if (mainWindow.isVisible()) positionClient();
  }
  screen.on('display-removed', keepOnScreen);
  screen.on('display-metrics-changed', keepOnScreen);
  for (const event of ['show', 'hide', 'minimize', 'restore']) mainWindow.on(event, notify);
  bubble.on('blur', () => {
    if (drag?.moved) savePosition();
    drag = null;
  });
  bubble.on('closed', onQuit);

  return {
    window: bubble,
    showClient,
    hideClient,
    setReady(value) {
      ready = value;
      notify();
    },
    show() {
      if (!bubble.isDestroyed()) bubble.showInactive();
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      clientTransition.dispose();
      savePosition();
      for (const name of Object.keys(handlers)) ipcMain.removeHandler(name);
      for (const [name, listener] of Object.entries(listeners))
        ipcMain.removeListener(name, listener);
      screen.removeListener('display-removed', keepOnScreen);
      screen.removeListener('display-metrics-changed', keepOnScreen);
    },
  };
}

module.exports = { createBubble, getClientPosition };
