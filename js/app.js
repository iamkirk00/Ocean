// app.js — sea stage, chat orchestration, editors, family voices, sheet UI.
import { SketchWhale, WHALE_CONFIGS, EMOTES } from './sketch-whale.js';
import { buildSystemPrompt, callLLM, testKey, parseEmote, scriptedReply, scriptedBanter, PROVIDERS, defaultModel } from './brain.js';
import { speakText, stopSpeaking, playBlob, listDeviceVoices, GROQ_TTS_VOICES, GROQ_DEFAULT_VOICE } from './voice.js';
import { loadCharacters, saveCharacters, resetCharacters, loadSettings, saveSettings, DEFAULT_CHARACTERS } from '../data/personas.js';
import { generateSheet, renderSingle, downloadCanvas } from './sheet.js';
import { createFamilyVoices } from './familyVoices.js';
import { createHomeContext } from './homeContext.js';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

let characters = loadCharacters();
let settings = migrateSettings(loadSettings());

// settings shape: { provider, keys: {anthropic, groq}, models: {anthropic, groq} }
function migrateSettings(s) {
  return {
    provider: s.provider || 'anthropic',
    keys: { anthropic: '', groq: '', ...(s.keys || {}) },
    models: { anthropic: defaultModel('anthropic'), groq: defaultModel('groq'), ...(s.models || {}) },
    voice: {
      enabled: true,
      engine: 'device',
      ...(s.voice || {}),
      device: { blu: 'auto', wright: 'auto', ...((s.voice || {}).device || {}) },
      groq: { ...GROQ_DEFAULT_VOICE, ...((s.voice || {}).groq || {}) },
    },
  };
}

// ============================================================ family board bridge
// When these pages are served from Family Commons (/ocean), the family's login
// is on this same origin — so the whales can read today's real board and think
// with the family server's AI. On GitHub Pages every call below no-ops.
const home = createHomeContext();
const OTHER = { blu: 'wright', wright: 'blu' };

// Browsers only allow audio after the user has interacted with the page.
let userInteracted = false;
for (const ev of ['pointerdown', 'keydown']) {
  window.addEventListener(ev, () => { userInteracted = true; }, { once: true, capture: true });
}
const voicePending = { wright: false, blu: false };
function voiceOn() { return settings.voice.enabled && userInteracted; }
function voiceCfg(charId) {
  return {
    engine: settings.voice.engine,
    deviceVoiceName: settings.voice.device[charId],
    groqKey: settings.keys.groq,
    groqVoice: settings.voice.groq[charId],
  };
}

// ============================================================ sea stage
const stageWrap = $('#stage-wrap');
const whales = {
  wright: new SketchWhale(WHALE_CONFIGS.wright, $('#mount-wright')),
  blu: new SketchWhale(WHALE_CONFIGS.blu, $('#mount-blu')),
};
// entrance: swim in from open water
whales.wright.x = -20;
whales.blu.x = 120;
let greeted = false;

const mounts = { wright: $('#mount-wright'), blu: $('#mount-blu') };
const shadows = { wright: $('#shadow-wright'), blu: $('#shadow-blu') };

// On phones, only the whale you're talking to takes the stage ("Both" shows both).
const phoneMq = window.matchMedia('(max-width: 760px)');
function visible(id) { return mounts[id].style.display !== 'none'; }
function setCast(ids, positions) {
  for (const id of ['wright', 'blu']) {
    const show = ids.includes(id);
    mounts[id].style.display = show ? '' : 'none';
    shadows[id].style.display = show ? '' : 'none';
    if (!show) bubbles[id].classList.add('hidden');
  }
  ids.forEach((id, i) => whales[id].walkTo(positions[i]));
}
function updateCast() {
  if (phoneMq.matches && who !== 'both') setCast([who], [50]);
  else setCast(['wright', 'blu'], [30, 70]);
}
phoneMq.addEventListener('change', updateCast);

// speech bubbles pinned above heads
const bubbles = { wright: $('#bubble-wright'), blu: $('#bubble-blu') };
function placeBubbles() {
  const wrapRect = stageWrap.getBoundingClientRect();
  for (const id of ['wright', 'blu']) {
    const el = bubbles[id];
    if (el.classList.contains('hidden')) continue;
    const r = mounts[id].getBoundingClientRect();
    el.style.left = `${r.left + r.width / 2 - wrapRect.left}px`;
    el.style.top = `${r.top - wrapRect.top + r.height * 0.06}px`;
  }
}

