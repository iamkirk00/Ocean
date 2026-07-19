// sketch-whale.js — "living sketch" 2D whale puppets for The Pod.
// Each whale is layered pencil-style SVG in the same graphite-on-paper style as
// the Rookery penguins — wobbly strokes, hatch shading — rigged for ocean
// animation (float, swim, breach, spout, dive) with the boiling-line effect.
// Drawn side-view facing right; the rig mirrors them to swim either way.

export const WHALE_CONFIGS = {
  wright: {
    id: 'wright',
    body: '#7b7575',          // charcoal — right whales are dark all over
    dark: '#5f5a5c',
    belly: '#cfc7b8',
    callosity: '#ece4cf',     // the rough white patches only right whales wear
    line: '#3f4550',
    defaultExpression: 'unimpressed',
    browWidth: 11,
    eye: { cx: 428, cy: 178, rW: 13, rH: 10 },
    jawTravel: 9,             // degrees the lower lip swings open
    lidSkew: 5,
    homeFacing: 1,            // stands stage-left, faces right (toward BLU)
    spout: 'v',               // right whales blow a V — true fact, great gag
  },
  blu: {
    id: 'blu',
    body: '#8fa7b8',          // blue-gray wash
    dark: '#6d8699',
    belly: '#f0ecdc',
    callosity: '#f0ecdc',
    line: '#3d4a58',
    defaultExpression: 'bright',
    browWidth: 4,
    eye: { cx: 450, cy: 158, rW: 10, rH: 12 },
    jawTravel: 12,
    lidSkew: 0,
    homeFacing: -1,           // stands stage-right, faces left (toward WRIGHT)
    spout: 'column',
  },
};

// Same expression grammar as the Rookery — one whale eye does the work of two.
export const EXPRESSIONS = {
  neutral:     { brow: 2,   browY: 0,   lid: 0.08, jawOpen: 0.05, pitch: 0,  bob: 0, pupil: 1.0,  pupilY: 0 },
  bright:      { brow: -10, browY: -5,  lid: 0.0,  jawOpen: 0.4,  pitch: 0,  bob: 0, pupil: 1.05, pupilY: 0 },
  unimpressed: { brow: 12,  browY: 3,   lid: 0.55, jawOpen: 0.0,  pitch: 0,  bob: 1, pupil: 0.92, pupilY: 0 },
  happy:       { brow: -8,  browY: -4,  lid: 0.15, jawOpen: 0.3,  pitch: -1, bob: 0, pupil: 1.0,  pupilY: 0 },
  laugh:       { brow: -10, browY: -6,  lid: 0.85, jawOpen: 1.0,  pitch: -2, bob: -3, pupil: 1.0, pupilY: 0 },
  think:       { brow: 12,  browY: -2,  lid: 0.3,  jawOpen: 0.0,  pitch: 3,  bob: 0, pupil: 0.85, pupilY: -4 },
  surprised:   { brow: -14, browY: -8,  lid: 0.0,  jawOpen: 0.6,  pitch: -1, bob: -2, pupil: 0.7, pupilY: 0 },
  annoyed:     { brow: 18,  browY: 5,   lid: 0.5,  jawOpen: 0.0,  pitch: 1,  bob: 1, pupil: 0.85, pupilY: 0 },
  sad:         { brow: -16, browY: -1,  lid: 0.45, jawOpen: 0.0,  pitch: 4,  bob: 3, pupil: 0.95, pupilY: 2 },
  determined:  { brow: 10,  browY: 2,   lid: 0.15, jawOpen: 0.12, pitch: -1, bob: 0, pupil: 1.0,  pupilY: 0 },
  skeptical:   { brow: -10, browY: -2,  lid: 0.4,  jawOpen: 0.0,  pitch: 1,  bob: 0, pupil: 0.9,  pupilY: 0 },
  excited:     { brow: -12, browY: -8,  lid: 0.0,  jawOpen: 0.8,  pitch: -3, bob: -2, pupil: 1.1, pupilY: 0 },
};

