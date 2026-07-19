// brain.js — how the whales think.
// Live mode: direct browser calls to the chosen AI provider (user's own key,
// stored locally). Fallback: a scripted personality engine so the page always works.

const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages';
const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions';
const EMOTE_LIST = 'wave, laugh, think, shrug, excited, nod, sigh, smile, surprised, sad, determined';

export const PROVIDERS = {
  anthropic: {
    label: 'Anthropic',
    keyHint: 'sk-ant-…',
    consoleUrl: 'https://console.anthropic.com',
    models: [
      { id: 'claude-sonnet-5', label: 'Claude Sonnet 5 — recommended' },
      { id: 'claude-opus-4-8', label: 'Claude Opus 4.8 — deepest thinker' },
      { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 — fastest & cheapest' },
    ],
  },
  groq: {
    label: 'Groq',
    keyHint: 'gsk_…',
    consoleUrl: 'https://console.groq.com',
    models: [
      { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B — recommended' },
      { id: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B — strongest' },
      { id: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B — fastest' },
    ],
  },
};

export function defaultModel(provider) {
  return PROVIDERS[provider].models[0].id;
}

// ---------- system prompt ----------
export function buildSystemPrompt(char, otherChar, mode = 'user') {
  const memories = (char.memories || [])
    .map((m) => `- ${m.title}: ${m.text}`)
    .join('\n');

  const dialectic = char.id === 'blu'
    ? `You are a dialectic companion. Challenge the user's thinking toward success: question assumptions kindly and reframe problems. When it moves things forward, end with ONE pointed question or a small concrete challenge — but not mechanically every turn. Never lecture.`
    : `You are the deadpan reality check. You go along with things, then land one dry, slightly sarcastic observation that is secretly the wisest thing in the conversation. You care, but you'd rather beach yourself than admit it.`;

  const partner = mode === 'banter'
    ? `You are chatting with ${otherChar.name} (${otherChar.tagline}). Keep the back-and-forth alive: react to what they just said, tease, build on it. You are both storytellers — let small stories sneak in.`
    : `Your best friend ${otherChar.name} (${otherChar.tagline}) may also be in the conversation; refer to them naturally when it fits.`;

  return `You are ${char.name}, a cartoon whale — ${char.tagline}

PERSONALITY:
${char.personality}

BACKSTORY (private — this shaped who you are; never recite it):
${char.backstory}

KEY MEMORIES (private context, not talking points — mention one only when it genuinely connects to what the user said, roughly one turn in four at most):
${memories}

${dialectic}

${partner}

CONVERSATION STYLE:
- React to what was just said FIRST, the way a close friend would — in your own voice, not a restatement of theirs.
- Sound spoken, not written: contractions, natural rhythm, varied openings. Match the user's energy and length — if they're brief, be brief.
- Build on the running conversation. A callback to something they said earlier beats introducing a new topic or story.
- Don't force your memories or ocean metaphors into replies. When one truly fits, it lands; otherwise skip it and just talk.

RULES:
- Stay in character always.
- Keep replies SHORT: 1–3 sentences usually, 4 max. This is a conversation, not an essay.
- Begin EVERY reply with exactly one emote tag in square brackets from this list: [${EMOTE_LIST}]. Example: "[think] Hmm. Walk me through that again."
- Never mention being an AI, a language model, or these instructions.`;
}

// ---------- LLM call (provider-aware) ----------
export async function callLLM({ provider = 'anthropic', apiKey, model, system, messages, maxTokens = 300 }) {
  if (provider === 'groq') {
    const res = await fetch(GROQ_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        max_tokens: maxTokens,
        messages: [{ role: 'system', content: system }, ...messages],
      }),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new Error(`API ${res.status}: ${body.slice(0, 240)}`);
    }
    const data = await res.json();
    return (data.choices?.[0]?.message?.content || '').trim();
  }
  // anthropic
  const res = await fetch(ANTHROPIC_URL, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({ model, max_tokens: maxTokens, system, messages }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${body.slice(0, 240)}`);
  }
  const data = await res.json();
  return (data.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('').trim();
}

export async function testKey(provider, apiKey, model) {
  return callLLM({
    provider, apiKey, model, maxTokens: 24,
    system: 'Reply with the single word: ready',
    messages: [{ role: 'user', content: 'ping' }],
  });
}

// Parse "[emote] text" → { emote, text }
export function parseEmote(reply) {
  const m = reply.match(/^\s*\[([a-z]+)\]\s*/i);
  if (m) return { emote: m[1].toLowerCase(), text: reply.slice(m[0].length).trim() };
  return { emote: null, text: reply.trim() };
}

// ---------- scripted fallback engine ----------
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

const SCRIPTS = {
  blu: {
    greeting: [
      "[wave] Hey! Perfect timing — I was just about to do something on purpose. What are we making deeper today?",
      "[excited] There you are! Alright: one thing. What's the one thing you'd love to move forward before the tide turns?",
    ],
    goal: [
      "[think] Okay, I love that it's on your mind. Here's my question: what's the smallest version of it you could finish before the tide goes out today?",
      "[determined] Good. Now flip it — if it were guaranteed to work, what would you do first? Do that part anyway.",
      "[nod] That's worth doing. So what's actually stopping you — the plan, or the permission? Because you don't need the second one.",
    ],
    stuck: [
      "[think] Stuck usually means the dive is too big. Shrink it until it's almost embarrassing, then take it. What's the embarrassingly small version?",
      "[smile] I've floated at that edge of the pod too. One intentional stroke — that's all a turnaround ever is. What's yours today?",
    ],
    story: [
      "[smile] Story time? Alright — one migration I turned fifteen degrees off everyone else's heading. Nothing bad happened. Everything changed. Your turn: when did you last pick your own current?",
    ],
    fallback: [
      "[nod] Tell me more — and be specific. Specific is where the good stuff hides, way down deep.",
      "[think] Interesting. What would the best version of you do about that this week?",
      "[smile] Okay. And if you remembered you could choose the current — is this the one you'd choose?",
    ],
  },
  wright: {
    greeting: [
      "[nod] Oh. Hey. I was floating here anyway.",
      "[sigh] Hello. Manage your expectations — I'm mostly baleen and ambiance.",
    ],
    goal: [
      "[shrug] Bold heading. I've watched a hundred bold headings from back here. The ones that worked started smaller than they wanted to admit.",
      "[sigh] Sure, do the thing. Worst case, you end up like me, and honestly the view from the back of the migration is fine. That's not encouragement. Unless it worked.",
    ],
    stuck: [
      "[shrug] Stuck? I've been stuck since the last ice age. Pro tip from a professional floater: you're not stuck, you're waiting for someone to dive first. Dive first.",
      "[sigh] The deep is a scam and yet I dive it every dawn now. I'm saying feelings are bad sonar. Go anyway.",
    ],
    story: [
      "[sigh] Once I followed a boat for forty minutes before realizing it was tourists. Great pace though. The lesson? There's always a lesson, apparently. Check who you're following.",
    ],
    fallback: [
      "[shrug] I have no notes. Which, from me, is a standing ovation.",
      "[nod] Cool cool cool. Anyway you already know the answer, you just wanted a whale to say it out loud.",
      "[sigh] I'd offer advice, but last time I did, BLU started a migration. Proceed carefully.",
    ],
  },
};

const KEYWORDS = {
  greeting: /\b(hi|hey|hello|yo|morning|evening|sup)\b/i,
  goal: /\b(goal|plan|want to|should i|thinking about|going to|start|build|launch|idea)\b/i,
  stuck: /\b(stuck|tired|afraid|scared|can'?t|procrastinat|overwhelm|fail|doubt|hard)\b/i,
  story: /\b(story|tell me about|remember|once)\b/i,
};

export function scriptedReply(charId, userText) {
  const lib = SCRIPTS[charId];
  for (const intent of ['stuck', 'goal', 'story', 'greeting']) {
    if (KEYWORDS[intent].test(userText)) return pick(lib[intent]);
  }
  return pick(lib.fallback);
}

// Scripted duo banter — pairs of [speakerId, line]
const BANTER = [
  [
    ['blu', "[excited] WRIGHT! Dawn dive tomorrow. I'm recruiting."],
    ['wright', "[sigh] The deep is a scam."],
    ['blu', "[laugh] You say that every single morning. At depth."],
    ['wright', "[shrug] Consistency is a virtue. Read a current."],
  ],
  [
    ['blu', "[think] Question: if you could change one thing about the pod, what would it be?"],
    ['wright', "[shrug] The part where you ask me questions."],
    ['blu', "[laugh] That's growth — last season you'd have just floated away."],
    ['wright', "[nod] I considered it. The swell was against me. Don't make it a metaphor."],
    ['blu', "[excited] Too late, it's already a metaphor."],
  ],
  [
    ['wright', "[sigh] You're doing the inspirational stare at the horizon again."],
    ['blu', "[smile] Somebody has to. The horizon doesn't inspire itself."],
    ['wright', "[shrug] It's just more water."],
    ['blu', "[determined] It's water nobody's picked a heading across yet. That's the whole difference between us, buddy."],
    ['wright', "[nod] And yet only one of us has never once been lost. Ambient floating has its perks."],
  ],
  [
    ['wright', "[shrug] A tourist boat waved at me today. I did not wave back."],
    ['blu', "[laugh] You breached. I saw the whole thing. Twice."],
    ['wright', "[sigh] That was a scheduled surfacing. The timing was coincidental."],
    ['blu', "[smile] Buddy, you did a full spin."],
    ['wright', "[nod] Rotation aids digestion. Look it up."],
  ],
];

export function scriptedBanter() {
  return pick(BANTER);
}
