(() => {
'use strict';
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

/* ---------- icons (the design's set, plus a cup for food and drink themes) ---------- */
const P = {
  sync:'<path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M3 21v-5h5"/>',
  battery:'<rect x="2" y="7" width="17" height="10" rx="2.5"/><path d="M22 11v2"/><path d="M11.5 9 9 12h4l-2.5 3"/>',
  login:'<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>',
  moon:'<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  tag:'<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  bell:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  brain:'<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a3 3 0 0 0-3-1z"/><path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
  spark:'<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
  play:'<path d="M7 4.5v15l12-7.5z"/>',
  pause:'<rect x="6" y="4.5" width="4" height="15" rx="1.2"/><rect x="14" y="4.5" width="4" height="15" rx="1.2"/>',
  arrow:'<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  up:'<path d="M12 19V5"/><path d="m6 11 6-6 6 6"/>',
  down:'<path d="M12 5v14"/><path d="m6 13 6 6 6-6"/>',
  check:'<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  inbox:'<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
  filter:'<path d="M3 5h18l-7 8v6l-4 1v-7z"/>',
  cluster:'<circle cx="7" cy="8" r="3"/><circle cx="17" cy="7" r="2.5"/><circle cx="12" cy="17" r="3.5"/>',
  gauge:'<path d="M4 18a8 8 0 1 1 16 0"/><path d="m12 18 4-6"/>',
  text:'<path d="M4 6h16M4 11h16M4 16h10"/>',
  store:'<path d="M5 8h14l-1 12H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  gplay:'<path d="M6 3.5v17l14-8.5z"/>',
  ticket:'<path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4z"/>',
  bubble:'<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
  at:'<circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 5 0v-1a9 9 0 1 0-4 7.5"/>',
  alert:'<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  cup:'<path d="M4 8h13v5a6 6 0 0 1-6 6h-1a6 6 0 0 1-6-6z"/><path d="M17 10h1.5a2.5 2.5 0 0 1 0 5H17"/><path d="M8 3v2M12 3v2"/>'
};
const FILLED = ['play','pause'];
const ic = n => `<svg viewBox="0 0 24 24" fill="${FILLED.includes(n)?'currentColor':'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]||''}</svg>`;
document.querySelectorAll('[data-ic]').forEach(el => el.innerHTML = ic(el.dataset.ic));

/* ---------- small helpers ---------- */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => Number(n).toLocaleString('en-US');
const sgn = n => n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : '0';
const plural = (n, w, ws) => `${fmt(n)} ${n === 1 ? w : (ws || w + 's')}`;
const slug = s => String(s ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
// SHA-1 hex of a string's UTF-8 bytes (synchronous: crypto.subtle is async and missing on plain http)
function sha1(str){
  const b = [...new TextEncoder().encode(str)], n = b.length;
  b.push(0x80); while (b.length % 64 !== 56) b.push(0);
  const bits = n * 8; for (let i = 7; i >= 0; i--) b.push(i > 3 ? 0 : (bits >>> (i * 8)) & 255);
  let h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0];
  const w = new Array(80), rotl = (x, k) => (x << k) | (x >>> (32 - k));
  for (let o = 0; o < b.length; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = (b[o+4*i] << 24) | (b[o+4*i+1] << 16) | (b[o+4*i+2] << 8) | b[o+4*i+3];
    for (let i = 16; i < 80; i++) w[i] = rotl(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
    let [a, bb, c, d, e] = h;
    for (let i = 0; i < 80; i++) {
      const [f, k] = i < 20 ? [(bb & c) | (~bb & d), 0x5A827999] : i < 40 ? [bb ^ c ^ d, 0x6ED9EBA1] : i < 60 ? [(bb & c) | (bb & d) | (c & d), 0x8F1BBCDC] : [bb ^ c ^ d, 0xCA62C1D6];
      const t = (rotl(a, 5) + f + e + k + w[i]) | 0;
      e = d; d = c; c = rotl(bb, 30); bb = a; a = t;
    }
    h = [h[0]+a, h[1]+bb, h[2]+c, h[3]+d, h[4]+e].map(x => x | 0);
  }
  return h.map(x => (x >>> 0).toString(16).padStart(8, '0')).join('');
}
// memory.business_tag() without the "business:" prefix: a-z0-9 slug, plus a hash of the
// full name when it has any non-ASCII letters, so names in other scripts don't collide
const bizSlug = s => {
  s = String(s ?? ''); const sl = slug(s);
  if (sl && /^[\x00-\x7f]*$/.test(s)) return sl;
  const digest = sha1(s.trim().toLowerCase()).slice(0, 10);
  return sl ? `${sl}-${digest}` : digest;
};
const trunc = (s, n) => s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s;
const sentences = s => (String(s || '').match(/[^.!?]+(?:[.!?]+["”’)]*|$)/g) || []).map(x => x.trim()).filter(Boolean);
const firstSentence = (s, n = 150) => trunc(sentences(s)[0] || String(s || ''), n);
const fmtDay = ts => new Date(ts).toLocaleDateString('en-US', {month:'short', day:'numeric'});
const fmtWhen = ts => new Date(ts).toLocaleString('en-US', {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'});
const PERIOD_RE = /^(\d{4})-(\d{2})-(\d{2}) to (\d{4})-(\d{2})-(\d{2})$/;
function periodDates(p){
  const m = PERIOD_RE.exec(p || '');
  return m ? [new Date(+m[1], m[2]-1, +m[3]), new Date(+m[4], m[5]-1, +m[6])] : null;
}
function fmtPeriod(p){
  const d = periodDates(p);
  if (!d) return p || 'period unknown';
  const o = {month:'short', day:'numeric'}, y = d[1].getFullYear();
  return `${d[0].toLocaleDateString('en-US', o)} – ${d[1].toLocaleDateString('en-US', o)}${y !== new Date().getFullYear() ? ', ' + y : ''}`;
}
const periodDays = p => { const d = periodDates(p); return d ? Math.round((d[1] - d[0]) / 864e5) + 1 : null; };

/* the design's motion helpers, unchanged */
const wait = ms => new Promise(r => setTimeout(r, reduce ? 0 : ms));
function typeInto(el, text, speed = 12){
  el._tok = (el._tok||0) + 1; const tok = el._tok;
  if (reduce) { el.textContent = text; el.classList.remove('typing'); return Promise.resolve(); }
  el.textContent = ''; el.classList.add('typing');
  const chunk = Math.max(1, Math.round(text.length/180));
  return new Promise(res => {
    let i = 0;
    const step = () => {
      if (el._tok !== tok) return res();
      i = Math.min(text.length, i + chunk); el.textContent = text.slice(0, i);
      if (i < text.length) setTimeout(step, speed); else { el.classList.remove('typing'); res(); }
    };
    step();
  });
}
function setText(el, text){ el._tok = (el._tok||0) + 1; el.classList.remove('typing'); el.textContent = text; }
function countUp(el, to, dur = 600, f = fmt){
  if (reduce) { el.textContent = f(to); el._v = to; return; }
  const from = el._v ?? to, t0 = performance.now(); el._v = to;
  const step = now => { const k = Math.min(1,(now-t0)/dur), e = 1-Math.pow(1-k,3); el.textContent = f(Math.round(from + (to-from)*e)); if (k<1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
let toastT;
function toast(msg){ $('#toastText').textContent = msg; $('#toast').classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => $('#toast').classList.remove('show'), 4200); }

/* ---------- storage: runs this browser has seen, per business ---------- */
const LS = {
  get(k, d){ try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch { return false; } }
};
const HKEY = 'fa.history.v1', LKEY = 'fa.last.v1', AKEY = 'fa.api.v1';
const MAX_BIZ = 12, MAX_RUNS = 12;
let HISTORY = LS.get(HKEY, {});
if (!HISTORY || typeof HISTORY !== 'object' || Array.isArray(HISTORY)) HISTORY = {};
function saveHistory(){
  // oldest businesses go first if the browser runs out of room
  for (let k = 0; k < MAX_BIZ && !LS.set(HKEY, HISTORY); k++) {
    const oldest = Object.values(HISTORY).sort((a,b) => (a.at||0) - (b.at||0))[0];
    if (!oldest || oldest.key === state.key) break;
    delete HISTORY[oldest.key];
  }
}

/* ---------- backend contract ---------- */
// themes[].degraded marks a placeholder 0 (Groq unavailable or an unusable reply);
// the text check covers servers from before that flag existed
const FALLBACK_RE = /LLM unavailable|Could not parse structured output/i;
// defaults for servers from before /health reported them; checkHealth() replaces both
let BANK = 'feedback-analyser-v2'; // memory.py default; HINDSIGHT_BANK_ID overrides it on the server
const REASONS = {
  too_short:       {n:'Too short',       d:'under 4 words',               c:'var(--sky)'},
  duplicate:       {n:'Duplicate',       d:'the same text twice',         c:'var(--teal)'},
  repeated_phrase: {n:'Repeated phrase', d:'one word is half the review', c:'var(--orange)'},
  gibberish:       {n:'Gibberish',       d:'too few vowels to be words',  c:'var(--blue)'},
  empty:           {n:'Empty',           d:'no text left after cleaning', c:'var(--teal-soft)'}
};
let SAMPLE_SIZE = 50; // scorer.py: themes[].count is counted within a random sample of this many
const reasonOf = r => REASONS[r] || {n:String(r).replace(/_/g, ' '), d:'filtered by the Checker', c:'var(--ink-3)'};

function normResult(res){
  const seen = {};
  const themes = (Array.isArray(res?.themes) ? res.themes : []).map(t => {
    let id = slug(t?.name) || 'theme';
    seen[id] = (seen[id] || 0) + 1; if (seen[id] > 1) id += '-' + seen[id];
    const reasoning = String(t?.reasoning ?? ''), next = String(t?.next_step ?? '');
    const raw = Math.round(Number(t?.score));
    return {
      id, name: String(t?.name ?? 'Untitled theme'),
      count: Math.max(0, parseInt(t?.count, 10) || 0),
      score: Number.isFinite(raw) ? Math.max(-5, Math.min(5, raw)) : 0,
      samples: (Array.isArray(t?.samples) ? t.samples : []).map(String).filter(s => s.trim()),
      reasoning, next_step: next, vs: String(t?.vs_competitors ?? '').trim(),
      fallback: t?.degraded === true || FALLBACK_RE.test(reasoning + ' ' + next)
    };
  }).sort((a,b) => a.score - b.score || b.count - a.count);  // README: sort ascending, worst first
  const by = res?.rejected_by_reason && typeof res.rejected_by_reason === 'object' ? res.rejected_by_reason : {};
  return {
    business: String(res?.business ?? ''), location: String(res?.location ?? ''), period: String(res?.period ?? ''),
    rejected_count: parseInt(res?.rejected_count, 10) || 0, rejected_by_reason: by, themes,
    gathered: res?.reviews_gathered != null && Number.isFinite(+res.reviews_gathered) ? +res.reviews_gathered : null,
    verified: res?.reviews_verified != null && Number.isFinite(+res.reviews_verified) ? +res.reviews_verified : null,
    warnings: (Array.isArray(res?.warnings) ? res.warnings : []).map(String).filter(Boolean),
    market: normMarket(res?.market)
  };
}
// result.market: null when competitors weren't scanned
function normMarket(m){
  if (!m || typeof m !== 'object') return null;
  const pts = a => (Array.isArray(a) ? a : []).map(p => typeof p === 'string' ? {point:p, evidence:''} : {point:String(p?.point ?? ''), evidence:String(p?.evidence ?? '')}).filter(p => p.point.trim());
  const num = v => v != null && Number.isFinite(+v) ? +v : null;
  return {discovered: m.discovered === true, competitors: (Array.isArray(m.competitors) ? m.competitors : []).map(c => ({
    name: String(c?.name ?? 'Unnamed competitor'), address: String(c?.address ?? ''), rating: num(c?.rating),
    review_count: num(c?.review_count), reviews_used: num(c?.reviews_used),
    strengths: pts(c?.strengths), weaknesses: pts(c?.weaknesses), degraded: c?.degraded === true
  }))};
}
const sampleOf = R => R.verified == null ? null : Math.min(SAMPLE_SIZE, R.verified);
const bizLabel = R => R.location ? `${R.business}, ${R.location}` : R.business;
const tagOf = R => `business:${bizSlug(bizLabel(R))}`;  // memory.business_tag()
const runLabel = rec => rec ? `${rec.mode === 'week' ? 'Week' : 'Run'} ${rec.run}${rec.mode !== 'week' && state.runs.some(r => r.at !== rec.at && r.run === rec.run) ? ` (${fmtDay(rec.at)})` : ''}` : '';
const realThemes = R => R.themes.filter(t => !t.fallback);
const worstOf = R => realThemes(R).find(t => t.score < 0) || null;
const bestOf = R => [...realThemes(R)].reverse().find(t => t.score > 0) || null;

/* ---------- colour carries meaning (from the design): orange act now, green good, sky watch, teal steady ---------- */
const SIG = {
  alert:{c:'var(--orange)', soft:'var(--orange-soft)', txt:'txt-alert'},
  good:{c:'var(--green)', soft:'var(--green-soft)', txt:'txt-good'},
  watch:{c:'var(--sky)', soft:'var(--sky-soft)', txt:'txt-watch'},
  steady:{c:'var(--teal-soft)', soft:'var(--teal-soft)', txt:'txt-steady'}
};
const sigKey = t => t.fallback ? 'steady' : t.score <= -3 ? 'alert' : t.score < 0 ? 'watch' : t.score === 0 ? 'steady' : 'good';
const sig = t => SIG[sigKey(t)];
const ICON_RULES = [
  [/pric|cost|expens|value|charg|bill|fee|afford|renew|refund|money|overhyp|hype/i, 'tag'],
  [/login|log in|sign.?in|signed|account|password|auth/i, 'login'],
  [/battery|drain/i, 'battery'],
  [/wait|queue|slow|delay|late|speed|time/i, 'clock'],
  [/sync|network|internet|signal|outage|coverage|wi-?fi|connect|card|terminal|payment/i, 'sync'],
  [/staff|service|rude|friendl|barista|waiter|support|manager|team|people|behaviou?r/i, 'bubble'],
  [/tea|coffee|chai|espresso|brew|food|taste|flavou?r|dish|menu|drink|pastr|bun|maska|meal|breakfast|lunch|dinner|quality/i, 'cup'],
  [/crowd|space|seat|clean|ambien|atmos|decor|music|noise|park|locat|store|shop|place|room/i, 'store'],
  [/dark mode|contrast|night/i, 'moon'],
  [/notif|remind/i, 'bell']
];
const themeIcon = t => (ICON_RULES.find(([re]) => re.test(t.name)) || [])[1] || (t.score < 0 ? 'alert' : t.score > 0 ? 'check' : 'text');

/* ---------- matching a theme across runs (names get reworded between runs) ---------- */
const STOP = new Set('a an and are as at be by for from has have in is it its of on or the to too very was were with not no our your their this that than but so all any more most less much many really quite just'.split(' '));
const SYN = [['pric','pric'],['overpric','pric'],['expens','pric'],['pricey','pric'],['costl','pric'],['cost','pric'],['afford','pric'],['queu','wait'],['delay','wait'],['slow','wait'],['cramp','crowd'],['busy','crowd'],['friend','staff'],['barist','staff'],['servic','staff'],['employe','staff'],['rude','staff'],['dirt','clean'],['hygien','clean']];
function stem(w){
  if (w.length > 5) w = w.replace(/(ingly|ing|edly|ed|ness|ies|es|ly|s)$/, '');
  if (w.length > 4) w = w.replace(/[ey]$/, '');
  const hit = SYN.find(([k]) => w.startsWith(k));
  return hit ? hit[1] : w;
}
const TOK = new Map();
function tokens(s){
  s = String(s);
  let v = TOK.get(s);
  if (!v) {
    v = new Set(s.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 1 && !STOP.has(w)).map(stem).filter(w => w.length > 2));
    if (TOK.size > 2000) TOK.clear();
    TOK.set(s, v);
  }
  return v;
}
function similarity(a, b){
  const A = tokens(a.name), B = tokens(b.name);
  let inter = 0; A.forEach(w => { if (B.has(w)) inter++; });
  if (!inter) return 0;
  let s = inter / (A.size + B.size - inter);
  if (a.score * b.score < 0) s *= .5;  // "tea praised" and "tea criticised" are different themes
  return s;
}
function matchIn(t, rec){
  if (!rec) return null;
  let best = null;
  rec.r.themes.forEach(u => { const s = similarity(t, u); if (s >= .34 && (!best || s > best.sim)) best = {t:u, sim:s}; });
  return best;
}
// sentences where the Analyst cites an earlier run it recalled from Hindsight
const CITE_RE = /\b(previous|prior|earlier|last|past)\s+(runs?|periods?|months?|analys[ie]s|time|weeks?)\b|\bruns?\s*\d+\b|\b(up|down|rose|fell|grew|dropped|increased|decreased) from\b|\bcompared (to|with)\b/i;
const cites = t => sentences(t.reasoning).filter(s => CITE_RE.test(s));

/* ---------- state ---------- */
const state = { key:null, runs:[], idx:-1, theme:null, example:false, running:false, stream:true, playing:false, mode:'shop', provider:'serpapi' };
const cur = () => state.runs[state.idx] || null;
const prevRec = () => state.idx > 0 ? state.runs[state.idx - 1] : null;
const byRun = (a, b) => a.run - b.run || (a.at||0) - (b.at||0);
const hydrate = runs => runs.map(r => ({...r, r: normResult(r.res)})).sort(byRun);

/* ---------- API ---------- */
// ?api= used to be saved for good, so one crafted link rerouted every later analysis
try { localStorage.removeItem(AKEY); } catch {}
const qsApi = (() => {
  const raw = new URLSearchParams(location.search).get('api'); if (!raw) return null;
  let u; try { u = new URL(raw); } catch { return null; }
  if (!/^https?:$/.test(u.protocol)) return null;
  const local = u.origin === location.origin || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(u.hostname);
  return local || confirm(`This link asks the dashboard to send analyses to ${u.origin}. Only allow it if you trust that server.`) ? u.origin + u.pathname : null;
})();
const API_CANDIDATES = [...new Set([qsApi, /^https?:$/.test(location.protocol) ? location.origin : null, 'http://localhost:8000'].filter(Boolean).map(s => s.replace(/\/+$/, '')))];
let API = API_CANDIDATES[0], apiUp = null, healthT;
async function checkHealth(quiet){
  const chip = $('#apiChip');
  if (!quiet) { chip.className = 'apichip well wait'; $('#apiText').textContent = 'checking API'; }
  for (const base of API_CANDIDATES) {
    try {
      const r = await fetch(base + '/health', {signal: AbortSignal.timeout(4000)});
      const j = r.ok ? await r.json() : null;
      if (j && j.status === 'ok') { API = base; apiUp = true; useServerInfo(j); break; }
    } catch {}
    apiUp = false;
  }
  chip.className = `apichip well ${apiUp ? 'ok' : 'down'}`;
  $('#apiText').textContent = apiUp ? 'API online' : 'API offline';
  chip.title = apiUp ? `Connected to ${API}` : `No API answered at ${API_CANDIDATES.join(' or ')}. See “Run it” below.`;
  $('#docsLink').href = API + '/docs';
  $('#demoKicker').textContent = apiUp ? `Workspace · connected to ${API.replace(/^https?:\/\//, '')}` : 'Workspace · API offline, start it to run analyses';
  clearTimeout(healthT);
  healthT = setTimeout(() => checkHealth(true), apiUp ? 60000 : 20000);
  return apiUp;
}
function useServerInfo(j){
  const bank = typeof j.bank_id === 'string' && j.bank_id ? j.bank_id : BANK;
  const size = Number.isInteger(j.sample_size) && j.sample_size > 0 ? j.sample_size : SAMPLE_SIZE;
  if (bank === BANK && size === SAMPLE_SIZE) return;
  BANK = bank; SAMPLE_SIZE = size;
  if (state.runs.length && !state.running) renderAll();
}
async function call(path, body){
  const ctl = new AbortController(), to = setTimeout(() => ctl.abort(), 300000); // README: allow well over 180 s
  let r;
  try {
    r = await fetch(API + path, {method:'POST', headers:{'Content-Type':'application/json'}, body: body ? JSON.stringify(body) : undefined, signal: ctl.signal});
  } catch (e) {
    throw {status:0, aborted: e.name === 'AbortError'};
  } finally { clearTimeout(to); }
  let data = null; try { data = await r.json(); } catch {}
  if (r.ok && data) return data;
  throw {status: r.status, detail: data?.detail};
}
function explainError(e, req){
  const d = typeof e.detail === 'string' ? e.detail : '';
  if (e.status === 0 && e.aborted) return ['The run took longer than 5 minutes, so the page stopped waiting.', 'The server may still finish it. Run again later to fetch a fresh result.'];
  if (e.status === 0) return [`Can't reach the API at ${API}.`, 'Start it with docker compose up, or uvicorn api:app --port 8000 from backend/.'];
  if (e.status === 404) return req.mode === 'week' ? [`No gathered reviews for that week.`, d] : [`Couldn't find reviews for that business. Try adding the city.`, d];
  if (e.status === 422) return ['The API rejected the request.', Array.isArray(e.detail) && e.detail[0]?.msg ? e.detail[0].msg : d];
  if (e.status === 502) return ["Couldn't analyse right now. Try again shortly.", d];
  if (e.status === 503) return ["The server is missing an API key, so it can't run analyses yet.", d || 'Add the key to .env and restart the API.'];
  if (e.status === 500) return ['The server hit a bug while analysing.', d || 'The server log has the details.'];
  return [`The API answered with status ${e.status}.`, d];
}

/* ---------- example data: a fictional café, in the exact shape POST /shops/analyse returns ---------- */
const EX_REQ = {name:'Tempo Café', location:'Example City', months:3, limit:200, provider:'serpapi', store:true};
const EXAMPLE = [
  {mode:'shop', run:1, at: Date.UTC(2026, 8, 1, 9, 12), ms:71000, stored:true, request:{...EX_REQ, run_number:1}, res:{
    week:1, business:'Tempo Café', location:'Example City', period:'2026-06-02 to 2026-08-30', rejected_count:9, rejected_by_reason:{too_short:7, duplicate:2},
    themes:[
      {name:'Espresso and cold brew quality', count:14, score:5, samples:['The cold brew here is the best in the neighbourhood, smooth and never bitter.','Espresso is pulled properly every time. I come back for it daily.'],
        reasoning:'All 14 mentions praise the coffee itself, and it is the reason most reviewers give for coming back. Nothing else in this period is praised as often or as strongly.',
        next_step:'Keep the current beans, grind and recipes exactly as they are, and train new staff on the same espresso routine.'},
      {name:'Friendly, quick baristas', count:9, score:3, samples:['Staff remember my order and are always cheerful.','Baristas are fast even when it is busy.'],
        reasoning:'Nine reviewers single out the staff as friendly and quick. A real strength, though it is mentioned less often than the coffee.',
        next_step:'Keep the current team structure on busy shifts and recognise the staff reviewers mention by name.'},
      {name:'Long weekend queues', count:11, score:-4, samples:['Waited 25 minutes for a latte on Saturday morning.','The weekend line goes out the door and moves slowly.'],
        reasoning:'Eleven reviewers complain about waits of 15 to 25 minutes on Saturday and Sunday mornings. It is the most frequent complaint and it drives people away at peak time.',
        next_step:'Add a second barista on weekend mornings from 8 to 11 and open a separate pickup point for pre-orders.'},
      {name:'Pricey pastries', count:8, score:-3, samples:['Six dollars for a small croissant is a lot.','Coffee is fairly priced but the pastries are overpriced.'],
        reasoning:'Eight mentions say the pastries cost too much for their size, while the coffee price itself is rarely criticised.',
        next_step:'Introduce a coffee-and-pastry combo at a lower combined price and check whether pastry complaints fall.'},
      {name:'Cramped seating', count:6, score:-2, samples:['Hard to find a seat, the tables are very close together.','Nice place but there is barely room to sit with a laptop.'],
        reasoning:'Six reviewers mention crowded seating. A real complaint, but lower priority than wait times and pricing.',
        next_step:'Rearrange the back room to add two more small tables.'}
    ]}},
  {mode:'shop', run:2, at: Date.UTC(2026, 8, 29, 8, 40), ms:84000, stored:true, request:{...EX_REQ, run_number:2, compare:true}, res:{
    week:2, business:'Tempo Café', location:'Example City', period:'2026-07-01 to 2026-09-28', rejected_count:11, rejected_by_reason:{too_short:8, duplicate:2, gibberish:1},
    themes:[
      {name:'Card machine outages at checkout', count:5, score:-5, samples:['Card reader was down again, had to walk to an ATM.','Could not pay by card twice this month. Cash only sign taped to the till.'],
        reasoning:'Five reviewers in this period could not pay by card, and nothing like it was recorded before, so it is new. Customers who cannot pay leave without buying, which makes this the single most urgent problem.',
        next_step:'Replace or service the card terminal this week and keep a backup mobile reader behind the counter.', vs_competitors:'Grind House reviewers specifically praise contactless payment that always works, so customers who hit the outage have an easy alternative nearby.'},
      {name:'Pastry prices', count:10, score:-4, samples:['Pastries keep getting more expensive.','Love the coffee, but $6.50 for a muffin is too much.'],
        reasoning:'Pricing complaints rose from 8 mentions in the previous run to 10, and reviewers now quote specific prices. The trend is getting worse, not better.',
        next_step:'Launch the coffee-and-pastry combo now and review pastry portion sizes against the price.', vs_competitors:'Crumb & Co. is praised for a five-dollar coffee-and-croissant combo, which makes Tempo\'s pastry prices stand out more.'},
      {name:'Weekend queue times', count:7, score:-3, samples:['The weekend wait is better than before but still 10+ minutes.','Saturday line moved faster with the extra barista.'],
        reasoning:'Down from 11 mentions in the previous run to 7, and several reviewers say the weekend wait has improved. Still a real problem, but less urgent than before.',
        next_step:'Keep the second weekend barista and add the pre-order pickup point to cut waits further.', vs_competitors:'Grind House is praised for fast weekend service, while Crumb & Co. has the same peak-time complaint.'},
      {name:'Cramped seating', count:6, score:-2, samples:['Tables are squeezed together, hard to have a conversation.','Always a struggle to find a seat after 10am.'],
        reasoning:'Six mentions, the same as the previous run. A steady, lower-priority complaint.',
        next_step:'Go ahead with rearranging the back room to add more small tables.'},
      {name:'Friendly baristas', count:10, score:3, samples:['The staff are lovely and always remember names.','Friendly team, quick service even on weekends.'],
        reasoning:'Ten reviewers praise the staff, up from 9 in the previous run. A consistent strength.',
        next_step:'Protect this by keeping experienced baristas on the busiest shifts.'},
      {name:'Espresso and cold brew quality', count:16, score:5, samples:['Still the best cold brew in town.','Consistently great espresso, never had a bad shot here.'],
        reasoning:'Sixteen mentions praise the coffee, up from 14 in the previous run, and it is still the most praised thing about the café by a wide margin.',
        next_step:'Keep the beans, recipes and espresso training unchanged.', vs_competitors:'Neither competitor is praised for its coffee the way Tempo is, so this is what sets the café apart locally.'}
    ],
    market:{discovered:true, competitors:[
      {name:'Grind House', address:'14 Mill Road, Example City', rating:4.4, review_count:612, reviews_used:57, degraded:false,
        strengths:[{point:'Fast weekend service', evidence:'In and out in five minutes even on Saturday.'}, {point:'Contactless payment always works', evidence:'Tap to pay, never had an issue.'}],
        weaknesses:[{point:'Burnt-tasting espresso', evidence:'Coffee tastes bitter and burnt.'}, {point:'Noisy and cramped', evidence:'Too loud to work here.'}]},
      {name:'Crumb & Co.', address:'2 Station Square, Example City', rating:4.2, review_count:388, reviews_used:52, degraded:false,
        strengths:[{point:'Cheap pastry combos', evidence:'Coffee and a croissant for five dollars.'}, {point:'Plenty of seating', evidence:'Always a table free.'}],
        weaknesses:[{point:'Watery cold brew', evidence:'Cold brew was weak and watery.'}, {point:'Slow at peak times', evidence:'Waited 20 minutes on a Sunday.'}]}
    ]}}}
];

/* ---------- charts (the design's chart, with runs on the x axis and the score in the pill) ---------- */
function niceMax(v){ const p = Math.pow(10, Math.floor(Math.log10(v))), n = v/p; return [1.5,2,2.5,3,4,5,6,8,10].find(x => n <= x)*p; }
function runsChart(series, sel, color, label){
  const n = series.length, W=640, H=270, L=40, R=12, T=40, B=30, pw=W-L-R, ph=H-T-B, step=pw/Math.max(n,1), bw=Math.min(step*.6, 72);
  const mx = niceMax(Math.max(4, ...series.map(p => p.v || 0))), y = v => T + ph - (v/mx)*ph;
  const every = Math.max(1, Math.ceil(n/7));
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}" style="--hue:${color}">`;
  [0, mx/2, mx].forEach(g => { s += `<line class="grid" x1="${L}" x2="${W-R}" y1="${y(g)}" y2="${y(g)}"/><text class="axis" x="${L-8}" y="${y(g)+4}" text-anchor="end">${g}</text>`; });
  series.forEach((p,i) => {
    const x0 = L + step*i + (step-bw)/2, cx = x0 + bw/2;
    if (p.v == null) {
      s += `<text class="future-label" x="${cx.toFixed(1)}" y="${T+ph-10}" text-anchor="middle">no match</text>`;
    } else {
      const h = Math.max(4, ph*p.v/mx), yy = T + ph - h, cls = i > sel ? 'bar future' : i === sel ? 'bar sel' : 'bar';
      s += `<rect class="${cls}" x="${x0.toFixed(1)}" y="${yy.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="${Math.min(8,bw/2).toFixed(1)}"><title>${esc(p.label)}: ${p.v} mentions, score ${sgn(p.score)}</title></rect>`;
      if (i <= sel && h > 14) s += `<rect class="shine" x="${(x0+4).toFixed(1)}" y="${(yy+4).toFixed(1)}" width="${(bw*.26).toFixed(1)}" height="${Math.min(h-8,34).toFixed(1)}" rx="4" pointer-events="none"/>`;
      if (i <= sel && (i === sel || n <= 8)) s += `<text class="val" x="${cx.toFixed(1)}" y="${(yy-8).toFixed(1)}" text-anchor="middle">${p.v}</text>`;
      s += `<rect class="relpill" x="${(cx-22).toFixed(1)}" y="6" width="44" height="20" rx="7" opacity="${i <= sel ? 1 : .45}"/><text class="reltext" x="${cx.toFixed(1)}" y="20" text-anchor="middle">${sgn(p.score)}</text>`;
    }
    if (i === sel || i % every === 0) s += `<text class="axis${i===sel?' cur':''}" x="${cx.toFixed(1)}" y="${H-8}" text-anchor="middle">${esc(p.label)}</text>`;
  });
  return s + '</svg>';
}
// every theme on one −5..+5 axis, worst at the top; rows jump to the theme
function scoreChart(themes, selId, demo){
  const W=640, rowH=34, T=34, B=12, L=222, R=24, n=themes.length, H=T+B+n*rowH;
  const mid = L + (W-L-R)/2, unit = (W-L-R)/2/5;
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${demo ? 'The −5 to +5 scale' : 'Score of each theme, from −5 to +5'}">`;
  [-5, 0, 5].forEach(v => {
    const x = mid + v*unit;
    s += `<line class="${v ? 'grid' : 'zero'}" x1="${x}" x2="${x}" y1="${T-6}" y2="${H-B}"/><text class="axis" x="${x}" y="${T-14}" text-anchor="middle">${v === -5 ? '−5 fix' : v === 5 ? '+5 protect' : '0'}</text>`;
  });
  themes.forEach((t,i) => {
    const yc = T + i*rowH + rowH/2, g = demo ? SIG[t.sig] : sig(t), w = Math.max(3, Math.abs(t.score)*unit), x = t.score < 0 ? mid - w : mid, sel = t.id && t.id === selId;
    s += `<g${demo ? '' : ` data-go="${esc(t.id)}"`} style="--hue:${g.c}"><rect class="hit" x="0" y="${yc - rowH/2}" width="${W}" height="${rowH}"/>`
      + `<title>${esc(t.name)}: ${sgn(t.score)}${t.count != null ? `, ${t.count} mentions` : ''}${t.fallback ? ' (not a real score: Groq was unavailable)' : ''}</title>`
      + `<text class="name${sel ? ' cur' : ''}" x="${L-14}" y="${yc+4}" text-anchor="end">${esc(trunc(t.name + (t.fallback ? ' ⚠' : ''), 31))}</text>`
      + `<rect class="bar${sel ? ' sel' : ''}" x="${x.toFixed(1)}" y="${yc-10}" width="${w.toFixed(1)}" height="20" rx="7"/>`
      + (w > 30 ? `<rect class="shine" x="${(x+5).toFixed(1)}" y="${yc-6}" width="${Math.min(w*.3, 40).toFixed(1)}" height="5" rx="2.5" pointer-events="none"/>` : '')
      + `<text class="val" x="${t.score < 0 ? mid + 8 : mid - 8}" y="${yc+4}" text-anchor="${t.score < 0 ? 'start' : 'end'}">${sgn(t.score)}</text></g>`;
  });
  return s + '</svg>';
}
function miniBars(values, on, color){
  const n = Math.max(values.length, 1), W=300, H=46, step=W/n, bw=Math.min(step*.62, 26), mx=Math.max(1, ...values);
  return `<svg class="minibars" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true" style="--c:${color}">` + values.map((v,i) => {
    const h = Math.max(3, (H-2)*v/mx);
    return `<rect class="${on[i]?'on':''}" x="${(i*step+(step-bw)/2).toFixed(1)}" y="${(H-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="3"/>`;
  }).join('') + '</svg>';
}
function meter(score, color){
  const W=170, H=16, mid=W/2, unit=(W/2-4)/5, w=Math.max(3, Math.abs(score)*unit), x = score < 0 ? mid - w : mid;
  return `<svg class="meter" viewBox="0 0 ${W} ${H}" aria-hidden="true" style="--c:${color}"><rect class="trk" x="2" y="5" width="${W-4}" height="6" rx="3"/><rect class="fillr" x="${x.toFixed(1)}" y="3" width="${w.toFixed(1)}" height="10" rx="5"/><line class="mid" x1="${mid}" x2="${mid}" y1="0" y2="${H}"/></svg>`;
}
function ring(score){
  const r = 34, C = 2*Math.PI*r;
  return `<svg viewBox="0 0 84 84" aria-hidden="true"><circle class="bg" cx="42" cy="42" r="${r}"/><circle class="fg" cx="42" cy="42" r="${r}" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${(C*(1-Math.abs(score)/5)).toFixed(1)}"/></svg><div><b>${sgn(score)}</b><small>score</small></div>`;
}
// one theme followed through every run, matched by name
function seriesFor(t){
  const rec = cur();
  return state.runs.map(r => {
    const u = r === rec ? t : matchIn(t, r)?.t;
    return {label: runLabel(r), v: u ? u.count : null, score: u ? u.score : null};
  });
}

/* ---------- hero ---------- */
function mcard(o){
  return `<span class="mc-top"><span class="blob" style="--c:${o.soft}">${ic(o.icon)}</span><span><b>${esc(o.title)}</b><small>${esc(o.sub)}</small></span></span>`
    + (o.row ? `<span class="mc-row"><span class="mc-num ${o.cls}">${esc(o.num)}</span><span class="mc-cap">${esc(o.cap)}</span></span>`
             : `<span class="mc-num ${o.cls}">${esc(o.num)}</span><span class="mc-cap">${esc(o.cap)}</span>`)
    + (o.bars || '');
}
function aim(el, go, scroll){ if (go) { el.dataset.go = go; delete el.dataset.scroll; } else { delete el.dataset.go; el.dataset.scroll = scroll; } }
function renderHero(){
  const rec = cur(), R = rec?.r, worst = R && worstOf(R), best = R && bestOf(R);
  const counts = R ? R.themes.map(t => t.count) : [];
  const fix = $('#mFix'), keep = $('#mKeep'), filt = $('#mFilt');
  aim(fix, worst?.id, 'demo');
  fix.innerHTML = worst
    ? mcard({row:1, icon:themeIcon(worst), soft:sig(worst).soft, title:worst.name, sub:`fix first · ${plural(worst.count, 'mention')}`, num:sgn(worst.score), cls:sig(worst).txt, cap:firstSentence(worst.next_step, 120), bars: miniBars(counts, R.themes.map(t => t.score < 0 && !t.fallback), 'var(--orange)')})
    : mcard({row:1, icon:'alert', soft:'var(--orange-soft)', title:'Fix first', sub:'the most urgent theme', num:'−5', cls:'txt-alert', cap: R ? 'Nothing scored below zero in this run.' : 'The single most urgent problem gets −5. Run an analysis to see yours.'});
  aim(keep, best?.id, 'demo');
  keep.innerHTML = best
    ? mcard({row:1, icon:themeIcon(best), soft:'var(--green-soft)', title:best.name, sub:`protect · ${plural(best.count, 'mention')}`, num:sgn(best.score), cls:'txt-good', cap:firstSentence(best.next_step, 120), bars: miniBars(counts, R.themes.map(t => t.score > 0 && !t.fallback), 'var(--green)')})
    : mcard({row:1, icon:'check', soft:'var(--green-soft)', title:'Protect', sub:'the biggest strength', num:'+5', cls:'txt-good', cap: R ? 'Nothing scored above zero in this run.' : 'The single best thing gets +5: the one to keep exactly as it is.'});
  aim(filt, null, R ? 'inbox' : 'how');
  const reasons = R ? Object.entries(R.rejected_by_reason).filter(([,n]) => n > 0) : [];
  filt.innerHTML = R
    ? mcard({icon:'filter', soft:'var(--sky-soft)', title:'Filtered before scoring', sub:'Checker · rules, no LLM', num:fmt(R.rejected_count), cls:'txt-watch',
        cap: R.rejected_count ? `reviews thrown out: ${reasons.map(([r,n]) => `${n} ${reasonOf(r).n.toLowerCase()}`).join(', ')}.` : 'No reviews needed filtering in this run.',
        bars: reasons.length ? miniBars(reasons.map(([,n]) => n), reasons.map(() => true), 'var(--sky)') : ''})
    : mcard({icon:'filter', soft:'var(--sky-soft)', title:'Filtered before scoring', sub:'Checker · rules, no LLM', num:'4 rules', cls:'txt-watch', cap:'Duplicates, reviews under 4 words, repeated-phrase spam and gibberish are thrown out first. It costs nothing.'});

  $('#orbNum').innerHTML = rec
    ? `<b>${esc(runLabel(rec))}</b><span>${esc(bizLabel(R))} · ${rec.stored ? 'remembered in Hindsight' : 'not stored in memory'}</span>`
    : `<b>−5 to +5</b><span>every theme scored, with a reason and a next step</span>`;
  $('#heroNote').innerHTML = state.example
    ? 'Example data for a fictional café. Run your own business to replace it.'
    : rec ? `These tiles show the run selected in the workspace, covering ${esc(fmtPeriod(R.period))}.`
          : `No runs yet. <button class="link" type="button" data-example>Preview with example data</button>`;
}

/* ---------- proof ---------- */
const SCALE = [
  {name:'Fix this before anything else', score:-5, sig:'alert', stamp:'urgent', cls:'new', note:'the single most urgent problem'},
  {name:'Real problems, by urgency', score:-3, sig:'watch', stamp:'fix', cls:'watch', note:'−1 to −4'},
  {name:'Real strengths, by importance', score:3, sig:'good', stamp:'protect', cls:'good', note:'+1 to +4'},
  {name:"The single best thing", score:5, sig:'good', stamp:"don't change", cls:'good', note:'keep it exactly as it is'}
];
const beliefCls = t => ({alert:'new', watch:'watch', good:'good', steady:'steady'})[sigKey(t)];
function compareRows(rec, prev){
  const order = {worse:0, new:1, better:2, same:3};
  return rec.r.themes.filter(t => !t.fallback).map(t => {
    const m = matchIn(t, prev);
    if (!m) return {t, kind:'new'};
    const d = t.score - m.t.score;
    return {t, m:m.t, kind: d > 0 ? 'better' : d < 0 ? 'worse' : 'same'};
  }).sort((a,b) => order[a.kind] - order[b.kind] || Math.abs(b.t.score) - Math.abs(a.t.score));
}
const KIND = {worse:{cls:'new', stamp:'worse'}, new:{cls:'watch', stamp:'new'}, better:{cls:'good', stamp:'better'}, same:{cls:'steady', stamp:'same'}};
function renderProof(){
  const rec = cur(), R = rec?.r, worst = R && worstOf(R), prev = prevRec();
  $('#pfBig').innerHTML = worst
    ? `<b class="${sig(worst).txt}">${sgn(worst.score)}</b><span>${esc(worst.name)} · ${plural(worst.count, 'mention')}. The most urgent theme in ${esc(runLabel(rec).toLowerCase())}.</span>`
    : R ? `<b class="txt-good">0</b><span>problems in ${esc(runLabel(rec).toLowerCase())}: nothing scored below zero</span>`
        : `<b class="txt-alert">−5</b><span>the single most urgent problem: work on it before anything else</span>`;
  $('#pfScores').innerHTML = R && R.themes.length ? scoreChart(R.themes, worst?.id) : scoreChart(SCALE, null, true);
  $('#pfMemo').innerHTML = worst
    ? `<span class="kicker"><i></i>Next step · from the Analyst</span><p>${esc(worst.next_step)}</p>`
    : `<span class="kicker"><i></i>How it's scored</span><p>The Analyst reads each theme's quotes and what memory recalls about earlier runs, then scores it the way an owner would triage feedback.</p>`;

  const pos = R ? [...realThemes(R)].filter(t => t.score > 0).reverse().slice(0, 3) : [];
  $('#pfKeep').innerHTML = !R
    ? [...SCALE].reverse().map(s => `<div class="belief ${s.cls} clay-sm"><span class="w">${sgn(s.score)}</span><p>${esc(s.name)}</p><span class="conf">${esc(s.note)}</span><span class="stamp">${esc(s.stamp)}</span></div>`).join('')
    : pos.length ? pos.map(t => `<button class="belief good clay-sm" data-go="${esc(t.id)}"><span class="w">${sgn(t.score)}</span><p>${esc(t.name)}</p><span class="conf">${plural(t.count, 'mention')}</span><span class="stamp">${t.score === 5 ? "don't change" : 'protect'}</span></button>`).join('')
    : `<p class="empty">Nothing scored above zero in this run.</p>`;

  // p-c: what the Analyst cited from memory, and the theme that moved most
  const cited = R ? realThemes(R).flatMap(t => cites(t).map(s => ({t, s}))) : [];
  const c0 = cited.find(c => c.t === worst) || cited[0];
  $('#pfRecall').innerHTML = c0
    ? `<span class="kicker"><i></i>Cited from memory · ${esc(c0.t.name)}</span><p>${esc(c0.s)}</p>`
    : R && state.runs.length < 2
      ? `<span class="kicker"><i></i>Nothing to recall yet</span><p>This is the first run this browser has seen for ${esc(bizLabel(R))}. From the next one, the Analyst cites earlier figures in its reasoning.</p>`
      : R ? `<span class="kicker"><i></i>Recalled from memory</span><p>The Analyst didn't quote an earlier figure in this run. Compare the runs below to see what moved.</p>`
          : `<span class="kicker"><i></i>What it sounds like</span><p>“Crowding was flagged 10 times last month, 5 this month.” From the second run of a business, the reasoning cites the earlier figures.</p>`;
  let pick = null;
  if (R && prev) R.themes.forEach(t => { const m = matchIn(t, prev); if (m && (!pick || Math.abs(t.count - m.t.count) > Math.abs(pick.t.count - pick.m.count))) pick = {t, m:m.t}; });
  if (R && !pick && state.runs.length > 1) { const t = worstOf(R) || R.themes[0]; if (t) pick = {t, m:null}; }
  if (pick) {
    const series = seriesFor(pick.t), first = series.find(p => p.v != null);
    $('#pfTrend').innerHTML = runsChart(series, state.idx, sig(pick.t).c, `${pick.t.name}: mentions per run`);
    $('#pfTrendCap').innerHTML = `<span>${esc(trunc(pick.t.name, 40))} · mentions per run</span><span>${esc(first.label.toLowerCase())} <b>${first.v}</b> → now <b>${pick.t.count}</b></span>`;
  } else {
    $('#pfTrend').innerHTML = `<p class="empty">${R ? 'One run so far. The next run of this business will be charted against it.' : 'Mentions per run appear here once a business has two runs.'}</p>`;
    $('#pfTrendCap').innerHTML = `<span>Mentions per run</span><span>${R ? `run 1 <b>${R.themes.length}</b> themes` : ''}</span>`;
  }

  $('#pfScope').innerHTML = R
    ? `<span class="kicker"><i></i>Scoped memory · ${esc(tagOf(R))}</span><p>Every run of ${esc(bizLabel(R))} is stored under this tag. Recall filters on it, so other businesses' history never gets cited here.</p>`
    : `<span class="kicker"><i></i>Scoped memory</span><p>Each business gets its own memory tag, so a café's history never shows up in a telecom's analysis.</p>`;

  const n = state.runs.length;
  $('#pfRuns').innerHTML = R
    ? `<b class="txt-watch">${plural(n, 'run')}</b><span>of ${esc(bizLabel(R))} in this browser${prev ? `, compared theme by theme with ${esc(runLabel(prev).toLowerCase())}` : '. Run it again to compare'}</span>`
    : `<b class="txt-watch">Run 2</b><span>is where memory pays off: each theme is compared with the run before it</span>`;
  $('#pfCompare').innerHTML = !R
    ? `<p class="empty">From the second run, each theme shows up here as better, worse, new or unchanged.</p>`
    : !prev ? `<p class="empty">${state.idx === 0 && n > 1 ? 'This is the earliest run. Drag the timeline forward to compare.' : 'Nothing to compare yet.'}</p>`
    : compareRows(rec, prev).slice(0, 5).map(({t, m, kind}) => `<button class="belief ${KIND[kind].cls} clay-sm" data-go="${esc(t.id)}"><span class="w">${prev.run}→${rec.run}</span><p>${esc(t.name)}</p><span class="conf">${m ? `${m.count} → ${t.count} mentions · ${sgn(m.score)} → ${sgn(t.score)}` : `${plural(t.count, 'mention')} · no match in ${esc(runLabel(prev).toLowerCase())}`}</span><span class="stamp">${KIND[kind].stamp}</span></button>`).join('');
}

/* ---------- how it works ---------- */
function renderRail(){
  const rec = cur(), R = rec?.r, worst = R && worstOf(R), best = R && bestOf(R);
  const S = [
    {ic:'inbox', b:'Gather', s:'Pulls reviews from Google Maps, Google Play, the App Store or a CSV into one table.', m: R ? (R.gathered != null ? `${fmt(R.gathered)} reviews · ${fmtPeriod(R.period)}` : fmtPeriod(R.period)) : 'newest 400 reviews by default'},
    {ic:'filter', b:'Check', s:'Rule-based, no LLM: duplicates, under 4 words, repeated-phrase spam and gibberish.', m: R ? `${fmt(R.rejected_count)} filtered out${R.verified != null ? ` · ${fmt(R.verified)} kept` : ''}` : '4 rules · costs nothing'},
    {ic:'cluster', b:'Find themes', s:`One Groq call reads a random sample of ${SAMPLE_SIZE} verified reviews and returns recurring themes with mention counts and quotes.`, m: R ? `${plural(R.themes.length, 'theme')} found` : '1 Groq call'},
    {ic:'gauge', b:'Score + explain', s:'One Groq call per theme scores it from −5 to +5 and writes the reason and the next step, using what memory recalls.', m: R ? `worst ${worst ? sgn(worst.score) : '—'} · best ${best ? sgn(best.score) : '—'}` : '1 Groq call per theme', key:true},
    {ic:'brain', b:'Remember', s:"Hindsight stores the run under the business's tag, so the next run can recall it.", m: R ? (rec.stored ? `stored as week:${rec.run}` : 'not stored: memory was off') : 'retain + recall', key:true}
  ];
  $('#rail').innerHTML = S.map((s,k) => `<li class="step tile clay-sm${s.key?' key':''}"><span class="blob">${ic(s.ic)}</span><span class="n">stage ${k+1}</span><h3>${s.b}</h3><p>${s.s}</p><span class="m">${esc(s.m)}</span></li>`).join('');
  const tag = R ? tagOf(R) : 'business:<name-location>', worstName = worst?.name || R?.themes[0]?.name || '<theme>';
  const V = [
    ['retain', "Stores each run: its themes, scores, reasoning, next steps and quotes, tagged with the business and the run number.", `tags ["${tag}", "week:${rec ? rec.run : 'n'}"]`],
    ['recall', "Before scoring a theme, pulls what this business's earlier runs said about it. Other businesses are filtered out.", `"past feedback about ${worstName}" · any_strict`],
    ['scope', "Every memory carries the business tag, so one business's history never leaks into another's analysis.", `bank ${BANK} · ${tag}`]
  ];
  $('#verbs').innerHTML = V.map(([c,p,s]) => `<li class="well"><code>${c}</code><p>${esc(p)}</p><small>${esc(s)}</small></li>`).join('');
}

/* ---------- workspace: toolbar, form, progress ---------- */
const STAGES = ['Gather','Check','Themes','Score','Remember'];
$('#prog').innerHTML = STAGES.map(s => `<div class="seg wait"><div class="bar"><i></i></div><div class="lbl"><span>${s}</span><b></b></div></div>`).join('');
function renderTool(){
  const rec = cur(), R = rec?.r;
  $('#wsName').textContent = R ? R.business || 'Unnamed business' : 'No business yet';
  $('#wsSub').textContent = R ? `${R.location || (rec.mode === 'week' ? 'gathered weeks' : 'no location')} · ${fmtPeriod(R.period)}` : 'enter one below';
  $('#wsIcon').innerHTML = ic(rec?.mode === 'week' ? 'clock' : 'store');
  $('#memTag').textContent = R ? tagOf(R) : '—';
  $('#memSub').textContent = R ? 'memory tag in Hindsight' : 'memory tag appears after a run';
  $('#xBadge').hidden = !state.example;
  if (!state.running) $('#lastRun').textContent = rec ? `${runLabel(rec).toLowerCase()} · ${fmtWhen(rec.at)} · ${Math.round(rec.ms/1000)} s` : 'no runs yet';
  $('#playBtn').disabled = state.runs.length < 2;
}
function renderProgDone(){
  if (state.running) return;
  const rec = cur(), R = rec?.r, worst = R && worstOf(R), days = R && periodDays(R.period);
  const vals = R ? [R.gathered != null ? fmt(R.gathered) : days ? `${days} d` : '✓', `−${fmt(R.rejected_count)}`, String(R.themes.length), worst ? sgn(worst.score) : '—', rec.stored ? `week:${rec.run}` : 'off'] : ['','','','',''];
  $$('#prog .seg').forEach((s,k) => {
    const i = s.querySelector('.bar i'); i.style.transition = ''; i.style.transform = '';
    s.classList.remove('on'); s.classList.toggle('wait', !R);
    s.querySelector('.lbl b').textContent = vals[k];
  });
}
// There is no progress endpoint, so stages advance on typical timings (README: 60-120 s).
// Score holds just short of full until the response lands; nothing claims to be done early.
const DURS = {shop:[35000, 1500, 9000, 90000, 0], week:[1500, 1000, 9000, 90000, 0]};
let progT = [];
function startProgress(mode){
  const segs = $$('#prog .seg'), d = DURS[mode];
  progT.forEach(clearTimeout); progT = [];
  segs.forEach(s => { const i = s.querySelector('.bar i'); i.style.transition = 'none'; i.style.transform = 'scaleX(0)'; s.classList.remove('wait','on'); s.querySelector('.lbl b').textContent = ''; });
  void document.body.offsetWidth;
  let t = 0;
  [0,1,2,3].forEach(k => {
    progT.push(setTimeout(() => {
      segs.forEach((s,j) => s.classList.toggle('on', j === k));
      if (k > 0) { const p = segs[k-1].querySelector('.bar i'); p.style.transition = 'transform .4s var(--out)'; p.style.transform = 'scaleX(1)'; segs[k-1].querySelector('.lbl b').textContent = '✓'; }
      const i = segs[k].querySelector('.bar i'); i.style.transition = `transform ${d[k]}ms ${k === 3 ? 'cubic-bezier(.1,.6,.3,1)' : 'linear'}`; i.style.transform = `scaleX(${k === 3 ? .92 : .96})`;
      segs[k].querySelector('.lbl b').innerHTML = '<span class="reading"><i></i><i></i><i></i></span>';
    }, t));
    t += d[k];
  });
}
async function finishProgress(){
  progT.forEach(clearTimeout); progT = [];
  for (const s of $$('#prog .seg')) {
    const i = s.querySelector('.bar i'); i.style.transition = 'transform .3s var(--out)'; i.style.transform = 'scaleX(1)';
    s.classList.remove('on'); await wait(120);
  }
}
function failProgress(){ progT.forEach(clearTimeout); progT = []; }

function setMode(m){
  state.mode = m;
  $$('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === m)));
  $$('[data-for]').forEach(el => el.hidden = el.dataset.for !== m);
  msg('');
}
function setProvider(p){
  state.provider = p;
  $$('[data-provider]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.provider === p)));
}
function msg(text, err, html){
  const el = $('#rfMsg');
  el.hidden = !text && !html; el.classList.toggle('err', !!err);
  if (html) el.innerHTML = html; else el.textContent = text || '';
}
const renderMonths = () => { const v = +$('#fMonths').value; $('#oMonths').textContent = v ? `${v} mo` : 'no limit'; };
const renderLimit = () => { $('#oLimit').textContent = fmt(+$('#fLimit').value); };
function readForm(){
  if (state.mode === 'shop') {
    const name = $('#fName').value.trim(), loc = $('#fLoc').value.trim();
    if (!name) return {error:'Enter a business name first.', focus:'#fName'};
    const run = Math.max(1, parseInt($('#fRun').value, 10) || 1), compare = $('#fCompare').checked;
    return {mode:'shop', path:'/shops/analyse', run, label: loc ? `${name}, ${loc}` : name,
      body:{name, location:loc, months:+$('#fMonths').value, limit:+$('#fLimit').value, provider:state.provider, store:$('#fStore').checked, run_number:run,
        compare, competitors: compare ? $('#fComp').value.split(';').map(s => s.trim()).filter(Boolean).slice(0, 5) : []}};
  }
  const week = parseInt($('#fWeek').value, 10), biz = $('#fBiz').value.trim();
  if (!(week >= 1)) return {error:'Enter a week number from 1 up.', focus:'#fWeek'};
  const compare = $('#fCompare').checked, qs = new URLSearchParams();
  if (biz) qs.set('business', biz);
  if (compare) qs.set('compare', 'true');
  return {mode:'week', path:`/weeks/${week}/run${qs.size ? '?' + qs : ''}`, run:week, label: biz || 'the default business', body:null, request:{week, business: biz || null, compare}};
}
// the next run number for whatever is typed, from this browser's history
let hintT;
function hintRun(){
  clearTimeout(hintT);
  hintT = setTimeout(() => {
    if (state.mode !== 'shop') return;
    const name = $('#fName').value.trim(), loc = $('#fLoc').value.trim();
    const e = name && HISTORY[`shop:${bizSlug(loc ? `${name}, ${loc}` : name)}`];
    // 2. nothing in history: a new business starts at run 1, not at the last business's next number
    if (!e) { $('#fRun').value = 1; msg(''); return; }
    const last = Math.max(...e.runs.map(r => r.run));
    $('#fRun').value = last + 1;
    msg('', false, `${plural(e.runs.length, 'earlier run')} of ${esc(e.label)} in this browser, so this will be run ${last + 1}. <button class="link" type="button" data-key="${esc(e.key)}">Show them</button>`);
  }, 250);
}
function fillForm(e){
  const last = e.runs[e.runs.length - 1], q = last?.request || {};
  setMode(e.mode);
  if (q.compare != null) { $('#fCompare').checked = !!q.compare; syncCompare(); }
  if (e.mode === 'shop') {
    $('#fName').value = q.name ?? e.name ?? ''; $('#fLoc').value = q.location ?? e.location ?? '';
    if (q.months != null) $('#fMonths').value = q.months;
    if (q.limit != null) $('#fLimit').value = q.limit;
    if (q.provider) setProvider(q.provider);
    if (q.store != null) $('#fStore').checked = !!q.store;
    $('#fComp').value = Array.isArray(q.competitors) ? q.competitors.join('; ') : '';
    $('#fRun').value = (last?.run || 0) + 1;
    renderMonths(); renderLimit();
  } else {
    $('#fBiz').value = q.business || e.name || ''; $('#fWeek').value = (last?.run || 0) + 1;
  }
}
function renderRecent(){
  const list = Object.values(HISTORY).filter(e => e?.runs?.length).sort((a,b) => (b.at||0) - (a.at||0)).slice(0, 6);
  const el = $('#recent'); el.hidden = !list.length;
  el.innerHTML = `<span class="kicker">Recent</span>` + list.map(e => `<button type="button" class="qchip clay-sm${e.key === state.key && !state.example ? ' is-on' : ''}" data-key="${esc(e.key)}">${esc(e.label)} <span class="mono">· ${plural(e.runs.length, e.mode === 'week' ? 'week' : 'run')}</span></button>`).join('');
}

/* ---------- briefing ---------- */
function headlineFor(rec){
  const R = rec.r, T = R.themes, real = realThemes(R), worst = worstOf(R), best = bestOf(R);
  if (!T.length) return 'No themes came back for this run.';
  if (!real.length) return `Groq was unavailable, so none of the ${T.length} themes got a real score. Run again once it's reachable.`;
  const parts = [];
  if (worst) parts.push(`“${worst.name}” is the ${worst.score === -5 ? 'one to fix before anything else' : 'most urgent problem'} (${sgn(worst.score)}).`);
  if (best) parts.push(`“${best.name}” is the strength to protect (${sgn(best.score)}).`);
  return parts.join(' ') || `${plural(T.length, 'theme')}, all neutral. Nothing stands out as a problem or a strength.`;
}
function renderBriefing(typed){
  const rec = cur(), h = $('#headline');
  h.classList.remove('txt-alert');
  $('#warns').hidden = true;
  if (!rec) {
    $('#briefEyebrow').textContent = 'Briefing';
    setText(h, 'No analysis yet. Enter a business above and run it.');
    $('#hls').innerHTML = `<button class="btn" type="button" data-example>${ic('play')}Preview with example data</button>`;
    return;
  }
  const R = rec.r;
  $('#briefEyebrow').textContent = `Briefing · ${runLabel(rec).toLowerCase()} · ${fmtPeriod(R.period)}`;
  typed ? typeInto(h, headlineFor(rec), 16) : setText(h, headlineFor(rec));
  const real = realThemes(R), neg = real.filter(t => t.score < 0).slice(0, 2), pos = real.filter(t => t.score > 0).reverse().slice(0, 2);
  const chip = t => `<button class="hl clay-sm" data-go="${esc(t.id)}"><span class="blob" style="--c:${sig(t).soft}">${ic(themeIcon(t))}</span><span>${esc(trunc(t.name, 34))} · ${sgn(t.score)}</span></button>`;
  const failed = R.themes.filter(t => t.fallback);
  $('#warns').hidden = !R.warnings.length;
  $('#warns').innerHTML = R.warnings.map(w => `<p class="memo well warn"><span class="kicker"><i></i>Warning · the result is still usable</span><span>${esc(w)}</span></p>`).join('');
  $('#hls').innerHTML = [...neg, ...pos].map(chip).join('')
    + (failed.length ? `<button class="hl clay-sm" data-go="${esc(failed[0].id)}"><span class="blob" style="--c:var(--orange-soft)">${ic('alert')}</span><span>${failed.length} of ${R.themes.length} not scored: Groq unavailable</span></button>` : '')
    || `<p class="empty">No themes came back.</p>`;
}
function showRunError(lines){
  const h = $('#headline');
  setText(h, lines[0]); h.classList.add('txt-alert'); $('#warns').hidden = true;
  $('#briefEyebrow').textContent = 'Briefing · run failed';
  $('#hls').innerHTML = lines[1] ? `<p class="errnote">${esc(lines[1])}</p>` : '';
}
function renderKpis(){
  const rec = cur(), R = rec?.r;
  const k = [['Themes found', R ? R.themes.length : 0, 'kT'],
    R && R.verified != null ? [R.gathered != null ? `Verified of ${fmt(R.gathered)} gathered` : 'Reviews verified', R.verified, 'kM'] : ['Mentions in themes', R ? R.themes.reduce((a,t) => a + t.count, 0) : 0, 'kM'], ['Filtered out', R ? R.rejected_count : 0, 'kF'], [state.example ? 'Example runs' : 'Runs in history', state.runs.length, 'kR']];
  if (!$('#kT')) {
    $('#kpis').innerHTML = k.map(([l,v,id]) => `<div class="kpi well"><b id="${id}">${fmt(v)}</b><span id="${id}l">${l}</span></div>`).join('') +
      `<div class="channels"><p class="kicker">Filtered by the Checker</p><div class="chbar" id="chbar"></div><div class="chlegend" id="chlegend"></div></div>`;
    k.forEach(([,v,id]) => $('#'+id)._v = v);
  } else k.forEach(([l,v,id]) => { countUp($('#'+id), v, 500); $('#'+id+'l').textContent = l; });
  const reasons = R ? Object.entries(R.rejected_by_reason).filter(([,n]) => n > 0) : [], total = reasons.reduce((a,[,n]) => a + n, 0);
  $('#chbar').style.background = total ? '' : 'var(--well)';
  $('#chbar').innerHTML = reasons.map(([r,n]) => `<i style="width:${n/total*100}%;background:${reasonOf(r).c}" title="${esc(reasonOf(r).n)}: ${n}"></i>`).join('');
  $('#chlegend').innerHTML = reasons.length
    ? reasons.map(([r,n]) => `<span title="${esc(reasonOf(r).d)}"><i style="background:${reasonOf(r).c}"></i>${esc(reasonOf(r).n)} <b class="mono">${fmt(n)}</b></span>`).join('')
    : `<span>${R ? 'Nothing was filtered out.' : 'Filtered reviews show up here, by rule.'}</span>`;
}

/* ---------- timeline of runs ---------- */
const posAt = (i, n) => n > 1 ? `calc(16px + (100% - 32px) * ${i/(n-1)})` : '16px';
function buildTrack(){
  const n = state.runs.length, sel = $('#runSel');
  sel.max = Math.max(0, n-1); sel.disabled = n < 2;
  $('#ticks').innerHTML = state.runs.map((r,i) => `<span data-i="${i}" class="${n > 6 && i % 2 && i !== n-1 ? 'opt' : ''}" style="left:${posAt(i,n)}">${esc(runLabel(r))}</span>`).join('');
  $('#pins').innerHTML = n <= 10 ? state.runs.map((r,i) => `<div class="pin" style="left:${posAt(i,n)}" title="${esc(runLabel(r))} · ${esc(fmtWhen(r.at))}"><span>${esc(fmtDay(r.at))}</span><i></i></div>`).join('') : '';
}
function renderTrack(){
  const n = state.runs.length, i = Math.max(0, state.idx);
  $('#runSel').value = i;
  $('#fill').style.width = !n ? '0px' : n > 1 ? `calc(32px + (100% - 32px) * ${i/(n-1)})` : '32px';
  $$('#ticks span').forEach(s => s.classList.toggle('cur', +s.dataset.i === i));
  $('#runSel').setAttribute('aria-valuetext', n ? runLabel(cur()) : 'No runs');
  $('#tlLabel').textContent = n ? `${runLabel(cur())} · ${fmtWhen(cur().at)}${i === n-1 ? ' · latest' : ''}` : 'No runs yet';
  $('#tlHint').textContent = n > 1 ? 'Drag back through earlier runs. Pins show when each one ran.' : n ? 'One run so far. Run it again later to compare.' : 'Each run of a business lands here.';
}

/* ---------- themes ---------- */
function deltaText(t, prev){
  if (!prev) return '';
  const m = matchIn(t, prev);
  if (!m) return `<span class="flat">new since ${esc(runLabel(prev).toLowerCase())}</span>`;
  const d = t.count - m.t.count, worse = t.score < 0 ? d > 0 : d < 0;
  return `<span class="${d === 0 ? 'flat' : worse ? 'up' : 'down'}">${d > 0 ? '+' : d < 0 ? '−' : '±'}${Math.abs(d)} vs ${esc(runLabel(prev).toLowerCase())}</span>`;
}
function renderThemes(){
  const rec = cur(), list = $('#tlist'), before = {};
  if (!rec) { list.innerHTML = `<li class="empty">Themes appear here, worst first, once a run finishes.</li>`; $('#themesSub').textContent = 'worst first'; return; }
  list.querySelectorAll('.titem').forEach(el => before[el.dataset.id] = el.getBoundingClientRect().top);
  const T = rec.r.themes, prev = prevRec();
  const groups = [['Fix these', T.filter(t => !t.fallback && t.score < 0)], ['Neutral', T.filter(t => t.fallback || t.score === 0)], ['Protect these', T.filter(t => !t.fallback && t.score > 0)]];
  let rank = 0;
  list.innerHTML = groups.filter(([,g]) => g.length).map(([title, g]) => `<li class="tgroup"><b>${title}</b><span>${g.length}</span></li>` + g.map(t => {
    const s = sig(t); rank++;
    return `<li><button class="titem clay-sm${t.id===state.theme?' is-sel':''}" data-id="${esc(t.id)}" aria-pressed="${t.id===state.theme}">
      <span class="blob" style="--c:${s.soft}">${ic(themeIcon(t))}</span>
      <span class="t-body"><span class="t-name">${esc(t.name)}</span>
        <span class="t-meta"><span>${plural(t.count, 'mention')}</span>${t.fallback ? '<span class="txt-alert">⚠ not scored</span>' : deltaText(t, prev)}</span>${meter(t.score, s.c)}</span>
      <span class="t-score"><small>#${rank}</small><b>${sgn(t.score)}</b><small>score</small></span></button></li>`;
  }).join('')).join('') || `<li class="empty">No themes came back for this run.</li>`;
  $('#themesSub').textContent = `worst first · ${runLabel(rec).toLowerCase()}`;
  if (!reduce) list.querySelectorAll('.titem').forEach(el => {
    const b = before[el.dataset.id]; if (b === undefined) return;
    const dy = b - el.getBoundingClientRect().top;
    if (Math.abs(dy) > 2) el.animate([{transform:`translateY(${dy}px)`},{transform:'none'}], {duration:520, easing:'cubic-bezier(.34,1.4,.64,1)'});
  });
}

/* ---------- detail ---------- */
function verdict(t, R){
  const V = (sg, icn, title, body, ba) => `<span class="blob" style="--c:${SIG[sg].soft}">${ic(icn)}</span><div><h4>${esc(title)}</h4><p>${esc(body)}</p>${ba ? `<div class="ba">${ba}</div>` : ''}</div>`;
  if (t.fallback) return V('alert', 'alert', 'Not a real score', "Groq was unavailable or rate limited, so the Analyst defaulted this theme to 0. Run again once it's reachable.");
  const real = realThemes(R), neg = real.filter(x => x.score < 0), pos = real.filter(x => x.score > 0).reverse();
  if (t.score < 0) {
    const k = neg.indexOf(t) + 1, ba = `<span>${sgn(t.score)}</span>→<span>problem ${k} of ${neg.length}</span>`;
    if (t.score === -5) return V('alert', 'alert', 'Fix this before anything else', '−5 is the single most urgent problem: the one to work on first.', ba);
    if (k === 1) return V('alert', 'alert', 'Fix this first', `The most urgent of the ${plural(neg.length, 'problem')} in this run.`, ba);
    if (t.score <= -3) return V('alert', 'alert', 'Fix soon', 'A real problem, ranked just below the most urgent ones.', ba);
    return V('watch', 'clock', 'Worth fixing, not urgent', 'A real complaint, but lower priority than the ones above it.', ba);
  }
  if (t.score > 0) {
    const k = pos.indexOf(t) + 1, ba = `<span>${sgn(t.score)}</span>→<span>strength ${k} of ${pos.length}</span>`;
    if (t.score === 5) return V('good', 'check', 'Keep doing exactly this', 'The single thing this business is best at right now.', ba);
    if (k === 1) return V('good', 'check', 'Protect this', `The strongest of the ${plural(pos.length, 'strength')} in this run.`, ba);
    return V('good', 'check', 'A real strength', 'Worth protecting, ranked below the ones above it.', ba);
  }
  return V('steady', 'text', 'Neutral', 'Mentioned, but neither a problem nor a strength.');
}
function trace(rec, t){
  const R = rec.r, tag = tagOf(R), q = rec.request || {};
  const call = rec.mode === 'week'
    ? `<span class="k">POST</span> /weeks/${rec.run}/run${q.business ? `?business=${esc(encodeURIComponent(q.business))}` : ''}`
    : `<span class="k">POST</span> /shops/analyse\n  <span class="s">${esc(JSON.stringify(q))}</span>`;
  return `<span class="c"># ${esc(runLabel(rec).toLowerCase())} · ${esc(t.name)}${state.example ? ' · example data, nothing was sent' : ''}</span>
${call}
  <span class="c">→ 200 · ${plural(R.themes.length, 'theme')} · ${fmt(R.rejected_count)} filtered · ${Math.round(rec.ms/1000)} s</span>
<span class="k">memory.recall_context</span>(<span class="s">"past feedback about ${esc(t.name)}"</span>)
  bank=<span class="s">"${BANK}"</span>, tags=[<span class="s">"${esc(tag)}"</span>], tags_match=<span class="s">"any_strict"</span>
<span class="k">call_llm</span>(SYSTEM_PROMPT, theme + ${plural(t.samples.length, 'quote')} + recalled memory)
  <span class="c">→ ${t.fallback ? 'fallback: LLM unavailable, score 0' : `score ${sgn(t.score)}`}</span>
${rec.stored
  ? `<span class="k">memory.store_week</span>(${rec.run}, result)\n  tags=[<span class="s">"${esc(tag)}"</span>, <span class="s">"week:${rec.run}"</span>]`
  : `<span class="c"># memory.store_week skipped: store was off for this run</span>`}`;
}
function renderDetail(typed){
  const rec = cur(), T = rec?.r.themes || [];
  $('#detailEmpty').hidden = !!T.length; $('#detailBody').hidden = !T.length;
  if (!T.length) return;
  const R = rec.r, t = T.find(x => x.id === state.theme) || T[0], g = sig(t), prev = prevRec();
  state.theme = t.id;
  const body = $('#detailBody');
  body.style.setProperty('--c', g.c);
  $('#dIcon').style.setProperty('--c', g.soft);
  $('#dIcon').innerHTML = ic(themeIcon(t));
  $('#dName').textContent = t.name;
  $('#dMeta').textContent = `${plural(t.count, 'mention')} · ${runLabel(rec).toLowerCase()} · ${fmtPeriod(R.period)}`;
  $('#dRing').innerHTML = ring(t.score);
  const m = matchIn(t, prev), share = T.reduce((a,x) => a + x.count, 0);
  const d = m && m.t.count ? (t.count - m.t.count) / m.t.count : null, worse = t.score < 0 ? d > 0 : d < 0;
  $('#dStats').innerHTML = `
    <div class="well"><b>${fmt(t.count)}</b><span>${sampleOf(R) != null ? `mentions in a sample of ${sampleOf(R)} reviews` : `mentions${share ? `, ${Math.round(t.count/share*100)}% of all` : ''}`}</span></div>
    <div class="well"><b class="${g.txt}">${sgn(t.score)}</b><span>score, −5 to +5</span></div>
    <div class="well"><b class="${!prev ? 'flat' : !m ? 'flat' : Math.abs(d) < .05 ? 'flat' : worse ? 'up' : 'down'}">${!prev ? '—' : !m ? 'new' : d === null ? '—' : `${d > 0 ? '+' : d < 0 ? '−' : ''}${Math.abs(Math.round(d*100))}%`}</b><span>${prev ? `mentions vs ${esc(runLabel(prev).toLowerCase())}` : 'no earlier run'}</span></div>`;
  const n = state.runs.length;
  $('#dChartCap').innerHTML = `<span>Mentions per run</span><span>${n > 1 ? 'pill = score · dashed = runs after the one selected' : 'one run so far'}</span>`;
  $('#dChart').innerHTML = runsChart(seriesFor(t), state.idx, g.c, `${t.name}: mentions per run`);
  $('#dVerdict').innerHTML = verdict(t, R);

  $('#dWhyNote').textContent = t.fallback ? "This is analyst.py's fallback text, not reasoning." : `The Analyst's reasoning for ${runLabel(rec).toLowerCase()}. It was given this theme's quotes plus what Hindsight recalled about earlier runs of this business${R.market?.competitors.length ? ', and what customers say about nearby competitors' : ''}.`;
  typed ? typeInto($('#dWhy'), t.reasoning || 'No reasoning came back.', 10) : setText($('#dWhy'), t.reasoning || 'No reasoning came back.');
  $('#dVsSec').hidden = !t.vs || t.fallback;
  $('#dVs').textContent = t.vs;
  const citing = cites(t).length;
  $('#dRel').innerHTML = `<span class="relchip"><b>period</b>${esc(fmtPeriod(R.period))}</span>`
    + (citing ? `<span class="relchip"><b>memory</b>cites an earlier run</span>` : '')
    + (R.market?.competitors.length ? `<span class="relchip"><b>market</b>scored against ${plural(R.market.competitors.length, 'competitor')}</span>` : '')
    + `<span class="relchip"><b>${rec.stored ? 'stored' : 'not stored'}</b>${rec.stored ? `as week:${rec.run}` : 'memory was off'}</span>`;
  $('#dQuotes').innerHTML = t.samples.length
    ? t.samples.map(q => `<blockquote class="quote well"><p>“${esc(q)}”</p><footer>${ic('bubble')}<b>Verified review</b> · passed the Checker</footer></blockquote>`).join('')
    : `<p class="empty">No quotes came back for this theme.</p>`;
  $('#dSteps').innerHTML = t.next_step
    ? `<li><label><input type="checkbox" id="step-${esc(t.id)}"><span>${esc(t.next_step)}</span></label></li>`
    : `<li class="empty">No next step came back.</li>`;

  const earlier = state.runs.slice(0, state.idx).reverse(), matches = earlier.map(r => ({r, m: matchIn(t, r)})).filter(x => x.m);
  $('#dMemCount').textContent = earlier.length ? `${matches.length} of ${plural(earlier.length, 'earlier run')}` : '';
  $('#dMem').innerHTML = matches.length ? matches.map(({r, m}, k) => {
    const kind = t.score > m.t.score ? 'better' : t.score < m.t.score ? 'worse' : 'same';
    return `<li class="clay-sm" style="animation-delay:${reduce ? 0 : k*60}ms"><span class="wk">${esc(runLabel(r))} · ${esc(fmtDay(r.at))}</span><span class="mtext">“${esc(m.t.name)}” scored ${sgn(m.t.score)} from ${plural(m.t.count, 'mention')}. ${esc(firstSentence(m.t.reasoning, 180))}</span>
      <span class="mfoot"><span class="kind k-${kind}">${kind === 'same' ? 'same score' : kind + ' now'}</span><span>name match</span><span class="relbar"><i style="width:${Math.round(m.sim*100)}%"></i></span><span>${m.sim.toFixed(2)}</span></span></li>`;
  }).join('') : `<li class="empty">${earlier.length ? `No theme with a similar name in ${earlier.length === 1 ? 'the earlier run' : 'the earlier runs'}.` : 'No earlier runs in this browser. Hindsight may still hold runs made from the CLI or another device, and the Analyst recalls those.'}</li>`;
  $('#dTrace').innerHTML = trace(rec, t);
  if (typed !== undefined) { body.classList.remove('swap'); void body.offsetWidth; body.classList.add('swap'); }
}

/* ---------- review stream: the run's quotes replayed, and what the Checker threw out ---------- */
let deck = [], streamKey = null, streamT;
function freshDeck(){
  const R = cur()?.r; if (!R) return [];
  const items = R.themes.flatMap(t => t.samples.map(x => ({k:'quote', t, x})))
    .concat(Object.entries(R.rejected_by_reason).filter(([,n]) => n > 0).map(([r,n]) => ({k:'spam', r, n})));
  for (let k = items.length-1; k > 0; k--) { const j = Math.floor(Math.random()*(k+1)); [items[k], items[j]] = [items[j], items[k]]; }
  return items;
}
function nextItem(){ if (!deck.length) deck = freshDeck(); return deck.pop(); }
function verdictChip(it){
  if (it.k === 'spam') return `<span class="tag spamtag">${esc(it.r)} · filtered</span>`;
  return `<button class="tag" data-go="${esc(it.t.id)}" style="--c:${sig(it.t).soft}">→ ${esc(trunc(it.t.name, 30))} · ${sgn(it.t.score)}</button>`;
}
function fbHTML(it, done){
  const top = it.k === 'spam'
    ? `<span class="ch">${ic('filter')}Checker</span><span>${plural(it.n, 'review')}</span>`
    : `<span class="ch">${ic('bubble')}Review</span><span>${plural(it.t.count, 'mention')} of this theme</span>`;
  const text = it.k === 'spam' ? `${reasonOf(it.r).n}: ${reasonOf(it.r).d}.` : it.x;
  return `<div><article class="fb clay-sm${done && it.k === 'spam' ? ' spam' : ''}">
    <div class="fb-top">${top}</div>
    <p>${esc(text)}</p>
    <div class="vslot">${done ? verdictChip(it) : `<span class="reading"><i></i><i></i><i></i>&nbsp;reading</span>`}</div>
  </article></div>`;
}
function pushFeedback(){
  const it = nextItem(); if (!it) return;
  const list = $('#stream'), li = document.createElement('li');
  list.querySelector('.empty')?.remove();
  li.className = 'fbw enter'; li.innerHTML = fbHTML(it, false);
  list.prepend(li);
  requestAnimationFrame(() => requestAnimationFrame(() => li.classList.remove('enter')));
  setTimeout(() => {
    const art = li.querySelector('.fb'); if (!art) return;
    li.querySelector('.vslot').innerHTML = verdictChip(it);
    if (it.k === 'spam') { art.classList.add('spam'); setTimeout(() => { li.classList.add('gone'); setTimeout(() => li.remove(), 500); }, 2200); }
  }, reduce ? 0 : 1100);
  const items = list.querySelectorAll('.fbw:not(.gone)');
  if (items.length > 6) { const old = items[items.length-1]; old.classList.add('gone'); setTimeout(() => old.remove(), 500); }
}
function resetStream(){
  const rec = cur(), key = rec ? `${state.key}#${rec.run}@${rec.at}` : null;
  if (key === streamKey) return;
  streamKey = key; deck = [];
  const R = rec?.r;
  countUp($('#cQuotes'), R ? R.themes.reduce((a,t) => a + t.samples.length, 0) : 0, 400);
  countUp($('#cSpam'), R ? R.rejected_count : 0, 400);
  countUp($('#cThemed'), R ? R.themes.length : 0, 400);
  if (!R) { $('#stream').innerHTML = `<li class="empty">Quotes from the reviews replay here once a run finishes, alongside what the Checker threw out.</li>`; return; }
  deck = freshDeck();
  const seed = deck.filter(it => it.k === 'quote').slice(0, 4);
  deck = deck.filter(it => !seed.includes(it));
  $('#stream').innerHTML = seed.length ? seed.map(it => `<li class="fbw">${fbHTML(it, true)}</li>`).join('') : `<li class="empty">No quotes came back in this run.</li>`;
}
function setStream(on){
  state.stream = on;
  $('#inbox').classList.toggle('paused', !on);
  $('#liveLabel').textContent = on ? 'replaying' : 'paused';
  $('#streamBtn').innerHTML = ic(on ? 'pause' : 'play');
  $('#streamBtn').setAttribute('aria-label', on ? 'Pause the review stream' : 'Resume the review stream');
  clearInterval(streamT);
  if (on) streamT = setInterval(() => { if (!document.hidden && inView && cur()) pushFeedback(); }, 2800);
}
let inView = false;
new IntersectionObserver(es => { inView = es[0].isIntersecting; }, {threshold:.05}).observe($('#inbox'));

/* ---------- ask: answered from the result on screen, no extra API call ---------- */
const QCHIPS = ['What should I fix first?', 'What should I protect?', 'What are competitors doing better?', 'What changed since the last run?', 'Why were reviews filtered out?'];
function themeAnswer(t, how){
  return {steps:[how, `read the Analyst's reasoning for “${trunc(t.name, 40)}”`], go:t.id,
    a:`${t.name} scored ${sgn(t.score)} from ${plural(t.count, 'mention')}. ${t.reasoning}${t.next_step ? ` Next step: ${t.next_step}` : ''}`};
}
const QSTOP = new Set('what why how when where which who should would could can does did about since last run runs first get got getting there here been being any tell show give me'.split(' ').map(stem));
function answerFor(q, rec){
  const R = rec.r, real = realThemes(R), prev = prevRec(), read = `read ${runLabel(rec).toLowerCase()} → ${plural(R.themes.length, 'theme')}, ${fmt(R.rejected_count)} filtered`;
  const QT = new Set([...tokens(q)].filter(w => !QSTOP.has(w))), byName = real.map(t => { let n = 0; tokens(t.name).forEach(w => { if (QT.has(w)) n++; }); return {t, n}; }).filter(x => x.n).sort((a,b) => b.n - a.n)[0];
  if (/filter|reject|spam|junk|remov|checker|thrown|drop|fake/i.test(q)) {
    const rs = Object.entries(R.rejected_by_reason).filter(([,n]) => n > 0);
    return {steps:[read, `rejected_by_reason → ${rs.map(([r,n]) => `${r} ${n}`).join(', ') || 'none'}`], a: R.rejected_count
      ? `The Checker threw out ${plural(R.rejected_count, 'review')} before scoring: ${rs.map(([r,n]) => `${n} ${reasonOf(r).n.toLowerCase()} (${reasonOf(r).d})`).join(', ')}. It uses fixed rules, not an LLM, so filtering costs nothing and gives the same answer every time.`
      : 'Nothing was filtered out in this run. Every gathered review passed the Checker.'};
  }
  if (/compet|rival|market|nearby|other (shop|place|caf|business)|neighbo/i.test(q)) {
    const M = R.market, list = (M?.competitors || []).filter(c => !c.degraded);
    if (!M) return {steps:[read, 'result.market → not scanned'], a:`This run didn't look at competitors. Tick “Compare with competitors” and run ${bizLabel(R)} again to see what similar places nearby do well and badly.`};
    if (!list.length) return {steps:[read, 'result.market → no competitor summarised'], a:'Competitors were scanned in this run, but none of their reviews could be summarised. The warnings on the briefing say why.'};
    const vs = real.filter(t => t.vs), lead = vs.sort((a,b) => a.score - b.score)[0];
    const good = list.map(c => c.strengths.length ? `${c.name} is praised for ${c.strengths.map(p => p.point.toLowerCase()).join(', ')}` : '').filter(Boolean);
    const bad = list.map(c => c.weaknesses.length ? `${c.name} is criticised for ${c.weaknesses.map(p => p.point.toLowerCase()).join(', ')}` : '').filter(Boolean);
    return {steps:[read, `result.market → ${plural(list.length, 'competitor')}`, `themes with a competitor note → ${vs.length}`], go: lead?.id,
      a:[...good, ...bad].join('. ') + '.' + (lead ? ` Against your themes, ${lead.name} (${sgn(lead.score)}): ${lead.vs}` : '')};
  }
  if (byName) return {...themeAnswer(byName.t, `match “${trunc(q, 40)}” → “${trunc(byName.t.name, 40)}”`), steps:[read, `match theme name → “${trunc(byName.t.name, 40)}”`, `read the Analyst's reasoning`]};
  if (/chang|since|last run|previous|earlier|trend|better|worse|compar|improv|moved/i.test(q)) {
    if (!prev) return {steps:[read, 'look for an earlier run → none'], a:`There is no earlier run of ${bizLabel(R)} in this browser to compare with. Run it again later with the next run number and each theme will be compared.`};
    const rows = compareRows(rec, prev), by = k => rows.filter(r => r.kind === k);
    const say = (list, f) => list.slice(0, 3).map(f).join('; ');
    const parts = [];
    if (by('worse').length) parts.push(`Worse: ${say(by('worse'), r => `${r.t.name} (${sgn(r.m.score)} → ${sgn(r.t.score)})`)}.`);
    if (by('new').length) parts.push(`New: ${say(by('new'), r => `${r.t.name} (${sgn(r.t.score)})`)}.`);
    if (by('better').length) parts.push(`Better: ${say(by('better'), r => `${r.t.name} (${sgn(r.m.score)} → ${sgn(r.t.score)})`)}.`);
    if (by('same').length) parts.push(`Unchanged: ${plural(by('same').length, 'theme')}.`);
    const lead = rows.find(r => r.kind === 'worse' || r.kind === 'new') || rows[0];
    return {steps:[read, `compare with ${runLabel(prev).toLowerCase()} → ${rows.filter(r => r.m).length} matched by name`], go: lead?.t.id,
      a:`Compared with ${runLabel(prev).toLowerCase()}: ${parts.join(' ')} Themes are matched by name, so a heavily reworded theme can show up as new.`};
  }
  if (/protect|best|strength|keep|good|love|prais|well|like/i.test(q)) { const b = bestOf(R); if (b) return themeAnswer(b, 'highest score → ' + sgn(b.score)); return {steps:[read], a:'Nothing scored above zero in this run, so there is no strength to single out.'}; }
  if (/fix|worst|urgent|problem|first|bad|complain|issue|wrong/i.test(q)) { const w = worstOf(R); if (w) return themeAnswer(w, 'lowest score → ' + sgn(w.score)); return {steps:[read], a:'Nothing scored below zero in this run, so there is nothing urgent to fix.'}; }
  const hit = real.map(t => { let n = 0; tokens(`${t.samples.join(' ')} ${t.reasoning}`).forEach(w => { if (QT.has(w)) n++; }); return {t, n}; }).filter(x => x.n).sort((a,b) => b.n - a.n)[0];
  if (hit) return {...themeAnswer(hit.t, ''), steps:[read, `search quotes and reasoning → “${trunc(hit.t.name, 40)}”`, `read the Analyst's reasoning`]};
  const w = worstOf(R), b = bestOf(R);
  return {steps:[read, 'no theme matched the question'], a:`That doesn't match anything in this run. The themes to look at are ${w ? `${w.name} (${sgn(w.score)}), the most urgent problem` : 'the ones in the list'}${b ? `, and ${b.name} (${sgn(b.score)}), the strength to protect` : ''}. Try asking about one of those, or what changed since the last run.`};
}
let askSeq = 0;
async function ask(text){
  const my = ++askSeq, box = $('#answer'), rec = cur(), stale = () => my !== askSeq;
  box.innerHTML = `<p class="q"></p><div class="strace"></div><p class="a"></p>`;
  box.querySelector('.q').textContent = text;
  if (!rec) { await typeInto(box.querySelector('.a'), 'Run an analysis first. Answers come from the result it returns.', 12); return; }
  const A = answerFor(text, rec), tr = box.querySelector('.strace');
  const step = async (label, ms) => { const d = document.createElement('div'); d.className = 'pending'; d.innerHTML = '<i></i><span></span>'; d.lastChild.textContent = label; tr.appendChild(d); await wait(ms); d.className = ''; };
  $('#agentBox').classList.add('thinking');
  for (const [k, s] of A.steps.filter(Boolean).entries()) { await step(s, [450, 400, 300][k] || 300); if (stale()) return; }
  $('#agentBox').classList.remove('thinking');
  await typeInto(box.querySelector('.a'), A.a, 12);
  if (stale()) return;
  if (A.go) { const t = rec.r.themes.find(x => x.id === A.go); const b = document.createElement('button'); b.className = 'btn goto'; b.dataset.go = A.go; b.innerHTML = `${ic('arrow')}Open ${esc(trunc(t.name, 32))}`; box.appendChild(b); }
}
function renderAskIdle(){
  askSeq++;  // a question still answering belongs to the run that was on screen
  if (!state.running) $('#agentBox').classList.remove('thinking');
  const rec = cur(), box = $('#answer');
  if (!rec) { box.innerHTML = `<p class="q">What should I fix first?</p><p class="a">Run an analysis and ask about it here: what to fix, what to protect, what changed since the last run, or why reviews were filtered out.</p>`; return; }
  const A = answerFor(QCHIPS[0], rec), t = A.go && rec.r.themes.find(x => x.id === A.go);
  box.innerHTML = `<p class="q">${esc(QCHIPS[0])}</p><div class="strace">${A.steps.filter(Boolean).map(s => `<div><i></i><span>${esc(s)}</span></div>`).join('')}</div>
    <p class="a">${esc(A.a)}</p>${t ? `<button class="btn goto" data-go="${esc(t.id)}">${ic('arrow')}Open ${esc(trunc(t.name, 32))}</button>` : ''}`;
}

/* ---------- cost ---------- */
// shop.py: page 1 returns 8 reviews, later pages 20, capped at MAX_PAGES searches a run.
// Star-only reviews carry no text, so a real run can need more pages than this minimum.
const FIRST_PAGE = 8, PAGE_SIZE = 20, MAX_PAGES = 30, GROQ_PER_RUN = 8, SERP_FREE = 250;
function renderCost(){
  const B = +$('#rBiz').value, Rn = +$('#rRuns').value, L = +$('#rLim').value, M = +$('#rMin').value;
  $('#oBiz').textContent = B; $('#oRuns').textContent = Rn; $('#oLim').textContent = fmt(L); $('#oMin').textContent = `${M} min`;
  const runs = B*Rn, perRun = Math.min(MAX_PAGES, 1 + Math.ceil(Math.max(0, L - FIRST_PAGE) / PAGE_SIZE)), got = Math.min(L, FIRST_PAGE + (MAX_PAGES - 1) * PAGE_SIZE);
  $('#rLimNote').textContent = got < L ? `A run stops at ${MAX_PAGES} searches, so expect at most about ${got} reviews with text, not ${fmt(L)}.` : `At least ${perRun} SerpApi ${perRun === 1 ? 'search' : 'searches'} per run, up to ${MAX_PAGES} when many reviews are star-only.`;
  const searches = runs * perRun, hours = runs * got/100 * M/60;
  $('#vHours').textContent = `${fmt(Math.round(hours))} hour${Math.round(hours) === 1 ? '' : 's'}`;
  const vs = $('#vSearch'); vs.textContent = fmt(searches); vs.className = searches > SERP_FREE ? 'txt-alert' : '';
  $('#vSearchNote').textContent = searches > SERP_FREE ? `SerpApi searches a month: over the ${SERP_FREE} free` : `SerpApi searches a month, of ${SERP_FREE} free`;
  $('#vGroq').textContent = fmt(runs * GROQ_PER_RUN);
}
$('#roiForm').addEventListener('input', renderCost);
$('#roiForm').addEventListener('submit', e => e.preventDefault());

/* ---------- loading runs ---------- */
function renderAll(typed){
  renderHero(); renderProof(); renderRail(); renderTool(); renderProgDone(); renderBriefing(typed); renderKpis();
  buildTrack(); renderTrack(); renderThemes(); renderDetail(typed ? true : undefined); resetStream(); renderAskIdle(); renderRecent(); renderMarket();
  $('#footNote').textContent = state.example ? 'The example café and its reviews are fictional.' : 'Scores come from Groq. Quotes are real reviews that passed the Checker.';
}
function pickTheme(prevTheme){
  const R = cur()?.r; if (!R) return null;
  const m = prevTheme && matchIn(prevTheme, cur());
  return (m?.t || worstOf(R) || R.themes[0] || {}).id || null;
}
function openRuns(key, runs, {example = false, run = null, at = null, typed = false} = {}){
  stopPlay();
  state.key = key; state.example = example; state.runs = runs;
  state.idx = run == null ? runs.length - 1 : Math.max(0, at != null ? runs.findIndex(r => r.at === at) : runs.findLastIndex(r => r.run === run));
  state.theme = pickTheme(null);
  renderAll(typed);
}
const busy = () => { if (state.running) toast('An analysis is still running. Open this once it finishes.'); return state.running; };
function openEntry(key){
  if (busy()) return;
  const e = HISTORY[key]; if (!e?.runs?.length) return;
  fillForm(e); msg('');
  openRuns(key, hydrate(e.runs));
  LS.set(LKEY, key);
  toast(`Loaded ${plural(e.runs.length, e.mode === 'week' ? 'week' : 'run')} of ${e.label} from this browser. Nothing was sent to the API.`);
}
function loadExample(){
  if (busy()) return;
  openRuns('example', hydrate(EXAMPLE), {example:true, typed:true});
  toast('Showing example data for a fictional café. Nothing was sent to the API.');
}
function setRun(i, typed){
  const before = cur()?.r.themes.find(t => t.id === state.theme);
  state.idx = Math.max(0, Math.min(state.runs.length - 1, i));
  state.theme = pickTheme(before);
  renderHero(); renderProof(); renderRail(); renderTool(); renderProgDone(); renderBriefing(typed); renderKpis();
  renderTrack(); renderThemes(); renderDetail(typed ? true : undefined); resetStream(); renderAskIdle(); renderMarket();
}

/* ---------- local market ---------- */
function renderMarket(){
  const rec = cur(), M = rec?.r.market, list = M?.competitors || [];
  $('#mktSub').textContent = !M ? "what nearby competitors' customers praise and criticise"
    : `${plural(list.length, 'competitor')}${M.discovered ? ', the busiest similar places nearby' : ''} · ${runLabel(rec).toLowerCase()}`;
  const pts = (a, cls, none) => a.length
    ? `<ul class="mkt-list ${cls}">${a.map(p => `<li><span>${esc(p.point)}</span>${p.evidence ? `<q>${esc(p.evidence)}</q>` : ''}</li>`).join('')}</ul>`
    : `<p class="empty">${none}</p>`;
  $('#mktGrid').innerHTML = !rec
    ? `<p class="empty">Run an analysis with “Compare with competitors” ticked to see what similar places nearby do well and badly. The Analyst scores each of your themes against them.</p>`
    : !M ? `<p class="empty">This run didn't compare with competitors. Tick “Compare with competitors” and run it again.</p>`
    : !list.length ? `<p class="empty">No competitor could be read for this run. The warnings above say why.</p>`
    : list.map(c => `<article class="mkt-card well">
        <header><h4>${esc(c.name)}</h4><span class="meta">${c.rating != null ? `${c.rating}★` : ''}${c.reviews_used != null ? ` · ${plural(c.reviews_used, 'review')} read` : c.review_count != null ? ` · ${plural(c.review_count, 'review')}` : ''}</span></header>
        ${c.address ? `<p class="addr">${esc(c.address)}</p>` : ''}
        ${c.degraded ? `<p class="empty">Groq didn't summarise this competitor's reviews in this run.</p>` : `
        <h5>Customers praise</h5>${pts(c.strengths, 'good', 'Nothing stood out.')}
        <h5>Customers complain about</h5>${pts(c.weaknesses, 'bad', 'Nothing stood out.')}`}
      </article>`).join('');
}
function syncCompare(){ $('#fComp').disabled = !$('#fCompare').checked; }
function selectTheme(id, scroll){
  if (!cur()?.r.themes.some(t => t.id === id)) return;
  state.theme = id; renderThemes(); renderDetail(true);
  if (scroll) $('#detail').scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block:'start'});
}
const dayOf = ts => new Date(ts).toDateString();
// servers from before the "stored" flag: asked to store and no warning saying it wasn't
const storedOf = (req, res) => typeof res?.stored === 'boolean' ? res.stored
  : (req.mode === 'week' || req.body?.store !== false) && !normResult(res).warnings.some(w => /not stored|isn't stored/i.test(w));
function saveRun(req, res, ms){
  const R = normResult(res), label = bizLabel(R) || req.label, key = `${req.mode}:${bizSlug(label)}`;
  const run = parseInt(res.week, 10) || req.run, at = Date.now();
  const rec = {mode:req.mode, run, at, ms, stored: storedOf(req, res), request: req.body || req.request, res};
  const e = HISTORY[key] || (HISTORY[key] = {key, mode:req.mode, label, name:R.business, location:R.location, runs:[]});
  // mirror what Hindsight replaces: week:N for weeks, run:N:<day> for shop runs
  const same = r => r.run === run && (req.mode === 'week' || dayOf(r.at) === dayOf(at));
  e.runs = e.runs.filter(r => !same(r)).concat(rec).sort(byRun).slice(-MAX_RUNS);
  e.label = label; e.at = rec.at;
  const all = Object.values(HISTORY).sort((a,b) => (b.at||0) - (a.at||0));
  all.slice(MAX_BIZ).forEach(x => delete HISTORY[x.key]);
  state.key = key; saveHistory(); LS.set(LKEY, key);
  return {key, run, at};
}

/* ---------- running an analysis ---------- */
let elapsedT;
async function runAnalysis(e){
  e?.preventDefault();
  if (state.running) return;
  const req = readForm();
  if (req.error) { msg(req.error, true); $(req.focus).focus(); return; }
  msg('');
  stopPlay();
  state.running = true;
  const btn = $('#runBtn'); btn.disabled = true; btn.lastElementChild.textContent = 'Analysing…';
  $('#agentBox').classList.add('thinking'); $('#heroOrb').classList.add('thinking');
  const t0 = performance.now();
  $('#lastRun').textContent = 'running · 0 s';
  elapsedT = setInterval(() => { $('#lastRun').textContent = `running · ${Math.round((performance.now()-t0)/1000)} s`; }, 1000);
  $('#briefEyebrow').textContent = `Briefing · ${req.mode === 'week' ? `week ${req.run}` : `run ${req.run}`} · in progress`;
  $('#headline').classList.remove('txt-alert');
  typeInto($('#headline'), req.mode === 'week' ? `Analysing week ${req.run} of ${req.label}. The Scorer and the Analyst make one Groq call per theme…` : `Reading reviews for ${req.label}. This usually takes one to two minutes…`, 14);
  $('#hls').innerHTML = '';
  startProgress(req.mode);
  try {
    if (apiUp === false) await checkHealth();
    const res = await call(req.path, req.body);
    const ms = Math.round(performance.now() - t0);
    await finishProgress();
    const {key, run, at} = saveRun(req, res, ms);
    state.running = false;
    openRuns(key, hydrate(HISTORY[key].runs), {run, at, typed:true});
    if (req.mode === 'shop') $('#fRun').value = run + 1;
    const R = cur().r, failed = R.themes.filter(t => t.fallback).length;
    toast(`${runLabel(cur())} done in ${Math.round(ms/1000)} s · ${plural(R.themes.length, 'theme')} · ${fmt(R.rejected_count)} filtered${failed ? ` · ${failed} not scored` : ''}${cur().stored ? ' · stored in Hindsight' : ''}.`);
  } catch (err) {
    failProgress();
    state.running = false;
    renderProgDone();
    const lines = err instanceof Error ? ['Something went wrong in the page.', err.message] : explainError(err, req);
    showRunError(lines);
    toast(lines[0]);
    if (err?.status === 0 && !err.aborted) checkHealth();
  } finally {
    state.running = false;
    clearInterval(elapsedT);
    btn.disabled = false; btn.lastElementChild.textContent = 'Run analysis';
    $('#agentBox').classList.remove('thinking'); $('#heroOrb').classList.remove('thinking');
    renderTool();
  }
}

/* ---------- wiring ---------- */
document.addEventListener('click', e => {
  const ex = e.target.closest('[data-example]');
  if (ex) { loadExample(); $('#demo').scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block:'start'}); return; }
  const go = e.target.closest('[data-go]'); if (go) { selectTheme(go.dataset.go, true); return; }
  const sc = e.target.closest('[data-scroll]'); if (sc) { document.getElementById(sc.dataset.scroll)?.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block:'start'}); return; }
  const ti = e.target.closest('.titem'); if (ti) { selectTheme(ti.dataset.id, matchMedia('(max-width: 880px)').matches); return; }
  const rk = e.target.closest('[data-key]'); if (rk) { openEntry(rk.dataset.key); return; }
  const md = e.target.closest('[data-mode]'); if (md) { setMode(md.dataset.mode); return; }
  const pv = e.target.closest('[data-provider]'); if (pv) { setProvider(pv.dataset.provider); return; }
  const ff = e.target.closest('[data-focus-form]'); if (ff) setTimeout(() => (state.mode === 'shop' ? $('#fName') : $('#fWeek')).focus({preventScroll:true}), reduce ? 0 : 650);
});
$('#runForm').addEventListener('submit', runAnalysis);
$('#fMonths').addEventListener('input', renderMonths);
$('#fLimit').addEventListener('input', renderLimit);
$('#fName').addEventListener('input', hintRun);
$('#fLoc').addEventListener('input', hintRun);
$('#runSel').addEventListener('input', e => { stopPlay(); setRun(+e.target.value, false); });
$('#runSel').addEventListener('change', () => { renderBriefing(true); });
$('#fCompare').addEventListener('change', syncCompare);
syncCompare();
$('#streamBtn').addEventListener('click', () => setStream(!state.stream));
let playT;
function stopPlay(){ state.playing = false; clearTimeout(playT); $('#playBtn').innerHTML = `${ic('play')}<span>Replay runs</span>`; }
function play(){
  if (state.playing) return stopPlay();
  const n = state.runs.length; if (n < 2) return;
  state.playing = true; $('#playBtn').innerHTML = `${ic('pause')}<span>Pause replay</span>`;
  let i = state.idx >= n-1 ? 0 : state.idx;
  const tick = () => {
    if (!state.playing) return;
    setRun(i, false);
    if (i >= n-1) { stopPlay(); renderBriefing(true); renderDetail(true); toast(`Replay done: ${plural(n, 'run')} of ${bizLabel(cur().r)}.`); return; }
    i++; playT = setTimeout(tick, reduce ? 400 : 1400);
  };
  tick();
}
$('#playBtn').addEventListener('click', play);
$('#qchips').innerHTML = QCHIPS.map((q,k) => `<button class="qchip clay-sm" data-q="${k}">${esc(q)}</button>`).join('');
$('#qchips').addEventListener('click', e => { const b = e.target.closest('[data-q]'); if (b) ask(QCHIPS[+b.dataset.q]); });
$('#askForm').addEventListener('submit', e => { e.preventDefault(); const v = $('#askInput').value.trim(); if (v) { ask(v); $('#askInput').value = ''; } });

/* nav: current section */
const links = [...document.querySelectorAll('.navlinks a')];
const secObs = new IntersectionObserver(es => es.forEach(en => {
  if (en.isIntersecting) links.forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + en.target.id));
}), {rootMargin:'-45% 0px -50% 0px'});
['proof','how','demo','roi','pilot'].forEach(id => secObs.observe(document.getElementById(id)));

/* hero tiles settle, then hover lift takes over */
$('#stack').querySelectorAll('.mcard').forEach(c => c.addEventListener('animationend', () => c.classList.remove('drop'), {once:true}));

/* boot */
renderMonths(); renderLimit(); renderCost(); setStream(true);
const last = LS.get(LKEY, null);
if (last && HISTORY[last]?.runs?.length) { fillForm(HISTORY[last]); openRuns(last, hydrate(HISTORY[last].runs)); }
else renderAll(false);
checkHealth();

/* bento reveal: tiles below the fold start 28px low and settle as they enter. They stay fully visible throughout. */
if (!reduce && 'IntersectionObserver' in window) {
  const io = new IntersectionObserver(es => es.forEach(en => {
    if (en.isIntersecting) { en.target.classList.remove('pre'); io.unobserve(en.target); }
  }), {rootMargin:'0px 0px -6% 0px'});
  document.querySelectorAll('.tile:not(.mcard), .tray').forEach(el => {
    if (el.getBoundingClientRect().top < innerHeight) return;
    const k = [...el.parentElement.children].indexOf(el);
    el.style.transitionDelay = `${(k % 4) * 70}ms`;
    el.classList.add('pre'); io.observe(el);
  });
}
})();
