// Prototipo SoundText Mobile (fase 0): apre un esempio, lo analizza nel
// Web Worker (Pyodide + st-language + core/), lo suona con js-synthesizer
// (FluidSynth in WebAssembly) in un AudioWorklet, ne cambia velocita' e
// trasposizione ed evidenzia il testo durante l'ascolto.
"use strict";

const TICKS_PER_BEAT = 480;          // core/midi_export.py
const SOUNDFONT_URL = "vendor/soundfont/TimGM6mb.sf2";
const $ = (id) => document.getElementById(id);
const ms = (t0) => Math.round(performance.now() - t0);

const state = {
  worker: null,
  booted: null,           // Promise del motore pronto
  song: null,             // { name, text, info, midi, spans, offsets }
  ctx: null,
  synth: null,
  audioReady: null,       // Promise
  playing: false,
  playToken: 0,
  speed: 1,
  semitones: 0,
  midi: null,             // MIDI che il player sta suonando (trasposto)
  pausedTick: 0,
  bpm: 120,
  lastTick: 0,
};

// ------------------------------------------------------------ worker

let nextId = 1;
const pending = new Map();

function call(cmd, data = {}) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    state.worker.postMessage({ cmd, id, ...data });
  });
}

function startWorker() {
  state.worker = new Worker("worker.js", { type: "module" });
  state.booted = new Promise((resolve, reject) => {
    state.worker.onmessage = (ev) => {
      const msg = ev.data;
      if (msg.type === "booted") return resolve(msg.timings);
      if (msg.type === "numpy") return void Metrics.record("numpy", { background_ms: msg.ms });
      const p = pending.get(msg.id);
      if (msg.type === "error") {
        if (p) { pending.delete(msg.id); p.reject(new Error(msg.message)); }
        else reject(new Error(msg.message));
        return;
      }
      if (p) { pending.delete(msg.id); p.resolve(msg); }
    };
    state.worker.onerror = (e) => reject(new Error(e.message));
  });
  state.worker.postMessage({ cmd: "boot" });
}

// ------------------------------------------------------------ service worker

async function serviceWorker() {
  if (!("serviceWorker" in navigator)) return false;
  try {
    await navigator.serviceWorker.register("sw.js");
    if (!navigator.serviceWorker.controller) {
      // Primo avvio: si aspetta che il service worker prenda la pagina,
      // cosi' Pyodide e il resto passano gia' dalla sua cache.
      await Promise.race([
        new Promise((r) => navigator.serviceWorker.addEventListener("controllerchange", r, { once: true })),
        new Promise((r) => setTimeout(r, 4000)),
      ]);
    }
    return !!navigator.serviceWorker.controller;
  } catch (e) {
    console.warn("service worker non registrato", e);
    return false;
  }
}

async function cached(url) {
  try {
    return !!(self.caches && await caches.match(new URL(url, location).href));
  } catch (e) {
    return false;
  }
}

// ------------------------------------------------------------ brano

function codepointOffsets(text) {
  // Python conta i code point, JavaScript le unita' UTF-16: servono solo
  // se il testo ha caratteri fuori dal piano di base (emoji, ...).
  if (!/[\uD800-\uDFFF]/.test(text)) return null;
  const map = [];
  let u = 0;
  for (const ch of text) { map.push(u); u += ch.length; }
  map.push(u);
  return map;
}

