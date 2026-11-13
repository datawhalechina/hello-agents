const button = document.getElementById('bubble');
const character = document.getElementById('bubble-character');
const canvas = document.getElementById('bubble-motion');
const bridge = window.assistantBubble;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const motion = window.PhoebeMotion.create({ button, character, canvas, reducedMotion });
let pointerHovered = false;
let gesture = null;
let finishing = false;
let suppressClickUntil = 0;
let interactionVersion = 0;

function interruptInteraction() {
  interactionVersion += 1;
  motion.cancelClick();
}

function updateCharacter() {
  motion.setInteraction({
    hovered: pointerHovered,
    focused: button.matches(':focus-visible'),
    // Keep the currently rendered pose while native drag validation is pending.
    pressed: button.classList.contains('pressed') || finishing,
  });
}

button.addEventListener('pointerenter', () => {
  pointerHovered = true;
  updateCharacter();
});
button.addEventListener('pointerleave', () => {
  pointerHovered = false;
  updateCharacter();
});
button.addEventListener('focus', updateCharacter);
button.addEventListener('blur', updateCharacter);
reducedMotion.addEventListener('change', () => {
  motion.motionPreferenceChanged();
  updateCharacter();
});

function showError() {
  button.title = '操作暂未完成，请重试 · 右键可打开菜单';
}

function toggle() {
  motion.playClick();
  bridge.toggle().catch(showError);
}

function updateState({ clientVisible, ready }) {
  button.classList.toggle('client-visible', clientVisible);
  button.classList.toggle('connecting', !ready);
  button.setAttribute('aria-expanded', String(clientVisible));
  button.setAttribute('aria-busy', String(!ready));
  const action = clientVisible ? '收起代码助手' : '打开代码助手';
  button.setAttribute('aria-label', `${action}${ready ? '' : '，服务正在启动'}`);
  button.title = `${ready ? action : '代码助手正在启动'} · 点击${clientVisible ? '收起' : '打开'} · 拖动移动 · 右键菜单`;
}

button.addEventListener('pointerdown', (event) => {
  if (event.button !== 0 || !event.isPrimary || gesture || finishing) return;
  interactionVersion += 1;
  event.preventDefault();
  button.setPointerCapture(event.pointerId);
  button.classList.add('pressed');
  // Freeze the visible pose before programmatic focus can emit a focus event.
  updateCharacter();
  button.focus({ preventScroll: true });
  gesture = {
    pointerId: event.pointerId,
    startX: event.screenX,
    startY: event.screenY,
    dragged: false,
    started: bridge.startDrag().then(
      () => true,
      () => false,
    ),
  };
});

function measureGesture(event) {
  if (!gesture || !Number.isFinite(event.screenX) || !Number.isFinite(event.screenY)) return;
  if (Math.hypot(event.screenX - gesture.startX, event.screenY - gesture.startY) > 6) {
    gesture.dragged = true;
  }
}

button.addEventListener('pointermove', (event) => {
  if (gesture?.pointerId === event.pointerId) {
    measureGesture(event);
    bridge.moveDrag();
  }
});

async function finishGesture(event, canceled) {
  if (!gesture || gesture.pointerId !== event.pointerId) return;
  measureGesture(event);
  const current = gesture;
  const version = interactionVersion;
  gesture = null;
  finishing = true;
  suppressClickUntil = performance.now() + 400;
  button.classList.remove('pressed');
  updateCharacter();
  if (button.hasPointerCapture(event.pointerId)) button.releasePointerCapture(event.pointerId);
  try {
    if (!(await current.started)) {
      showError();
      return;
    }
    // The main process measures native screen coordinates, including the final position.
    const result = await bridge.endDrag();
    if (!canceled && version === interactionVersion && !current.dragged && result && !result.dragged) {
      toggle();
    }
  } catch {
    showError();
  } finally {
    finishing = false;
    updateCharacter();
  }
}

button.addEventListener('pointerup', (event) => {
  event.preventDefault();
  void finishGesture(event, false);
});
button.addEventListener('pointercancel', (event) => {
  interruptInteraction();
  void finishGesture(event, true);
});
button.addEventListener('lostpointercapture', (event) => {
  // Releasing capture normally also emits this event; it must not cancel the new click.
  if (!gesture || gesture.pointerId !== event.pointerId) return;
  interruptInteraction();
  void finishGesture(event, true);
});

button.addEventListener('click', (event) => {
  event.preventDefault();
  // Pointer gestures are handled above; detail 0 preserves assistive-technology activation.
  if (event.detail === 0 && performance.now() >= suppressClickUntil) toggle();
});

button.addEventListener('contextmenu', (event) => {
  event.preventDefault();
  interruptInteraction();
  if (gesture) void finishGesture({ pointerId: gesture.pointerId }, true);
  bridge.menu();
});

button.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    if (!event.repeat && !gesture && !finishing) toggle();
  } else if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
    event.preventDefault();
    interruptInteraction();
    if (gesture) void finishGesture({ pointerId: gesture.pointerId }, true);
    bridge.menu();
  } else if (event.key === 'Escape' && gesture) {
    event.preventDefault();
    interruptInteraction();
    void finishGesture({ pointerId: gesture.pointerId }, true);
  }
});

window.addEventListener('blur', () => {
  // Opening the client changes window focus while the pointer can remain over
  // this always-on-top character. Focus loss is not itself a pointer leave.
  pointerHovered = button.matches(':hover');
  // A real pointer gesture is canceled on blur, but an accepted click keeps playing.
  interactionVersion += 1;
  if (gesture) void finishGesture({ pointerId: gesture.pointerId }, true);
  updateCharacter();
});

const unsubscribe = bridge.onState(updateState);
window.addEventListener('beforeunload', unsubscribe, { once: true });
window.addEventListener('beforeunload', () => {
  motion.dispose();
}, { once: true });
updateCharacter();