// Emote tags the AI uses — same vocabulary as the Rookery, ocean choreography.
export const EMOTES = {
  wave:      { anim: 'wave',    expr: 'happy' },
  laugh:     { anim: 'laugh',   expr: 'laugh' },
  think:     { anim: 'think',   expr: 'think' },
  shrug:     { anim: 'shrug',   expr: 'skeptical' },
  excited:   { anim: 'breach',  expr: 'excited' },
  nod:       { anim: 'nod',     expr: 'happy' },
  sigh:      { anim: 'sigh',    expr: 'unimpressed' },
  smile:     { anim: null,      expr: 'happy' },
  surprised: { anim: 'spout',   expr: 'surprised' },
  sad:       { anim: null,      expr: 'sad' },
  determined:{ anim: null,      expr: 'determined' },
};

// Static poses for the character sheet. Flipper degrees: positive = swung
// down/forward from the shoulder.
export const POSES = {
  float:    { flip: 0,   flipFar: 0,  pitch: 0,  bob: 0,  fluke: 0,   expr: null },
  wave:     { flip: -95, flipFar: 0,  pitch: -2, bob: 0,  fluke: 6,   expr: 'happy' },
  wide:     { flip: -70, flipFar: 55, pitch: -1, bob: -2, fluke: 10,  expr: 'excited' },
  think:    { flip: -40, flipFar: 0,  pitch: 6,  bob: 2,  fluke: -8,  expr: 'think' },
  shrug:    { flip: -35, flipFar: 30, pitch: 0,  bob: -2, fluke: 14,  expr: 'skeptical' },
  point:    { flip: -80, flipFar: 0,  pitch: -3, bob: 0,  fluke: 4,   expr: 'determined' },
  glide:    { flip: 18,  flipFar: 0,  pitch: -4, bob: -3, fluke: -18, expr: 'happy' },
  drift:    { flip: 8,   flipFar: 0,  pitch: 7,  bob: 4,  fluke: 6,   expr: 'unimpressed' },
};

const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// ============================================================ SVG authoring
const NS = 'http://www.w3.org/2000/svg';

function defs(c) {
  const seeds = [3, 11, 23];
  const filters = seeds.map((s, i) => `
    <filter id="boil-${c.id}-${i}" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.012 0.018" numOctaves="2" seed="${s}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="4.5"/>
    </filter>`).join('');
  const e = c.eye;
  return `<defs>${filters}
    <pattern id="hatch-${c.id}" width="7" height="7" patternTransform="rotate(32)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="7" stroke="${c.line}" stroke-width="1.1" opacity="0.4"/>
    </pattern>
    <clipPath id="eyeclip-${c.id}"><ellipse cx="${e.cx}" cy="${e.cy}" rx="${e.rW}" ry="${e.rH}"/></clipPath>
  </defs>`;
}

const stroke = (c, w = 3.2) => `fill="none" stroke="${c.line}" stroke-width="${w}" stroke-linecap="round" stroke-opacity="0.9"`;
const filled = (c, fill, w = 3.2) => `fill="${fill}" stroke="${c.line}" stroke-width="${w}" stroke-linejoin="round" stroke-opacity="0.9"`;

function stipple(c, cx, cy, spread, n, seedOffset = 0) {
  let dots = '';
  for (let i = 0; i < n; i++) {
    // deterministic pseudo-random scatter (stable across boiling re-renders)
    const a = Math.sin(i * 12.9898 + seedOffset) * 43758.5453;
    const b = Math.sin(i * 78.233 + seedOffset) * 12543.21;
    const dx = ((a - Math.floor(a)) - 0.5) * spread;
    const dy = ((b - Math.floor(b)) - 0.5) * spread * 0.6;
    dots += `<circle cx="${(cx + dx).toFixed(1)}" cy="${(cy + dy).toFixed(1)}" r="1.1" fill="${c.line}" opacity="0.5"/>`;
  }
  return dots;
}

