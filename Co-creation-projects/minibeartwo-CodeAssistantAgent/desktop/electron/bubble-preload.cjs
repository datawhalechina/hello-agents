const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('assistantBubble', {
  startDrag: () => ipcRenderer.invoke('bubble:drag-start'),
  moveDrag: () => ipcRenderer.send('bubble:drag-move'),
  endDrag: () => ipcRenderer.invoke('bubble:drag-end'),
  toggle: () => ipcRenderer.invoke('bubble:toggle'),
  menu: () => ipcRenderer.send('bubble:menu'),
  onState: (callback) => {
    if (typeof callback !== 'function') return () => {};
    const listener = (_event, state) => {
      if (state && typeof state.clientVisible === 'boolean' && typeof state.ready === 'boolean') {
        callback({ clientVisible: state.clientVisible, ready: state.ready });
      }
    };
    ipcRenderer.on('bubble:state', listener);
    return () => ipcRenderer.removeListener('bubble:state', listener);
  },
});
