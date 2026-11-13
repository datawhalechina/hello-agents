/**
 * Encode the approved transparent 3-column x 2-row action sheet.
 * All cells share one crop, scale, and placement, preserving source pose offsets.
 * The existing idle portrait and original source image are never overwritten.
 * Usage: node scripts/build-mascot-assets.mjs <actions-sheet.png> [output-dir] [192|256]
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { PNG } from 'pngjs';
import gifenc from 'gifenc';

const { GIFEncoder, quantize, applyPalette } = gifenc;
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const [sourceArg, outputArg, sizeArg = '256', ...extra] = process.argv.slice(2);
if (!sourceArg || extra.length || !['192', '256'].includes(sizeArg)) {
  console.error('Usage: node scripts/build-mascot-assets.mjs <actions-sheet.png> [output-dir] [192|256]');
  process.exit(1);
}

const source = path.resolve(sourceArg);
const outputDir = path.resolve(outputArg || path.join(scriptDir, '../electron/assets'));
const size = Number(sizeArg);
const filenames = [
  'phoebe-hover-still.png', 'phoebe-hover.gif',
  'phoebe-click-still.png', 'phoebe-click.gif', 'phoebe-animation.json',
  'phoebe-poses.png', 'phoebe-poses.js',
];
const samePath = (a, b) => a.toLocaleLowerCase('en-US') === b.toLocaleLowerCase('en-US');
if (filenames.some((name) => samePath(path.join(outputDir, name), source))) {
  throw new Error('The action sheet must be separate from the output asset files.');
}

// Guard the accepted idle artwork against any accidental changes during encoding.
const protectedAssets = ['phoebe-source.png', 'phoebe-idle.png'];
const hashFile = (filename) => fs.existsSync(filename)
  ? crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex') : null;
const protectedHashes = Object.fromEntries(protectedAssets.map((name) => [
  name, hashFile(path.join(outputDir, name)),
]));

const sheet = PNG.sync.read(fs.readFileSync(source));
const columns = 3;
const rows = 2;
if (sheet.width % columns !== 0 || sheet.height % rows !== 0) {
  throw new Error(`The action sheet must divide evenly into 3 columns and 2 rows; received ${sheet.width}x${sheet.height}.`);
}
const cellWidth = sheet.width / columns;
const cellHeight = sheet.height / rows;
if (cellWidth < 32 || cellHeight < 32) {
  throw new Error('Every action-sheet cell must be at least 32x32 pixels.');
}

// Normalize only the alpha silhouette: retain the largest connected character
// and its two-pixel antialiased fringe; never recolour or redraw the source art.
const cleanupThreshold = 32;
const fringeRadius = 2;
const cleanupFrames = [];
const cleanedSheet = { ...sheet, data: Buffer.from(sheet.data) };
for (let frame = 0; frame < columns * rows; frame++) {
  const originX = (frame % columns) * cellWidth;
  const originY = Math.floor(frame / columns) * cellHeight;
  const alphaAt = (pixel) => sheet.data[
    ((originY + Math.floor(pixel / cellWidth)) * sheet.width + originX + pixel % cellWidth) * 4 + 3
  ];
  const labels = new Int32Array(cellWidth * cellHeight);
  const queue = new Int32Array(labels.length);
  let componentsFound = 0;
  let mainLabel = 0;
  let mainCorePixels = 0;
  let totalCorePixels = 0;
  for (let pixel = 0; pixel < labels.length; pixel++) {
    if (labels[pixel] || alphaAt(pixel) < cleanupThreshold) continue;
    const label = ++componentsFound;
    let head = 0;
    let tail = 0;
    labels[pixel] = label;
    queue[tail++] = pixel;
    while (head < tail) {
      const current = queue[head++];
      const x = current % cellWidth;
      const y = Math.floor(current / cellWidth);
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const nx = x + dx;
          const ny = y + dy;
          if (nx < 0 || nx >= cellWidth || ny < 0 || ny >= cellHeight) continue;
          const neighbor = ny * cellWidth + nx;
          if (!labels[neighbor] && alphaAt(neighbor) >= cleanupThreshold) {
            labels[neighbor] = label;
            queue[tail++] = neighbor;
          }
        }
      }
    }
    totalCorePixels += tail;
    if (tail > mainCorePixels) {
      mainCorePixels = tail;
      mainLabel = label;
    }
  }
  if (!mainLabel) throw new Error(`Cell ${frame} has no visible connected character.`);

  const keep = new Uint8Array(labels.length);
  for (let pixel = 0; pixel < labels.length; pixel++) {
    if (labels[pixel] !== mainLabel) continue;
    keep[pixel] = 1;
    const x = pixel % cellWidth;
    const y = Math.floor(pixel / cellWidth);
    for (let dy = -fringeRadius; dy <= fringeRadius; dy++) {
      for (let dx = -fringeRadius; dx <= fringeRadius; dx++) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || nx >= cellWidth || ny < 0 || ny >= cellHeight) continue;
        const neighbor = ny * cellWidth + nx;
        if (alphaAt(neighbor) < cleanupThreshold) keep[neighbor] = 1;
      }
    }
  }

  let originalVisiblePixels = 0;
  let keptVisiblePixels = 0;
  let droppedVisiblePixels = 0;
  let normalizedTransparentPixels = 0;
  for (let pixel = 0; pixel < labels.length; pixel++) {
    const offset = ((originY + Math.floor(pixel / cellWidth)) * sheet.width
      + originX + pixel % cellWidth) * 4;
    const alpha = sheet.data[offset + 3];
    if (alpha > 0) {
      originalVisiblePixels++;
      if (keep[pixel]) keptVisiblePixels++;
      else droppedVisiblePixels++;
    } else if (sheet.data[offset] || sheet.data[offset + 1] || sheet.data[offset + 2]) {
      normalizedTransparentPixels++;
    }
    // Erase unused RGB as well as alpha so transparent pixels remain canonical.
    if (!keep[pixel] || alpha === 0) cleanedSheet.data.fill(0, offset, offset + 4);
  }
  cleanupFrames.push({
    frame, componentsFound, mainCorePixels,
    discardedCorePixels: totalCorePixels - mainCorePixels,
    originalVisiblePixels, keptVisiblePixels, droppedVisiblePixels,
    normalizedTransparentPixels,
  });
}

const commonBounds = { left: cellWidth, top: cellHeight, right: -1, bottom: -1 };
const cellBounds = [];
for (let frame = 0; frame < columns * rows; frame++) {
  const originX = (frame % columns) * cellWidth;
  const originY = Math.floor(frame / columns) * cellHeight;
  const bounds = { left: cellWidth, top: cellHeight, right: -1, bottom: -1 };
  let transparent = false;
  let opaque = false;
  for (let y = 0; y < cellHeight; y++) {
    for (let x = 0; x < cellWidth; x++) {
      const alpha = cleanedSheet.data[((originY + y) * sheet.width + originX + x) * 4 + 3];
      if (alpha === 0) transparent = true;
      if (alpha >= 128) opaque = true;
      // Near-invisible specks do not control the shared silhouette crop.
      if (alpha >= 16) {
        bounds.left = Math.min(bounds.left, x);
        bounds.top = Math.min(bounds.top, y);
        bounds.right = Math.max(bounds.right, x);
        bounds.bottom = Math.max(bounds.bottom, y);
      }
    }
  }
  if (bounds.right < 0 || !transparent || !opaque) {
    throw new Error(`Cell ${frame} must contain visible artwork and a transparent background.`);
  }
  cellBounds.push(bounds);
  commonBounds.left = Math.min(commonBounds.left, bounds.left);
  commonBounds.top = Math.min(commonBounds.top, bounds.top);
  commonBounds.right = Math.max(commonBounds.right, bounds.right);
  commonBounds.bottom = Math.max(commonBounds.bottom, bounds.bottom);
}

const cropWidth = commonBounds.right - commonBounds.left + 1;
const cropHeight = commonBounds.bottom - commonBounds.top + 1;
// A single common art box leaves the same safety margin for every action frame.
const padding = Math.round(size * 0.047);
const scale = (size - padding * 2) / Math.max(cropWidth, cropHeight);
const width = Math.max(1, Math.round(cropWidth * scale));
const height = Math.max(1, Math.round(cropHeight * scale));
const left = Math.floor((size - width) / 2);
const top = Math.floor((size - height) / 2);

function renderFrame(frame) {
  const originX = (frame % columns) * cellWidth + commonBounds.left;
  const originY = Math.floor(frame / columns) * cellHeight + commonBounds.top;
  const data = Buffer.alloc(size * size * 4);

  // Area resampling in premultiplied alpha avoids dark/white edge fringes.
  for (let y = 0; y < height; y++) {
    const y0 = (y * cropHeight) / height;
    const y1 = ((y + 1) * cropHeight) / height;
    for (let x = 0; x < width; x++) {
      const x0 = (x * cropWidth) / width;
      const x1 = ((x + 1) * cropWidth) / width;
      let alpha = 0;
      const rgb = [0, 0, 0];
      for (let sy = Math.floor(y0); sy < Math.ceil(y1); sy++) {
        const weightY = Math.min(y1, sy + 1) - Math.max(y0, sy);
        for (let sx = Math.floor(x0); sx < Math.ceil(x1); sx++) {
          const weight = weightY * (Math.min(x1, sx + 1) - Math.max(x0, sx));
          const offset = ((originY + sy) * sheet.width + originX + sx) * 4;
          const weightedAlpha = cleanedSheet.data[offset + 3] * weight;
          alpha += weightedAlpha;
          for (let channel = 0; channel < 3; channel++) {
            rgb[channel] += cleanedSheet.data[offset + channel] * weightedAlpha;
          }
        }
      }
      const target = ((top + y) * size + left + x) * 4;
      const outputAlpha = Math.round(alpha / ((x1 - x0) * (y1 - y0)));
      if (outputAlpha > 0) {
        for (let channel = 0; channel < 3; channel++) {
          data[target + channel] = Math.round(rgb[channel] / alpha);
        }
      }
      data[target + 3] = outputAlpha;
    }
  }
  return data;
}

const rgbaFrames = Array.from({ length: columns * rows }, (_, frame) => renderFrame(frame));

// Runtime poses share the accepted idle's planted-foot anchor. Jump height belongs
// to the continuous player rather than to a succession of baked image offsets.
const idlePath = path.join(outputDir, 'phoebe-idle.png');
if (!fs.existsSync(idlePath)) throw new Error('The accepted idle PNG is required for pose registration.');
const idle = PNG.sync.read(fs.readFileSync(idlePath));
if (idle.width !== size || idle.height !== size) {
  throw new Error('Pose size must match the existing idle PNG.');
}
function opaqueBounds(data) {
  const bounds = { left: size, top: size, right: -1, bottom: -1 };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    if (data[(y * size + x) * 4 + 3] < 64) continue;
    bounds.left = Math.min(bounds.left, x);
    bounds.top = Math.min(bounds.top, y);
    bounds.right = Math.max(bounds.right, x);
    bounds.bottom = Math.max(bounds.bottom, y);
  }
  return bounds;
}
function footAnchor(data) {
  const bounds = opaqueBounds(data);
  let weight = 0, sum = 0;
  const depth = Math.round(size * 0.105);
  for (let y = bounds.bottom - depth; y <= bounds.bottom; y++) {
    for (let x = 0; x < size; x++) {
      const offset = (y * size + x) * 4;
      const [r, g, b, alpha] = data.subarray(offset, offset + 4);
      if (alpha < 64 || r < 145 || g < 140 || b < r * 0.87) continue;
      sum += x * alpha;
      weight += alpha;
    }
  }
  return { x: weight ? sum / weight : (bounds.left + bounds.right) / 2, y: bounds.bottom };
}
const planted = footAnchor(idle.data);
const poseIds = ['idle', 'hover0', 'hover1', 'hover2', 'anticipate', 'air', 'land'];
const shifts = [{ x: 0, y: 0 }];
const registered = [Buffer.from(idle.data), ...rgbaFrames.map((data) => {
  const anchor = footAnchor(data);
  const dx = Math.round(planted.x - anchor.x);
  const dy = Math.round(planted.y - anchor.y);
  shifts.push({ x: dx, y: dy });
  const target = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const offset = (y * size + x) * 4;
    const tx = x + dx, ty = y + dy;
    if (tx < 0 || tx >= size || ty < 0 || ty >= size) {
      if (data[offset + 3] >= 64) throw new Error('Registered pose would clip the character.');
      continue;
    }
    data.copy(target, (ty * size + tx) * 4, offset, offset + 4);
  }
  return target;
})];

// Stable semantic anchors keep the face, head and boots registered during pose
// morphing. Arms are deliberately not mesh anchors: raising/lowering them would
// invert the same triangle topology between the idle and hands-behind poses.
// Measured on the registered 256px atlas: iris/closed-eye and boot centres
// were verified against connected components; head/body landmarks were reviewed.
// A skin-colour bounding box is unsuitable here because blonde hair and legs can
// be mistaken for the face. Keep these landmarks with this accepted artwork.
const measuredSourceSha256 = '00025626b9b59964fb9f44a6db4ca960dff15be47e84a85616cec8253fce53e2';
if (hashFile(source) !== measuredSourceSha256) {
  throw new Error('Changed artwork requires corresponding pose landmarks before encoding.');
}
const anchorNames = ['crown', 'templeLeft', 'templeRight', 'eyeLeft', 'eyeRight',
  'cheekLeft', 'cheekRight', 'chin', 'chest', 'waist', 'footLeft', 'footRight'];
const measuredAnchors = [
  [[121,31],[74,100],[160,122],[92.1,108.5],[137.7,119.7],[82,128],[151,137],[128,146],[117.2,173],[117.2,202],[105.1,232.3],[135.3,230.5]],
  [[127,40],[82,110],[170,136],[102.3,119.2],[147.4,134.1],[88,142],[159,150],[133,159],[116.9,183],[116.9,208],[104.6,232.1],[131.5,232.2]],
  [[128,43],[83,112],[167,138],[104.3,120.4],[148.2,137.4],[90,144],[159,153],[135,161],[116.8,184],[116.8,209],[104.5,232],[131.6,232.2]],
  [[123,42],[81,113],[160,136],[99.8,120.8],[143.6,135.4],[86,144],[154,152],[131,160],[116.9,183],[116.9,208],[104.7,232.1],[131.6,232.2]],
  [[124,39],[80,109],[164,132],[94,116],[148.1,129.8],[87,138],[155,146],[125,154],[117.5,179],[117.5,206],[104.2,231.9],[132.2,232]],
  [[120,56],[80,117],[161,146],[95.9,122.7],[143.7,144.7],[87,145],[151,157],[129,166],[117,188],[117,211],[104.5,231.6],[134,230.3]],
  [[121,41],[79,111],[161,135],[92.1,119.5],[143.5,133],[86,140],[152,148],[123,155],[117.1,180],[117.1,206],[104.2,231.8],[132,232]],
];
// Match the silhouette as well as the face. Without these outline landmarks a
// correctly aligned face could still leave two hat brims or two hair outlines.
const outlineNames = ['hatPeak', 'brimLeft', 'brimRight', 'butterfly',
  'hairLeft', 'hairRight', 'hairTipLeft', 'hairTipRight', 'mouth'];
const measuredOutlines = [
  [[120,13],[20,57],[223,108],[190.6,58],[19,187],[216,193],[75,222],[162,227],[111.8,129]],
  [[131,26],[34,61],[230,128],[204.3,76.5],[19,171],[218,204],[77,218],[162,229],[120.3,141]],
  [[136,28],[41,63],[230,133],[206.9,79.9],[20,169],[219,207],[78,217],[169,230],[119.6,144.4]],
  [[129,27],[32,67],[223,130],[197.1,77.7],[20,172],[217,204],[75,219],[160,230],[117.4,142.6]],
  [[127,25],[29,66],[225,124],[197.5,72.3],[18,177],[216,199],[66,220],[162,226],[116.8,136.7]],
  [[132,45],[42,69],[219,149],[198.6,99.3],[10,161],[220,205],[83,218],[177,229],[113.4,145.9]],
  [[126,26],[28,66],[220,126],[194,74.4],[18,177],[215,199],[68,219],[161,227],[113.9,138.9]],
];
function poseAnchors(index) {
  return {
    topLeft: [0, 0], topRight: [size, 0], bottomRight: [size, size], bottomLeft: [0, size],
    ...Object.fromEntries(anchorNames.map((name, point) => [name,
      measuredAnchors[index][point].map((value) => Math.round(value * size / 256 * 100) / 100),
    ])),
    ...Object.fromEntries(outlineNames.map((name, point) => [name,
      measuredOutlines[index][point].map((value) => Math.round(value * size / 256 * 100) / 100),
    ])),
  };
}
const poseMetadata = {
  schemaVersion: 1, size, atlas: './assets/phoebe-poses.png',
  groundY: planted.y, footCenterX: Math.round(planted.x * 100) / 100,
  clickDurationMs: 800,
  poses: registered.map((data, index) => ({
    id: poseIds[index], rect: [index * size, 0, size, size],
    shift: shifts[index], bounds: opaqueBounds(data), anchors: poseAnchors(index),
  })),
};
const atlas = Buffer.alloc(size * registered.length * size * 4);
registered.forEach((data, index) => {
  for (let y = 0; y < size; y++) data.copy(atlas,
    (y * size * registered.length + index * size) * 4, y * size * 4, (y + 1) * size * 4);
});
// Share one palette across both actions so changing poses cannot alter colours.
const visiblePixels = [];
for (const data of rgbaFrames) {
  for (let offset = 0; offset < data.length; offset += 4) {
    if (data[offset + 3] >= 128) {
      visiblePixels.push(data[offset], data[offset + 1], data[offset + 2], 255);
    }
  }
}
if (!visiblePixels.length) throw new Error('The resized action frames contain no visible artwork.');
const opaquePalette = quantize(Uint8Array.from(visiblePixels), 255, { format: 'rgb565' });
const palette = [[0, 0, 0], ...opaquePalette];
const indexedFrames = rgbaFrames.map((data) => {
  const indexed = applyPalette(data, opaquePalette, 'rgb565');
  for (let pixel = 0; pixel < indexed.length; pixel++) {
    indexed[pixel] = data[pixel * 4 + 3] >= 128 ? indexed[pixel] + 1 : 0;
  }
  return indexed;
});

const actions = {
  hover: {
    gif: 'phoebe-hover.gif', still: 'phoebe-hover-still.png',
    frameIndices: [0, 1, 2, 1, 0], delaysMs: [180, 220, 260, 220, 220], loop: true,
  },
  click: {
    gif: 'phoebe-click.gif', still: 'phoebe-click-still.png',
    frameIndices: [3, 4, 4, 5], delaysMs: [100, 180, 220, 300], loop: false,
  },
};
const encoded = new Map();
encoded.set('phoebe-poses.png', PNG.sync.write({
  width: size * registered.length, height: size, data: atlas,
}, { colorType: 6 }));
encoded.set('phoebe-poses.js', `window.PHOEBE_POSES = ${JSON.stringify(poseMetadata, null, 2)};\n`);
for (const action of Object.values(actions)) {
  const gif = GIFEncoder();
  action.frameCount = action.frameIndices.length;
  action.durationMs = action.delaysMs.reduce((sum, delay) => sum + delay, 0);
  for (let frame = 0; frame < action.frameIndices.length; frame++) {
    gif.writeFrame(indexedFrames[action.frameIndices[frame]], size, size, {
      palette: frame === 0 ? palette : undefined,
      transparent: true,
      transparentIndex: 0,
      dispose: 2,
      delay: action.delaysMs[frame],
      // gifenc: -1 omits the NETSCAPE extension and plays once; 0 loops forever.
      repeat: action.loop ? 0 : -1,
    });
  }
  gif.finish();
  encoded.set(action.gif, gif.bytes());
  encoded.set(action.still, PNG.sync.write({
    width: size, height: size, data: rgbaFrames[action.frameIndices[0]],
  }, { colorType: 6 }));
}

const manifest = {
  schemaVersion: 1,
  width: size,
  height: size,
  hoverDurationMs: actions.hover.durationMs,
  clickDurationMs: actions.click.durationMs,
  sourceSheet: path.basename(source),
  sourceSha256: hashFile(source),
  layout: { columns, rows, cellWidth, cellHeight },
  alphaCleanup: {
    method: 'largest-8-connected-component-with-low-alpha-fringe',
    coreAlphaThreshold: cleanupThreshold,
    fringeRadiusPixels: fringeRadius,
    transparentRgb: 'zero',
    sourceSheetModified: false,
    frames: cleanupFrames,
  },
  transform: {
    crop: commonBounds,
    scale,
    padding,
    outputBounds: { left, top, width, height },
    // The shared bottom anchor is never recomputed for individual jump frames.
    sourceBottomAnchor: commonBounds.bottom + 1,
    outputBottomAnchor: top + height,
  },
  cellBounds,
  runtime: {
    renderer: 'registered-pose-mesh-with-continuous-timeline',
    atlas: 'phoebe-poses.png', metadata: 'phoebe-poses.js',
    groundY: poseMetadata.groundY, footCenterX: poseMetadata.footCenterX,
    poseIds, shifts,
  },
  hover: actions.hover,
  click: actions.click,
};
encoded.set('phoebe-animation.json', `${JSON.stringify(manifest, null, 2)}\n`);
fs.mkdirSync(outputDir, { recursive: true });
for (const [name, contents] of encoded) fs.writeFileSync(path.join(outputDir, name), contents);
for (const name of protectedAssets) {
  if (hashFile(path.join(outputDir, name)) !== protectedHashes[name]) {
    throw new Error(`The preserved asset unexpectedly changed: ${name}`);
  }
}
console.log(JSON.stringify({
  source, outputDir, width: size, height: size,
  hover: actions.hover, click: actions.click,
  preservedSha256: protectedHashes, files: filenames,
}, null, 2));
