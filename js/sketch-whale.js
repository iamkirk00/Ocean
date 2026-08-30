// sketch-whale.js — "living sketch" 2D whale puppets for The Pod.
//
// Comic proportions on purpose: real whales are long ribbons, which reads as a
// submarine on a stage. These are chunky, round, big-eyed cartoons — BLU is a
// proper blue teardrop with a cream pleated chin, WRIGHT is a charcoal loaf
// with the arched mouth and warty callosities only a right whale wears. Same
// graphite-on-paper style as the Rookery penguins: wobbly strokes, hatch
// shading, and a boiling line that re-jitters like pencil animation.
//
// Drawn in side view facing right; the rig mirrors them with scaleX.

export const WHALE_CONFIGS = {
  wright: {
    id: 'wright',
    body: '#5c5d66',          // charcoal — right whales are dark all over
    dark: '#45464f',
    belly: '#83848d',
    lip: '#74757f',        // lower lip, a shade up from the body so the arch reads
    callosity: '#efe7d3',     // the crusty white patches, his one accessory
    line: '#33363f',
    defaultExpression: 'unimpressed',
    browWidth: 11,
    eye: { cx: 404, cy: 176, rW: 15, rH: 13 },
    jawTravel: 13,            // degrees the great lower lip swings open
    lidSkew: 5,
    homeFacing: 1,            // stage-left, facing right (toward BLU)
    spout: 'v',               // right whales blow a V — true fact, free gag
    hinge: [392, 206],        // where the jaw pivots
  },
  blu: {
    id: 'blu',
    body: '#4f8dc2',          // actually blue, at last
    dark: '#3a72a4',
    belly: '#f4ecd8',
    callosity: '#f4ecd8',
    line: '#2f4a5e',
    defaultExpression: 'bright',
    browWidth: 4.5,
    eye: { cx: 468, cy: 166, rW: 16, rH: 18 },
    jawTravel: 15,
    lidSkew: 0,
    homeFacing: -1,           // stage-right, facing left (toward WRIGHT)
    spout: 'column',
    hinge: [412, 202],
  },
};

// One whale eye does the work of two.
export const EXPRESSIONS = {
  neutral:     { brow: 2,   browY: 0,   lid: 0.08, jawOpen: 0.05, pitch: 0,  bob: 0, pupil: 1.0,  pupilY: 0 },
  bright:      { brow: -10, browY: -5,  lid: 0.0,  jawOpen: 0.4,  pitch: 0,  bob: 0, pupil: 1.05, pupilY: 0 },
  unimpressed: { brow: 12,  browY: 3,   lid: 0.55, jawOpen: 0.0,  pitch: 0,  bob: 1, pupil: 0.92, pupilY: 0 },
  happy:       { brow: -8,  browY: -4,  lid: 0.15, jawOpen: 0.3,  pitch: -1, bob: 0, pupil: 1.0,  pupilY: 0 },
  laugh:       { brow: -10, browY: -6,  lid: 0.85, jawOpen: 1.0,  pitch: -2, bob: -3, pupil: 1.0, pupilY: 0 },
  think:       { brow: 12,  browY: -2,  lid: 0.3,  jawOpen: 0.0,  pitch: 3,  bob: 0, pupil: 0.85, pupilY: -5 },
  surprised:   { brow: -14, browY: -8,  lid: 0.0,  jawOpen: 0.6,  pitch: -1, bob: -2, pupil: 0.7, pupilY: 0 },
  annoyed:     { brow: 18,  browY: 5,   lid: 0.5,  jawOpen: 0.0,  pitch: 1,  bob: 1, pupil: 0.85, pupilY: 0 },
  sad:         { brow: -16, browY: -1,  lid: 0.45, jawOpen: 0.0,  pitch: 4,  bob: 3, pupil: 0.95, pupilY: 2 },
  determined:  { brow: 10,  browY: 2,   lid: 0.15, jawOpen: 0.12, pitch: -1, bob: 0, pupil: 1.0,  pupilY: 0 },
  skeptical:   { brow: -10, browY: -2,  lid: 0.4,  jawOpen: 0.0,  pitch: 1,  bob: 0, pupil: 0.9,  pupilY: 0 },
  excited:     { brow: -12, browY: -8,  lid: 0.0,  jawOpen: 0.8,  pitch: -3, bob: -2, pupil: 1.1, pupilY: 0 },
};

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