function spoutMarkup(c) {
  if (c.spout === 'v') {
    // the right whale's signature V-shaped double blow
    return `<g class="spout" opacity="0">
      <path d="M428,100 C420,78 411,58 400,44" ${stroke(c, 3.4)}/>
      <path d="M438,100 C446,78 455,58 466,44" ${stroke(c, 3.4)}/>
      <circle cx="396" cy="40" r="5" fill="${c.line}" opacity="0.35"/>
      <circle cx="404" cy="30" r="3.6" fill="${c.line}" opacity="0.3"/>
      <circle cx="470" cy="40" r="5" fill="${c.line}" opacity="0.35"/>
      <circle cx="462" cy="30" r="3.6" fill="${c.line}" opacity="0.3"/>
    </g>`;
  }
  // blue whale: one tall proud column
  return `<g class="spout" opacity="0">
    <path d="M444,106 C441,84 443,58 439,36" ${stroke(c, 3.6)}/>
    <path d="M452,106 C455,82 452,54 458,34" ${stroke(c, 3.2)}/>
    <circle cx="440" cy="30" r="5.5" fill="${c.line}" opacity="0.35"/>
    <circle cx="456" cy="24" r="4" fill="${c.line}" opacity="0.3"/>
    <circle cx="448" cy="16" r="3" fill="${c.line}" opacity="0.25"/>
  </g>`;
}

// ---------- BLU side view ----------
// Long elegant taper, tiny dorsal fin set far back, ventral throat pleats,
// slim flipper, graceful fluke — every blue-whale signature, in pencil.
function bluSide(c) {
  const body = `M512,152 C500,128 478,116 452,112 C410,103 330,100 250,106 C236,104 226,102 218,100 C214,86 206,84 200,92 C198,100 192,104 184,108 C150,116 116,128 96,142 C88,147 84,150 82,154 L82,158 C110,172 152,190 212,202 C280,213 350,212 404,200 C432,193 452,185 466,177 C484,169 500,161 512,152 Z`;
  const back = `M512,152 C500,128 478,116 452,112 C410,103 330,100 250,106 C236,104 226,102 218,100 C214,86 206,84 200,92 C198,100 192,104 184,108 C150,116 116,128 96,142 C88,147 84,150 82,154 C150,142 300,132 420,142 C462,146 492,150 512,152 Z`;
  return `
  <g class="root">
    <g class="flipperFar"><path d="M418,196 C408,220 394,240 380,250 C373,254 370,247 374,239 C383,222 398,206 408,194 Z" ${filled(c, c.dark)}/></g>
    <g class="body">
      <path d="${body}" ${filled(c, c.body)}/>
      <path d="${back}" fill="${c.dark}" stroke="none" opacity="0.55"/>
      <path d="${body}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.24"/>
      <path d="M96,148 C160,164 260,184 360,190 C300,200 200,192 120,168 Z" fill="${c.belly}" stroke="none" opacity="0.65"/>
      <!-- ventral pleats: the throat grooves -->
      <g ${stroke(c, 2)} opacity="0.5">
        <path d="M436,190 C400,202 340,208 280,206"/>
        <path d="M446,184 C410,198 350,205 290,204"/>
        <path d="M456,178 C424,192 370,201 320,202"/>
        <path d="M464,172 C438,186 392,196 352,199"/>
      </g>
      <path d="M440,112 q7,-4 14,0" ${stroke(c, 2.6)}/>
      ${spoutMarkup(c)}
      <!-- mouth line + dark inner mouth (revealed when the jaw drops) -->
      <path class="mouthShape" d="M430,188 C462,180 490,166 512,152 C500,180 465,196 436,194 Z" fill="#33404d" stroke="none"/>
      <g class="jaw">
        <path d="M428,188 C452,197 482,190 508,166 C502,190 470,208 440,203 C432,199 428,194 428,188 Z" ${filled(c, c.belly, 2.8)}/>
        <path d="M436,196 C458,200 480,194 498,180" ${stroke(c, 1.8)}/>
      </g>
      <path d="M512,152 C490,166 462,180 430,188" ${stroke(c, 3)}/>
      <g class="eyes">
        <ellipse cx="450" cy="158" rx="10" ry="12" ${filled(c, '#fdfaf2', 2.6)}/>
        <g class="pupil"><circle cx="451" cy="160" r="5.5" fill="#2c333c"/><circle cx="453" cy="157" r="1.8" fill="#fdfaf2" opacity="0.9"/></g>
        <g clip-path="url(#eyeclip-${c.id})"><g class="lid"><rect x="436" y="122" width="30" height="48" fill="${c.body}"/><line x1="436" y1="170" x2="466" y2="170" stroke="${c.line}" stroke-width="2.6" stroke-opacity="0.85"/></g></g>
        <g class="brow"><path d="M436,140 Q450,132 464,140" ${stroke(c, c.browWidth)}/></g>
      </g>
      <g class="flipper"><path d="M398,194 C382,214 358,236 340,245 C331,249 327,243 331,234 C342,215 368,199 386,191 Z" ${filled(c, c.dark)}/></g>
    </g>
    <g class="fluke">
      <path d="M84,146 C62,120 42,104 26,99 C32,118 36,135 34,152 C36,169 32,186 24,206 C42,199 64,181 86,163 Z" ${filled(c, c.dark)}/>
      <path d="M34,152 L84,155" ${stroke(c, 2)}/>
    </g>
  </g>`;
}