let last = performance.now();
function loop(now) {
  requestAnimationFrame(loop);
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  const t = now / 1000;
  for (const id of ['wright', 'blu']) {
    const p = whales[id];
    p.update(dt, t);
    mounts[id].style.left = `${p.x}%`;
    shadows[id].style.left = `${p.x}%`;
  }
  if (!greeted && !whales.blu.walk && !whales.wright.walk) {
    greeted = true;
    if (visible('blu')) {
      whales.blu.play('wave', 2.4);
      speak('blu', "Hey! Welcome to the Pod. Ask us anything — or just say hi.", 5200);
    }
    if (visible('wright')) {
      setTimeout(() => { whales.wright.play('sigh', 2); speak('wright', "I was told there would be krill.", 4200); }, visible('blu') ? 2600 : 400);
    }
  }
  placeBubbles();
}
requestAnimationFrame(loop);

// ============================================================ speaking
const bubbleTimers = {};
// One whale talks at a time: every speak() is queued behind the previous one
// (bubble + voice), so conversations stage naturally instead of overlapping.
let speechQueue = Promise.resolve();
function speak(charId, text, holdMs = null) {
  const run = () => new Promise((resolve) => {
    const el = bubbles[charId];
    const p = whales[charId];
    clearTimeout(bubbleTimers[charId]);
    clearInterval(bubbleTimers[charId + '_tw']);
    el.classList.remove('hidden');
    el.textContent = '';
    p.setTalking(true);

    let textDone = false;
    let voiceDone = true;
    let resolved = false;
    const maybeFinish = () => {
      if (textDone && voiceDone && !resolved) { resolved = true; resolve(); }
    };

    if (voiceOn()) {
      voiceDone = false;
      voicePending[charId] = true;
      speakText(charId, text, voiceCfg(charId), {
        onstart: () => p.setTalking(true),
        onend: () => { voicePending[charId] = false; voiceDone = true; p.setTalking(false); maybeFinish(); },
      });
      // never let a stuck audio engine hang the whole conversation
      setTimeout(() => {
        if (!voiceDone) { voiceDone = true; voicePending[charId] = false; maybeFinish(); }
      }, 45000);
    }

    let i = 0;
    const tw = setInterval(() => {
      i += 2;
      el.textContent = text.slice(0, i);
      if (i >= text.length) {
        clearInterval(tw);
        if (!voicePending[charId]) p.setTalking(false); // else the voice closes the jaw
        const hold = holdMs ?? Math.max(2600, text.length * 45);
        bubbleTimers[charId] = setTimeout(() => el.classList.add('hidden'), hold);
        textDone = true;
        maybeFinish();
      }
    }, 24);
    bubbleTimers[charId + '_tw'] = tw;
  });
  speechQueue = speechQueue.then(run, run);
  return speechQueue;
}

function performEmote(charId, emote) {
  const p = whales[charId];
  const e = EMOTES[emote];
  if (!e) return;
  if (e.anim) p.play(e.anim, 2.2);
  else if (e.expr) p.setExpression(e.expr, 3);
}

// A board fact, said the way each whale would say it.
const FACT_LINES = {
  blu: [
    '[smile] Straight from the family board: {f}.',
    '[nod] Checked the board — {f}. What are you doing with that?',
  ],
  wright: [
    '[shrug] Board says {f}. Don\'t shoot the messenger.',
    '[nod] {f}. I read it so you didn\'t have to. This is my whole contribution.',
  ],
};
function factLine(charId, fact) {
  const arr = FACT_LINES[charId];
  return arr[Math.floor(Math.random() * arr.length)].replace('{f}', fact);
}

// ============================================================ chat
const chatLog = $('#chat-log');
const chatHistory = { wright: [], blu: [] }; // per-character API transcripts
let who = 'blu';
let busy = false;
updateCast(); // kicks off the entrance swim for whoever is on stage

// ---- mobile chat drawer: collapse after sending so the stage stays visible
const chatPanel = $('#chat-panel');
const collapseBtn = $('#chat-collapse');
function setChatCollapsed(on) {
  chatPanel.classList.toggle('collapsed', on);
  collapseBtn.textContent = on ? '▴ open chat' : '▾ hide chat — watch the sea';
  chatPanel.scrollTop = 0; // focus inside overflow:hidden can force-scroll; pin it
  if (on) document.activeElement?.blur?.();
}
collapseBtn.addEventListener('click', () => setChatCollapsed(!chatPanel.classList.contains('collapsed')));