// Static poses for the character sheet.
export const POSES = {
  float:    { flip: 0,   flipFar: 0,  pitch: 0,  bob: 0,  fluke: 0,   expr: null },
  wave:     { flip: -95, flipFar: 0,  pitch: -2, bob: 0,  fluke: 6,   expr: 'happy' },
  wide:     { flip: -70, flipFar: 55, pitch: -1, bob: -2, fluke: 10,  expr: 'excited' },
  think:    { flip: -40, flipFar: 0,  pitch: 6,  bob: 2,  fluke: -8,  expr: 'think' },
  shrug:    { flip: -35, flipFar: 30, pitch: 0,  bob: -2, fluke: 14,  expr: 'skeptical' },
  point:    { flip: -80, flipFar: 0,  pitch: -3, bob: 0,  fluke: 4,   expr: 'determined' },
  breach:   { flip: -60, flipFar: 40, pitch: -26, bob: -4, fluke: -20, expr: 'excited' },
  drift:    { flip: 8,   flipFar: 0,  pitch: 7,  bob: 4,  fluke: 6,   expr: 'unimpressed' },
};

const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ease = (t) => t * t * (3 - 2 * t);           // smoothstep

// ============================================================ SVG authoring
const NS = 'http://www.w3.org/2000/svg';

function defs(c) {
  const seeds = [3, 11, 23];
  const filters = seeds.map((s, i) => `
    <filter id="boil-${c.id}-${i}" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.012 0.018" numOctaves="2" seed="${s}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="4"/>
    </filter>`).join('');
  const e = c.eye;
  return `<defs>${filters}
    <pattern id="hatch-${c.id}" width="7" height="7" patternTransform="rotate(32)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="7" stroke="${c.line}" stroke-width="1.1" opacity="0.4"/>
    </pattern>
    <clipPath id="eyeclip-${c.id}"><ellipse cx="${e.cx}" cy="${e.cy}" rx="${e.rW}" ry="${e.rH}"/></clipPath>
    <clipPath id="bodyclip-${c.id}"><path d="${c.id === 'blu' ? BLU_BODY : WRIGHT_BODY}"/></clipPath>
  </defs>`;
}

const stroke = (c, w = 3.4) => `fill="none" stroke="${c.line}" stroke-width="${w}" stroke-linecap="round" stroke-opacity="0.92"`;
const filled = (c, fill, w = 3.4) => `fill="${fill}" stroke="${c.line}" stroke-width="${w}" stroke-linejoin="round" stroke-opacity="0.92"`;

/** Deterministic warty scatter — stable across boiling re-renders. */
function warts(c, cx, cy, spread, n, seed = 0) {
  let out = '';
  for (let i = 0; i < n; i++) {
    const a = Math.sin(i * 12.9898 + seed) * 43758.5453;
    const b = Math.sin(i * 78.233 + seed) * 12543.21;
    const dx = ((a - Math.floor(a)) - 0.5) * spread;
    const dy = ((b - Math.floor(b)) - 0.5) * spread * 0.55;
    const r = 1.6 + (a - Math.floor(a)) * 1.8;
    out += `<circle cx="${(cx + dx).toFixed(1)}" cy="${(cy + dy).toFixed(1)}" r="${r.toFixed(1)}" fill="${c.line}" opacity="0.35"/>`;
  }
  return out;
}

