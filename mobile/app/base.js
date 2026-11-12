// SoundText Mobile: i brani (archivio nel browser, songs.js), il testo
// modificabile e il lettore. Il brano si analizza nel Web Worker (Pyodide +
// st-language + core/), si suona con js-synthesizer (FluidSynth in
// WebAssembly) in un AudioWorklet, con velocita', trasposizione ed
// evidenziazione del testo durante l'ascolto.
"use strict";

const TICKS_PER_BEAT = 480;          // core/midi_export.py
const SOUNDFONT_URL = "vendor/soundfont/TimGM6mb.sf2";
const $ = (id) => document.getElementById(id);
const ms = (t0) => Math.round(performance.now() - t0);

const state = {
  worker: null,
  booted: null,           // Promise del motore pronto
  doc: null,              // brano aperto (vedi "documento")
  song: null,             // ultima analisi: { name, text, info, midi, spans, offsets }
  analyzing: null,
  examples: [],
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
  // lettore completo (tappa 4): restano per il brano aperto, anche dopo una modifica
  timeline: { length: 0, bars: [0] },   // fine del brano e inizio delle battute, in battiti
  muted: new Set(),       // nomi delle tracce in mute
  solo: new Set(),        // nomi delle tracce in solo
  metronome: false,
  loop: { a: null, b: null, on: false },  // in battiti
  midiKey: "",            // la combinazione di trasposizione, mute e metronomo di state.midi
  seeking: false,         // il dito sta trascinando la barra di avanzamento
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
  state.worker.postMessage({ cmd: "boot", language: I18n.language });
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

// Senza rete dopo il primo avvio (criterio della fase 1): FluidSynth per
// l'AudioWorklet, il SoundFont e verovio, che altrimenti si scaricano al
// primo Play e alla prima Partitura, entrano nella cache in background, uno
// alla volta (il service worker li tiene in stmobile-vendor). Non se il
// telefono chiede di risparmiare dati.
const WORKLET_MODULES = ["vendor/js-synthesizer/libfluidsynth-2.4.6.js", "vendor/js-synthesizer/js-synthesizer.worklet.js"];
// js-synthesizer.js lo carica la pagina, ma al primo avvio prima che il
// service worker la controlli: senza questo non sarebbe nella cache.
const OFFLINE_EXTRAS = ["vendor/js-synthesizer/js-synthesizer.js", ...WORKLET_MODULES, SOUNDFONT_URL,
                        "vendor/verovio/verovio-toolkit-wasm.js"];

async function prefetchForOffline() {
  if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return;
  if (navigator.connection && navigator.connection.saveData) return;
  for (const url of OFFLINE_EXTRAS) {
    if (await cached(url)) continue;
    const t0 = performance.now();
    try {
      const resp = await fetch(url);
      await resp.arrayBuffer();
      Metrics.record("offline", { url, ok: resp.ok, ms: ms(t0) });
    } catch (e) {
      Metrics.record("offline", { url, ok: false, error: String(e.message || e) });
    }
  }
}

// ------------------------------------------------------------ documento
//
// state.doc e' il brano aperto: { kind: "song" | "example", id, file, name,
// text, eol, bom }. Gli esempi sono in sola lettura: la prima modifica ne
// crea una copia fra i brani dell'utente. state.song e' l'ultima analisi del
// motore (il testo analizzato e' state.song.text): se il testo cambia, si
// rianalizza al prossimo Play.

// I commenti nella lingua dell'app; le parole del formato (Tempo:,
// Metrica:...) restano quelle del file .st.
const newSongText = () => `// ${t("Nuovo brano: scrivi qui la tua musica.")}
// ${t("Ogni traccia comincia con il suo nome e i due punti; le battute si separano con |")}

ST: 2.6
Tempo: 100 BPM
Metrica: 4/4
Tonalita: C

Piano:
  1: C | F | G7 | C |

Bass:
  4: c*2 e*2 g*2 e*2 | f*2 a*2 c*3 a*2 | g*2 b*2 d*3 b*2 | 4c*2 |
`;

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

function rememberDoc(doc) {
  try {
    localStorage.setItem("stmobile.last", JSON.stringify(doc ? { kind: doc.kind, id: doc.id, file: doc.file } : null));
  } catch (e) {}
}

// Apre un documento: lo mostra subito e lo fa analizzare in background.
function openDoc(doc) {
  stop(true);
  stopVoice();
  state.doc = doc;
  state.song = null;
  state.semitones = 0;
  $("trans").value = 0; $("transOut").value = "0";
  state.muted.clear();
  state.solo.clear();
  state.loop = { a: null, b: null, on: false };
  state.timeline = { length: 0, bars: [0] };
  renderLoop();
  showPosition(0);
  resetScore();
  struct.undo = [];
  showText(doc.text);
  setEditable(true);
  clearCheck();
  scheduleCheck(0);
  showDocTitle();
  rememberDoc(doc);
  renderSongs();
  $("play").disabled = false;
  return analyze().catch(() => {});
}

function showDocTitle() {
  const doc = state.doc;
  $("title").textContent = doc ? doc.name : "SoundText";
  $("nowName").textContent = doc ? doc.name : "–";
  $("badge").hidden = !(doc && doc.kind === "example");
  $("badge").textContent = t("esempio: le modifiche creano una copia");
}

// Analizza il testo attuale, se non e' gia' quello analizzato.
async function analyze() {
  const doc = state.doc;
  if (!doc) return null;
  const text = doc.text;
  if (state.song && state.song.text === text) return state.song;
  if (state.analyzing && state.analyzing.text === text) return state.analyzing.promise;
  const promise = (async () => {
    setStatus(t("Analisi…"));
    await state.booted;
    const t0 = performance.now();
    let r;
    try {
      r = await call("load", { name: doc.name, text });
    } catch (e) {
      if (state.doc === doc && doc.text === text) setStatus(shortError(e), true);
      throw e;
    }
    const roundtrip = ms(t0);
    if (state.doc !== doc || doc.text !== text) return null;      // superata da una modifica
    const song = { name: doc.name, text, info: r.info, midi: r.midi, spans: null, offsets: codepointOffsets(text) };
    state.song = song;
    if (state.previewing) state.savedMidi = r.midi; else state.midi = r.midi;
    state.midiKey = "";
    state.bpm = (r.info.bpm || 120) * state.speed;
    fillFollow(r.info.tracks);
    fillScoreTracks(r.info.tracks);
    setTimeline(r.info.timeline);
    renderMixer();
    // trasposizione, mute, solo e metronomo restano dopo una modifica del testo
    if (midiKey() !== "") await renderMidi();
    const tm = r.timings;
    // roundtrip_ms: dalla richiesta al brano pronto da suonare
    Metrics.record("analisi", {
      song: doc.name, chars: text.length, tracks: r.info.tracks.length,
      parse_ms: Math.round(tm.parse_s * 1000), midi_ms: Math.round(tm.midi_s * 1000),
      worker_total_ms: tm.total_ms, roundtrip_ms: roundtrip,
    });
    setStatus(t("Tracce: {n}, pronto in {ms} ms", { n: r.info.tracks.length, ms: roundtrip }));
    if (document.body.classList.contains("view-partitura")) setTimeout(() => showScore().catch(showError), 0);
    // La mappa per l'evidenziazione arriva dopo: si puo' gia' suonare.
    song.spansReady = call("spans").then((m) => {
      if (state.song !== song) return;
      song.spans = m.spans;
      lastKey = "";
      Metrics.record("mappa", { song: doc.name, spans: m.spans.length / 6, ms: m.ms });
      measureMemory("dopo l'analisi di " + doc.name);
    }).catch(() => {});
    return song;
  })();
  state.analyzing = { text, promise };
  try {
    return await promise;
  } finally {
    if (state.analyzing && state.analyzing.promise === promise) state.analyzing = null;
  }
}

// Il messaggio di un errore di notazione, senza il traceback di Python.
function errorText(e) {
  const lines = String(e && e.message || e).trim().split("\n").filter(Boolean);
  return (lines[lines.length - 1] || t("sconosciuto")).replace(/^[\w.]*(Error|Exception): /, "");
}

function shortError(e) {
  return t("Errore: {message}", { message: errorText(e) });
}

function showText(text) {
  const pre = $("text");
  pre.textContent = text;
  pre.scrollTop = 0;
  clearHighlight();
}

function fillFollow(tracks) {
  const sel = $("follow");
  const previous = sel.value;
  sel.innerHTML = "";
  tracks.forEach((tr, i) => sel.add(new Option(tr.name, String(i))));
  const melodic = tracks.findIndex((tr) => !tr.percussion);
  sel.value = previous && Number(previous) < tracks.length ? previous : String(Math.max(0, melodic));
}
