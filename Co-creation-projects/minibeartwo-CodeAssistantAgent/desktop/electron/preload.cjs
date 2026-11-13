const { contextBridge, ipcRenderer, webUtils } = require('electron');

// Keep an early menu request until React has subscribed during startup.
const settingsListeners = new Set();
let pendingSettings = false;
ipcRenderer.on('assistant:open-settings', () => {
  if (!settingsListeners.size) pendingSettings = true;
  else for (const listener of settingsListeners) listener();
});

contextBridge.exposeInMainWorld('codeAssistant', {
  bootstrap: () => ipcRenderer.invoke('assistant:bootstrap'),
  openWorkspace: () => ipcRenderer.invoke('assistant:open-workspace'),
  openDroppedProject: async (file) => {
    const droppedPath = webUtils.getPathForFile(file);
    if (!droppedPath) throw new Error('请从文件管理器拖入本地项目。');
    return ipcRenderer.invoke('assistant:open-dropped-workspace', droppedPath);
  },
  windowState: () => ipcRenderer.invoke('assistant:window-state'),
  windowControl: (action) => ipcRenderer.invoke('assistant:window-control', action),
  request: (method, path, body) => ipcRenderer.invoke('assistant:request', { method, path, body }),
  watchTask: (taskId, after = 0) => ipcRenderer.invoke('assistant:watch', { taskId, after }),
  unwatchTask: (taskId) => ipcRenderer.invoke('assistant:unwatch', taskId),
  onOpenSettings: (callback) => {
    settingsListeners.add(callback);
    if (pendingSettings) {
      pendingSettings = false;
      callback();
    }
    return () => settingsListeners.delete(callback);
  },
  onEvent: (callback) => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('assistant:event', listener);
    return () => ipcRenderer.removeListener('assistant:event', listener);
  },
});
