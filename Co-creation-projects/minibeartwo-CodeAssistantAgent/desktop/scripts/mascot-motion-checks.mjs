/** Exercise rendered mascot frames, including interrupted transitions, in the isolated QA app. */
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { PNG } from 'pngjs';

export async function assertMascotMotion({
  bubblePage, application, nativeState, bubbleTitle, artifacts, checks, pause, eventually, animation,
}) {
  const button = bubblePage.locator('#bubble');
  // Reduced feedback lasts 180 ms, so observe transient states on browser frames.
  // An 80 ms Node poll plus media emulation round trips can miss a valid gesture.
  const hasPose = async (pose, motion) => {
    const state = await bubblePage.waitForFunction(({ pose, motion }) => {
      const target = document.getElementById('bubble');
      const image = document.getElementById('bubble-character');
      return target.dataset.pose === pose && target.dataset.motion === motion &&
        target.dataset.render === 'canvas' && image.complete && image.naturalWidth > 0 &&
        !!window.__mascotMotion?.snapshot;
    }, { pose, motion }, { timeout: 15000, polling: 'raf' }).catch((error) => {
      throw new Error(`Mascot must render ${pose}/${motion} on its decoded canvas: ${error.message}`);
    });
    await state.dispose();
  };
  const snapshot = () => bubblePage.evaluate(() => window.__mascotMotion.snapshot());
  const leave = async () => {
    await button.evaluate((element) => element.blur());
    await bubblePage.mouse.move(0, 0);
  };
  const focusNative = async () => {
    await application.evaluate(({ BrowserWindow }, title) => {
      BrowserWindow.getAllWindows().find((window) => window.getTitle() === title).focus();
    }, bubbleTitle);
    await eventually(() => application.evaluate(({ BrowserWindow }, title) =>
      BrowserWindow.getAllWindows().find((window) => window.getTitle() === title).isFocused(),
    bubbleTitle), 'The synthetic pointer must have an active native bubble');
  };
  const assertStopped = async (message) => {
    await eventually(async () => !(await snapshot()).running, `${message}: renderer settles`);
    const before = await snapshot();
    await pause(180);
    const after = await snapshot();
    assert.equal(after.frame, before.frame, `${message}: no background animation frames remain`);
    assert.equal(after.running, false, `${message}: requestAnimationFrame loop is stopped`);
  };
  const assertReducedFeedback = async () => {
    const before = await snapshot();
    assert.equal(before.running, false, 'reduced feedback starts without an animation loop');
    await pause(80);
    const after = await snapshot();
    assert.equal(after.running, false, 'reduced feedback keeps its animation loop stopped');
    assert.ok(after.frame - before.frame <= 1,
      'reduced feedback permits only its eventual static pose restoration');
  };
  const screenshot = (name) => bubblePage.screenshot({
    path: path.join(artifacts, `${name}.png`), omitBackground: true,
  });
  const startTrace = () => bubblePage.evaluate(() => {
    window.__mascotTraceObserver?.disconnect();
    window.__mascotTrace = [];
    const record = () => {
      const target = document.getElementById('bubble');
      window.__mascotTrace.push({ at: performance.now(), ...target.dataset });
    };
    window.__mascotTraceObserver = new MutationObserver(record);
    window.__mascotTraceObserver.observe(document.getElementById('bubble'), {
      attributes: true, attributeFilter: ['data-pose', 'data-motion', 'data-play'],
    });
    record();
  });
  const trace = () => bubblePage.evaluate(() => window.__mascotTrace);
  const assertFeedbackDuration = async (reduced = false) => {
    const entries = await trace();
    const clicks = entries.filter((entry) => entry.pose === 'click');
    assert.ok(clicks.length, 'an accepted activation enters click feedback');
    const token = clicks.at(-1).play;
    const began = clicks.find((entry) => entry.play === token).at;
    const ended = entries.find((entry) => entry.at > began && entry.pose !== 'click');
    assert.ok(ended, 'click feedback returns to the current pointer/focus state');
    assert.ok(
      ended.at - began >= (reduced ? 60 : animation.clickDurationMs - 120) &&
      ended.at - began <= (reduced ? 450 : animation.clickDurationMs + 600),
      `click feedback remains a complete bounded gesture: ${Math.round(ended.at - began)} ms`,
    );
  };

  // Sample the real canvas each browser frame. Premultiplied pixel differences detect
  // blank/decode flashes and picture replacements that status attributes alone cannot.
  const beginFrames = () => bubblePage.evaluate(() => {
    cancelAnimationFrame(window.__mascotSampleRaf);
    const surface = document.getElementById('bubble-motion');
    const context = surface.getContext('2d', { willReadFrequently: true });
    window.__mascotSamples = [];
    window.__mascotFilmstrip = [];
    let previous = null;
    let lastCapture = -Infinity;
    const collect = (at) => {
      const data = context.getImageData(0, 0, surface.width, surface.height).data;
      let left = surface.width; let top = surface.height; let right = -1; let bottom = -1;
      let mass = 0; let momentX = 0; let momentY = 0; let difference = 0;
      for (let i = 0; i < data.length; i += 4) {
        const alpha = data[i + 3] / 255;
        const x = (i / 4) % surface.width;
        const y = Math.floor(i / 4 / surface.width);
        if (data[i + 3] >= 32) {
          left = Math.min(left, x); top = Math.min(top, y);
          right = Math.max(right, x); bottom = Math.max(bottom, y);
        }
        mass += alpha; momentX += alpha * x; momentY += alpha * y;
        if (previous) {
          const before = previous[i + 3] / 255;
          difference += Math.abs(alpha - before);
          for (let channel = 0; channel < 3; channel++) {
            difference += Math.abs(data[i + channel] * alpha - previous[i + channel] * before) / 255;
          }
        }
      }
      const target = document.getElementById('bubble');
      window.__mascotSamples.push({
        at: performance.now(), rafAt: at, ...window.__mascotMotion.snapshot(), pose: target.dataset.pose,
        width: surface.width, height: surface.height,
        bounds: { left, top, right, bottom }, mass,
        centroid: { x: momentX / mass, y: momentY / mass },
        difference: previous ? difference / (surface.width * surface.height * 4) : 0,
      });
      if (at - lastCapture >= 85 && window.__mascotFilmstrip.length < 20) {
        window.__mascotFilmstrip.push({ at, png: surface.toDataURL('image/png') });
        lastCapture = at;
      }
      previous = data;
      if (window.__mascotSamples.length < 240) window.__mascotSampleRaf = requestAnimationFrame(collect);
    };
    window.__mascotSampleRaf = requestAnimationFrame(collect);
  });
  const endFrames = async (name) => {
    const result = await bubblePage.evaluate(() => {
      cancelAnimationFrame(window.__mascotSampleRaf);
      return { samples: window.__mascotSamples, filmstrip: window.__mascotFilmstrip };
    });
    const contiguous = result.samples.filter((entry, index, samples) =>
      index && entry.at - samples[index - 1].at < 55);
    const maxDifference = Math.max(...contiguous.map((entry) => entry.difference));
    const weightChange = (entry) => {
      const previous = result.samples[result.samples.indexOf(entry) - 1];
      return Math.max(...entry.weights.map((weight, index) => Math.abs(weight - previous.weights[index])));
    };
    // Event handlers may flush several real draws between two sampler callbacks.
    // Check the per-frame blend limit only where output diagnostics confirm that
    // these captures are adjacent, while retaining raw gap measurements below.
    const adjacentRenders = contiguous.filter((entry) => {
      const previous = result.samples[result.samples.indexOf(entry) - 1];
      return entry.frame - previous.frame <= 2 && entry.renderTime - previous.renderTime <= 35;
    });
    const maxWeightChange = Math.max(...adjacentRenders.map(weightChange));
    const rawMaxWeightChange = Math.max(...contiguous.map(weightChange));
    const renderDurations = result.samples.map((entry) => entry.renderDuration).filter(Number.isFinite).sort((a, b) => a - b);
    const renderDuration = {
      median: renderDurations[Math.floor(renderDurations.length / 2)],
      p95: renderDurations[Math.floor(renderDurations.length * 0.95)],
      max: renderDurations.at(-1),
    };
    await writeFile(path.join(artifacts, `${name}-frames.json`), JSON.stringify({
      samples: result.samples, maxDifference, maxWeightChange, rawMaxWeightChange, renderDuration,
    }, null, 2));
    if (result.filmstrip.length) {
      const images = result.filmstrip.map((entry) => PNG.sync.read(Buffer.from(entry.png.split(',')[1], 'base64')));
      const size = images[0].width;
      const columns = Math.min(8, images.length);
      const strip = new PNG({ width: columns * size, height: Math.ceil(images.length / columns) * size });
      images.forEach((image, index) => PNG.bitblt(image, strip, 0, 0, image.width, image.height,
        (index % columns) * size, Math.floor(index / columns) * size));
      await writeFile(path.join(artifacts, `${name}-filmstrip.png`), PNG.sync.write(strip));
    }
    assert.ok(result.samples.length >= 8, `${name}: actual browser frames were sampled`);
    assert.ok(result.samples.every((entry) => entry.mass > 1200 && entry.bounds.bottom > 0),
      `${name}: every canvas frame contains a visible character`);
    assert.ok(result.samples.every((entry) => Number.isFinite(entry.centroid.x)),
      `${name}: no transparent/decode flashes`);
    assert.ok(contiguous.length >= 5, `${name}: enough consecutive output frames were observed`);
    assert.ok(adjacentRenders.length >= 5, `${name}: enough adjacent renderer frames were observed`);
    assert.ok(maxDifference < 0.15,
      `${name}: adjacent rendered frames blend continuously (${maxDifference.toFixed(4)})`);
    assert.ok(maxWeightChange < 0.45,
      `${name}: pose blend continues from its current value (${maxWeightChange.toFixed(3)})`);
    assert.ok(result.samples.every((entry, index, samples) =>
      !index || entry.motionTime >= samples[index - 1].motionTime),
    `${name}: the animation clock never moves backwards`);
    assert.ok(result.samples.every((entry) => entry.meshQuality.every((quality) => quality === 1)),
      `${name}: every pose uses its full registered mesh without shrinking a flipped triangle`);
    assert.ok(result.samples.every((entry) => entry.weights.every((weight) => weight >= 0 && weight <= 1) &&
      Math.abs(entry.weights.reduce((sum, weight) => sum + weight, 0) - 1) < 0.0001),
    `${name}: visible pose coverage stays normalized through interrupted blends`);
    return result.samples;
  };
  const assertGrounded = (samples, message) => {
    const levels = samples.map((entry) => entry.bounds.bottom * 256 / entry.height + entry.jump);
    const range = Math.max(...levels) - Math.min(...levels);
    assert.ok(range <= 10,
      `${message}: visible feet keep a registered ground baseline (${range.toFixed(2)} source pixels)`);
  };

  await bubblePage.emulateMedia({ reducedMotion: 'no-preference' });
  await leave();
  await hasPose('idle', 'static');
  await assertStopped('idle');
  const idleComparison = await bubblePage.evaluate(async () => {
    const source = new Image();
    source.src = './assets/phoebe-idle.png';
    await source.decode();
    const actual = document.getElementById('bubble-motion');
    const reference = document.createElement('canvas');
    reference.width = actual.width; reference.height = actual.height;
    reference.getContext('2d').drawImage(source, 0, 0, reference.width, reference.height);
    const before = reference.getContext('2d').getImageData(0, 0, reference.width, reference.height).data;
    const after = actual.getContext('2d').getImageData(0, 0, actual.width, actual.height).data;
    let changed = 0; let largest = 0;
    for (let index = 0; index < before.length; index++) if (before[index] !== after[index]) {
      changed++; largest = Math.max(largest, Math.abs(before[index] - after[index]));
    }
    return { changed, largest };
  });
  assert.equal(idleComparison.changed, 0,
    `default idle draws the original image pixels directly: ${JSON.stringify(idleComparison)}`);
  const box = await button.boundingBox();
  assert.equal(box.width, 88, 'the character retains its 88 DIP interaction target');
  assert.equal(box.height, 88);
  await screenshot('phoebe-idle');
  await beginFrames();
  await button.hover();
  await hasPose('hover', 'animated');
  await pause(620);
  await screenshot('phoebe-hover');
  await leave();
  await hasPose('idle', 'static');
  const hoverFrames = await endFrames('phoebe-hover-transition');
  assert.ok(hoverFrames.some((entry) => entry.difference > 0.002), 'hover changes actual character pixels');
  assert.ok(hoverFrames.some((entry) => entry.mesh === 'registered-triangles' && entry.triangleCount > 0),
    'rendered transitions use the registered character mesh');
  assertGrounded(hoverFrames, 'hover enter/leave');
  checks.push('canvas hover eases in and out with continuous visible frames and a registered foot baseline');

  await beginFrames();
  for (let index = 0; index < 4; index++) {
    await button.hover(); await pause(65);
    await leave(); await pause(65);
  }
  await hasPose('idle', 'static');
  const reversed = await endFrames('phoebe-hover-interrupted');
  assertGrounded(reversed, 'rapid hover reversal');
  checks.push('rapid hover enter/leave reverses the current blend without a picture reset or empty frame');

  await bubblePage.keyboard.press('Tab');
  await eventually(() => button.evaluate((element) =>
    element === document.activeElement && element.matches(':focus-visible')),
  'Keyboard traversal visibly focuses the character button');
  await hasPose('hover', 'static');
  await assertStopped('keyboard focus');
  await screenshot('phoebe-keyboard-focus');
  await leave();
  await hasPose('idle', 'static');
  checks.push('keyboard focus shows its distinct static pose and stops animation work');

  await bubblePage.emulateMedia({ reducedMotion: 'reduce' });
  await button.hover();
  await hasPose('hover', 'reduced');
  await assertStopped('reduced-motion hover');
  await screenshot('phoebe-reduced-motion');
  await leave();
  await hasPose('idle', 'reduced');
  await bubblePage.emulateMedia({ reducedMotion: 'no-preference' });
  await hasPose('idle', 'static');
  checks.push('reduced-motion preference renders static poses and leaves no active animation loop');

  await focusNative();
  await startTrace();
  await beginFrames();
  await button.click();
  await hasPose('click', 'animated');
  assert.equal((await nativeState()).mainVisible, true, 'a tap opens the native client immediately');
  await bubblePage.evaluate(() => window.dispatchEvent(new Event('blur')));
  await hasPose('click', 'animated');
  await leave();
  await hasPose('idle', 'static');
  const clickFrames = await endFrames('phoebe-click-transition');
  await assertFeedbackDuration();
  assertGrounded(clickFrames, 'click jump and landing');
  const jumping = clickFrames.filter((entry) => entry.pose === 'click');
  const peak = Math.max(...jumping.map((entry) => entry.jump));
  assert.ok(peak > 3, `the click visibly leaves the ground (${peak.toFixed(2)} source pixels)`);
  const peakIndex = jumping.findIndex((entry) => entry.jump === peak);
  assert.ok(jumping.slice(0, peakIndex).some((entry, index, entries) =>
    index && entry.jump - entries[index - 1].jump > 0.25), 'jump visibly rises across successive frames');
  assert.ok(jumping.slice(peakIndex).some((entry, index, entries) =>
    index && entries[index - 1].jump - entry.jump > 0.25), 'jump visibly falls across successive frames');
  const nearPeak = jumping.filter((entry) => entry.jump >= peak * 0.92);
  assert.ok(nearPeak.at(-1).at - nearPeak[0].at < 180,
    'the jump passes through its apex instead of freezing in the air');
  checks.push('click anticipates, rises and falls continuously, lands on the same baseline and blends out despite native blur');

  await startTrace();
  await beginFrames();
  await button.focus();
  await bubblePage.keyboard.press('Enter');
  await hasPose('click', 'animated');
  const firstPlay = (await snapshot()).play;
  await eventually(async () => !(await nativeState()).mainVisible, 'Enter fades the client out during feedback');
  await pause(140);
  await bubblePage.keyboard.press('Space');
  await hasPose('click', 'animated');
  assert.ok((await snapshot()).play > firstPlay, 'rapid keyboard activation accepts a new gesture');
  assert.equal((await nativeState()).mainVisible, true, 'Space toggles immediately');
  await button.hover();
  await hasPose('hover', 'animated');
  await assertFeedbackDuration();
  await endFrames('phoebe-keyboard-replay');
  await leave();
  await hasPose('idle', 'static');
  checks.push('Enter and Space start feedback; rapid activation keeps the current rendered blend and restores hover');

  await startTrace();
  await button.evaluate((element) => element.click());
  await hasPose('click', 'animated');
  await eventually(async () => !(await nativeState()).mainVisible, 'assistive activation fades the client out');
  await pause(190);
  await screenshot('phoebe-click');
  await leave();
  await hasPose('idle', 'static');
  await assertFeedbackDuration();
  checks.push('assistive activation uses the same complete click gesture and returns to idle');

  await focusNative();
  await startTrace();
  await beginFrames();
  await button.click();
  await hasPose('click', 'animated');
  const pointerPlay = (await snapshot()).play;
  assert.equal((await nativeState()).mainVisible, true, 'first rapid pointer tap opens the client');
  await focusNative();
  await bubblePage.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(await button.getAttribute('data-pose'), 'click', 'second tap occurs during feedback');
  await button.click();
  await hasPose('click', 'animated');
  await eventually(async () => (await snapshot()).play > pointerPlay,
    'second pointer tap accepts a new gesture after native drag validation');
  await eventually(async () => !(await nativeState()).mainVisible, 'second rapid pointer tap finishes hiding the client');
  await leave();
  await hasPose('idle', 'static');
  await assertFeedbackDuration();
  const rapidFrames = await endFrames('phoebe-pointer-replay');
  const releases = (await trace()).filter((entry, index, entries) =>
    index && entries[index - 1].pose === 'pressed' && entry.pose !== 'pressed');
  assert.ok(releases.every((entry) => entry.pose === 'click'),
    'a completed tap goes directly from held pose into click feedback with no hover flash');
  assertGrounded(rapidFrames, 'rapid click replay');
  checks.push('rapid pointer taps continue from the visible pose and never insert hover between press and click');

  await bubblePage.emulateMedia({ reducedMotion: 'reduce' });
  await startTrace();
  await button.click();
  await hasPose('click', 'reduced');
  assert.equal((await nativeState()).mainVisible, true, 'reduced-motion tap still opens the client immediately');
  await screenshot('phoebe-click-reduced-motion');
  await assertReducedFeedback();
  await leave();
  await hasPose('idle', 'reduced');
  await assertFeedbackDuration(true);
  checks.push('reduced-motion activation gives timed static feedback without an animation loop');

  await bubblePage.emulateMedia({ reducedMotion: 'no-preference' });
  await button.focus();
  // The preceding reduced pointer gesture ends before its 400 ms duplicate-click
  // guard. A fresh keyboard activation is independent of that pointer guard.
  await bubblePage.keyboard.press('Enter');
  await hasPose('click', 'animated');
  await bubblePage.emulateMedia({ reducedMotion: 'reduce' });
  await hasPose('click', 'reduced');
  await assertReducedFeedback();
  await bubblePage.emulateMedia({ reducedMotion: 'no-preference' });
  await hasPose('click', 'animated');
  await leave();
  await hasPose('idle', 'static');
  assert.equal((await nativeState()).mainVisible, false, 'motion checks leave the client hidden');
  checks.push('a motion preference change takes effect during the active gesture');

  await focusNative();
  await startTrace();
  await button.hover();
  await button.evaluate((element) => element.addEventListener('pointerdown', (event) => {
    window.__mascotSmokePointerId = event.pointerId;
  }, { once: true }));
  await bubblePage.mouse.down();
  await eventually(() => button.getAttribute('data-pose').then((pose) => pose === 'pressed'),
    'pointer down enters the held pose');
  const pointerId = await bubblePage.evaluate(() => window.__mascotSmokePointerId);
  await button.dispatchEvent('pointercancel', { pointerId, isPrimary: true, pointerType: 'mouse' });
  await bubblePage.mouse.up();
  await eventually(() => button.getAttribute('data-pose').then((pose) => pose !== 'pressed'),
    'canceled pointer capture releases the held pose');
  await pause(120);
  assert.equal((await nativeState()).mainVisible, false, 'pointer cancellation never toggles the client');
  assert.ok(!(await trace()).some((entry) => entry.pose === 'click'), 'canceled gesture never plays click feedback');
  await application.evaluate(({ Menu }) => {
    global.__mascotSmokeRealPopup = Menu.prototype.popup;
    global.__mascotSmokeMenuOpened = false;
    Menu.prototype.popup = function () { global.__mascotSmokeMenuOpened = true; };
  });
  await startTrace();
  await button.dispatchEvent('contextmenu', { button: 2 });
  await eventually(() => application.evaluate(() => global.__mascotSmokeMenuOpened),
    'context menu reaches the native menu');
  assert.equal((await nativeState()).mainVisible, false, 'context menu never toggles the client');
  assert.ok(!(await trace()).some((entry) => entry.pose === 'click'), 'context menu never plays click feedback');
  await application.evaluate(({ Menu }) => { Menu.prototype.popup = global.__mascotSmokeRealPopup; });
  await leave();
  await hasPose('idle', 'static');
  checks.push('pointer cancellation and native context menu preserve the client state without click feedback');
}