function addMsg(kind, text, name = null) {
  const div = document.createElement('div');
  div.className = `msg ${kind}`;
  if (name) {
    const n = document.createElement('span');
    n.className = 'msg-name';
    n.textContent = name;
    div.appendChild(n);
  }
  div.appendChild(document.createTextNode(text));
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

function provider() { return settings.provider; }
function homeAi() { const st = home.status(); return st.serverPresent && st.serverAi && st.signedIn; }
function hasKey() {
  if (provider() === 'home') return homeAi();
  return !!(settings.keys[provider()] && settings.keys[provider()].trim());
}
function model() {
  if (provider() === 'home') return 'family';
  return settings.models[provider()] || defaultModel(provider());
}

/** One way in for both characters, whichever brain is answering. */
async function askCharacter(charId, mode, messages) {
  const char = characters[charId];
  const other = characters[OTHER[charId]];
  if (provider() === 'home') {
    // Server mode: the house server thinks (board already in its prompt).
    // Browser mode: this device thinks with the family's key, board included.
    if (home.aiRoute() === 'server') {
      return home.serverChat({ character: charId, persona: char, other, mode, messages });
    }
    await home.refresh();
    return home.browserChat(buildSystemPrompt(char, other, mode, home.todayPrompt()), messages);
  }
  await home.refresh();   // keep today's board fresh for the prompt below
  return callLLM({
    provider: provider(),
    apiKey: settings.keys[provider()],
    model: model(),
    system: buildSystemPrompt(char, other, mode, home.todayPrompt()),
    messages,
  });
}

function refreshBrainStatus(state = null, msg = null) {
  const el = $('#brain-status');
  if (state === 'error') {
    el.className = 'error';
    el.textContent = msg || 'API error — fell back to scripted mode';
    return;
  }
  const st = home.status();
  const board = st.hasToday ? ` · reading today's board (${st.weekday})` : '';
  if (hasKey()) {
    el.className = 'online';
    el.textContent = provider() === 'home'
      ? `live AI — the family server${board}`
      : `live AI — ${PROVIDERS[provider()].label} · ${model()}${board}`;
  } else if (st.hasToday) {
    el.className = 'offline';
    el.textContent = `scripted mode — but they can still read today's board${st.serverAi ? ' (pick Family server in Settings for live AI)' : ''}`;
  } else {
    el.className = 'offline';
    el.textContent = 'scripted mode — add an API key in Settings for live AI';
  }
}
refreshBrainStatus();

// make a silent Groq→device voice fallback visible instead of mysterious
window.addEventListener('voice-fallback', (e) => {
  refreshBrainStatus('error', `Groq voice unavailable (${String(e.detail).slice(0, 60)}) — using device voice`);
  setTimeout(() => refreshBrainStatus(), 6000);
});

async function charRespond(charId, userText) {
  const char = characters[charId];
  const other = characters[charId === 'blu' ? 'wright' : 'blu'];
  chatHistory[charId].push({ role: 'user', content: userText });
  if (chatHistory[charId].length > 24) chatHistory[charId].splice(0, chatHistory[charId].length - 24);

  let raw;
  if (hasKey()) {
    try {
      raw = await askCharacter(charId, 'user', chatHistory[charId]);
      refreshBrainStatus();
    } catch (err) {
      console.warn(err);
      refreshBrainStatus('error', `API error (${err.message.slice(0, 60)}…) — falling back`);
      // The thinking failed, but the board is still right here.
      const fact = home.factAnswer(userText);
      raw = fact ? factLine(charId, fact) : scriptedReply(charId, userText);
    }
  } else {
    await new Promise((r) => setTimeout(r, 500 + Math.random() * 600));
    // No AI — but if the family board is here, real facts still beat a script.
    await home.refresh();
    const fact = home.factAnswer(userText);
    raw = fact ? factLine(charId, fact) : scriptedReply(charId, userText);
  }
  chatHistory[charId].push({ role: 'assistant', content: raw });

  const { emote, text } = parseEmote(raw);
  if (emote) performEmote(charId, emote);
  addMsg(charId, text, char.name);
  await speak(charId, text); // hold the floor until this whale finishes
  return text;
}

$('#chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('#chat-input');
  const text = input.value.trim();
  if (!text || busy) return;
  input.value = '';
  busy = true;
  $('#chat-send').disabled = true;
  addMsg('user', text, 'You');
  if (phoneMq.matches) setChatCollapsed(true); // clear the stage for the reply

  try {
    if (who === 'both') {
      const typing1 = addMsg('blu typing', '…');
      const bluText = await charRespond('blu', text);
      typing1.remove();
      await new Promise((r) => setTimeout(r, 500));
      const typing2 = addMsg('wright typing', '…');
      await charRespond('wright', `${text}\n\n(${characters.blu.name} just replied: "${bluText}" — react to the user and to that.)`);
      typing2.remove();
    } else {
      const typing = addMsg(`${who} typing`, '…');
      await charRespond(who, text);
      typing.remove();
    }
  } finally {
    busy = false;
    $('#chat-send').disabled = false;
    if (!chatPanel.classList.contains('collapsed')) input.focus();
    else chatPanel.scrollTop = 0;
  }
});

