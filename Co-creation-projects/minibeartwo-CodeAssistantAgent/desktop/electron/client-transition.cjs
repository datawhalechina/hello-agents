/** Fade in place; native position changes only happen before the window is shown. */
function createClientTransition({ window, positionWindow, reduceMotion, onState }) {
  let requested = window.isVisible() && !window.isMinimized();
  let progress = requested ? 1 : 0;
  let opacity = window.getOpacity();
  let timer = null;

  function cancel() {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  function paint(value) {
    progress = value;
    window.setOpacity(opacity * value);
  }

  function finish() {
    cancel();
    if (window.isDestroyed()) return;
    if (requested) paint(1);
    else {
      progress = 0;
      window.hide();
      window.setSkipTaskbar(true);
      window.setOpacity(opacity);
    }
    onState();
  }

  function animate() {
    cancel();
    const target = requested ? 1 : 0;
    if (reduceMotion() || Math.abs(target - progress) < 0.001) { finish(); return; }
    const from = progress;
    const began = performance.now();
    // Linear opacity makes the appearance gradual instead of front-loading most
    // of the change. Avoid moving a Windows native window on every timer tick.
    const duration = Math.max(16, (requested ? 480 : 180) * Math.abs(target - from));
    const frameDuration = 1000 / 60;
    let nextFrame = began + frameDuration;
    const schedule = () => {
      const now = performance.now();
      // Account for native API time and Windows timer rounding instead of adding
      // a fresh 16ms delay after every completed frame. Drop missed frames.
      if (nextFrame <= now) nextFrame = now + frameDuration;
      timer = setTimeout(tick, Math.max(1, nextFrame - now));
    };
    const tick = () => {
      timer = null;
      if (window.isDestroyed()) return;
      const elapsed = Math.min(1, (performance.now() - began) / duration);
      paint(from + (target - from) * elapsed);
      if (elapsed >= 1) finish();
      else {
        nextFrame += frameDuration;
        schedule();
      }
    };
    schedule();
  }

  function show() {
    if (window.isDestroyed()) return;
    const fresh = !window.isVisible() || window.isMinimized();
    if (requested && !fresh) { window.focus(); return; }
    requested = true;
    if (fresh) {
      cancel();
      opacity = window.getOpacity();
      progress = 0;
      window.setOpacity(0);
      if (window.isMinimized()) window.restore();
      positionWindow();
    }
    window.setSkipTaskbar(false);
    window.show();
    window.focus();
    onState();
    animate();
  }

  function hide() {
    if (window.isDestroyed()) return;
    requested = false;
    onState();
    if (!window.isVisible() || window.isMinimized()) {
      cancel();
      progress = 0;
      window.hide();
      window.setSkipTaskbar(true);
      window.setOpacity(opacity);
      return;
    }
    animate();
  }

  function settle() {
    if (timer === null || window.isDestroyed()) return;
    finish();
  }

  function externallyHidden() {
    requested = false;
    if (timer !== null) {
      cancel();
      progress = 0;
      window.setOpacity(opacity);
    }
    onState();
  }

  function dispose() {
    cancel();
    window.removeListener('hide', externallyHidden);
    window.removeListener('minimize', settle);
    window.removeListener('maximize', settle);
    window.removeListener('unmaximize', settle);
    window.removeListener('closed', dispose);
    if (!window.isDestroyed()) window.setOpacity(opacity);
  }

  window.on('hide', externallyHidden);
  window.on('minimize', settle);
  window.on('maximize', settle);
  window.on('unmaximize', settle);
  window.on('closed', dispose);
  return { show, hide, settle, dispose, isOpen: () => requested && !window.isMinimized() };
}

module.exports = { createClientTransition };