// Chunky comic silhouettes — fat leaf shapes, tail tip at left, snout at right.
const BLU_BODY = 'M112,152 C148,100 236,70 330,74 C432,78 512,118 516,176 C519,216 468,252 378,260 C276,269 168,222 112,152 Z';
const WRIGHT_BODY = 'M104,158 C144,102 240,66 348,70 C452,74 512,114 508,170 C504,218 448,254 348,260 C238,266 154,224 104,158 Z';

function spoutMarkup(c) {
  if (c.spout === 'v') {
    return `<g class="spout" opacity="0">
      <path d="M446,74 C434,50 422,32 408,18" ${stroke(c, 3.6)}/>
      <path d="M458,74 C470,50 482,32 496,18" ${stroke(c, 3.6)}/>
      <circle cx="404" cy="14" r="5.5" fill="${c.line}" opacity="0.3"/>
      <circle cx="500" cy="14" r="5.5" fill="${c.line}" opacity="0.3"/>
      <circle cx="414" cy="4" r="3.6" fill="${c.line}" opacity="0.24"/>
      <circle cx="490" cy="4" r="3.6" fill="${c.line}" opacity="0.24"/>
    </g>`;
  }
  return `<g class="spout" opacity="0">
    <path d="M418,80 C414,54 418,32 412,10" ${stroke(c, 4)}/>
    <path d="M428,80 C434,52 430,28 440,8" ${stroke(c, 3.4)}/>
    <circle cx="412" cy="8" r="6" fill="${c.line}" opacity="0.3"/>
    <circle cx="440" cy="4" r="4.4" fill="${c.line}" opacity="0.26"/>
    <circle cx="426" cy="-6" r="3.2" fill="${c.line}" opacity="0.2"/>
  </g>`;
}

// ---------- BLU: round, blue, cheerful ----------
function bluSide(c) {
  return `
  <g class="root">
    <g class="flipperFar"><path d="M392,226 C372,252 342,272 318,278 C308,280 304,272 311,263 C328,242 360,224 380,216 Z" ${filled(c, c.dark)}/></g>
    <g class="fluke">
      <path d="M120,150 C96,120 66,100 38,92 C50,116 57,134 55,152 C57,172 48,192 34,214 C64,204 98,180 122,158 Z" ${filled(c, c.dark)}/>
      <path d="M55,152 L118,154" ${stroke(c, 2)}/>
    </g>
    <g class="body">
      <path d="${BLU_BODY}" ${filled(c, c.body)}/>
      <g clip-path="url(#bodyclip-${c.id})">
        <!-- darker back, cream underside: the blue whale's two-tone -->
        <path d="M100,150 C150,92 240,62 336,66 C440,70 520,112 524,168 C470,132 380,110 280,116 C196,121 138,134 100,150 Z" fill="${c.dark}" opacity="0.75"/>
        <path d="M112,168 C186,196 300,210 402,204 C458,200 498,190 524,174 L540,300 L100,300 Z" fill="${c.belly}" opacity="0.95"/>
        <path d="${BLU_BODY}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.2"/>
        <!-- ventral pleats along the chin -->
        <g ${stroke(c, 2.2)} opacity="0.5">
          <path d="M486,214 C470,236 444,248 418,250"/>
          <path d="M470,222 C456,242 432,254 408,255"/>
          <path d="M452,228 C440,246 418,257 396,258"/>
          <path d="M434,232 C424,249 404,259 384,260"/>
        </g>
      </g>
      <path d="${BLU_BODY}" fill="none" stroke="${c.line}" stroke-width="3.6" stroke-linejoin="round" stroke-opacity="0.92"/>
      <!-- tiny dorsal fin, set far back like the real thing -->
      <path d="M200,86 C208,72 217,66 226,64 C221,74 218,82 217,92 Z" ${filled(c, c.dark, 2.8)}/>
      <path d="M404,80 q8,-5 16,0" ${stroke(c, 2.8)}/>
      ${spoutMarkup(c)}
      <!-- mouth: dark interior, then the hinged lower jaw over it -->
      <path class="mouthShape" d="M516,178 C494,198 458,210 414,206 C452,226 496,214 518,190 Z" fill="#23384a" stroke="none"/>
      <g class="jaw">
        <path d="M412,202 C452,214 492,204 516,178 C520,206 494,236 448,242 C420,244 408,226 412,202 Z" ${filled(c, c.belly, 3.2)}/>
      </g>
      <path d="M516,178 C494,198 458,210 414,206" ${stroke(c, 4)}/>
      <g class="eyes">
        <ellipse cx="468" cy="166" rx="16" ry="18" ${filled(c, '#fdfaf2', 3)}/>
        <g class="pupil">
          <circle cx="471" cy="169" r="8.5" fill="#22303c"/>
          <circle cx="475" cy="163" r="3" fill="#fdfaf2" opacity="0.95"/>
        </g>
        <g clip-path="url(#eyeclip-${c.id})"><g class="lid"><rect x="448" y="120" width="42" height="60" fill="${c.body}"/><line x1="448" y1="180" x2="490" y2="180" stroke="${c.line}" stroke-width="3" stroke-opacity="0.85"/></g></g>
        <g class="brow"><path d="M452,140 Q468,130 486,140" ${stroke(c, c.browWidth)}/></g>
      </g>
      <g class="flipper"><path d="M400,232 C384,262 356,288 330,296 C319,299 314,290 321,280 C339,256 372,234 392,224 Z" ${filled(c, c.dark)}/></g>
    </g>
  </g>`;
}