$$('#who-picker .who').forEach((btn) => btn.addEventListener('click', () => {
  $$('#who-picker .who').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  who = btn.dataset.who;
  updateCast();
}));

// ---- duo banter
$('#btn-banter').addEventListener('click', async () => {
  if (busy) return;
  busy = true;
  $('#btn-banter').disabled = true;
  addMsg('sys', '— BLU & WRIGHT start riffing —');
  setCast(['wright', 'blu'], [34, 66]); // banter needs both on stage, even on phones
  if (phoneMq.matches) setChatCollapsed(true);

  try {
    if (hasKey()) {
      const transcript = [];
      let speaker = Math.random() < 0.6 ? 'blu' : 'wright';
      for (let turn = 0; turn < 5; turn++) {
        const char = characters[speaker];
        const other = characters[speaker === 'blu' ? 'wright' : 'blu'];
        const messages = transcript.length
          ? transcript.map((tr) => ({ role: tr.speaker === speaker ? 'assistant' : 'user', content: tr.raw }))
          : [{ role: 'user', content: '(Kick off a short, fun exchange with your best friend. Pick any topic from your life.)' }];
        let raw;
        try {
          raw = await askCharacter(speaker, 'banter', messages);
        } catch (err) {
          refreshBrainStatus('error', 'API error mid-banter — switched to script');
          break;
        }
        transcript.push({ speaker, raw });
        const { emote, text } = parseEmote(raw);
        if (emote) performEmote(speaker, emote);
        addMsg(speaker, text, char.name);
        await speak(speaker, text);
        await new Promise((r) => setTimeout(r, 550)); // a beat between turns
        speaker = speaker === 'blu' ? 'wright' : 'blu';
      }
      if (transcript.length) { busy = false; $('#btn-banter').disabled = false; return; }
    }
    // scripted banter
    for (const [speaker, raw] of scriptedBanter()) {
      const { emote, text } = parseEmote(raw);
      if (emote) performEmote(speaker, emote);
      addMsg(speaker, text, characters[speaker].name);
      await speak(speaker, text);
      await new Promise((r) => setTimeout(r, 550));
    }
  } finally {
    busy = false;
    $('#btn-banter').disabled = false;
    setTimeout(updateCast, 2500); // after the last bubble, restore the phone cast
  }
});

// ---- direct animation buttons
$$('.anim-btn[data-anim]').forEach((btn) => btn.addEventListener('click', () => {
  const anim = btn.dataset.anim;
  const targets = who === 'both' ? ['blu', 'wright'] : [who];
  for (const id of targets) {
    if (anim === 'swim') {
      const base = id === 'wright' ? 30 : 70;
      whales[id].walkTo(base + (Math.random() * 24 - 12));
    } else {
      const e = EMOTES[anim];
      whales[id].play(e?.anim || anim, 2.6);
      if (e && e.expr) whales[id].setExpression(e.expr, 2.6);
    }
  }
}));

// ============================================================ family voices
const familyVoices = createFamilyVoices({
  dbName: 'pod.voices',
  vaultUrl: 'voices/family.vault',
  playBlob,
  onChange: () => {
    familyVoices.renderSoundboard($('#cameo-bar'), onCameo);
    if ($('#view-family').classList.contains('active')) familyVoices.renderBooth($('#voice-booth'));
  },
});
familyVoices.init().then(() => familyVoices.renderSoundboard($('#cameo-bar'), onCameo));