async function openSong(name, text) {
  stop(true);
  setStatus(`Analisi di ${name}…`);
  $("play").disabled = true;
  await state.booted;
  const t0 = performance.now();
  const r = await call("load", { name, text });
  const roundtrip = ms(t0);
  const song = { name, text, info: r.info, midi: r.midi, spans: null, offsets: codepointOffsets(text) };
  state.song = song;
  state.semitones = 0;
  $("trans").value = 0; $("transOut").value = "0";
  state.midi = r.midi;
  state.pausedTick = 0;
  state.bpm = (r.info.bpm || 120) * state.speed;
  showText(text);
  fillFollow(r.info.tracks);
  const t = r.timings;
  // roundtrip_ms: dalla richiesta al brano pronto da suonare
  Metrics.record("analisi", {
    song: name, chars: text.length, tracks: r.info.tracks.length,
    parse_ms: Math.round(t.parse_s * 1000), midi_ms: Math.round(t.midi_s * 1000),
    worker_total_ms: t.total_ms, roundtrip_ms: roundtrip,
  });
  setStatus(`${name}: ${r.info.tracks.length} tracce, pronto in ${roundtrip} ms`);
  $("play").disabled = false;
  // La mappa per l'evidenziazione arriva dopo: si puo' gia' suonare.
  song.spansReady = call("spans").then((m) => {
    if (state.song !== song) return;
    song.spans = m.spans;
    lastKey = "";
    Metrics.record("mappa", { song: name, spans: m.spans.length / 6, ms: m.ms });
    measureMemory("dopo l'analisi di " + name);
  });
}

function showText(text) {
  const pre = $("text");
  pre.textContent = text;
  pre.scrollTop = 0;
  clearHighlight();
}

function fillFollow(tracks) {
  const sel = $("follow");
  sel.innerHTML = "";
  tracks.forEach((t, i) => sel.add(new Option(t.name, String(i))));
  const melodic = tracks.findIndex((t) => !t.percussion);
  sel.value = String(Math.max(0, melodic));
}

// ------------------------------------------------------------ audio

function unlockInGesture() {
  // Tutto cio' che iOS vuole dentro il gestore del tocco, senza await prima.
  if ($("audioSession").checked && navigator.audioSession) {
    try { navigator.audioSession.type = "playback"; } catch (e) {}
  }
  if (!state.ctx) {
    state.ctx = new (window.AudioContext || window.webkitAudioContext)({ latencyHint: "playback" });
  }
  const resumed = state.ctx.resume();
  if ($("unlockAudio").checked && !state.silentAudio) {
    // Un elemento <audio> che suona in loop un silenzio: su iPhone porta la
    // sessione audio in "riproduzione", che non rispetta l'interruttore
    // silenzioso (da verificare nelle prove).
    const a = new Audio(silentWavUrl());
    a.loop = true;
    a.setAttribute("playsinline", "");
    a.play().catch(() => {});
    state.silentAudio = a;
  }
  return resumed;
}

function silentWavUrl() {
  const rate = 8000, n = rate / 2;
  const buf = new ArrayBuffer(44 + n * 2);
  const v = new DataView(buf);
  const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + n * 2, true); w(8, "WAVEfmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
  v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, n * 2, true);
  return URL.createObjectURL(new Blob([buf], { type: "audio/wav" }));
}

async function initAudio() {
  const ctx = state.ctx;
  const t0 = performance.now();
  await ctx.audioWorklet.addModule("vendor/js-synthesizer/libfluidsynth-2.4.6.js");
  await ctx.audioWorklet.addModule("vendor/js-synthesizer/js-synthesizer.worklet.js");
  const synth = new JSSynth.AudioWorkletNodeSynthesizer();
  synth.init(ctx.sampleRate, { midiChannelCount: 32 });
  const node = synth.createAudioNode(ctx, { outputChannelCount: [2] });
  node.connect(ctx.destination);
  const worklet_ms = ms(t0);

  const t1 = performance.now();
  const sfCached = await cached(SOUNDFONT_URL);
  const resp = await fetch(SOUNDFONT_URL);
  if (!resp.ok) throw new Error(`SoundFont non trovato (${resp.status})`);
  const sf = await resp.arrayBuffer();
  const download_ms = ms(t1);
  const t2 = performance.now();
  await synth.loadSFont(sf);
  const sfload_ms = ms(t2);
  state.synth = synth;
  Metrics.record("audio", {
    worklet_ms, soundfont_cached: sfCached, soundfont_bytes: sf.byteLength, soundfont_fetch_ms: download_ms,
    soundfont_load_ms: sfload_ms, sample_rate: ctx.sampleRate,
    base_latency_ms: Math.round((ctx.baseLatency || 0) * 1000),
    output_latency_ms: Math.round((ctx.outputLatency || 0) * 1000),
  });
}