// ---------- WRIGHT: chunky charcoal loaf, arched mouth, callosities ----------
function wrightSide(c) {
  return `
  <g class="root">
    <g class="flipperFar"><path d="M356,232 C340,258 314,278 290,284 C281,286 277,278 284,269 C300,250 332,230 348,222 Z" ${filled(c, c.dark)}/></g>
    <g class="fluke">
      <path d="M112,156 C88,124 56,104 26,96 C38,122 45,140 43,158 C45,180 36,200 22,224 C54,214 88,188 114,164 Z" ${filled(c, c.dark)}/>
      <path d="M43,158 L110,160" ${stroke(c, 2)}/>
    </g>
    <g class="body">
      <path d="${WRIGHT_BODY}" ${filled(c, c.body)}/>
      <g clip-path="url(#bodyclip-${c.id})">
        <path d="M96,156 C140,98 240,60 350,64 C452,68 516,108 512,164 C458,124 372,102 276,108 C192,113 134,138 96,156 Z" fill="${c.dark}" opacity="0.6"/>
        <path d="M160,214 C240,256 340,266 430,240 L430,300 L150,300 Z" fill="${c.belly}" opacity="0.35"/>
        <path d="${WRIGHT_BODY}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.28"/>
      </g>
      <path d="${WRIGHT_BODY}" fill="none" stroke="${c.line}" stroke-width="3.6" stroke-linejoin="round" stroke-opacity="0.92"/>
      <path d="M430,72 q8,-5 16,0" ${stroke(c, 2.8)}/>
      ${spoutMarkup(c)}
      <!-- the signature: a huge arched mouth that swallows half the head -->
      <path class="mouthShape" d="M510,142 C516,198 488,244 434,252 C400,256 384,238 382,210 C398,236 432,240 464,220 C492,202 506,172 510,142 Z" fill="#24262e" stroke="none"/>
      <g class="jaw">
        <path d="M382,208 C400,238 434,242 466,222 C494,204 508,174 510,142 C522,200 492,258 428,266 C394,268 378,240 382,208 Z" ${filled(c, c.lip, 3.2)}/>
        <path d="M392,222 C412,244 446,244 474,224" ${stroke(c, 2.2)} opacity="0.35"/>
        <path d="M462,244 q14,-11 24,-4 q4,11 -9,15 q-14,2 -15,-11 Z" ${filled(c, c.callosity, 2.2)}/>
        ${warts(c, 471, 249, 15, 4, 7)}
      </g>
      <path d="M510,142 C516,198 488,244 434,252 C404,256 386,238 382,210" ${stroke(c, 5.4)} stroke-opacity="1"/>
      <path d="M506,150 C511,198 484,236 432,244 C408,247 393,235 388,216" fill="none" stroke="${c.callosity}" stroke-width="2" stroke-linecap="round" opacity="0.5"/>
      <!-- callosities: the bonnet on the rostrum, and the patch over the eye -->
      <path d="M472,104 q16,-15 34,-6 q11,8 1,18 q-22,8 -37,-10 Z" ${filled(c, c.callosity, 2.4)}/>
      ${warts(c, 488, 108, 26, 7, 1)}
      <path d="M398,146 q12,-11 24,-5 q8,5 1,12 q-16,5 -25,-7 Z" ${filled(c, c.callosity, 2.2)}/>
      ${warts(c, 410, 148, 16, 5, 3)}
      <g class="eyes">
        <ellipse cx="404" cy="176" rx="15" ry="13" ${filled(c, '#f6f2e6', 3)}/>
        <g class="pupil"><circle cx="408" cy="178" r="6" fill="#26242c"/><circle cx="411" cy="174" r="2.2" fill="#f6f2e6" opacity="0.85"/></g>
        <g clip-path="url(#eyeclip-${c.id})"><g class="lid"><rect x="385" y="140" width="40" height="48" fill="${c.body}"/><line x1="385" y1="188" x2="425" y2="188" stroke="${c.line}" stroke-width="3" stroke-opacity="0.85"/></g></g>
        <g class="brow"><path d="M386,154 L424,148" ${stroke(c, c.browWidth)}/></g>
      </g>
      <g class="flipper"><path d="M350,238 C334,266 306,288 280,294 C270,296 266,288 273,278 C291,254 324,234 342,226 Z" ${filled(c, c.dark)}/></g>
    </g>
  </g>`;
}