// Scripted reactions when a real family voice plays on the stage.
const pickOf = (arr) => arr[Math.floor(Math.random() * arr.length)];
const CAMEO_LINES = {
  blu: [
    '[excited] {m}! Now THAT is a voice built for open water. Again!',
    "[laugh] You hear that, WRIGHT? {m} just out-sang the whole pod.",
    '[wave] {m} on deck! The ocean just got better.',
  ],
  wright: [
    '[surprised] Was that {m}? The ocean has a PA system now. Concerning. Kind of great.',
    '[shrug] {m} speaks, and suddenly everyone listens. I take notes.',
    "[nod] Heard you, {m}. I'm choosing to interpret that as applause.",
  ],
};

async function onCameo(member, label) {
  if (busy) return;
  const id = who === 'both' ? (Math.random() < 0.5 ? 'blu' : 'wright') : who;
  performEmote(id, 'surprised');
  await new Promise((r) => setTimeout(r, 1100)); // let the clip land first
  busy = true;
  try {
    if (hasKey()) {
      await charRespond(id, `(Family cameo: ${member}'s real recorded voice just played on the stage — they said "${label}". React briefly in character, addressing ${member} by name. Do not treat this as the user typing.)`);
    } else {
      const raw = pickOf(CAMEO_LINES[id]).replaceAll('{m}', member);
      const { emote, text } = parseEmote(raw);
      if (emote) performEmote(id, emote);
      addMsg(id, text, characters[id].name);
      await speak(id, text);
    }
  } finally {
    busy = false;
  }
}

// ============================================================ tabs
$$('#tabs .tab').forEach((btn) => btn.addEventListener('click', () => {
  $$('#tabs .tab').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  $$('.view').forEach((v) => v.classList.remove('active'));
  $(`#view-${btn.dataset.tab}`).classList.add('active');
  if (btn.dataset.tab === 'family') familyVoices.renderBooth($('#voice-booth'));
  // device voice lists load lazily on some platforms — refresh when visiting settings
  if (btn.dataset.tab === 'settings' && settings.voice.engine === 'device') renderVoiceRows();
}));

// ============================================================ character editors
function renderEditors() {
  const wrap = $('#char-editors');
  wrap.innerHTML = '';
  for (const id of ['blu', 'wright']) {
    const c = characters[id];
    const card = document.createElement('div');
    card.className = 'char-card';
    card.innerHTML = `
      <h3><span class="char-chip" style="background:${c.color}"></span>${c.name}</h3>
      <p class="tagline-note">Fields below are this character's mind. Replace the sample memories with your own — real moments make the companion real.</p>
      <label class="field"><span>Name</span><input type="text" data-f="name" value=""></label>
      <label class="field"><span>Tagline</span><input type="text" data-f="tagline" value=""></label>
      <label class="field"><span>Personality</span><textarea rows="6" data-f="personality"></textarea></label>
      <label class="field"><span>Backstory</span><textarea rows="8" data-f="backstory"></textarea></label>
      <div class="memories-head"><span>Key memories</span><button type="button" class="mem-add">+ Add memory</button></div>
      <div class="mem-list"></div>
      <div class="char-save-row"><button type="button" class="char-save">Save ${c.name}</button><span class="save-flash">Saved ✓</span></div>
    `;
    card.querySelector('[data-f="name"]').value = c.name;
    card.querySelector('[data-f="tagline"]').value = c.tagline;
    card.querySelector('[data-f="personality"]').value = c.personality;
    card.querySelector('[data-f="backstory"]').value = c.backstory;

    const memList = card.querySelector('.mem-list');
    const addMemory = (m = { title: '', text: '' }) => {
      const div = document.createElement('div');
      div.className = 'memory';
      div.innerHTML = `<button type="button" class="mem-del">remove</button>
        <input type="text" placeholder="Memory title" value="">
        <textarea placeholder="What happened, and why it matters…"></textarea>`;
      div.querySelector('input').value = m.title;
      div.querySelector('textarea').value = m.text;
      div.querySelector('.mem-del').addEventListener('click', () => div.remove());
      memList.appendChild(div);
    };
    (c.memories || []).forEach(addMemory);
    card.querySelector('.mem-add').addEventListener('click', () => addMemory());

    card.querySelector('.char-save').addEventListener('click', () => {
      characters[id] = {
        ...c,
        name: card.querySelector('[data-f="name"]').value.trim() || c.name,
        tagline: card.querySelector('[data-f="tagline"]').value.trim(),
        personality: card.querySelector('[data-f="personality"]').value,
        backstory: card.querySelector('[data-f="backstory"]').value,
        memories: [...memList.querySelectorAll('.memory')].map((mDiv) => ({
          title: mDiv.querySelector('input').value.trim(),
          text: mDiv.querySelector('textarea').value.trim(),
        })).filter((m) => m.title || m.text),
      };
      saveCharacters(characters);
      chatHistory[id] = []; // new mind, fresh transcript
      const flash = card.querySelector('.save-flash');
      flash.classList.add('show');
      setTimeout(() => flash.classList.remove('show'), 1800);
    });
    wrap.appendChild(card);
  }
}
renderEditors();

