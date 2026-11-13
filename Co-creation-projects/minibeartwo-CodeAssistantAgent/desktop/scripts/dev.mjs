import { spawn, execFile } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const vite = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js')], {
  cwd: root,
  stdio: 'inherit',
  windowsHide: true,
});
let electron;
function stopChild(child) {
  if (!child || child.exitCode !== null) return;
  if (process.platform === 'win32')
    execFile('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true }, () => {});
  else child.kill('SIGTERM');
}
const stop = () => {
  stopChild(electron);
  stopChild(vite);
};
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
vite.on('exit', (code) => {
  if (code) {
    stopChild(electron);
    process.exitCode = code;
  }
});
try {
  let ready = false;
  for (let index = 0; index < 100; index++) {
    try {
      const response = await fetch('http://127.0.0.1:5173');
      if (response.ok) {
        ready = true;
        break;
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  if (!ready) throw new Error('Vite 启动超时。');
  const env = { ...process.env, CODE_ASSISTANT_DEV_URL: 'http://127.0.0.1:5173' };
  delete env.ELECTRON_RUN_AS_NODE;
  electron = spawn(require('electron'), ['.'], {
    cwd: root,
    env,
    stdio: 'inherit',
    windowsHide: true,
  });
  electron.on('exit', (code) => {
    stopChild(vite);
    process.exitCode = code || 0;
  });
} catch (error) {
  stop();
  throw error;
}
