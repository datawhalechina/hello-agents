/* One interruptible clock drives geometry, texture blending and the jump trajectory. */
(() => {
  'use strict';

  const ids = ['idle', 'hover0', 'hover1', 'hover2', 'anticipate', 'air', 'land'];
  const clamp = (value, low = 0, high = 1) => Math.max(low, Math.min(high, value));
  const ease = (value) => {
    const t = clamp(value);
    return t * t * t * (t * (t * 6 - 15) + 10);
  };
  const lerp = (a, b, t) => a + (b - a) * t;
  const single = (index) => ids.map((_, current) => Number(current === index));
  const blend = (from, to, amount) => from.map((value, index) => lerp(value, to[index], amount));
  const copy = (value) => ({ ...value, weights: [...value.weights] });
  const round = (value) => Number(value.toFixed(5));
  const area = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);

  // Use one topology for every expression. Eye, cheek, chin, torso and boot vertices
  // correspond across textures, so fading expressions does not duplicate the face.
  function triangulate(vertices, size) {
    const points = [...vertices, [-size * 8, -size * 4], [size * 9, -size * 4], [size / 2, size * 10]];
    const count = vertices.length;
    let triangles = [[count, count + 1, count + 2]];
    function inside(point, triangle) {
      const [a, b, c] = triangle.map((index) => points[index]);
      const ax = a[0] - point[0]; const ay = a[1] - point[1];
      const bx = b[0] - point[0]; const by = b[1] - point[1];
      const cx = c[0] - point[0]; const cy = c[1] - point[1];
      const determinant = (ax * ax + ay * ay) * (bx * cy - by * cx)
        - (bx * bx + by * by) * (ax * cy - ay * cx)
        + (cx * cx + cy * cy) * (ax * by - ay * bx);
      return determinant * Math.sign(area(a, b, c)) > 0.00001;
    }
    for (let index = 0; index < count; index += 1) {
      const bad = triangles.filter((triangle) => inside(points[index], triangle));
      const edges = new Map();
      for (const triangle of bad) {
        for (let edge = 0; edge < 3; edge += 1) {
          const a = triangle[edge]; const b = triangle[(edge + 1) % 3];
          const key = a < b ? `${a}:${b}` : `${b}:${a}`;
          if (edges.has(key)) edges.delete(key);
          else edges.set(key, [a, b]);
        }
      }
      triangles = triangles.filter((triangle) => !bad.includes(triangle));
      for (const [a, b] of edges.values()) {
        const triangle = area(points[a], points[b], points[index]) > 0 ? [a, b, index] : [b, a, index];
        if (Math.abs(area(...triangle.map((vertex) => points[vertex]))) > 0.0001) triangles.push(triangle);
      }
    }
    return triangles.filter((triangle) => triangle.every((index) => index < count));
  }

  function loadImage(source) {
    const image = new Image();
    image.decoding = 'async';
    image.src = source;
    return image.decode().then(() => image);
  }

  function create({ button, character, canvas, reducedMotion }) {
    const configuration = window.PHOEBE_POSES;
    const size = configuration?.size || 256;
    const ground = configuration?.groundY || 243;
    const pivot = configuration?.footCenterX || size / 2;
    const context = canvas.getContext('2d', { alpha: true });
    const layer = document.createElement('canvas');
    layer.width = size; layer.height = size;
    const layerContext = layer.getContext('2d', { alpha: true });
    canvas.width = size; canvas.height = size;
    let ready = false;
    let failed = false;
    let disposed = false;
    let raf = null;
    let realTime = performance.now();
    let animationTime = realTime;
    let lastTime = animationTime;
    let renderTime = realTime;
    let renderDuration = 0;
    let input = { hovered: false, focused: false, pressed: false };
    let visible = { weights: single(0), jump: 0, scaleX: 1, scaleY: 1, phase: 'idle', progress: 1 };
    let weightVelocity = ids.map(() => 0);
    let transition = null;
    let click = null;
    let held = null;
    let hoverStart = lastTime;
    let pressScale = 1;
    let frame = 0;
    let play = 0;
    let reducedClick = false;
    let staticTimer = null;
    let atlas;
    let original;
    let textures = [];
    let meshes = [];
    let triangles = [];
    let meshQuality = [];
    let diagnostics = {};

    const destination = () => input.hovered || input.focused ? 1 : 0;
    const targetVisual = () => ({ weights: single(destination()), jump: 0, scaleX: 1, scaleY: 1 });

    function motionNow() {
      const actual = Math.max(realTime, performance.now());
      // Opening a native window can stall one frame. Preserve the action's
      // intermediate poses instead of skipping the whole anticipation or landing.
      animationTime += Math.min(20, actual - realTime);
      realTime = actual;
      return animationTime;
    }

    function clearStaticTimer() {
      if (staticTimer !== null) window.clearTimeout(staticTimer);
      staticTimer = null;
    }

    function stop() {
      if (raf !== null) window.cancelAnimationFrame(raf);
      raf = null;
    }

    function transitionToDestination(now, duration = 380) {
      transition = { from: copy(visible), velocity: [...weightVelocity], start: now, duration, destination: destination() };
      click = null;
    }

    function isMoving() {
      return ready && !reducedMotion.matches && !disposed
        && (Math.abs(pressScale - (input.pressed ? 0.967 : 1)) > 0.0001
          || (!held && Boolean(click || transition || input.hovered)));
    }

    function schedule() {
      if (raf === null && isMoving()) raf = window.requestAnimationFrame(tick);
    }

    function hover(now) {
      // A slow round trip, with zero velocity at each extreme, replaces frame steps.
      const cycle = (now - hoverStart) / 2100 * Math.PI * 2;
      const position = 1 - Math.cos(cycle);
      const left = position < 1 ? 1 : 2;
      const right = position < 1 ? 2 : 3;
      const amount = ease(position < 1 ? position : position - 1);
      return {
        weights: blend(single(left), single(right), amount),
        jump: 0,
        scaleX: 1 - 0.0015 * Math.sin(cycle),
        scaleY: 1 + 0.0025 * Math.sin(cycle),
        phase: 'hover-loop',
        progress: ((now - hoverStart) % 2100) / 2100,
      };
    }

    function continueJump(elapsed) {
      // A second activation starts at the currently visible height and velocity.
      // The inherited trajectory decays smoothly; it never teleports to the floor.
      const duration = 400;
      const t = clamp(elapsed / duration);
      const h00 = 2 * t ** 3 - 3 * t ** 2 + 1;
      const h10 = t ** 3 - 2 * t ** 2 + t;
      return Math.max(0, h00 * click.from.jump + h10 * click.velocity * duration / 1000);
    }

    function clickVisual(now) {
      const elapsed = Math.max(0, now - click.start);
      const duration = click.end - click.start;
      const carry = continueJump(elapsed);
      if (elapsed < 120) {
        const progress = ease(elapsed / 120);
        return {
          weights: blend(click.from.weights, single(4), progress),
          jump: carry,
          scaleX: lerp(click.from.scaleX, 1.035, progress),
          scaleY: lerp(click.from.scaleY, 0.94, progress),
          phase: 'click-anticipate', progress: elapsed / duration,
        };
      }
      if (elapsed < 400) {
        const airTime = elapsed - 120;
        const progress = airTime / 280;
        let weights = blend(single(4), single(5), ease(airTime / 105));
        if (airTime > 190) weights = blend(single(5), single(6), ease((airTime - 190) / 90));
        return {
          weights,
          jump: carry + 14 * 4 * progress * (1 - progress),
          scaleX: lerp(1.035, 1, ease(airTime / 70)) - 0.015 * Math.sin(Math.PI * progress),
          scaleY: lerp(0.94, 1, ease(airTime / 70)) + 0.025 * Math.sin(Math.PI * progress),
          phase: 'click-air', progress: elapsed / duration,
        };
      }
      if (elapsed < 520) {
        const progress = (elapsed - 400) / 120;
        const compression = Math.sin(Math.PI * progress) ** 2;
        return {
          weights: single(6), jump: 0,
          scaleX: 1 + 0.028 * compression,
          scaleY: 1 - 0.055 * compression,
          phase: 'click-land', progress: elapsed / duration,
        };
      }
      if (!click.settle) {
        click.settle = { from: { weights: single(6), jump: 0, scaleX: 1, scaleY: 1 }, start: click.start + 520, duration: 280, destination: destination() };
      }
      const progress = ease((now - click.settle.start) / click.settle.duration);
      const result = {
        weights: blend(click.settle.from.weights, single(click.settle.destination), progress),
        jump: lerp(click.settle.from.jump, 0, progress),
        scaleX: lerp(click.settle.from.scaleX, 1, progress),
        scaleY: lerp(click.settle.from.scaleY, 1, progress),
        phase: 'click-settle', progress: clamp(elapsed / duration),
      };
      if (now >= click.end) {
        click = null;
        hoverStart = now;
        result.phase = input.hovered ? 'hover-loop' : 'idle';
        result.progress = 1;
      }
      return result;
    }

    function evaluate(time) {
      const now = Math.max(time, lastTime);
      const delta = clamp(now - lastTime, 0, 80);
      lastTime = now;
      if (reducedMotion.matches) {
        pressScale = 1;
        visible = { ...targetVisual(), weights: single(reducedClick ? 6 : destination()), phase: reducedClick ? 'reduced-click' : 'reduced', progress: 1 };
        return;
      }
      const targetScale = input.pressed ? 0.967 : 1;
      pressScale = lerp(pressScale, targetScale, 1 - Math.exp(-delta / 42));
      if (Math.abs(pressScale - targetScale) < 0.0001) pressScale = targetScale;
      if (held) {
        visible = { ...copy(held.visual), phase: 'held' };
        return;
      }
      if (click) {
        visible = clickVisual(now);
        return;
      }
      if (transition) {
        const progress = clamp((now - transition.start) / transition.duration);
        const amount = ease(progress);
        // Preserve the outgoing velocity during a quick hover reversal. This
        // quintic basis reaches zero displacement, velocity and acceleration at
        // the destination, while starting with the currently visible velocity.
        const tangent = progress - 6 * progress ** 3 + 8 * progress ** 4 - 3 * progress ** 5;
        const weights = blend(transition.from.weights, single(transition.destination), amount)
          .map((weight, index) => clamp(weight + transition.velocity[index] * transition.duration / 1000 * tangent));
        const total = weights.reduce((sum, weight) => sum + weight, 0) || 1;
        visible = {
          weights: weights.map((weight) => weight / total),
          jump: lerp(transition.from.jump, 0, amount),
          scaleX: lerp(transition.from.scaleX, 1, amount),
          scaleY: lerp(transition.from.scaleY, 1, amount),
          phase: transition.destination ? 'hover-enter' : 'hover-exit', progress,
        };
        if (progress >= 1) {
          transition = null;
          hoverStart = now;
          visible.phase = input.hovered ? 'hover-loop' : 'idle';
        }
        return;
      }
      visible = input.hovered ? hover(now) : { ...targetVisual(), phase: input.focused ? 'focus' : 'idle', progress: 1 };
    }

    function advance(time) {
      const previous = visible.weights;
      const previousTime = lastTime;
      evaluate(time);
      const elapsed = (lastTime - previousTime) / 1000;
      if (held || reducedMotion.matches) weightVelocity = ids.map(() => 0);
      else if (elapsed > 0) weightVelocity = visible.weights.map((weight, index) => (weight - previous[index]) / elapsed);
    }

    function warpTexture(texture, source, destinationMesh) {
      layerContext.setTransform(1, 0, 0, 1, 0, 0);
      layerContext.clearRect(0, 0, size, size);
      layerContext.globalCompositeOperation = 'source-over';
      for (const triangle of triangles) {
        const [a, b, c] = triangle.map((index) => source[index]);
        const [p, q, r] = triangle.map((index) => destinationMesh[index]);
        const determinant = area(a, b, c);
        if (Math.abs(determinant) < 0.0001 || Math.abs(area(p, q, r)) < 0.0001) continue;
        const sourceX1 = b[0] - a[0]; const sourceY1 = b[1] - a[1];
        const sourceX2 = c[0] - a[0]; const sourceY2 = c[1] - a[1];
        const targetX1 = q[0] - p[0]; const targetY1 = q[1] - p[1];
        const targetX2 = r[0] - p[0]; const targetY2 = r[1] - p[1];
        const aa = (targetX1 * sourceY2 - targetX2 * sourceY1) / determinant;
        const bb = (targetY1 * sourceY2 - targetY2 * sourceY1) / determinant;
        const cc = (targetX2 * sourceX1 - targetX1 * sourceX2) / determinant;
        const dd = (targetY2 * sourceX1 - targetY1 * sourceX2) / determinant;
        const ee = p[0] - aa * a[0] - cc * a[1];
        const ff = p[1] - bb * a[0] - dd * a[1];
        const center = [(p[0] + q[0] + r[0]) / 3, (p[1] + q[1] + r[1]) / 3];
        // Subpixel overlap closes antialias seams within a pose. Poses themselves
        // are then added as premultiplied layers, rather than source-over ghosts.
        const expanded = [p, q, r].map((point) => {
          const length = Math.hypot(point[0] - center[0], point[1] - center[1]) || 1;
          return [point[0] + 0.32 * (point[0] - center[0]) / length, point[1] + 0.32 * (point[1] - center[1]) / length];
        });
        layerContext.save();
        layerContext.beginPath();
        layerContext.moveTo(...expanded[0]); layerContext.lineTo(...expanded[1]); layerContext.lineTo(...expanded[2]);
        layerContext.closePath(); layerContext.clip();
        layerContext.setTransform(aa, bb, cc, dd, ee, ff);
        layerContext.drawImage(texture, 0, 0);
        layerContext.restore();
      }
    }

    function publish() {
      const clicking = Boolean(click || reducedClick);
      const pose = input.pressed ? 'pressed' : clicking ? 'click' : input.hovered || input.focused ? 'hover' : 'idle';
      const motion = reducedMotion.matches ? 'reduced' : isMoving() ? 'animated' : 'static';
      button.classList.toggle('hovering', pose === 'hover');
      diagnostics = {
        render: ready ? 'canvas' : 'image', pose, motion,
        phase: visible.phase, progress: round(visible.progress), play, frame,
        jump: round(visible.jump), ground: round(ground - visible.jump),
        scale: round(pressScale * visible.scaleY), weights: visible.weights.map(round),
        renderTime: round(renderTime), renderDuration: round(renderDuration), motionTime: round(lastTime),
        mesh: 'registered-triangles', triangleCount: triangles.length, meshQuality,
      };
      for (const name of ['render', 'pose', 'motion', 'phase', 'progress', 'play', 'frame', 'jump', 'ground', 'scale']) {
        button.dataset[name] = String(diagnostics[name]);
      }
      button.dataset.weights = JSON.stringify(diagnostics.weights);
      button.dataset.mesh = diagnostics.mesh;
      button.dataset.running = String(isMoving());
    }

    function render() {
      const started = performance.now();
      if (!ready) {
        const source = reducedClick || click ? './assets/phoebe-click-still.png'
          : input.hovered || input.focused ? './assets/phoebe-hover-still.png' : './assets/phoebe-idle.png';
        if (failed && character.getAttribute('src') !== source) character.setAttribute('src', source);
        publish();
        return;
      }
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.clearRect(0, 0, size, size);
      context.globalCompositeOperation = 'source-over';
      context.globalAlpha = 1;
      const scaleX = visible.scaleX * pressScale;
      const scaleY = visible.scaleY * pressScale;
      context.setTransform(scaleX, 0, 0, scaleY, pivot * (1 - scaleX), ground * (1 - scaleY) - visible.jump);
      if (visible.weights[0] >= 0.9999999) {
        // At rest, retain the exact supplied image, without a warp or redraw style.
        context.drawImage(original, 0, 0, size, size);
      } else {
        const targetMesh = meshes[0].map((_, index) => [
          meshes.reduce((sum, mesh, pose) => sum + mesh[index][0] * visible.weights[pose], 0),
          meshes.reduce((sum, mesh, pose) => sum + mesh[index][1] * visible.weights[pose], 0),
        ]);
        context.globalCompositeOperation = 'lighter';
        for (let index = 0; index < textures.length; index += 1) {
          if (visible.weights[index] < 0.00001) continue;
          warpTexture(textures[index], meshes[index], targetMesh);
          context.globalAlpha = visible.weights[index];
          context.drawImage(layer, 0, 0);
        }
      }
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.globalAlpha = 1;
      context.globalCompositeOperation = 'source-over';
      frame += 1;
      renderTime = performance.now();
      renderDuration = renderTime - started;
      publish();
    }

    function flush() {
      const now = motionNow();
      advance(now);
      render();
      return now;
    }

    function tick() {
      raf = null;
      if (disposed) return;
      // RAF timestamps can predate intervening pointer events; use one clock.
      flush();
      schedule();
    }

    function setInteraction(next) {
      const now = flush();
      const previous = input;
      input = { ...input, ...next };
      if (reducedMotion.matches) {
        stop();
        click = null; transition = null; held = null;
      } else if (input.pressed && !previous.pressed) {
        held = { visual: copy(visible), start: now };
      } else if (!input.pressed && previous.pressed && held) {
        const paused = now - held.start;
        if (click) {
          click.start += paused; click.end += paused;
          if (click.settle) click.settle.start += paused;
          if (click.settle && click.settle.destination !== destination()) {
            click.settle = { from: copy(visible), start: now, duration: Math.max(160, click.end - now), destination: destination() };
            click.end = now + click.settle.duration;
          }
        }
        if (transition) transition.start += paused;
        held = null;
        if (!click) transitionToDestination(now, 320);
      }
      const destinationChanged = previous.hovered !== input.hovered || previous.focused !== input.focused;
      if (!reducedMotion.matches && destinationChanged && !held) {
        if (click?.settle) {
          click.settle = { from: copy(visible), start: now, duration: Math.max(160, click.end - now), destination: destination() };
          click.end = now + click.settle.duration;
        } else if (!click) {
          // Keyboard focus also enters continuously, then leaves no idle RAF.
          transitionToDestination(now, input.hovered ? 420 : 380);
        }
      }
      render();
      schedule();
    }

    function playClick() {
      const now = flush();
      clearStaticTimer();
      play += 1;
      if (reducedMotion.matches || failed) {
        reducedClick = true;
        staticTimer = window.setTimeout(() => {
          reducedClick = false; staticTimer = null;
          flush();
        }, 180);
        advance(now); render();
        return;
      }
      let velocity = 0;
      if (click && !held) {
        const elapsed = now - click.start;
        if (elapsed >= 120 && elapsed < 400) velocity = 56 / 0.28 * (1 - 2 * ((elapsed - 120) / 280));
      }
      click = { from: copy(visible), start: now, end: now + 800, velocity, settle: null };
      transition = null;
      // Native validation may still own the held flag until its finally block.
      if (held) held.start = now;
      render();
      schedule();
    }

    function cancelClick() {
      const now = flush();
      clearStaticTimer(); reducedClick = false;
      click = null;
      if (!held && !reducedMotion.matches) transitionToDestination(now, 320);
      render(); schedule();
    }

    function motionPreferenceChanged() {
      const now = motionNow();
      const acceptedClick = Boolean(click || reducedClick);
      const from = copy(visible);
      stop(); clearStaticTimer();
      click = null; transition = null; held = null;
      pressScale = 1;
      hoverStart = now;
      reducedClick = reducedMotion.matches && acceptedClick;
      visible = { ...targetVisual(), weights: single(reducedClick ? 6 : destination()), phase: reducedMotion.matches ? 'reduced' : 'idle', progress: 1 };
      if (reducedClick) {
        staticTimer = window.setTimeout(() => {
          reducedClick = false; staticTimer = null;
          flush();
        }, 180);
      } else if (!reducedMotion.matches && acceptedClick) {
        // Resume feedback with a short continuous landing/settle, rather than
        // restarting the jump or snapping away from its static accessibility pose.
        visible = from;
        click = {
          from, start: now - 520, end: now + 240, velocity: 0,
          settle: { from, start: now, duration: 240, destination: destination() },
        };
      }
      if (!reducedMotion.matches && input.pressed) held = { visual: copy(visible), start: now };
      advance(now); render(); schedule();
    }

    const api = {
      setInteraction, playClick, cancelClick, motionPreferenceChanged,
      snapshot: () => ({ ...diagnostics, weights: [...(diagnostics.weights || [])], running: raf !== null }),
      dispose() { disposed = true; stop(); clearStaticTimer(); },
    };
    window.__mascotMotion = Object.freeze({ snapshot: api.snapshot });

    Promise.resolve().then(async () => {
      if (!configuration || !context || !layerContext) throw new Error('Missing mascot resources');
      [atlas, original] = await Promise.all([loadImage(configuration.atlas), loadImage('./assets/phoebe-idle.png')]);
      if (disposed) return;
      const poses = ids.map((id) => {
        const pose = configuration.poses.find((entry) => entry.id === id);
        if (!pose) throw new Error(`Missing mascot pose ${id}`);
        return pose;
      });
      const names = Object.keys(poses[0].anchors);
      meshes = poses.map((pose) => names.map((name) => [...pose.anchors[name]]));
      triangles = triangulate(meshes[0], size);
      if (triangles.length < 10) throw new Error('Invalid mascot correspondence mesh');
      meshQuality = meshes.map((mesh, index) => {
        if (!index) return 1;
        let amount = 1;
        const originalMesh = mesh.map((point) => [...point]);
        while (amount > 0.05 && triangles.some((triangle) => area(...triangle.map((vertex) => mesh[vertex])) < 0.2)) {
          amount *= 0.9;
          for (let vertex = 0; vertex < mesh.length; vertex += 1) {
            mesh[vertex] = [lerp(meshes[0][vertex][0], originalMesh[vertex][0], amount), lerp(meshes[0][vertex][1], originalMesh[vertex][1], amount)];
          }
        }
        return round(amount);
      });
      textures = poses.map((pose) => {
        const texture = document.createElement('canvas');
        texture.width = size; texture.height = size;
        texture.getContext('2d').drawImage(atlas, ...pose.rect, 0, 0, size, size);
        return texture;
      });
      ready = true;
      const now = motionNow();
      lastTime = now;
      advance(now); render(); schedule();
    }).catch((error) => {
      failed = true;
      console.error('Mascot canvas unavailable; retaining static character.', error);
      render();
    });
    render();
    return api;
  }

  window.PhoebeMotion = Object.freeze({ create });
})();