// ---------- WRIGHT side view ----------
// Stocky, huge arched mouth, callosity patches, broad paddles, and — the
// signature — no dorsal fin at all.
function wrightSide(c) {
  const body = `M500,150 C480,116 450,102 420,98 C370,90 300,92 240,102 C180,112 122,134 96,150 C88,155 84,158 84,162 L84,166 C120,187 172,210 242,224 C302,233 352,230 392,220 C398,213 398,206 398,200 C436,206 470,192 500,156 Z`;
  return `
  <g class="root">
    <g class="flipperFar"><path d="M372,212 C360,236 344,254 328,262 C320,265 317,258 322,249 C332,231 352,216 364,208 Z" ${filled(c, c.dark)}/></g>
    <g class="body">
      <path d="${body}" ${filled(c, c.body)}/>
      <path d="${body}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.32"/>
      <path d="M110,162 C180,186 260,204 330,208 C260,214 170,196 118,172 Z" fill="${c.belly}" stroke="none" opacity="0.4"/>
      <path d="M428,104 q7,-4 14,0" ${stroke(c, 2.6)}/>
      ${spoutMarkup(c)}
      <!-- dark inner mouth behind the great lower lip -->
      <path class="mouthShape" d="M400,198 C436,208 470,194 498,160 C486,196 452,216 414,212 Z" fill="#3a3540" stroke="none"/>
      <g class="jaw">
        <path d="M396,200 C428,209 462,200 494,168 C502,196 478,232 438,236 C412,236 398,220 396,200 Z" ${filled(c, c.dark, 3)}/>
        <path d="M470,222 q10,-8 18,-4 q4,8 -6,12 q-10,2 -12,-8 Z" ${filled(c, c.callosity, 2)}/>
        ${stipple(c, 476, 226, 14, 5, 7)}
      </g>
      <path d="M500,156 C470,194 436,208 398,198" ${stroke(c, 4.2)}/>
      <!-- callosities: the bonnet on the rostrum and the patch above the eye -->
      <path d="M470,132 q8,-12 20,-9 q9,3 5,12 q-14,6 -25,-3 Z" ${filled(c, c.callosity, 2)}/>
      ${stipple(c, 481, 132, 18, 6, 1)}
      <path d="M428,152 q7,-8 16,-5 q6,3 2,9 q-11,4 -18,-4 Z" ${filled(c, c.callosity, 2)}/>
      ${stipple(c, 436, 153, 12, 4, 3)}
      <g class="eyes">
        <ellipse cx="428" cy="178" rx="13" ry="10" ${filled(c, '#f6f2e6', 2.6)}/>
        <g class="pupil"><circle cx="431" cy="180" r="4.6" fill="#2f2b33"/></g>
        <g clip-path="url(#eyeclip-${c.id})"><g class="lid"><rect x="411" y="148" width="36" height="42" fill="${c.body}"/><line x1="411" y1="190" x2="447" y2="190" stroke="${c.line}" stroke-width="2.6" stroke-opacity="0.85"/></g></g>
        <g class="brow"><path d="M412,162 L446,158" ${stroke(c, c.browWidth)}/></g>
      </g>
      <g class="flipper"><path d="M352,214 C336,238 316,262 296,272 C286,277 281,269 287,257 C300,234 326,216 344,208 Z" ${filled(c, c.dark)}/></g>
    </g>
    <g class="fluke">
      <path d="M88,152 C64,124 42,108 22,104 C30,124 36,142 34,160 C36,178 30,196 22,216 C42,210 68,190 90,168 Z" ${filled(c, c.dark)}/>
      <path d="M34,160 L88,160" ${stroke(c, 2)}/>
    </g>
  </g>`;
}

