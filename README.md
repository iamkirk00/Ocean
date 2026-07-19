# BLU & WRIGHT — The Pod 🐋

An interactive, AI-enabled sea stage for two whale personas — the ocean-going
sibling of [Iceberg](https://github.com/iamkirk00/Iceberg)'s Rookery:

- **BLU** — *Biggest heart in the ocean.* A blue whale: intentional, warm,
  inspirational — a dialectic companion who challenges your thinking toward
  success and usually ends with a question or a small concrete challenge.
- **WRIGHT** — *The right whale. Allegedly.* Floats at the back of the
  migration, goes with the flow, and lands perfectly timed, slightly sarcastic
  one-liners that are secretly the wisest thing in the sea.

Both are fully rigged, animated **living sketches** — layered pencil-style SVG
puppets (graphite strokes, hatch shading, sea-glass paper) with a boiling-line
effect that re-jitters the linework like hand-drawn pencil animation. No
external assets, no engine. Real anatomy jokes included: WRIGHT has callosities
and a V-shaped spout and no dorsal fin, because right whales actually do.

## Features

- **Sea stage** — the whales float just under a penciled surface with
  idle/swim/wave/laugh/think/shrug/**breach** animations, blinking, talking
  jaws, spouts, and speech bubbles pinned above their heads.
- **AI brain** — pick a provider in *Settings* (Anthropic or Groq), paste your
  API key, and choose a model. The whales respond in-persona, drawing on their
  editable backstories and memories; replies start with an emote tag (`[wave]`,
  `[think]`, …) that drives their animation. Without a key, a built-in scripted
  personality engine keeps the page fully working.
- **Family Voices** 🎙 — record short clips of real family members (a hello, a
  laugh, a victory whoop) in the browser. They join the **Family cameo**
  soundboard on the stage — play one and the whales react to it in character.
  Clips stay on-device until you seal them into an **encrypted voice vault**
  (`voices/family.vault`, AES-256-GCM with a family passphrase) that can safely
  live in this public repo: the repo only ever holds scrambled bytes, and any
  family device can unlock the whole crew with the passphrase.
- **Duo mode** — talk to *Both*, or hit *"Let them chat"* and watch BLU & WRIGHT
  riff with each other (AI-driven when a key is set, scripted otherwise).
- **Character Studio** — edit each whale's name, tagline, personality, backstory,
  and key memories. Everything persists in your browser; export/import as JSON.
- **Character sheet export** — one click renders a full model sheet per character
  (side/front/top turnaround, 8 poses, 8 expression close-ups) as a PNG. Click
  any cell to download that single render as a transparent 1024×1024 PNG.

## Run it

It's a fully static site — no build step.

**Locally:**

```bash
python3 -m http.server 8080   # or any static server
# open http://localhost:8080
```

(Opening `index.html` directly from disk won't work — ES modules need a server.)

**Publish on GitHub Pages:** push to `main`; the included workflow
(`.github/workflows/pages.yml`) publishes to the `gh-pages` branch on every
push. The page appears at `https://<user>.github.io/Ocean/`.

## The voice vault, in one minute

1. Open **Family Voices**, add each family member, record a few clips each.
2. Hit **Seal & export** with a passphrase the whole family knows — you get a
   `family.vault` file.
3. Commit that file to the repo at `voices/family.vault` (drag-drop in the
   GitHub web UI works).
4. On any device, the site spots the vault, asks for the passphrase once, and
   the whole crew appears on the soundboard. Lock it again anytime.

Clips are encrypted in the browser before export (PBKDF2 → AES-256-GCM via
WebCrypto). Without the passphrase the vault is noise.

## Project layout

```
index.html            page shell + tabs (Stage / Characters / Family Voices / Sheet / Settings)
css/style.css         all styling incl. the sea-paper stage
js/sketch-whale.js    pencil-style SVG whale puppets: drawing, rig, expressions, poses, FSM
js/brain.js           AI provider clients, system-prompt builder, scripted fallback
js/familyVoices.js    voice booth, IndexedDB clip store, encrypted vault, cameo soundboard
js/voice.js           text-to-speech (device voices or Groq TTS) + clip playback
js/sheet.js           character-sheet renderer/exporter (SVG → PNG)
js/app.js             stage, chat orchestration, editors, UI wiring
data/personas.js      default character minds + localStorage persistence
voices/               drop family.vault here to publish the (encrypted) family voices
```
