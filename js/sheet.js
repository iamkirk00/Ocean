// sheet.js — renders turnaround views, poses, and expression close-ups of the
// sketch whales into a downloadable model-sheet PNG (plus per-cell PNGs).
import { SketchWhale, WHALE_CONFIGS, buildSVG } from './sketch-whale.js';

const VIEWS = [
  { label: 'SIDE', view: 'side' },
  { label: 'FRONT', view: 'front' },
  { label: 'TOP', view: 'top' },
];
const POSE_ROW = [
  { label: 'FLOAT', pose: 'float' },
  { label: 'WAVE', pose: 'wave' },
  { label: 'FLIPPERS WIDE', pose: 'wide' },
  { label: 'THINKING', pose: 'think' },
  { label: 'SHRUG', pose: 'shrug' },
  { label: 'POINT', pose: 'point' },
  { label: 'GLIDE', pose: 'glide' },
  { label: 'DRIFT', pose: 'drift' },
];
const EXPR_ROW = [
  { label: 'NEUTRAL', expr: 'neutral' },
  { label: 'BRIGHT', expr: 'bright' },
  { label: 'HAPPY', expr: 'happy' },
  { label: 'LAUGH', expr: 'laugh' },
  { label: 'THINKING', expr: 'think' },
  { label: 'SURPRISED', expr: 'surprised' },
  { label: 'UNIMPRESSED', expr: 'unimpressed' },
  { label: 'DETERMINED', expr: 'determined' },
];

// Offscreen rigged puppet per character, reused for posing.
const _rigs = {};
function rig(charId) {
  if (!_rigs[charId]) {
    const holder = document.createElement('div');
    _rigs[charId] = new SketchWhale(WHALE_CONFIGS[charId], holder);
    _rigs[charId].facing = 1; // sheet renders always face right
  }
  return _rigs[charId];
}

function svgToImage(svgMarkup) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgMarkup);
  });
}

// Render one cell to an Image. opts: { pose, expr, view, framing }
async function renderCellImage(charId, opts) {
  let markup;
  if ((opts.view || 'side') === 'side') {
    const p = rig(charId);
    p.facing = 1;
    p.setPose(opts.pose || 'float', opts.expr || null);
    markup = p.svg.outerHTML;
  } else {
    markup = buildSVG(WHALE_CONFIGS[charId], opts.view);
  }
  return svgToImage(markup);
}

// Draw an image (560x320 viewBox) into a square cell, full body or head crop.
function drawInto(ctx, img, x, y, size, framing) {
  if (framing === 'bust') {
    // crop the head end (whales face right) of the 560x320 drawing
    ctx.drawImage(img, 330, 60, 230, 220, x, y, size, size * (220 / 230));
  } else {
    const s = size / 580;
    ctx.drawImage(img, x + (size - 560 * s) / 2, y + (size - 320 * s) / 2, 560 * s, 320 * s);
  }
}

// ---------- full sheet ----------
export async function generateSheet(charId, charData) {
  const CELL = 300, PAD = 26, LABEL_H = 34, TITLE_H = 110, ROW_GAP = 40;
  const cols = 8;
  const W = PAD * 2 + CELL * cols;
  const rows = [
    { title: 'TURNAROUND', items: VIEWS.map((v) => ({ label: v.label, opts: { view: v.view } })) },
    { title: 'POSES', items: POSE_ROW.map((p) => ({ label: p.label, opts: { pose: p.pose } })) },
    { title: 'EXPRESSIONS', items: EXPR_ROW.map((e) => ({ label: e.label, opts: { pose: 'float', expr: e.expr, framing: 'bust' } })) },
  ];
  const H = TITLE_H + rows.length * (CELL + LABEL_H + ROW_GAP) + PAD;

  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');

  // sea-paper background
  ctx.fillStyle = '#e9efec';
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = '#c9d6d0';
  ctx.lineWidth = 4;
  ctx.strokeRect(10, 10, W - 20, H - 20);

  // title
  ctx.fillStyle = '#37424e';
  ctx.font = '700 52px "Avenir Next", "Segoe UI", sans-serif';
  ctx.fillText(`${charData.name} — CHARACTER SHEET`, PAD + 6, 68);
  ctx.font = 'italic 24px "Avenir Next", "Segoe UI", sans-serif';
  ctx.fillStyle = '#63707c';
  ctx.fillText(charData.tagline, PAD + 8, 98);

  const cellMap = []; // for click-to-download
  let y = TITLE_H;
  for (const row of rows) {
    ctx.fillStyle = '#63707c';
    ctx.font = '700 20px "Avenir Next", "Segoe UI", sans-serif';
    ctx.fillText(row.title, PAD + 4, y + 14);
    const rowY = y + 26;
    const n = row.items.length;
    const rowW = n * CELL;
    const startX = (W - rowW) / 2;
    for (let i = 0; i < n; i++) {
      const item = row.items[i];
      const x = startX + i * CELL;
      const img = await renderCellImage(charId, item.opts);
      drawInto(ctx, img, x + 8, rowY, CELL - 16, item.opts.framing);
      ctx.fillStyle = '#37424e';
      ctx.font = '600 18px "Avenir Next", "Segoe UI", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(item.label, x + CELL / 2, rowY + CELL + 4);
      ctx.textAlign = 'left';
      cellMap.push({ x: x + 8, y: rowY, w: CELL - 16, h: CELL - 16, charId, label: item.label, opts: item.opts });
    }
    y += CELL + LABEL_H + ROW_GAP;
  }

  ctx.fillStyle = '#8b98a3';
  ctx.font = '16px "Avenir Next", "Segoe UI", sans-serif';
  ctx.fillText('The Pod — BLU & WRIGHT', PAD + 6, H - 24);
  return { canvas, cellMap };
}

// High-res single cell with transparent background.
export async function renderSingle(charId, opts, size = 1024) {
  const img = await renderCellImage(charId, opts);
  const out = document.createElement('canvas');
  out.width = size;
  out.height = size;
  drawInto(out.getContext('2d'), img, 0, 0, size, opts.framing);
  return out;
}

export function downloadCanvas(canvas, filename) {
  canvas.toBlob((blob) => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }, 'image/png');
}