// ---------- static front / top views (for the character sheet) ----------
function frontView(c) {
  const wright = c.id === 'wright';
  const bodyPath = wright
    ? `M280,60 C220,62 178,96 170,150 C163,204 196,252 252,268 C214,276 190,290 182,302 L378,302 C370,290 346,276 308,268 C364,252 397,204 390,150 C382,96 340,62 280,60 Z`
    : `M280,64 C236,66 206,94 200,142 C195,190 216,240 258,262 C230,272 212,286 206,300 L354,300 C348,286 330,272 302,262 C344,240 365,190 360,142 C354,94 324,66 280,64 Z`;
  const mouth = wright
    ? `<path d="M212,196 C240,236 320,236 348,196" ${stroke(c, 3.4)}/>`
    : `<path d="M226,206 C254,224 306,224 334,206" ${stroke(c, 3)}/>`;
  const call = wright
    ? `<path d="M266,84 q14,-12 28,0 q6,10 -8,14 q-18,2 -20,-14 Z" ${filled(c, c.callosity, 2)}/>${stipple(c, 280, 90, 22, 6, 5)}`
    : '';
  const spout = wright
    ? `<path d="M264,58 C254,42 246,30 236,20 M296,58 C306,42 314,30 324,20" ${stroke(c, 3)} opacity="0.5"/>`
    : `<path d="M276,54 C274,38 276,26 272,14 M286,54 C289,38 287,24 291,14" ${stroke(c, 3)} opacity="0.5"/>`;
  const eyes = wright
    ? `<ellipse cx="222" cy="166" rx="12" ry="9" ${filled(c, '#f6f2e6', 2.4)}/><circle cx="224" cy="168" r="4.2" fill="#2f2b33"/>
       <ellipse cx="338" cy="166" rx="12" ry="9" ${filled(c, '#f6f2e6', 2.4)}/><circle cx="336" cy="168" r="4.2" fill="#2f2b33"/>
       <path d="M206,150 L238,146 M322,146 L354,150" ${stroke(c, 8)}/>`
    : `<ellipse cx="238" cy="158" rx="9" ry="12" ${filled(c, '#fdfaf2', 2.4)}/><circle cx="239" cy="160" r="4.8" fill="#2c333c"/>
       <ellipse cx="322" cy="158" rx="9" ry="12" ${filled(c, '#fdfaf2', 2.4)}/><circle cx="321" cy="160" r="4.8" fill="#2c333c"/>
       <path d="M226,142 Q238,134 250,142 M310,142 Q322,134 334,142" ${stroke(c, 3.6)}/>`;
  return `
  <g class="root">
    <path d="M150,222 C120,240 104,262 100,282 C118,276 140,262 158,244 Z" ${filled(c, c.dark)}/>
    <path d="M410,222 C440,240 456,262 460,282 C442,276 420,262 402,244 Z" ${filled(c, c.dark)}/>
    <path d="${bodyPath}" ${filled(c, c.body)}/>
    <path d="${bodyPath}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.3"/>
    ${wright ? '' : `<g ${stroke(c, 2)} opacity="0.5"><path d="M240,222 C260,232 300,232 320,222"/><path d="M236,236 C258,247 302,247 324,236"/><path d="M240,250 C260,260 300,260 320,250"/></g>`}
    ${spout}${call}${eyes}${mouth}
  </g>`;
}