$('#btn-export-chars').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(characters, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'pod-characters.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
});

$('#file-import-chars').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    for (const id of ['blu', 'wright']) if (data[id]) characters[id] = { ...DEFAULT_CHARACTERS[id], ...data[id] };
    saveCharacters(characters);
    renderEditors();
  } catch { alert('Could not read that file — expected the JSON exported from this page.'); }
  e.target.value = '';
});

$('#btn-reset-chars').addEventListener('click', () => {
  if (!confirm('Reset both characters to the default personas? Your edits will be lost.')) return;
  characters = resetCharacters();
  renderEditors();
});

// ============================================================ character sheet
let sheetChar = 'blu';
let sheetCellMap = [];
$$('#sheet-char-pick .seg-btn').forEach((btn) => btn.addEventListener('click', () => {
  $$('#sheet-char-pick .seg-btn').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  sheetChar = btn.dataset.char;
}));

$('#btn-gen-sheet').addEventListener('click', async () => {
  const btn = $('#btn-gen-sheet');
  btn.disabled = true;
  try {
    const { canvas: sheet, cellMap } = await generateSheet(sheetChar, characters[sheetChar]);
    sheetCellMap = cellMap;
    const preview = $('#sheet-preview');
    preview.width = sheet.width;
    preview.height = sheet.height;
    preview.getContext('2d').drawImage(sheet, 0, 0);
    preview.classList.add('ready');
    $('#btn-dl-sheet').disabled = false;
  } finally {
    btn.disabled = false;
  }
});

$('#btn-dl-sheet').addEventListener('click', () => {
  downloadCanvas($('#sheet-preview'), `${characters[sheetChar].name.toLowerCase()}-character-sheet.png`);
});

$('#sheet-preview').addEventListener('click', async (e) => {
  const preview = $('#sheet-preview');
  const r = preview.getBoundingClientRect();
  const x = (e.clientX - r.left) * (preview.width / r.width);
  const y = (e.clientY - r.top) * (preview.height / r.height);
  const cell = sheetCellMap.find((c) => x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h);
  if (!cell) return;
  const single = await renderSingle(cell.charId, cell.opts, 1024);
  downloadCanvas(single, `${characters[cell.charId].name.toLowerCase()}-${cell.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.png`);
});

// ============================================================ settings
let uiProvider = settings.provider;

/** Adds the "Family server" choice when this page is served by Family Commons. */
function syncHomeProviderUI() {
  const st = home.status();
  const pick = $('#provider-pick');
  let btn = pick.querySelector('[data-provider="home"]');
  if (st.serverPresent && st.serverAi) {
    if (!btn) {
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'seg-btn';
      btn.dataset.provider = 'home';
      btn.textContent = 'Family server';
      btn.addEventListener('click', () => {
        settings.keys[uiProvider] = $('#set-apikey').value.trim();
        uiProvider = 'home';
        renderProviderUI();
      });
      pick.prepend(btn);
    }
  } else if (btn) {
    btn.remove();
  }
  refreshBrainStatus();
}

