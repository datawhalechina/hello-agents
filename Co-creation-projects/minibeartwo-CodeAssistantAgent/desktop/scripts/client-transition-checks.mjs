/** Verify gradual opacity, fixed placement and interrupted fades with a controlled clock. */
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

export async function assertClientTransitions(desktop, checks) {
  const source = await readFile(path.join(desktop, 'electron/client-transition.cjs'), 'utf8');
  function fixture({ reduced = false, opacity = 1, maximized = false } = {}) {
    let now = 0;
    let sequence = 0;
    const timers = new Map();
    const trace = [];
    class NativeWindow extends EventEmitter {
      visible = false;
      minimized = false;
      destroyed = false;
      opacity = opacity;
      bounds = { x: 100, y: 200, width: 650, height: 500 };
      isVisible() { return this.visible; }
      isMinimized() { return this.minimized; }
      isMaximized() { return maximized; }
      isFullScreen() { return false; }
      isDestroyed() { return this.destroyed; }
      getOpacity() { return this.opacity; }
      setOpacity(value) { this.opacity = value; trace.push({ at: now, opacity: value }); }
      getPosition() { return [this.bounds.x, this.bounds.y]; }
      setPosition(x, y) { Object.assign(this.bounds, { x, y }); trace.push({ at: now, x, y }); }
      setSkipTaskbar(value) { this.skipTaskbar = value; }
      show() { this.visible = true; trace.push({ at: now, shownAtOpacity: this.opacity }); }
      hide() { if (this.visible) { this.visible = false; this.emit('hide'); } }
      restore() { this.minimized = false; this.emit('restore'); }
      focus() {}
    }
    const window = new NativeWindow();
    const loaded = { exports: {} };
    runInNewContext(source, {
      module: loaded, performance: { now: () => now },
      setTimeout: (callback, delay) => {
        const id = ++sequence;
        timers.set(id, { at: now + delay, callback });
        return id;
      },
      clearTimeout: (id) => timers.delete(id),
    });
    const transition = loaded.exports.createClientTransition({
      window,
      positionWindow: () => { if (!maximized) window.setPosition(100, 200); },
      reduceMotion: () => reduced,
      onState: () => {},
    });
    function advance(duration) {
      const end = now + duration;
      for (;;) {
        const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > end) break;
        now = next[1].at;
        timers.delete(next[0]);
        next[1].callback();
      }
      now = end;
    }
    return { window, transition, advance, trace, timers };
  }

  const opening = fixture();
  opening.transition.show();
  assert.equal(opening.window.isVisible(), true, 'show starts immediately with an invisible native window');
  assert.equal(opening.trace.find((frame) => 'shownAtOpacity' in frame).shownAtOpacity, 0,
    'zero opacity is set before show, preventing a one-frame flash');
  assert.equal(opening.window.bounds.x, 100);
  opening.advance(64);
  assert.ok(opening.window.opacity > 0 && opening.window.opacity < 1, 'opening renders intermediate opacity');
  assert.ok(opening.window.opacity < 0.2, 'entrance reveals gradually instead of appearing almost immediately');
  opening.advance(176);
  assert.ok(Math.abs(opening.window.opacity - 0.5) < 0.04, 'halfway through the fade is about half opaque');
  opening.advance(260);
  assert.equal(opening.window.opacity, 1);
  assert.deepEqual(opening.window.bounds, { x: 100, y: 200, width: 650, height: 500 });
  assert.equal(opening.timers.size, 0);
  opening.transition.show();
  assert.equal(opening.window.opacity, 1, 'an already open client is focused without restarting the fade');
  opening.transition.hide();
  assert.equal(opening.transition.isOpen(), false, 'toggle intent changes at the start of fade-out');
  assert.equal(opening.window.isVisible(), true, 'native window remains available while fading out');
  opening.advance(64);
  assert.ok(opening.window.opacity > 0 && opening.window.opacity < 1, 'closing renders intermediate opacity');
  opening.advance(160);
  assert.equal(opening.window.isVisible(), false);
  assert.equal(opening.window.opacity, 1, 'hidden window restores its original opacity');
  assert.equal(opening.window.skipTaskbar, true);
  assert.equal(opening.timers.size, 0);
  assert.equal(opening.trace.filter((frame) => 'x' in frame).length, 1,
    'position is set once before show; opening and closing never move the native window');
  const showFrame = opening.trace.findIndex((frame) => 'shownAtOpacity' in frame);
  assert.ok(opening.trace.findIndex((frame) => 'x' in frame) < showFrame,
    'the final resting position is selected while the window is still invisible');
  checks.push('client gradually fades in place over 480ms, without per-frame movement, resizing or flashing');

  const reversed = fixture();
  reversed.transition.show();
  reversed.advance(96);
  const beforeHide = reversed.window.opacity;
  reversed.transition.hide();
  assert.equal(reversed.window.opacity, beforeHide, 'reversing to hide does not jump opacity');
  reversed.advance(20);
  const beforeReopen = reversed.window.opacity;
  assert.ok(beforeReopen < beforeHide);
  const position = reversed.window.getPosition();
  reversed.transition.show();
  assert.equal(reversed.window.opacity, beforeReopen, 'reopening continues from the current frame');
  assert.deepEqual(reversed.window.getPosition(), position);
  reversed.advance(500);
  assert.equal(reversed.window.isVisible(), true, 'an obsolete hide callback cannot hide the reopened client');
  assert.equal(reversed.window.opacity, 1);
  assert.equal(reversed.timers.size, 0);
  checks.push('rapid open/close/open reverses continuously and cancels obsolete callbacks');

  for (const opacity of [0, 0.4]) {
    const capped = fixture({ opacity });
    capped.transition.show();
    capped.advance(600);
    assert.equal(capped.window.opacity, opacity, 'external opacity settings are preserved');
    capped.transition.hide();
    capped.advance(200);
    assert.equal(capped.window.opacity, opacity);
  }
  const reduced = fixture({ reduced: true });
  reduced.transition.show();
  assert.equal(reduced.window.opacity, 1);
  assert.equal(reduced.timers.size, 0);
  reduced.transition.hide();
  assert.equal(reduced.window.isVisible(), false);
  assert.equal(reduced.timers.size, 0);
  const maximized = fixture({ maximized: true });
  maximized.transition.show();
  maximized.advance(600);
  assert.equal(maximized.trace.some((frame) => 'x' in frame), false, 'maximized windows fade without moving');
  checks.push('client respects reduced motion, maximization, and externally limited native opacity');

  const cancelled = fixture();
  cancelled.transition.show();
  cancelled.advance(32);
  cancelled.window.hide();
  cancelled.advance(400);
  assert.equal(cancelled.transition.isOpen(), false);
  assert.equal(cancelled.window.isVisible(), false);
  assert.equal(cancelled.window.opacity, 1);
  assert.equal(cancelled.timers.size, 0);
  cancelled.transition.show();
  cancelled.advance(32);
  cancelled.window.minimized = true;
  cancelled.window.emit('minimize');
  assert.equal(cancelled.window.opacity, 1, 'minimizing cannot strand the client at partial opacity');
  assert.equal(cancelled.timers.size, 0);
  cancelled.transition.show();
  cancelled.advance(32);
  cancelled.transition.dispose();
  cancelled.advance(500);
  assert.equal(cancelled.window.opacity, 1);
  assert.equal(cancelled.timers.size, 0);
  assert.equal(cancelled.window.listenerCount('hide'), 0);
  checks.push('native hide/minimize/dispose settle opacity and leave no animation timers or event handlers');

  const moved = fixture();
  moved.transition.show();
  moved.advance(600);
  moved.window.setPosition(320, 450);
  const positionCalls = moved.trace.filter((frame) => 'x' in frame).length;
  moved.transition.hide();
  moved.advance(240);
  assert.deepEqual(moved.window.getPosition(), [320, 450], 'closing fades at the user-selected position');
  assert.equal(moved.trace.filter((frame) => 'x' in frame).length, positionCalls);
  moved.transition.show();
  moved.advance(600);
  assert.deepEqual(moved.window.getPosition(), [100, 200], 'a fresh opening docks beside the mascot again');
  checks.push('manual window movement is preserved during fade-out and next opening redocks once');
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const checks = [];
  await assertClientTransitions(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'), checks);
  console.log(`Client transition checks passed (${checks.length}).`);
}