async function startPlayer(fromTick) {
  const synth = state.synth;
  const token = ++state.playToken;
  await synth.resetPlayer();
  await synth.addSMFDataToPlayer(state.midi.slice().buffer);
  synth.setPlayerTempo(0, state.speed);   // 0 = PlayerSetTempoType.Internal: moltiplicatore del tempo del file
  if (fromTick > 0) synth.seekPlayer(fromTick);
  await synth.playPlayer();
  state.playing = true;
  setPlayButton();
  synth.waitForPlayerStopped().then(() => {
    if (token !== state.playToken) return;
    state.playing = false;
    state.pausedTick = 0;
    setPlayButton();
    clearHighlight();
    setStatus("Fine del brano");
  });
}

async function play() {
  // Primo tocco: niente await prima di unlockInGesture (iOS).
  const tTap = performance.now();
  const resumed = unlockInGesture();
  if (state.playing) return pause();
  try {
    await resumed;
    if (!state.audioReady) {
      setStatus("Preparo il sintetizzatore e il SoundFont…");
      state.audioReady = initAudio();
    }
    await state.audioReady;
    await startPlayer(state.pausedTick);
    const first = !state.firstPlayDone;
    state.firstPlayDone = true;
    Metrics.record("play", { first, tap_to_play_ms: ms(tTap), ctx_state: state.ctx.state, song: state.song.name });
    setStatus(`Suona ${state.song.name}`);
    batteryProbe();
    requestAnimationFrame(frame);
  } catch (e) {
    state.audioReady = null;
    setStatus("Errore audio: " + e.message);
    console.error(e);
  }
}

async function pause() {
  if (!state.synth) return;
  state.playToken++;
  state.pausedTick = await state.synth.retrievePlayerCurrentTick();
  state.synth.stopPlayer();
  state.synth.midiAllSoundsOff();
  state.playing = false;
  setPlayButton();
  setStatus("In pausa");
}

function stop(reset) {
  if (state.synth && state.playing) {
    state.playToken++;
    state.synth.stopPlayer();
    state.synth.midiAllSoundsOff();
  }
  state.playing = false;
  if (reset) state.pausedTick = 0;
  setPlayButton();
  clearHighlight();
}

function setPlayButton() {
  const b = $("play");
  b.textContent = state.playing ? "❚❚" : "▶";
  b.setAttribute("aria-label", state.playing ? "Pausa" : "Suona");
}

async function setTranspose(semitones) {
  state.semitones = semitones;
  $("transOut").value = (semitones > 0 ? "+" : "") + semitones;
  if (!state.song) return;
  const r = await call("transpose", { semitones });
  if (r.semitones !== state.semitones) return;   // superata da un'altra modifica
  state.midi = r.midi;
  Metrics.record("trasposizione", { semitones, ms: r.ms });
  if (state.playing) {
    const tick = await state.synth.retrievePlayerCurrentTick();
    state.synth.midiAllSoundsOff();
    await startPlayer(tick);
  }
}

function setSpeed(percent) {
  state.speed = percent / 100;
  $("speedOut").value = percent + "%";
  if (state.synth) state.synth.setPlayerTempo(0, state.speed);
}

// ------------------------------------------------------------ evidenziazione

const highlightApi = !!(window.CSS && CSS.highlights && window.Highlight);
let lastKey = "";
let lastFollow = -1;
let pollBusy = false;
let lastBpmPoll = 0;

function clearHighlight() {
  if (highlightApi) { CSS.highlights.delete("st-note"); CSS.highlights.delete("st-box"); }
  lastKey = "";
}

function rangeFor(node, cs, ce) {
  const off = state.song.offsets;
  const r = new Range();
  r.setStart(node, off ? off[cs] : cs);
  r.setEnd(node, off ? off[ce] : ce);
  return r;
}