function renderProviderUI() {
  const p = PROVIDERS[uiProvider];
  $$('#provider-pick .seg-btn').forEach((b) =>
    b.classList.toggle('active', b.dataset.provider === uiProvider));
  // The family server keeps its own key — nothing to paste on this device.
  const serverSide = Boolean(p.serverSide);
  $('#set-apikey').closest('.field').style.display = serverSide ? 'none' : '';
  $('#set-model').closest('.field').style.display = serverSide ? 'none' : '';
  $('#btn-test-key').style.display = serverSide ? 'none' : '';
  if (serverSide) {
    const st = home.status();
    $('#key-help').textContent = st.signedIn
      ? 'Using the family server\'s own AI — no key needed here, and they can read today\'s board.'
      : 'Sign in to Family Commons in this browser, then reload — the whales will use the family server\'s AI.';
    $('#key-help').closest('.field').style.display = '';
    return;
  }
  $('#set-apikey').value = settings.keys[uiProvider] || '';
  $('#set-apikey').placeholder = p.keyHint;
  $('#key-help').innerHTML =
    `Stored only in this browser. Sent only to ${p.label}. ` +
    `Create a key at <a href="${p.consoleUrl}" target="_blank" rel="noopener">${p.consoleUrl.replace('https://', '')}</a>.`;
  const sel = $('#set-model');
  sel.innerHTML = '';
  for (const m of p.models) {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = m.label;
    sel.appendChild(opt);
  }
  sel.value = settings.models[uiProvider] || defaultModel(uiProvider);
}
renderProviderUI();

$$('#provider-pick .seg-btn').forEach((btn) => btn.addEventListener('click', () => {
  // keep whatever key is typed for the provider we're leaving
  settings.keys[uiProvider] = $('#set-apikey').value.trim();
  settings.models[uiProvider] = $('#set-model').value || settings.models[uiProvider];
  uiProvider = btn.dataset.provider;
  renderProviderUI();
}));

$('#btn-save-settings').addEventListener('click', () => {
  settings.provider = uiProvider;
  if (!PROVIDERS[uiProvider].serverSide) {
    settings.keys[uiProvider] = $('#set-apikey').value.trim();
    settings.models[uiProvider] = $('#set-model').value;
  }
  saveSettings(settings);
  refreshBrainStatus();
  const res = $('#test-result');
  res.className = 'ok';
  res.textContent = 'Saved.';
  setTimeout(() => (res.textContent = ''), 2000);
});

$('#btn-test-key').addEventListener('click', async () => {
  const res = $('#test-result');
  const key = $('#set-apikey').value.trim();
  if (!key) { res.className = 'bad'; res.textContent = 'Enter a key first.'; return; }
  res.className = '';
  res.textContent = 'Testing…';
  try {
    await testKey(uiProvider, key, $('#set-model').value);
    res.className = 'ok';
    res.textContent = `✓ Connected — the whales are thinking with ${PROVIDERS[uiProvider].label}.`;
  } catch (err) {
    res.className = 'bad';
    res.textContent = `✗ ${err.message.slice(0, 120)}`;
  }
});

// ============================================================ voice settings
const SAMPLE_LINES = {
  blu: "Now this is a story worth singing. Pull up some current, friend!",
  wright: "I had a thought. I'm keeping it. You get this sentence instead.",
};

function refreshVoiceToggleUI() {
  $$('#voice-toggle .seg-btn').forEach((b) =>
    b.classList.toggle('active', (b.dataset.v === 'on') === settings.voice.enabled));
  $('#btn-voice').textContent = settings.voice.enabled ? '🔊' : '🔇';
  $('#voice-engine').value = settings.voice.engine;
  $('#voice-engine-help').textContent = settings.voice.engine === 'groq'
    ? 'Uses the Groq key from the section above. Accept the PlayAI TTS model terms once in console.groq.com if prompted.'
    : 'Zero setup — voice quality depends on your device. iPhones and Macs sound best.';
}