// ---------- static front / top views (character sheet) ----------
function frontView(c) {
  const wright = c.id === 'wright';
  const bodyPath = wright
    ? 'M280,64 C200,68 152,116 152,178 C152,240 204,282 280,284 C356,282 408,240 408,178 C408,116 360,68 280,64 Z'
    : 'M280,66 C204,70 158,116 158,176 C158,238 208,280 280,282 C352,280 402,238 402,176 C402,116 356,70 280,66 Z';
  const call = wright
    ? `<path d="M258,94 q20,-16 42,-4 q10,8 -2,16 q-26,8 -40,-12 Z" ${filled(c, c.callosity, 2.4)}/>${warts(c, 280, 100, 34, 7, 5)}`
    : '';
  const spout = wright
    ? `<path d="M262,58 C250,38 240,24 228,12 M298,58 C310,38 320,24 332,12" ${stroke(c, 3.4)} opacity="0.5"/>`
    : `<path d="M272,56 C269,36 271,22 266,8 M288,56 C292,36 289,20 295,6" ${stroke(c, 3.4)} opacity="0.5"/>`;
  const eyes = wright
    ? `<ellipse cx="212" cy="180" rx="15" ry="13" ${filled(c, '#f6f2e6', 2.8)}/><circle cx="215" cy="182" r="6" fill="#26242c"/>
       <ellipse cx="348" cy="180" rx="15" ry="13" ${filled(c, '#f6f2e6', 2.8)}/><circle cx="345" cy="182" r="6" fill="#26242c"/>
       <path d="M194,158 L230,152 M330,152 L366,158" ${stroke(c, 9)}/>`
    : `<ellipse cx="220" cy="170" rx="16" ry="18" ${filled(c, '#fdfaf2', 2.8)}/><circle cx="224" cy="173" r="8.5" fill="#22303c"/><circle cx="228" cy="167" r="3" fill="#fdfaf2"/>
       <ellipse cx="340" cy="170" rx="16" ry="18" ${filled(c, '#fdfaf2', 2.8)}/><circle cx="336" cy="173" r="8.5" fill="#22303c"/><circle cx="340" cy="167" r="3" fill="#fdfaf2"/>
       <path d="M202,144 Q220,134 238,144 M322,144 Q340,134 358,144" ${stroke(c, 4)}/>`;
  const mouth = wright
    ? `<path d="M196,206 C232,258 328,258 364,206" ${stroke(c, 4.4)}/>${warts(c, 280, 246, 40, 6, 9)}`
    : `<path d="M214,212 C248,242 312,242 346,212" ${stroke(c, 4)}/>
       <g ${stroke(c, 2)} opacity="0.45"><path d="M240,240 C258,252 302,252 320,240"/><path d="M244,254 C262,264 298,264 316,254"/></g>`;
  return `
  <g class="root">
    <path d="M150,216 C116,238 96,264 92,286 C114,280 140,264 160,242 Z" ${filled(c, c.dark)}/>
    <path d="M410,216 C444,238 464,264 468,286 C446,280 420,264 400,242 Z" ${filled(c, c.dark)}/>
    <path d="${bodyPath}" ${filled(c, c.body)}/>
    <g clip-path="url(#bodyclip-${c.id})"></g>
    <path d="${bodyPath}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.22"/>
    <ellipse cx="280" cy="236" rx="86" ry="52" fill="${c.belly}" opacity="${wright ? 0.3 : 0.85}" stroke="none"/>
    ${spout}${call}${eyes}${mouth}
  </g>`;
}