async function frame() {
  if (!state.playing) return;
  requestAnimationFrame(frame);
  if (pollBusy) return;
  pollBusy = true;
  try {
    const tick = await state.synth.retrievePlayerCurrentTick();
    const now = performance.now();
    if (now - lastBpmPoll > 1000) {
      lastBpmPoll = now;
      state.synth.retrievePlayerBpm().then((b) => { if (b > 0) state.bpm = b; });
    }
    // Il player e' avanti rispetto a cio' che si sente della latenza d'uscita;
    // retrievePlayerBpm e' gia' il tempo effettivo (con la velocita').
    const ctx = state.ctx;
    const latency = (ctx.outputLatency || 0) + (ctx.baseLatency || 0);
    const beat = tick / TICKS_PER_BEAT - latency * state.bpm / 60;
    state.lastTick = tick;
    highlightAt(beat);
    $("pos").textContent = `battito ${Math.max(0, beat).toFixed(1)} · ${Math.round(state.bpm)} BPM`;
  } catch (e) {
    console.warn(e);
  } finally {
    pollBusy = false;
  }
}

function highlightAt(beat) {
  const s = state.song.spans;
  if (!s) return;                       // mappa non ancora pronta           // 6 numeri per span: traccia, cs, ce, b0, durata, livello
  const deepest = new Map();            // traccia -> indice dello span piu' profondo attivo
  const boxes = [];
  for (let i = 0; i < s.length; i += 6) {
    const b0 = s[i + 3];
    if (b0 > beat) continue;
    if (beat >= b0 + s[i + 4]) continue;
    const tr = s[i];
    const prev = deepest.get(tr);
    if (prev === undefined || s[i + 5] > s[prev + 5]) {
      if (prev !== undefined) boxes.push(prev);
      deepest.set(tr, i);
    } else {
      boxes.push(i);
    }
  }
  const notes = [...deepest.values()];
  const key = notes.join(",") + "|" + boxes.join(",");
  if (key === lastKey) return;
  lastKey = key;
  const node = $("text").firstChild;
  if (!node) return;
  if (highlightApi) {
    CSS.highlights.set("st-box", new Highlight(...boxes.map((i) => rangeFor(node, s[i + 1], s[i + 2]))));
    CSS.highlights.set("st-note", new Highlight(...notes.map((i) => rangeFor(node, s[i + 1], s[i + 2]))));
  }
  const follow = Number($("follow").value);
  const fi = deepest.get(follow);
  if (fi !== undefined && fi !== lastFollow) {
    lastFollow = fi;
    scrollToRange(rangeFor(node, s[fi + 1], s[fi + 2]));
    if (!highlightApi) setStatus("Suona: " + state.song.text.slice(s[fi + 1], s[fi + 2]));
  }
}

function scrollToRange(range) {
  const pre = $("text");
  const r = range.getBoundingClientRect();
  const box = pre.getBoundingClientRect();
  if (r.top < box.top + 8 || r.bottom > box.bottom - 8) {
    pre.scrollTop += r.top - box.top - box.height / 3;
  }
  if (r.left < box.left || r.right > box.right) {
    pre.scrollLeft += r.left - box.left - 40;
  }
}

// ------------------------------------------------------------ memoria e batteria

async function measureMemory(when) {
  try {
    const page = await Metrics.pageMemory();
    const w = await call("memory");
    Metrics.record("memoria", { when_label: when, pyodide_heap_bytes: w.heap_bytes, ...page });
  } catch (e) {
    console.warn("memoria", e);
  }
}

async function batteryProbe() {
  if (state.batteryTimer || !navigator.getBattery) return;
  try {
    const battery = await navigator.getBattery();
    const start = { level: battery.level, t: Date.now() };
    Metrics.record("batteria", { minute: 0, level: battery.level, charging: battery.charging });
    state.batteryTimer = setInterval(() => {
      if (!state.playing) return;
      const minute = Math.round((Date.now() - start.t) / 60000);
      Metrics.record("batteria", { minute, level: battery.level, charging: battery.charging,
                                    drop_percent: Math.round((start.level - battery.level) * 100) });
      if (minute >= 10) measureMemory("dopo 10 minuti di ascolto");
    }, 60000);
  } catch (e) { /* non disponibile (Safari, Firefox) */ }
}

// ------------------------------------------------------------ avvio