function renderVoiceRows() {
  const wrap = $('#voice-rows');
  wrap.innerHTML = '';
  for (const id of ['blu', 'wright']) {
    const label = document.createElement('label');
    label.className = 'field';
    const sel = document.createElement('select');
    if (settings.voice.engine === 'groq') {
      for (const v of GROQ_TTS_VOICES) {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v.replace('-PlayAI', '') + (v === GROQ_DEFAULT_VOICE[id] ? ' — recommended' : '');
        sel.appendChild(opt);
      }
      sel.value = settings.voice.groq[id];
    } else {
      const auto = document.createElement('option');
      auto.value = 'auto';
      auto.textContent = 'Auto — picked to fit their character';
      sel.appendChild(auto);
      for (const v of listDeviceVoices().filter((v) => v.lang.toLowerCase().startsWith('en'))) {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = `${v.name} (${v.lang})`;
        sel.appendChild(opt);
      }
      sel.value = settings.voice.device[id] || 'auto';
    }
    sel.addEventListener('change', () => {
      settings.voice[settings.voice.engine === 'groq' ? 'groq' : 'device'][id] = sel.value;
      saveSettings(settings);
      // audition the new voice immediately so changes are self-verifying
      userInteracted = true;
      stopSpeaking();
      speakText(id, id === 'blu' ? 'BLU here — how do I sound?' : 'WRIGHT. Voice check. Riveting.', voiceCfg(id), {});
    });
    const test = document.createElement('button');
    test.type = 'button';
    test.textContent = `▶ Hear ${characters[id].name}`;
    test.style.marginTop = '6px';
    test.addEventListener('click', () => {
      userInteracted = true;
      stopSpeaking();
      speakText(id, SAMPLE_LINES[id], voiceCfg(id), {});
    });
    const span = document.createElement('span');
    span.textContent = `${characters[id].name} voice`;
    label.append(span, sel, test);
    wrap.appendChild(label);
  }
}

$$('#voice-toggle .seg-btn').forEach((btn) => btn.addEventListener('click', () => {
  settings.voice.enabled = btn.dataset.v === 'on';
  if (!settings.voice.enabled) stopSpeaking();
  saveSettings(settings);
  refreshVoiceToggleUI();
}));

$('#voice-engine').addEventListener('change', () => {
  settings.voice.engine = $('#voice-engine').value;
  saveSettings(settings);
  refreshVoiceToggleUI();
  renderVoiceRows();
});

$('#btn-voice').addEventListener('click', () => {
  settings.voice.enabled = !settings.voice.enabled;
  if (!settings.voice.enabled) stopSpeaking();
  saveSettings(settings);
  refreshVoiceToggleUI();
});

// device voice lists load asynchronously in some browsers
if ('speechSynthesis' in window) {
  speechSynthesis.addEventListener?.('voiceschanged', () => {
    if (settings.voice.engine === 'device') renderVoiceRows();
  });
}
refreshVoiceToggleUI();
renderVoiceRows();

// ============================================================ boot the family bridge
// Detects Family Commons, pulls today's board, and — first visit on the family
// server — points the whales at the server's AI so nobody has to paste a key.
home.init().then((st) => {
  if (st.serverPresent && st.serverAi && !loadSettings().provider) {
    settings.provider = 'home';
    uiProvider = 'home';
    saveSettings(settings);
  }
  syncHomeProviderUI();
  renderProviderUI();
  refreshBrainStatus();
});

// ============================================================ voice inbound
// Push-to-talk via the browser's built-in speech recognition. The final
// transcript drops into the chat box and sends itself.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const micButtons = [$('#btn-mic'), $('#btn-mic-stage')];
let rec = null;
let listening = false;

function setListening(on) {
  listening = on;
  for (const b of micButtons) {
    b.classList.toggle('listening', on);
    b.textContent = on ? '🔴' : '🎤';
  }
  $('#chat-input').placeholder = on ? 'Listening… tap 🔴 to stop' : 'Share a goal, a doubt, a story…';
}

function toggleMic() {
  if (!SR || busy) return;
  if (listening) { try { rec?.stop(); } catch {} return; }
  stopSpeaking(); // don't transcribe the whales
  rec = new SR();
  rec.lang = 'en-US';
  rec.interimResults = true;
  let finalText = '';
  rec.onresult = (e) => {
    let interim = '';
    for (const r of e.results) {
      if (r.isFinal) finalText += r[0].transcript;
      else interim += r[0].transcript;
    }
    $('#chat-input').value = (finalText + ' ' + interim).trim();
  };
  rec.onerror = () => setListening(false);
  rec.onend = () => {
    setListening(false);
    const text = $('#chat-input').value.trim();
    if (text) $('#chat-form').requestSubmit();
  };
  setListening(true);
  try { rec.start(); } catch { setListening(false); }
}

if (!SR) {
  for (const b of micButtons) {
    b.style.display = 'none';
  }
} else {
  for (const b of micButtons) b.addEventListener('click', toggleMic);
}