function topView(c) {
  const wright = c.id === 'wright';
  const bodyPath = wright
    ? 'M500,160 C486,120 424,96 348,92 C250,86 156,110 104,140 C88,149 80,156 80,160 C80,164 88,171 104,180 C156,210 250,234 348,228 C424,224 486,200 500,160 Z'
    : 'M512,160 C498,122 440,100 368,96 C266,90 168,114 108,144 C90,153 82,156 82,160 C82,164 90,167 108,176 C168,206 266,230 368,224 C440,220 498,198 512,160 Z';
  const call = wright
    ? `<path d="M452,146 q20,-8 38,2 q8,10 -10,15 q-26,3 -28,-17 Z" ${filled(c, c.callosity, 2.4)}/>${warts(c, 470, 154, 32, 8, 9)}`
    : `<path d="M300,110 L300,210" ${stroke(c, 2)} opacity="0.3"/>`;
  return `
  <g class="root">
    <path d="M86,150 C58,120 34,102 12,94 C22,120 29,140 27,160 C29,182 20,202 10,228 C36,220 62,196 88,168 Z" ${filled(c, c.dark)}/>
    <path d="M320,${wright ? 112 : 118} C304,84 284,64 262,54 C270,80 276,100 278,${wright ? 110 : 116} Z" ${filled(c, c.dark)}/>
    <path d="M320,${wright ? 208 : 202} C304,236 284,256 262,266 C270,240 276,220 278,${wright ? 210 : 204} Z" ${filled(c, c.dark)}/>
    <path d="${bodyPath}" ${filled(c, c.body)}/>
    <path d="${bodyPath}" fill="url(#hatch-${c.id})" stroke="none" opacity="0.3"/>
    <path d="M${wright ? 446 : 458},160 q11,-7 22,0 q-11,7 -22,0 Z" ${filled(c, c.belly, 2)}/>
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
      boil: q('.boil'), root: q('.root'), body: q('.body'), fluke: q('.fluke'),
      flipper: q('.flipper'), flipperFar: q('.flipperFar'), brow: q('.brow'),
      lid: q('.lid'), pupil: q('.pupil'), jaw: q('.jaw'), spout: q('.spout'),
    };
    const wright = config.id === 'wright';
    this._origins = {
      root: '300px 170px',
      fluke: wright ? '112px 158px' : '120px 152px',
      flipper: wright ? '348px 230px' : '396px 228px',
      flipperFar: wright ? '354px 226px' : '390px 220px',
      jaw: `${config.hinge[0]}px ${config.hinge[1]}px`,
      brow: `${config.eye.cx}px ${config.eye.cy - 20}px`,
      pupil: `${config.eye.cx}px ${config.eye.cy}px`,
      spout: wright ? '452px 74px' : '423px 80px',
    };
    for (const k of ['root', 'fluke', 'flipper', 'flipperFar', 'jaw', 'brow', 'pupil', 'spout']) {
      if (this.parts[k]) this.parts[k].style.transformOrigin = this._origins[k];
    }
    this.parts.lid.style.transformOrigin = `${config.eye.cx}px ${config.eye.cy}px`;

    this.x = 0;                 // stage percent — the stage moves this.el
    this.facing = config.homeFacing;
    // Leap state, applied by the stage to the MOUNT (not the SVG) so the whale
    // can rise clean out of its own box without clipping.
    this.lift = 0;              // percent of its own height
    this.roll = 0;              // degrees
    this.onSplash = null;       // fired once, at the moment of re-entry
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
    this._splashed = false;
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
    // A breach is a whole performance: give it room to coil, fly and land.
    this.stateDur = name === 'breach' ? Math.max(duration, 2.9) : duration;
    if (name === 'breach') this._splashed = false;
    const emote = EMOTES[name];
    if (emote && emote.expr) this.setExpression(emote.expr, this.stateDur);
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

  setPose(name, exprOverride = null) {
    const p = POSES[name] || POSES.float;
    this.talking = false;
    this.blink = 0;
    this._talkOpen = 0;
    this._spout = name === 'breach' ? 1 : 0;
    this.lift = 0;
    this.roll = 0;
    this.exprCurrent = { ...EXPRESSIONS[exprOverride || p.expr || this.cfg.defaultExpression] };
    this._apply(this.exprCurrent, { flip: p.flip, flipFar: p.flipFar, fluke: p.fluke, pitch: p.pitch, bob: p.bob });
  }

  _apply(e, m) {
    const p = this.parts;
    const lid = Math.max(e.lid, this.blink);
    const lidRange = this.cfg.eye.rH * 2 + 20;
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
      p.spout.style.transform = `scaleY(${0.35 + s * 0.65})`;
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

    this._boilT += dt;
    if (this._boilT > 0.16) {
      this._boilT = 0;
      this._boilIdx = (this._boilIdx + 1) % 3;
      this.parts.boil.setAttribute('filter', `url(#boil-${this.cfg.id}-${this._boilIdx})`);
    }

    this.blinkTimer -= dt;
    if (this.blinkTimer <= 0) { this.blinkTimer = 2 + Math.random() * 4; this.blink = 1; }
    if (this.blink > 0) this.blink = Math.max(0, this.blink - dt * 7);

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

    let spoutTarget = 0;
    let liftTarget = 0;
    let rollTarget = 0;

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
        m.flip = -(18 + 22 * Math.sin(t * 2.4 + phase));
        m.fluke = Math.sin(t * 2.0 + phase) * 10;
      } else {
        m.flip = -Math.max(0, Math.sin(t * 1.4 + phase)) * 10;
      }
    } else if (s === 'wave') {
      const k = Math.min(1, st * 4);
      m.flip = -k * 92 + Math.sin(st * 9) * 18 * k;
      m.pitch -= 2 * k;
    } else if (s === 'laugh') {
      const b = Math.abs(Math.sin(st * 8));
      m.bob -= b * 7;
      m.pitch -= 2;
      m.flip = -12 - b * 18;
      m.fluke = Math.sin(st * 8) * 16;
      spoutTarget = 0.5 + b * 0.5;
    } else if (s === 'think') {
      const k = Math.min(1, st * 3);
      m.pitch += 6 * k;
      m.flip = -k * 44;
      m.fluke = -k * 10 + Math.sin(t * 1.6) * 4;
    } else if (s === 'shrug' || s === 'sigh') {
      const k = Math.min(1, st * 4) * (this.stateDur - st > 0.4 ? 1 : Math.max(0, (this.stateDur - st) / 0.4));
      m.flip = -k * 38;
      m.flipFar = k * 30;
      m.bob -= k * 3;
      m.browLift = -k * 3;
      if (s === 'sigh') spoutTarget = k * 0.45;
    } else if (s === 'breach') {
      // ---- the big one, in five beats ----
      const T = clamp(st / this.stateDur, 0, 1);
      if (T < 0.17) {
        // 1. ANTICIPATION — sink, coil, nose down. You feel it coming.
        const k = ease(T / 0.17);
        liftTarget = -9 * k;
        m.pitch += 12 * k;
        m.flip = 26 * k;
        m.fluke = 22 * k;
        m.browLift = -3 * k;
      } else if (T < 0.84) {
        // 2-4. LAUNCH, HANG, FALL — one arc, nose up going out, over coming in.
        const u = (T - 0.17) / 0.67;
        const arc = Math.sin(u * Math.PI);
        liftTarget = arc * 118 - 9 * (1 - ease(Math.min(1, u * 3)));
        m.pitch += -34 * Math.cos(u * Math.PI);
        m.flip = -20 - 45 * arc;
        m.flipFar = 15 + 38 * arc;
        m.fluke = -26 * Math.cos(u * Math.PI) + Math.sin(st * 14) * 7 * arc;
        // BLU throws a full flip at the top; WRIGHT keeps his dignity.
        if (this.cfg.id === 'blu') {
          const spin = clamp((u - 0.12) / 0.72, 0, 1);
          rollTarget = -360 * ease(spin) * this.facing;
        } else {
          rollTarget = -12 * arc * this.facing;
        }
        spoutTarget = u < 0.3 ? 1 : 0;      // blows on the way out
      } else {
        // 5. IMPACT — hit the water, squash, settle.
        const k = (T - 0.84) / 0.16;
        if (!this._splashed) {
          this._splashed = true;
          this.onSplash?.(this.cfg.id);
        }
        liftTarget = -7 * Math.sin(k * Math.PI);   // dunk under, bounce back
        m.pitch += 16 * (1 - ease(k));
        m.bob += 6 * Math.sin(k * Math.PI * 2) * (1 - k);
        m.fluke = 18 * (1 - k);
        rollTarget = 0;
      }
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
        this.facing = this.cfg.homeFacing;
      } else {
        this.x += Math.sign(dx) * Math.min(dist, speed * dt);
        m.pitch += -3;
        m.fluke = Math.sin(t * 7) * 24;
        m.flip = 14 + Math.sin(t * 7 + 1) * 8;
        m.bob += Math.sin(t * 3.5) * 3;
      }
    }

    this._spout = lerp(this._spout, spoutTarget, Math.min(1, dt * 6));
    // The leap tracks hard (it's ballistic); the settle eases.
    this.lift = s === 'breach' ? lerp(this.lift, liftTarget, Math.min(1, dt * 22)) : lerp(this.lift, 0, Math.min(1, dt * 8));
    this.roll = s === 'breach' ? lerp(this.roll, rollTarget, Math.min(1, dt * 26)) : lerp(this.roll, 0, Math.min(1, dt * 8));

    if (st > this.stateDur && s !== 'swim') {
      this.state = this.talking ? 'talk' : 'idle';
      this.stateTime = 0;
      this.stateDur = Infinity;
    }

    this._apply(this.exprCurrent, m);
  }
}