function setStatus(text) {
  $("status").textContent = text;
}

async function loadExample(name) {
  const text = await (await fetch("bundle/examples/" + encodeURIComponent(name))).text();
  await openSong(name, text);
}

async function main() {
  const tPage = performance.now();
  const startedHidden = document.visibilityState === "hidden";
  if (!window.isSecureContext) {
    // http:// fuori da localhost: niente service worker ne' AudioWorklet
    const warn = document.createElement("p");
    warn.id = "insecure";
    warn.textContent = "Pagina non sicura: il testo si apre, ma l'audio e l'uso offline non funzionano. " +
      "Usa HTTPS, http://localhost, o in Chrome per Android il flag " +
      "chrome://flags/#unsafely-treat-insecure-origin-as-secure con " + location.origin + ".";
    warn.style.cssText = "margin:4px 16px;padding:8px;border-radius:6px;background:#7a2e00;color:#fff;font-size:13px";
    $("status").before(warn);
  }
  const sw = await serviceWorker();
  const coldCache = !(await cached("vendor/pyodide/pyodide.asm.wasm"));
  startWorker();
  const files = await (await fetch("bundle/files.json")).json();
  const sel = $("song");
  files.examples.forEach((n) => sel.add(new Option(n.replace(/\.st$/, ""), n)));
  sel.onchange = () => loadExample(sel.value).catch(showError);
  $("file").onchange = async (ev) => {
    const f = ev.target.files[0];
    if (f) openSong(f.name, await f.text()).catch(showError);
  };
  $("play").onclick = () => play();
  $("speed").oninput = (ev) => setSpeed(Number(ev.target.value));
  $("trans").onchange = (ev) => setTranspose(Number(ev.target.value)).catch(showError);
  $("trans").oninput = (ev) => { $("transOut").value = ev.target.value; };
  $("follow").onchange = () => { lastFollow = -1; };
  // Schermo bloccato, app in background: il tick si chiede al player (non
  // quello dell'ultimo fotogramma, che in background non si aggiorna), cosi'
  // fra "hidden" e "visible" si vede se la musica e' andata avanti.
  const lifecycle = async (event) => {
    let tick = null;
    try { if (state.synth) tick = await state.synth.retrievePlayerCurrentTick(); } catch (e) {}
    Metrics.record("visibilita", { event, state: document.visibilityState, playing: state.playing,
                                   ctx_state: state.ctx ? state.ctx.state : null, tick });
  };
  document.addEventListener("visibilitychange", () => lifecycle("visibilitychange"));
  // Chrome: pagina congelata o ripresa (risparmio energetico, scheda in background)
  document.addEventListener("freeze", () => lifecycle("freeze"));
  document.addEventListener("resume", () => lifecycle("resume"));

  try {
    const t = await state.booted;
    Metrics.record("avvio", {
      cache: coldCache ? "senza cache (primo avvio)" : "con cache", service_worker: sw,
      page_to_ready_ms: ms(tPage), ...t, ...Metrics.device(),
      // scheda ricaricata dal browser dopo averla scaricata in background
      discarded: document.wasDiscarded === true, started_hidden: startedHidden,
    });
    setStatus(`Motore pronto in ${(t.total_ms / 1000).toFixed(1)} s (${t.versions})`);
    await loadExample(files.examples[0]);
    if (new URLSearchParams(location.search).has("misura")) await automaticMeasure();
  } catch (e) {
    showError(e);
  }
}

// ?misura=1: analizza i due esempi della fase 0 e manda le misure con un
// POST a "misure" (il server di prova in mobile/misura_headless.py).
async function automaticMeasure() {
  await state.song.spansReady;
  for (const name of ["symphony_d_minor_box.st", "jazz_aaba.st", "symphony_d_minor_box.st"]) {
    await loadExample(name);
    await state.song.spansReady;
  }
  await measureMemory("fine della misura automatica");
  await fetch("misure", { method: "POST", body: JSON.stringify(Metrics.all()) }).catch(() => {});
}

function showError(e) {
  console.error(e);
  setStatus("Errore: " + (e && e.message || e));
}

main();