function topView(c) {
  const wright = c.id === 'wright';
  const bodyPath = wright
    ? `M500,160 C480,128 440,112 390,108 C300,102 190,112 120,140 C96,150 84,156 80,160 C84,164 96,170 120,180 C190,208 300,218 390,212 C440,208 480,192 500,160 Z`
    : `M512,160 C496,136 466,124 430,120 C330,110 200,118 110,146 C92,152 84,156 82,160 C84,164 92,168 110,174 C200,202 330,210 430,200 C466,196 496,184 512,160 Z`;
  const call = wright
    ? `<path d="M462,150 q16,-6 30,2 q6,8 -8,12 q-20,2 -22,-14 Z" ${filled(c, c.callosity, 2)}/>${stipple(c, 476, 156, 26, 7, 9)}`
    : `<path d="M300,120 L300,200" ${stroke(c, 2)} opacity="0.35"/>`;
  return `
  <g class="root">
    <path d="M84,150 C58,124 38,110 20,106 C28,126 34,144 32,160 C34,176 28,194 20,214 C38,210 58,196 84,170 Z" ${filled(c, c.dark)}/>
    <path d="M330,${wright ? 118 : 124} C316,92 298,74 278,66 C284,88 288,106 290,${wright ? 116 : 122} Z" ${filled(c, c.dark)}/>
    <path d="M330,${wright ? 202 : 196} C316,228 298,246 278,254 C284,232 288,214 290,${wright ? 204 : 198} Z" ${filled(c, c.dark)}/>
    <path d="${bodyPath}" ${filled(c, c.body)}/>
    <path d="${bodyPath}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.32"/>
    <path d="M${wright ? 452 : 462},160 q10,-6 20,0 q-10,6 -20,0 Z" ${filled(c, c.belly, 2)}/>
    ${call}
  </g>`;
}

export function buildSVG(config, view = 'side') {
  const inner = view === 'side'
    ? (config.id === 'wright' ? wrightSide(config) : bluSide(config))
    : view === 'front' ? frontView(config) : topView(config);
  return `<svg xmlns="${NS}" viewBox="0 0 560 320" width="560" height="320" class="whale-svg whale-${config.id}">
    ${defs(config)}
    <g class="boil" filter="url(#boil-${config.id}-0)">${inner}</g>
  </svg>`;
}

// ============================================================ rigged puppet
export class SketchWhale {
  constructor(config, mountEl) {
    this.cfg = config;
    this.el = mountEl;
    this.el.innerHTML = buildSVG(config, 'side');
    this.svg = this.el.querySelector('svg');
    const q = (s) => this.svg.querySelector(s);
    this.parts = {
      boil: q('.boil'),
      root: q('.root'),
      body: q('.body'),
      fluke: q('.fluke'),
      flipper: q('.flipper'),
      flipperFar: q('.flipperFar'),
      brow: q('.brow'),
      lid: q('.lid'),
      pupil: q('.pupil'),
      jaw: q('.jaw'),
      spout: q('.spout'),
    };
    const wright = config.id === 'wright';
    this._origins = {
      root: '280px 160px',
      fluke: wright ? '88px 160px' : '84px 154px',
      flipper: wright ? '352px 212px' : '396px 194px',
      flipperFar: wright ? '368px 214px' : '414px 196px',
      jaw: wright ? '398px 200px' : '429px 189px',
      brow: `${config.eye.cx}px ${config.eye.cy - 18}px`,
      pupil: `${config.eye.cx}px ${config.eye.cy}px`,
      spout: wright ? '433px 100px' : '448px 106px',
    };
    for (const k of ['root', 'fluke', 'flipper', 'flipperFar', 'jaw', 'brow', 'pupil', 'spout']) {
      if (this.parts[k]) this.parts[k].style.transformOrigin = this._origins[k];
    }
    this.parts.lid.style.transformOrigin = `${config.eye.cx}px ${config.eye.cy}px`;

    this.x = 0;                 // stage percent — the stage moves this.el
    this.facing = config.homeFacing;
    this.state = 'idle';
    this.stateTime = 0;
    this.stateDur = Infinity;
    this.talking = false;
    this.talkPhase = Math.random() * 10;
    this.blinkTimer = 1.5 + Math.random() * 3;
    this.blink = 0;
    this.walk = null;
    this._boilT = 0;
    this._boilIdx = 0;
    this._talkOpen = 0;
    this._spout = 0;
    this.exprCurrent = { ...EXPRESSIONS[config.defaultExpression] };
    this.exprTarget = { ...EXPRESSIONS[config.defaultExpression] };
    this.baseExpression = config.defaultExpression;
    this.exprHoldTimer = 0;
    this._apply(this.exprCurrent, {});
  }

  setExpression(name, holdSeconds = 0) {
    const e = EXPRESSIONS[name];
    if (!e) return;
    this.exprTarget = { ...e };
    if (holdSeconds > 0) this.exprHoldTimer = holdSeconds;
    else this.baseExpression = name;
  }

  play(name, duration = 2.2) {
    this.state = name;
    this.stateTime = 0;
    this.stateDur = duration;
    const emote = EMOTES[name];
    if (emote && emote.expr) this.setExpression(emote.expr, duration);
  }

  setTalking(on) {
    this.talking = on;
    if (on && this.state === 'idle') { this.state = 'talk'; this.stateTime = 0; this.stateDur = Infinity; }
    if (!on && this.state === 'talk') { this.state = 'idle'; this.stateTime = 0; this.stateDur = Infinity; }
  }

  walkTo(xPercent, speed = 26) { // API name kept from the Rookery; whales swim
    this.walk = { toX: xPercent, speed };
    if (Math.abs(xPercent - this.x) > 0.5) this.facing = xPercent > this.x ? 1 : -1;
    this.state = 'swim';
    this.stateTime = 0;
    this.stateDur = Infinity;
  }

  faceToward() { /* kept for API compatibility */ }

  // Static pose for the character sheet.
  setPose(name, exprOverride = null) {
    const p = POSES[name] || POSES.float;
    this.talking = false;
    this.blink = 0;
    this._talkOpen = 0;
    this._spout = 0;
    this.exprCurrent = { ...EXPRESSIONS[exprOverride || p.expr || this.cfg.defaultExpression] };
    this._apply(this.exprCurrent, {
      flip: p.flip, flipFar: p.flipFar, fluke: p.fluke,
      pitch: p.pitch, bob: p.bob,
    });
  }

  _apply(e, m) {
    const p = this.parts;
    const lid = Math.max(e.lid, this.blink);
    const lidRange = this.cfg.eye.rH * 2 + 16;
    p.lid.style.transform = `translateY(${-lidRange * (1 - lid)}px) rotate(${this.cfg.lidSkew}deg)`;
    p.brow.style.transform = `translateY(${e.browY + (m.browLift || 0)}px) rotate(${e.brow}deg)`;
    p.pupil.style.transform = `translateY(${e.pupilY}px) scale(${e.pupil})`;
    const open = clamp(this.talking ? Math.max(e.jawOpen, this._talkOpen) : e.jawOpen, 0, 1);
    p.jaw.style.transform = `rotate(${open * this.cfg.jawTravel}deg)`;
    p.flipper.style.transform = `rotate(${m.flip || 0}deg)`;
    if (p.flipperFar) p.flipperFar.style.transform = `rotate(${m.flipFar || 0}deg)`;
    p.fluke.style.transform = `rotate(${m.fluke || 0}deg)`;
    if (p.spout) {
      const s = clamp(this._spout, 0, 1);
      p.spout.style.opacity = s.toFixed(2);
      p.spout.style.transform = `scaleY(${0.4 + s * 0.6})`;
    }
    const pitch = (e.pitch || 0) + (m.pitch || 0);
    const bob = (e.bob || 0) + (m.bob || 0);
    p.root.style.transform =
      `translateY(${(m.rootY || 0) + bob}px) scaleX(${this.facing}) rotate(${pitch + (m.rootRot || 0)}deg)`;
  }

  update(dt, t) {
    this.stateTime += dt;
    const st = this.stateTime;
    const phase = this.talkPhase;

    // boiling pencil line
    this._boilT += dt;
    if (this._boilT > 0.16) {
      this._boilT = 0;
      this._boilIdx = (this._boilIdx + 1) % 3;
      this.parts.boil.setAttribute('filter', `url(#boil-${this.cfg.id}-${this._boilIdx})`);
    }

    // blink
    this.blinkTimer -= dt;
    if (this.blinkTimer <= 0) { this.blinkTimer = 2 + Math.random() * 4; this.blink = 1; }
    if (this.blink > 0) this.blink = Math.max(0, this.blink - dt * 7);

    // expression lerp + hold expiry
    if (this.exprHoldTimer > 0) {
      this.exprHoldTimer -= dt;
      if (this.exprHoldTimer <= 0) this.exprTarget = { ...EXPRESSIONS[this.baseExpression] };
    }
    for (const k in this.exprTarget) {
      this.exprCurrent[k] = lerp(this.exprCurrent[k], this.exprTarget[k], Math.min(1, dt * 7));
    }

    this._talkOpen = this.talking
      ? 0.25 + 0.35 * Math.abs(Math.sin(t * 8 + phase)) + 0.15 * Math.sin(t * 21 + phase)
      : 0;

    // spout decays unless a state below feeds it
    let spoutTarget = 0;

    // ---- motion layers: everything floats
    const m = {
      bob: Math.sin(t * 1.1 + phase) * 4,
      pitch: Math.sin(t * 0.7 + phase) * 1.2,
      fluke: Math.sin(t * 1.3 + phase) * 6,
      flip: Math.sin(t * 1.0 + phase) * 4,
      flipFar: 0, rootY: 0, rootRot: 0, browLift: 0,
    };

    const s = this.state;
    if (s === 'talk' || this.talking) {
      m.pitch += Math.sin(t * 2.8 + phase) * 0.8;
      if (this.cfg.id === 'blu') {
        m.flip = -(18 + 22 * Math.sin(t * 2.4 + phase));      // BLU talks with his flipper
        m.fluke = Math.sin(t * 2.0 + phase) * 10;
      } else {
        m.flip = -Math.max(0, Math.sin(t * 1.4 + phase)) * 10; // WRIGHT barely bothers
      }
    } else if (s === 'wave') {
      const k = Math.min(1, st * 4);
      m.flip = -k * 92 + Math.sin(st * 9) * 18 * k;            // pec-slap hello
      m.pitch -= 2 * k;
    } else if (s === 'laugh') {
      const b = Math.abs(Math.sin(st * 8));
      m.bob -= b * 7;
      m.pitch -= 2;
      m.flip = -12 - b * 18;
      m.fluke = Math.sin(st * 8) * 16;
      spoutTarget = 0.5 + b * 0.5;                             // giggle-spout
    } else if (s === 'think') {
      const k = Math.min(1, st * 3);
      m.pitch += 6 * k;                                        // nose dips — half a dive
      m.flip = -k * 44;
      m.fluke = -k * 10 + Math.sin(t * 1.6) * 4;
    } else if (s === 'shrug' || s === 'sigh') {
      const k = Math.min(1, st * 4) * (this.stateDur - st > 0.4 ? 1 : Math.max(0, (this.stateDur - st) / 0.4));
      m.flip = -k * 38;
      m.flipFar = k * 30;
      m.bob -= k * 3;
      m.browLift = -k * 3;
      if (s === 'sigh') spoutTarget = k * 0.45;                 // a visible, weary blow
    } else if (s === 'breach') {
      // the big one: leap, hang, splash back
      const T = clamp(st / this.stateDur, 0, 1);
      const arc = Math.sin(T * Math.PI);
      m.rootY = -arc * 90;
      m.rootRot = -arc * 14 * this.facing * this.cfg.homeFacing; // lean into the leap
      m.flip = -arc * 70;
      m.flipFar = arc * 50;
      m.fluke = Math.sin(st * 6) * 22;
      spoutTarget = T < 0.35 ? 1 : 0;
    } else if (s === 'spout') {
      spoutTarget = Math.min(1, st * 5) * (this.stateDur - st > 0.5 ? 1 : Math.max(0, (this.stateDur - st) / 0.5));
    } else if (s === 'nod') {
      m.pitch += Math.sin(st * 8) * 4;
    } else if (s === 'swim' && this.walk) {
      const { toX, speed } = this.walk;
      const dx = toX - this.x;
      const dist = Math.abs(dx);
      if (dist < 0.4) {
        this.walk = null;
        this.state = 'idle';
        this.facing = this.cfg.homeFacing;                     // settle facing your friend
      } else {
        this.x += Math.sign(dx) * Math.min(dist, speed * dt);
        m.pitch += -3;                                          // lean into the glide
        m.fluke = Math.sin(t * 7) * 24;                         // strong tail beats
        m.flip = 14 + Math.sin(t * 7 + 1) * 8;
        m.bob += Math.sin(t * 3.5) * 3;
      }
    }

    this._spout = lerp(this._spout, spoutTarget, Math.min(1, dt * 6));

    if (st > this.stateDur && s !== 'swim') {
      this.state = this.talking ? 'talk' : 'idle';
      this.stateTime = 0;
      this.stateDur = Infinity;
    }

    this._apply(this.exprCurrent, m);
  }
}
