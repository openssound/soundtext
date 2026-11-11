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

// ------------------------------------------------------------ editor

const editor = {
  plaintextOnly: false,
  saveTimer: null,
};

function setupEditor() {
  const pre = $("text");
  pre.contentEditable = "plaintext-only";
  editor.plaintextOnly = pre.contentEditable === "plaintext-only";
  pre.addEventListener("input", onEdit);
  setEditable(false);
}

// Senza un brano aperto il testo non si modifica (e dice cosa fare, vedi style.css).
function setEditable(on) {
  const pre = $("text");
  showMusicBar(on);
  pre.contentEditable = on ? (editor.plaintextOnly ? "plaintext-only" : "true") : "false";
  pre.classList.toggle("empty", !on);
}

function editorText() {
  const pre = $("text");
  return editor.plaintextOnly ? pre.textContent : pre.innerText;
}

async function onEdit() {
  const doc = state.doc;
  if (!doc) return;
  doc.text = editorText();
  clearHighlight();
  scheduleCheck();
  if (doc.kind === "example" && !doc.copying) {
    // prima modifica di un esempio: diventa un brano dell'utente
    doc.copying = true;
    const name = await Songs.freeName(doc.name);
    const song = await Songs.create({ name, text: doc.text, eol: doc.eol, bom: doc.bom, source: "esempio " + doc.file });
    Object.assign(doc, { kind: "song", id: song.id, name, copying: false });
    showDocTitle();
    rememberDoc(doc);
    renderSongs();
    setStatus(t("Copia salvata fra i tuoi brani"));
  }
  clearTimeout(editor.saveTimer);
  editor.saveTimer = setTimeout(saveDoc, 600);
}

async function saveDoc() {
  const doc = state.doc;
  if (!doc || doc.kind !== "song") return;
  const song = await Songs.get(doc.id);
  if (!song) return;
  song.text = doc.text;
  await Songs.put(song);
}

// Prima di suonare: il testo dell'editor in un solo nodo, per le Range
// dell'evidenziazione.
function normalizeEditor() {
  const pre = $("text");
  if (pre.childNodes.length !== 1 || pre.firstChild.nodeType !== Node.TEXT_NODE) {
    const top = pre.scrollTop;
    pre.textContent = state.doc.text;
    pre.scrollTop = top;
  }
}

// Il brano con un testo nuovo fatto dall'app (Crea, Struttura): come una
// modifica scritta a mano (salvataggio, controlli, copia di un esempio).
async function replaceDocText(text) {
  const pre = $("text");
  const top = pre.scrollTop;
  pre.textContent = text;
  pre.scrollTop = top;
  await onEdit();
}

// ------------------------------------------------------------ controlli del testo
//
// Colori della sintassi, avvisi e blocchi (engine.check_text nel worker),
// chiesti all'apertura e poco dopo l'ultima modifica. Un risultato per un
// testo che nel frattempo e' cambiato si scarta.

const checks = { timer: null, running: false, again: false, last: null, ranges: [] };
const CHECK_DELAY_MS = 700;

function scheduleCheck(delay = CHECK_DELAY_MS) {
  clearTimeout(checks.timer);
  checks.timer = setTimeout(runCheck, delay);
}

async function runCheck() {
  if (!state.doc) return;
  if (checks.running) { checks.again = true; return; }
  checks.running = true;
  const doc = state.doc;
  const text = doc.text;
  try {
    await state.booted;
    const r = await call("check", { text });
    if (state.doc === doc && doc.text === text) {
      checks.last = { text, ...r.result };
      applyCheck();
      Metrics.record("controllo", { song: doc.name, ms: r.ms, warnings: r.result.warnings.length });
    }
  } catch (e) {
    console.warn("controllo del testo", e);
  } finally {
    checks.running = false;
    if (checks.again) { checks.again = false; scheduleCheck(0); }
  }
}

function clearCheck() {
  checks.last = null;
  if (highlightApi) {
    for (const name of [...CSS.highlights.keys()]) {
      if (name.startsWith("syn-") || name.startsWith("voice-") || name === "warn") CSS.highlights.delete(name);
    }
  }
  renderWarnings([]);
  renderBlocks([]);
}

function applyCheck() {
  const c = checks.last;
  if (!c || !state.doc || state.doc.text !== c.text) return;
  renderWarnings(c.warnings);
  renderBlocks(c.blocks);
  if (!highlightApi) return;
  const pre = $("text");
  if (pre.childNodes.length > 1) pre.normalize();
  const node = pre.firstChild;
  if (!node || node.nodeType !== Node.TEXT_NODE || node.data !== c.text) return;
  const off = codepointOffsets(c.text);
  const range = (s, e) => {
    const r = new Range();
    r.setStart(node, off ? off[s] : s);
    r.setEnd(node, off ? off[e] : e);
    return r;
  };
  const byCategory = new Map();
  for (let i = 0; i < c.syntax.length; i += 3) {
    const name = c.categories[c.syntax[i + 2]];
    if (!byCategory.has(name)) byCategory.set(name, []);
    byCategory.get(name).push(range(c.syntax[i], c.syntax[i] + c.syntax[i + 1]));
  }
  for (const name of [...CSS.highlights.keys()]) {
    if (name.startsWith("syn-") || name.startsWith("voice-") || name === "warn") CSS.highlights.delete(name);
  }
  for (const [name, ranges] of byCategory) CSS.highlights.set("syn-" + name, new Highlight(...ranges));
  const voices = [[], [], [], []];
  for (let i = 0; i < c.voices.length; i += 3) {
    voices[c.voices[i + 2]].push(range(c.voices[i], c.voices[i] + c.voices[i + 1]));
  }
  voices.forEach((ranges, i) => {
    if (ranges.length) {
      const h = new Highlight(...ranges);
      h.priority = -1;
      CSS.highlights.set("voice-" + i, h);
    }
  });
  // gli avvisi senza un token colorato (intestazioni, errori di un blocco)
  // le parti che l'app non suona hanno un avviso nell'elenco, non una sottolineatura
  const warn = new Highlight(...c.warnings.filter((w) => w.end > w.start && w.kind !== "unsupported")
    .map((w) => range(w.start, w.end)));
  warn.priority = 1;
  CSS.highlights.set("warn", warn);
}

function lineOf(text, pos) {
  let line = 1;
  for (let i = text.indexOf("\n"); i >= 0 && i < pos; i = text.indexOf("\n", i + 1)) line++;
  return line;
}

function renderWarnings(warnings) {
  const button = $("warnButton");
  const list = $("warnings");
  button.hidden = warnings.length === 0;
  $("warnCount").textContent = warnings.length;
  button.setAttribute("aria-label", t("Avvisi nel testo: {n}", { n: warnings.length }));
  if (!warnings.length) {
    list.hidden = true;
    button.setAttribute("aria-expanded", "false");
  }
  list.innerHTML = "";
  const text = state.doc ? state.doc.text : "";
  for (const w of warnings) {
    const li = document.createElement("li");
    li.className = w.kind;
    const b = document.createElement("button");
    const where = document.createElement("span");
    where.className = "where";
    where.textContent = t("riga {n}", { n: lineOf(text, w.start) });
    b.append(where, w.message);
    b.onclick = () => goTo(w.start, w.end);
    li.append(b);
    list.append(li);
  }
  setWarningStatus(warnings);
}

function setWarningStatus(warnings) {
  if (state.playing) return;
  const status = $("status");
  if (status.classList.contains("error")) return;
  if (warnings.length) setStatus(t("Avvisi nel testo: {n}", { n: warnings.length }));
}

function renderBlocks(blocks) {
  const sel = $("goto");
  sel.innerHTML = "";
  sel.add(new Option(t("Vai a…"), ""));
  const groups = { track: t("Tracce"), box: t("Box"), pattern: t("Pattern") };
  for (const [kind, label] of Object.entries(groups)) {
    const items = blocks.filter((b) => b.kind === kind);
    if (!items.length) continue;
    const og = document.createElement("optgroup");
    og.label = label;
    for (const b of items) og.append(new Option(b.label, String(b.start)));
    sel.append(og);
  }
}

// Porta il cursore (e la vista) a una posizione del testo.
function goTo(start, end = start) {
  const pre = $("text");
  const node = pre.firstChild;
  if (!node || node.nodeType !== Node.TEXT_NODE) return;
  const off = codepointOffsets(state.doc.text);
  const r = new Range();
  r.setStart(node, off ? off[start] : start);
  r.setEnd(node, off ? off[end] : end);
  setView("testo");
  scrollToRange(r, true);
  const sel = getSelection();
  sel.removeAllRanges();
  r.collapse(true);
  sel.addRange(r);
}

// ------------------------------------------------------------ barra musicale
//
// Una riga di tasti sopra la tastiera del telefono, in tre pagine (note;
// durate e struttura; accordi della tonalita', pattern e funzioni), con i
// suggerimenti di core.completion e "▶ battuta". I tasti scrivono con
// document.execCommand("insertText"), come la tastiera: l'annulla del
// telefono e il salvataggio (evento input) funzionano come per il testo
// scritto a mano.

const bar = { page: 0, transforms: [], suggestTimer: null, suggestFor: null, playing: false };

function textNode() {
  const pre = $("text");
  if (pre.childNodes.length > 1) pre.normalize();
  return pre.firstChild && pre.firstChild.nodeType === Node.TEXT_NODE ? pre.firstChild : null;
}

// Posizione del cursore nel testo (null se il cursore non e' nell'editor)
function caretPos() {
  const sel = getSelection();
  const node = textNode();
  if (!sel.rangeCount || !node) return $("text").contains(sel.anchorNode) ? 0 : null;
  const r = sel.getRangeAt(0);
  if (r.endContainer === node) return r.endOffset;
  if (r.endContainer === $("text")) return r.endOffset === 0 ? 0 : node.data.length;
  return null;
}

function selectRange(start, end) {
  const node = textNode();
  if (!node) return false;
  const r = new Range();
  r.setStart(node, Math.min(start, node.data.length));
  r.setEnd(node, Math.min(end, node.data.length));
  const sel = getSelection();
  sel.removeAllRanges();
  sel.addRange(r);
  return true;
}

function typeText(s) {
  $("text").focus({ preventScroll: true });
  document.execCommand("insertText", false, s);
}

// La parola prima del cursore (fino allo spazio)
function wordBefore(text, pos) {
  let i = pos;
  while (i > 0 && !/\s/.test(text[i - 1])) i--;
  return text.slice(i, pos);
}

function needsSpaceBefore(text, pos) {
  if (pos === 0) return false;
  const prev = text[pos - 1];
  if (/\s/.test(prev) || prev === "(" || prev === "[") return false;
  return !/^\d+$/.test(wordBefore(text, pos));   // "2" + "c" = "2c": un moltiplicatore
}

// Un token nuovo, con lo spazio prima (se serve) e dopo.
function insertToken(tok, trailing = true) {
  if (!state.doc) return;
  const pos = caretPos() ?? state.doc.text.length;
  const text = state.doc.text;
  const after = text[pos];
  typeText((needsSpaceBefore(text, pos) ? " " : "") + tok + (trailing && !(after && /\s/.test(after)) ? " " : ""));
}

// Un pezzo che si attacca al token precedente: alterazioni, ottava, ")".
function attach(suffix) {
  if (!state.doc) return;
  const pos = caretPos() ?? state.doc.text.length;
  const text = state.doc.text;
  if (pos > 0 && text[pos - 1] === " " && pos > 1 && !/\s/.test(text[pos - 2])) {
    selectRange(pos - 1, pos);
    typeText(suffix + " ");
  } else {
    typeText(suffix + (text[pos] && /\s/.test(text[pos]) ? "" : " "));
  }
}

// Cancella il token prima del cursore (con lo spazio che lo segue).
function deleteToken() {
  if (!state.doc) return;
  const pos = caretPos() ?? state.doc.text.length;
  const text = state.doc.text;
  let start = pos;
  while (start > 0 && text[start - 1] === " ") start--;
  while (start > 0 && !/\s/.test(text[start - 1])) start--;
  if (start === pos) return;
  selectRange(start, pos);
  $("text").focus({ preventScroll: true });
  document.execCommand("delete");
}

// ---- tonalita' e accordi

const SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const FLAT_KEYS = new Set(["F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm", "Abm"]);

// La tonalita' in vigore al cursore: l'ultimo key= prima, altrimenti Tonalita:
function keyAt(text, pos) {
  const before = text.slice(0, pos);
  const keys = [...before.matchAll(/(?:^|\s)key=([A-G][#b]?m?)\b/g)];
  if (keys.length) return keys[keys.length - 1][1];
  const head = text.match(/^(?:Tonalita|Tonalità|Key):\s*([A-G][#b]?m?)\b/m);
  return head ? head[1] : "C";
}

// Gli accordi della scala (triadi, piu' la dominante con la settima)
function diatonicChords(key) {
  const minor = key.endsWith("m");
  const tonic = minor ? key.slice(0, -1) : key;
  let root = PC[tonic[0]] + (tonic[1] === "#" ? 1 : tonic[1] === "b" ? -1 : 0);
  root = (root + 12) % 12;
  const names = FLAT_KEYS.has(key) ? FLATS : SHARPS;
  const steps = minor ? [0, 2, 3, 5, 7, 8, 10] : [0, 2, 4, 5, 7, 9, 11];
  const qualities = minor ? ["m", "dim", "", "m", "m", "", ""] : ["", "m", "m", "", "", "m", "dim"];
  const chords = steps.map((s, i) => names[(root + s) % 12] + qualities[i]);
  chords.push(names[(root + 7) % 12] + "7");
  return chords;
}

// ---- tasti

function K(label, run, cls = "", aria = "") {
  return { label, run, cls, aria };
}
const SEP = { sep: true };

function pageKeys(page) {
  const common = [SEP, K("⌫", deleteToken, "wide", t("Cancella il token")),
                  K("▶ " + t("battuta"), playBarAtCaret, "wide play-bar", t("Suona la battuta del cursore"))];
  if (page === 0) {
    return [
      ..."cdefgab".split("").map((n) => K(n, () => insertToken(n), "", t("nota {n}", { n: n.toUpperCase() }))),
      K("r", () => insertToken("r"), "", t("pausa")),
      SEP,
      K("#", () => attach("#"), "", t("diesis")), K("♭", () => attach("b"), "", t("bemolle")),
      ...[3, 4, 5, 6].map((o) => K("*" + o, () => attach("*" + o), "", t("ottava {n}", { n: o }))),
      K("~", () => attach("~"), "", t("legatura")),
      ...common,
    ];
  }
  if (page === 1) {
    return [
      ...[["1:", t("semibreve")], ["2:", t("minima")], ["4:", t("semiminima")], ["8:", t("croma")],
          ["16:", t("semicroma")], ["8T:", t("terzina di crome")]].map(([g, name]) => K(g, () => insertToken(g), "", name)),
      SEP,
      ...["2", "3", "4"].map((m) => K(m, () => insertToken(m, false), "", t("moltiplicatore {n}", { n: m }))),
      SEP,
      K("|", () => insertToken("|"), "", t("stanghetta")),
      K("(", () => insertToken("(", false), "", t("apri gruppo")), K(")", () => attach(")"), "", t("chiudi gruppo")),
      K("[", () => insertToken("[", false), "", t("apri blocco")), K("]", () => attach("]"), "", t("chiudi blocco")),
      ...common,
    ];
  }
  const text = state.doc ? state.doc.text : "";
  const pos = caretPos() ?? text.length;
  const patterns = (checks.last ? checks.last.blocks : []).filter((b) => b.kind === "pattern").map((b) => b.label);
  return [
    ...diatonicChords(keyAt(text, pos)).map((c) => K(c, () => insertToken(c), "", t("accordo {name}", { name: c }))),
    SEP,
    K("✦ " + t("Trasforma"), openTransform, "wide", t("Trasforma il richiamo di pattern sotto il cursore")),
    ...patterns.map((p) => K(p, () => insertToken(p), "", t("pattern {name}", { name: p }))),
    ...(patterns.length ? [SEP] : []),
    ...bar.transforms.map((f) => K(f.call, () => attach(f.call), "", f.help)),
    ...common,
  ];
}

function renderKeys() {
  const box = $("keys");
  box.innerHTML = "";
  for (const k of pageKeys(bar.page)) {
    if (k.sep) {
      const s = document.createElement("span");
      s.className = "sep";
      box.append(s);
      continue;
    }
    const b = document.createElement("button");
    b.textContent = k.label;
    if (k.cls) b.className = k.cls;
    if (k.aria) { b.title = k.aria; b.setAttribute("aria-label", k.aria); }
    b.onclick = () => Promise.resolve(k.run()).catch(showError);
    box.append(b);
  }
}

function setPage(page) {
  bar.page = page;
  for (const b of document.querySelectorAll(".pages button")) {
    b.setAttribute("aria-selected", String(Number(b.dataset.page) === page));
  }
  renderKeys();
}

// ---- suggerimenti

function scheduleSuggest() {
  clearTimeout(bar.suggestTimer);
  bar.suggestTimer = setTimeout(suggest, 150);
}

async function suggest() {
  const box = $("suggest");
  const pos = caretPos();
  if (!state.doc || pos === null || document.activeElement !== $("text")) { box.innerHTML = ""; return; }
  const text = state.doc.text;
  const word = wordBefore(text, pos);
  if (!word || word.length < 1) { box.innerHTML = ""; return; }
  const key = text + "\u0000" + pos;
  bar.suggestFor = key;
  let r;
  try {
    r = (await call("complete", { args: [text, pos] })).result;
  } catch (e) {
    return;
  }
  if (bar.suggestFor !== key || state.doc.text !== text) return;
  box.innerHTML = "";
  for (const item of r.items) {
    const b = document.createElement("button");
    b.textContent = item.text;
    b.title = item.label;
    b.setAttribute("aria-label", t("Suggerimento: {text}", { text: item.text }));
    b.onclick = () => {
      if (state.doc.text !== text) return;
      selectRange(r.start, r.end);
      const after = text[r.end];
      typeText(item.text + (after && /\s/.test(after) ? "" : " "));
      box.innerHTML = "";
    };
    box.append(b);
  }
}

// ---- ▶ battuta: suona la battuta sotto il cursore

async function playBarAtCaret() {
  const resumed = unlockInGesture();
  if (!state.doc) return;
  const pos = caretPos() ?? 0;
  if (state.playing) await pause();
  await resumed;
  if (!state.song || state.song.text !== state.doc.text) {
    if (!(await analyze())) return;
  }
  const song = state.song;
  await song.spansReady;
  const s = song.spans;
  if (!s) return;
  // lo span piu' profondo che contiene il cursore, altrimenti il primo dopo
  let best = -1, next = -1;
  for (let i = 0; i < s.length; i += 6) {
    if (s[i + 1] <= pos && pos <= s[i + 2]) {
      if (best < 0 || s[i + 5] > s[best + 5]) best = i;
    } else if (s[i + 1] > pos && (next < 0 || s[i + 1] < s[next + 1])) {
      next = i;
    }
  }
  const at = best >= 0 ? best : next;
  if (at < 0) { setStatus(t("Il cursore non è su una nota da suonare")); return; }
  const [start, end] = (await call("bar", { args: [song.text, s[at + 3]] })).result;
  if (!state.audioReady) {
    setStatus(t("Preparo il sintetizzatore e il SoundFont…"));
    state.audioReady = initAudio();
  }
  await state.audioReady;
  const keep = state.pausedTick;
  const stop = { beat: end, restore: keep };
  state.stopAtBeat = stop;
  await startPlayer(Math.round(start * TICKS_PER_BEAT));
  setStatus(t("Battuta {n}", { n: barNumber(start) }));
  requestAnimationFrame(frame);
}

function setupMusicBar() {
  for (const b of document.querySelectorAll(".pages button")) b.onclick = () => setPage(Number(b.dataset.page));
  // I tasti non prendono il fuoco: il cursore e la tastiera restano nel testo.
  $("musicbar").addEventListener("pointerdown", (ev) => {
    if (ev.target.closest("button")) ev.preventDefault();
  });
  const pre = $("text");
  pre.addEventListener("focus", () => document.body.classList.add("editing"));
  pre.addEventListener("blur", () => setTimeout(() => {
    if (document.activeElement !== pre) document.body.classList.remove("editing");
  }, 100));
  pre.addEventListener("input", scheduleSuggest);
  document.addEventListener("selectionchange", () => {
    if (document.activeElement === pre) {
      scheduleSuggest();
      if (bar.page === 2) renderKeys();      // gli accordi seguono la tonalita' al cursore
    }
  });
  setPage(0);
}

function showMusicBar(on) {
  $("musicbar").hidden = !on;
}

// ------------------------------------------------------------ brani

function formatDate(time) {
  return new Date(time).toLocaleString(I18n.locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

async function renderSongs() {
  const list = await Songs.list().catch(() => []);
  const ul = $("mySongs");
  ul.innerHTML = "";
  $("noSongs").hidden = list.length > 0;
  for (const song of list) {
    ul.append(songItem(song.name, t("modificato {date}", { date: formatDate(song.updated) }),
                       state.doc && state.doc.kind === "song" && state.doc.id === song.id,
                       () => openSong(song.id), [
      [t("Rinomina"), () => renameSong(song.id)],
      [t("Duplica"), () => duplicate(song)],
      [t("Condividi"), () => share(song)],
      [t("Elimina"), () => deleteSong(song.id), "danger"],
    ]));
  }
  const ex = $("examples");
  ex.innerHTML = "";
  for (const file of state.examples) {
    ex.append(songItem(exampleTitle(file), t("sola lettura"),
                       state.doc && state.doc.kind === "example" && state.doc.file === file,
                       () => openExample(file, true), [
      [t("Crea una copia"), async () => duplicate(await exampleDoc(file))],
      [t("Condividi"), async () => share(await exampleDoc(file))],
    ]));
  }
}

function songItem(title, subtitle, current, onOpen, actions) {
  const li = document.createElement("li");
  if (current) li.classList.add("current");
  const open = document.createElement("button");
  open.className = "open";
  open.innerHTML = "<span></span><small></small>";
  open.firstChild.textContent = title;
  open.lastChild.textContent = subtitle;
  open.onclick = onOpen;
  const more = document.createElement("button");
  more.className = "more";
  more.textContent = "⋯";
  more.setAttribute("aria-label", t("Altre azioni per {name}", { name: title }));
  more.setAttribute("aria-expanded", "false");
  more.onclick = () => {
    const menu = li.querySelector(".menu");
    if (menu) { menu.remove(); li.classList.remove("has-menu"); more.setAttribute("aria-expanded", "false"); return; }
    const div = document.createElement("div");
    div.className = "menu";
    for (const [label, fn, cls] of actions) {
      const b = document.createElement("button");
      b.textContent = label;
      if (cls) b.className = cls;
      b.onclick = () => Promise.resolve(fn()).catch(showError);
      div.append(b);
    }
    li.classList.add("has-menu");
    li.append(div);
    more.setAttribute("aria-expanded", "true");
  };
  li.append(open, more);
  return li;
}

// Il nome di un esempio da mostrare: "jazz_1_evening_swing__sfz__plugin-areverb.st"
// diventa "jazz 1 evening swing" (dopo "__" ci sono i componenti usati).
function exampleTitle(file) {
  return file.replace(/\.st$/, "").split("__")[0].replace(/_/g, " ");
}

async function exampleDoc(file) {
  const bytes = new Uint8Array(await (await fetch("bundle/examples/" + encodeURIComponent(file))).arrayBuffer());
  const f = StFormat.fromBytes(bytes);
  return { kind: "example", file, name: exampleTitle(file), text: f.text, eol: f.eol, bom: f.bom };
}

async function openExample(file, show) {
  const doc = await exampleDoc(file);
  const ready = openDoc(doc);
  if (show) setView("testo");
  return ready;
}

async function openSong(id, show = true) {
  const song = await Songs.get(id);
  if (!song) return;
  const ready = openDoc({ kind: "song", id: song.id, name: song.name, text: song.text, eol: song.eol, bom: song.bom });
  if (show) setView("testo");
  return ready;
}

async function newSong() {
  const name = await Songs.freeName(t("Nuovo brano"));
  const song = await Songs.create({ name, text: newSongText(), source: "nuovo" });
  await openSong(song.id);
}

async function openFile(file) {
  const f = StFormat.fromBytes(new Uint8Array(await file.arrayBuffer()));
  const name = await Songs.freeName(StFormat.nameFromFile(file.name));
  const song = await Songs.create({ name, text: f.text, eol: f.eol, bom: f.bom, source: "file " + file.name });
  await openSong(song.id);
}

async function renameSong(id) {
  const song = await Songs.get(id);
  const name = prompt(t("Nuovo nome del brano"), song.name);
  if (!name || !name.trim() || name.trim() === song.name) return;
  song.name = await Songs.freeName(name.trim());
  await Songs.put(song);
  if (state.doc && state.doc.kind === "song" && state.doc.id === id) {
    state.doc.name = song.name;
    showDocTitle();
  }
  renderSongs();
}

async function duplicate(source) {
  const name = await Songs.freeName(source.name);
  const song = await Songs.create({ name, text: source.text, eol: source.eol, bom: source.bom,
                                    source: "copia di " + source.name });
  renderSongs();
  return song;
}

async function deleteSong(id) {
  const song = await Songs.get(id);
  if (!confirm(t("Eliminare «{name}»? Non si può annullare.", { name: song.name }))) return;
  await Songs.remove(id);
  if (state.doc && state.doc.kind === "song" && state.doc.id === id) {
    stop(true);
    state.doc = null;
    state.song = null;
    showText("");
    setEditable(false);
    clearCheck();
    showDocTitle();
    rememberDoc(null);
    $("play").disabled = true;
  }
  renderSongs();
}

// Condivide il .st (foglio di condivisione del telefono) o lo scarica.
async function share(song) {
  const fileName = StFormat.fileName(song.name);
  const file = new File([StFormat.toBytes(song)], fileName, { type: "text/plain" });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: song.name });
      return;
    } catch (e) {
      if (e.name === "AbortError") return;
    }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(file);
  a.download = fileName;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 10000);
}

// ------------------------------------------------------------ crea
//
// Giro armonico, batteria, basso e accompagnamento con i generatori di
// SoundText (engine.generate nel worker, gli stessi risultati delle
// finestre «Genera ...» del computer). Ogni modifica rigenera la parte (con
// lo stesso seme: «Un'altra» ne sceglie uno nuovo) e, se si sta ascoltando,
// l'anteprima riparte con la parte nuova. «Aggiungi al brano» mette la
// parte in una traccia nuova in fondo al file.

const gen = {
  kind: "progression",
  choices: null, choicesFor: null,   // engine.generator_choices del testo del brano
  values: {},                        // per generatore: i valori dei campi
  seeds: {},                         // per generatore: il seme
  text: "", textFor: "",             // ultima parte generata e per quali valori
  timer: null, busy: null,
};

// I campi di ogni generatore: [nome, tipo, etichetta, opzioni]. Le etichette
// sono quelle delle finestre di SoundText.
function genFields(kind) {
  const c = gen.choices;
  const opts = (list) => list.map((o) => [o.value, o.label]);
  const variability = ["variability", "range", t("Variabilità:")];
  const bars = ["bars", "number", t("Battute:")];
  const intensity = ["intensity", "select", t("Intensità:"), opts(c.intensities)];
  const sources = c.sources.map((n) => [n, n]);
  const instruments = (k) => c.instruments[k].map((n) => [n, n]);
  if (kind === "progression") {
    const mode = /m$/.test(gen.values.progression?.key || c.key) ? "minor" : "major";
    return [
      ["key", "select", t("Tonalità:"), c.keys.map((k) => [k, k])],
      ["style", "select", t("Stile:"), opts(c.progression.filter((p) => p.mode === mode))],
      ["chord_bars", "select", t("Durata di ogni accordo:"), opts(c.chord_durations)],
      bars, ["instrument", "select", t("Strumento:"), instruments("progression")], variability,
      ["ending", "check", t("Cadenza finale")],
    ];
  }
  if (kind === "drums") {
    return [
      ["style", "select", t("Stile:"), opts(c.drums)], bars, intensity, variability,
      ["phrase_fills", "check", t("Fill a frasi")], ["ending", "check", t("Finale sull'ultima battuta")],
    ];
  }
  const common = [["source", "select", t("Accordi da:"), sources]];
  if (kind === "bass") {
    return [...common,
      ["style", "select", t("Stile:"), opts(c.bass)], ["instrument", "select", t("Strumento:"), instruments("bass")],
      bars, intensity, variability,
      ["kick_track", "select", t("Segui la cassa di:"), [["", t("nessuna")], ...c.kick_tracks.map((n) => [n, n])]],
      ["performance", "check", t("Esecuzione dello strumento")],
    ];
  }
  return [...common,
    ["style", "select", t("Stile:"), opts(c.comping)], ["instrument", "select", t("Strumento:"), instruments("comping")],
    bars, intensity, variability,
    ["voice_leading", "check", t("Rivolti vicini")], ["performance", "check", t("Esecuzione dello strumento")],
  ];
}

function genDefaults(kind) {
  const c = gen.choices;
  const songBars = c.bars > 0 ? Math.min(64, c.bars) : 8;
  const base = { variability: 35, intensity: "normal" };
  if (kind === "progression") {
    const mode = /m$/.test(c.key) ? "minor" : "major";
    return { ...base, key: c.key, style: c.progression.find((p) => p.mode === mode).value, chord_bars: 1,
             bars: 0, instrument: c.instruments.progression[0], ending: false };
  }
  if (kind === "drums") return { ...base, style: c.drums[0]?.value, bars: songBars, phrase_fills: true, ending: false };
  const source = c.sources[c.sources.length - 1] || "";
  if (kind === "bass") {
    return { ...base, source, style: c.bass[0].value, instrument: c.instruments.bass[0], bars: songBars,
             kick_track: "", performance: false };
  }
  return { ...base, source, style: c.comping[0].value, instrument: c.instruments.comping[0], bars: songBars,
           voice_leading: true, performance: false };
}

async function loadGenChoices() {
  const text = state.doc ? state.doc.text : "";
  if (gen.choices && gen.choicesFor === text) return;
  await state.booted;
  const c = (await call("generator_choices", { args: [text] })).result;
  gen.choices = c;
  gen.choicesFor = text;
  // i valori restano, ma la sorgente degli accordi deve esistere ancora
  for (const kind of Object.keys(gen.values)) {
    const v = gen.values[kind];
    if ("source" in v && !c.sources.includes(v.source)) v.source = c.sources[c.sources.length - 1] || "";
    if (v.kick_track && !c.kick_tracks.includes(v.kick_track)) v.kick_track = "";
  }
}

async function showCrea() {
  if (!document.body.classList.contains("view-crea")) return;
  try {
    await loadGenChoices();
  } catch (e) {
    $("genStatus").textContent = shortError(e);
    return;
  }
  renderGenForm();
  scheduleGenerate(0);
}

async function setGenKind(kind) {
  if (state.previewing) stopPreview();
  gen.kind = kind;
  for (const b of document.querySelectorAll(".gentabs button")) {
    b.setAttribute("aria-selected", String(b.dataset.gen === kind));
  }
  $("genStatus").textContent = "";
  await showCrea();
}

function renderGenForm() {
  const kind = gen.kind;
  const form = $("genForm");
  form.replaceChildren();
  if (!gen.choices) return;
  const values = gen.values[kind] || (gen.values[kind] = genDefaults(kind));
  for (const [name, type, label, options] of genFields(kind)) {
    const id = `gen-${name}`;
    let input;
    if (type === "select") {
      input = document.createElement("select");
      for (const [value, text] of options) input.add(new Option(text, String(value)));
      if (!options.some(([v]) => String(v) === String(values[name])) && options.length) values[name] = options[0][0];
      input.value = String(values[name] ?? "");
    } else if (type === "number") {
      input = document.createElement("input");
      input.type = "number";
      input.min = kind === "progression" ? "0" : "1";
      input.max = "256";
      input.inputMode = "numeric";
      input.value = String(values[name]);
    } else if (type === "range") {
      input = document.createElement("input");
      input.type = "range";
      input.min = "0"; input.max = "100"; input.step = "5";
      input.value = String(values[name]);
      input.setAttribute("aria-valuetext", values[name] + "%");
    } else {
      input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !!values[name];
    }
    input.id = id;
    input.name = name;
    const lab = document.createElement("label");
    lab.htmlFor = id;
    lab.textContent = type === "range" ? `${label} ${values[name]}%` : label;
    if (type === "check") {
      const row = document.createElement("label");
      row.className = "check";
      row.append(input, " ", label);
      form.append(row);
    } else {
      form.append(lab, input);
    }
    const update = () => {
      let v = type === "check" ? input.checked : input.value;
      if (type === "number" || type === "range") v = Number(v);
      if (name === "chord_bars") v = Number(v);
      values[name] = v;
      if (type === "range") { lab.textContent = `${label} ${v}%`; input.setAttribute("aria-valuetext", v + "%"); }
      if (name === "key") { renderGenForm(); }     // gli stili seguono il modo della tonalita'
      scheduleGenerate(type === "range" || type === "number" ? 250 : 0);
    };
    input.addEventListener(type === "range" || type === "number" ? "input" : "change", update);
  }
  if (kind !== "progression" && kind !== "drums" && !gen.choices.sources.length) {
    $("genStatus").textContent = t("Nel brano non c'è ancora una traccia con degli accordi da seguire.");
  }
}

// Le opzioni per engine.generate dai valori dei campi
function genOptions(kind) {
  const v = { ...gen.values[kind] };
  const out = { ...v, variability: v.variability / 100, seed: gen.seeds[kind] ?? null, track: t("Nuova traccia") };
  if (out.kick_track === "") delete out.kick_track;
  if (out.source === "") delete out.source;
  delete out.instrument;
  if (kind === "bass" || kind === "comping") out.instrument = v.instrument;
  return out;
}

function scheduleGenerate(delay = 150) {
  clearTimeout(gen.timer);
  gen.timer = setTimeout(() => generatePart().catch(showError), delay);
}

async function generatePart() {
  if (!state.doc || !gen.choices) return;
  const kind = gen.kind;
  const options = genOptions(kind);
  const key = JSON.stringify([state.doc.text, kind, options]);
  if (key === gen.textFor && gen.text) return gen.text;
  const status = $("genStatus");
  let r;
  try {
    r = (await call("generate", { args: [state.doc.text, kind, options] })).result;
  } catch (e) {
    if (gen.kind !== kind) return null;
    gen.text = "";
    gen.textFor = "";
    $("genText").textContent = "";
    status.textContent = errorText(e);
    $("genAdd").disabled = true;
    return null;
  }
  if (gen.kind !== kind || JSON.stringify([state.doc.text, kind, genOptions(kind)]) !== key) return null;  // superata
  gen.seeds[kind] = r.seed;
  gen.text = r.text;
  gen.textFor = JSON.stringify([state.doc.text, kind, genOptions(kind)]);
  $("genText").textContent = r.text;
  status.textContent = "";
  $("genAdd").disabled = false;
  if (state.previewing) listenToPart(true).catch(showError);    // l'anteprima segue le modifiche
  return r.text;
}

// Strumento e nome della traccia nuova
function genTrack(kind) {
  const v = gen.values[kind];
  if (kind === "drums") return { instrument: "Drums", name: null };
  if (kind === "progression") return { instrument: v.instrument, name: t("Accordi") };
  return { instrument: v.instrument, name: null };
}

// Il brano con la parte nuova in fondo
async function songWithPart() {
  const part = await generatePart() || gen.text;
  if (!part) throw new Error(errorText($("genStatus").textContent || t("Niente da aggiungere")));
  const { instrument, name } = genTrack(gen.kind);
  return (await call("add_track", { args: [state.doc.text, instrument, part, name] })).result;
}

// ▶ Ascolta: il brano con la parte nuova, dall'inizio (o dal punto in cui
// era l'anteprima, se si sta rigenerando mentre suona)
async function listenToPart(again = false) {
  if (!again && state.previewing) { stopPreview(); return; }
  const resumed = again ? null : unlockInGesture();
  if (resumed) await resumed;
  const song = await songWithPart();
  const r = await call("preview", { text: song.text });
  await playPreview(r.midi);
}

async function addPartToSong() {
  if (!state.doc) return;
  if (state.previewing) stopPreview();
  const { text, name } = await songWithPart();
  await replaceDocText(text);
  // Si resta in Crea, pronti per la parte dopo (giro -> batteria -> basso ->
  // accompagnamento): la traccia nuova si vede nel Testo e si sente con Play.
  const done = t("Traccia «{name}» aggiunta al brano", { name });
  setStatus(done);
  const order = GENERATOR_ORDER;
  const next = order[order.indexOf(gen.kind) + 1];
  gen.choices = null;                    // le tracce sono cambiate: nuove sorgenti di accordi
  gen.textFor = "";
  if (next) await setGenKind(next); else await showCrea();
  $("genStatus").textContent = done;
}

const GENERATOR_ORDER = ["progression", "drums", "bass", "comping"];

function setupCrea() {
  for (const b of document.querySelectorAll(".gentabs button")) b.onclick = () => setGenKind(b.dataset.gen).catch(showError);
  $("genAgain").onclick = () => { gen.seeds[gen.kind] = null; gen.textFor = ""; scheduleGenerate(0); };
  $("genListen").onclick = () => listenToPart().catch(showError);
  $("genAdd").onclick = () => addPartToSong().catch(showError);
}

// ------------------------------------------------------------ trasforma
//
// La finestra Trasforma di SoundText sul richiamo di pattern sotto il
// cursore (%Tema, %Tema.invert...): la catena di funzioni si scrive nel
// campo o si allunga con «Aggiungi una funzione»; a ogni modifica il
// motore dice cosa suona passo per passo, nel punto del brano dove sta
// (engine.transform_preview), e mostra prima e dopo in una piccola
// partitura da ascoltare. «Sostituisci» scrive il richiamo nuovo,
// «Scrivi le note» lo scrive per esteso nota per nota.

const tf = { pos: 0, text: "", result: null, timer: null };

function base64Bytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function openTransform() {
  if (!state.doc) return;
  const pos = caretPos() ?? 0;
  const ref = (await call("transform_at", { args: [state.doc.text, pos] })).result;
  if (!ref) { setStatus(t("Metti il cursore su un richiamo di pattern (%Nome).")); return; }
  tf.pos = pos;
  tf.text = state.doc.text;
  tf.result = null;
  $("tfTitle").textContent = t("Trasforma %{name}", { name: ref.pattern });
  $("tfToken").value = ref.token;
  const add = $("tfAdd");
  add.replaceChildren(new Option(t("Aggiungi una funzione…"), ""));
  for (const f of bar.transforms) add.add(new Option(f.ready, f.ready));
  $("tfHelp").textContent = "";
  $("tfStages").replaceChildren();
  $("tfError").textContent = "";
  $("tfBefore").replaceChildren();
  $("tfAfter").replaceChildren();
  $("transform").showModal();
  refreshTransform();
}

function scheduleTransform() {
  clearTimeout(tf.timer);
  tf.timer = setTimeout(() => refreshTransform().catch(showError), 300);
}

async function refreshTransform() {
  const token = $("tfToken").value.trim();
  const r = (await call("transform_preview", { args: [tf.text, tf.pos, token] })).result;
  if ($("tfToken").value.trim() !== token) return;            // superata
  tf.result = r;
  $("tfError").textContent = r.error || (r.warnings || []).join("\n");
  const ok = !r.error;
  $("tfReplace").disabled = !ok;
  $("tfFreeze").disabled = !ok;
  $("tfPlayAfter").disabled = !ok;
  const list = $("tfStages");
  list.replaceChildren();
  for (const [step, notes] of ok ? r.stages : []) {
    const li = document.createElement("li");
    const code = document.createElement("code");
    code.textContent = step;
    li.append(code, " → ", notes || "–");
    list.append(li);
  }
  if (!ok) { $("tfAfter").replaceChildren(); return; }
  await Promise.all([miniScore($("tfBefore"), r.xml_before), miniScore($("tfAfter"), r.xml_after)]);
}

// Una striscia di partitura (verovio, come la schermata Partitura)
async function miniScore(box, xml) {
  const width = Math.max(240, box.clientWidth || 300);
  try {
    const r = await scoreCall({ cmd: "render", xml, scale: 35, pageWidth: Math.round(width * 100 / 35) });
    box.innerHTML = r.pages[0] || "";
    const svg = box.querySelector("svg");
    if (svg) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", t("Partitura")); }
  } catch (e) {
    box.textContent = errorText(e);
  }
}

async function playTransform(which) {
  const resumed = unlockInGesture();
  await resumed;
  const r = tf.result;
  if (!r || r.error) return;
  await playPreview(base64Bytes(which === "before" ? r.midi_before : r.midi_after),
                    which === "before" ? t("Ascolto del pattern") : t("Ascolto del pattern con le funzioni"));
}

async function applyTransform(freeze) {
  const r = tf.result;
  if (!r || r.error || !state.doc) return;
  if (state.previewing) stopPreview();
  if (state.doc.text !== tf.text) { $("tfError").textContent = t("Il testo è cambiato: riapri Trasforma."); return; }
  let out;
  try {
    out = (await call("transform_apply", { args: [tf.text, tf.pos, r.token, freeze] })).result;
  } catch (e) {
    $("tfError").textContent = errorText(e);
    return;
  }
  $("transform").close();
  if (!freeze) {
    // come se lo si scrivesse: entra nell'annulla della tastiera
    selectRange(r.start, r.end);
    typeText(r.token);
  } else {
    await replaceDocText(out.text);
    goTo(out.start, out.end);
  }
  setStatus(freeze ? t("Note scritte per esteso") : t("Richiamo sostituito"));
}

function setupTransform() {
  $("tfToken").addEventListener("input", scheduleTransform);
  $("tfAdd").onchange = (ev) => {
    const call = ev.target.value;
    if (!call) return;
    const f = bar.transforms.find((x) => x.ready === call);
    $("tfHelp").textContent = f ? f.help : "";
    $("tfToken").value = $("tfToken").value.trim() + call;
    ev.target.value = "";
    refreshTransform().catch(showError);
  };
  $("tfPlayBefore").onclick = () => playTransform("before").catch(showError);
  $("tfPlayAfter").onclick = () => playTransform("after").catch(showError);
  $("tfReplace").onclick = () => applyTransform(false).catch(showError);
  $("tfFreeze").onclick = () => applyTransform(true).catch(showError);
  $("tfClose").onclick = () => $("transform").close();
  $("transform").addEventListener("close", () => { if (state.previewing) stopPreview(); });
}

// ------------------------------------------------------------ struttura
//
// Le sezioni del brano una sotto l'altra, le tracce in colonne (scorrono in
// orizzontale), i box nelle celle (engine.structure). Un tocco su un box o
// su una sezione apre le azioni; le modifiche (engine.box_edit) cambiano
// solo le intestazioni e i blocchi dei box. «Annulla» torna indietro di una
// modifica della Struttura.

const struct = { info: null, infoFor: null, undo: [] };

async function showStructure() {
  if (!document.body.classList.contains("view-struttura") || !state.doc) {
    if (!state.doc) $("structure").replaceChildren(hint(t("Apri un brano per vederne la struttura.")));
    return;
  }
  const text = state.doc.text;
  if (struct.infoFor !== text) {
    await state.booted;
    try {
      struct.info = (await call("structure", { args: [text] })).result;
      struct.infoFor = text;
    } catch (e) {
      struct.info = null;
      $("structure").replaceChildren(hint(t("Struttura non disponibile: {message}", { message: errorText(e) }), true));
      return;
    }
  }
  renderStructure();
}

function hint(text, error = false) {
  const p = document.createElement("p");
  p.className = error ? "hint error" : "hint";
  p.style.padding = "0 16px";
  p.textContent = text;
  return p;
}

function renderStructure() {
  const info = struct.info;
  const box = $("structure");
  $("structUndo").disabled = struct.undo.length === 0;
  const plain = info.tracks.filter((tr) => tr.plain && tr.boxes.length);
  $("structSplit").hidden = plain.length === 0;
  if (!info.tracks.length) { box.replaceChildren(hint(t("Il brano non ha ancora tracce."))); return; }
  const sections = info.sections;
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  const corner = document.createElement("th");
  corner.className = "sec";
  corner.textContent = t("Sezione");
  head.append(corner);
  for (const tr of info.tracks) {
    const th = document.createElement("th");
    th.textContent = tr.name;
    th.title = tr.instrument;
    th.scope = "col";
    head.append(th);
  }
  const body = table.createTBody();
  sections.forEach((sec, i) => {
    const until = i + 1 < sections.length ? sections[i + 1].beat : Infinity;
    const row = body.insertRow();
    const th = document.createElement("th");
    th.className = "sec";
    th.scope = "row";
    const b = document.createElement("button");
    // l'ultima sezione arriva alla fine del brano
    const lastBar = i + 1 < sections.length ? sections[i + 1].bar - 1
      : info.bars.filter((b) => b < info.end - 1e-6).length;
    b.append(sec.name || t("(senza nome)"));
    const small = document.createElement("small");
    small.textContent = lastBar && lastBar > sec.bar ? t("battute {first}–{last}", { first: sec.bar, last: lastBar })
                                                     : t("battuta {n}", { n: sec.bar });
    b.append(small);
    b.setAttribute("aria-label", t("Sezione {name}, {where}", { name: sec.name || t("(senza nome)"), where: small.textContent }));
    b.onclick = () => sectionActions(sec);
    th.append(b);
    row.append(th);
    for (const tr of info.tracks) {
      const cell = row.insertCell();
      for (const bx of tr.boxes) {
        if (bx.beat < sec.beat - 1e-9 || bx.beat >= until - 1e-9) continue;
        const c = document.createElement("button");
        c.className = "box" + (tr.plain ? " plain" : "");
        c.append(tr.plain ? t("testo della traccia") : bx.name || "–");
        const sm = document.createElement("small");
        sm.textContent = bx.bars === 1 ? t("battuta {n}", { n: bx.bar })
                                       : t("battute {first}–{last}", { first: bx.bar, last: bx.bar + bx.bars - 1 });
        c.append(sm);
        c.setAttribute("aria-label", t("Box {name}, traccia {track}, {where}",
                                       { name: tr.plain ? t("testo della traccia") : bx.name, track: tr.name, where: sm.textContent }));
        c.onclick = () => boxActions(tr, bx);
        cell.append(c);
      }
    }
  });
  box.replaceChildren(table);
}

// Il foglio delle azioni (in basso, come sul telefono)
function sheet(title, actions) {
  const dlg = $("sheet");
  $("sheetTitle").textContent = title;
  const list = $("sheetActions");
  list.replaceChildren();
  for (const [label, run, cls] of actions) {
    const b = document.createElement("button");
    b.textContent = label;
    if (cls) b.className = cls;
    b.onclick = () => { dlg.close(); Promise.resolve(run()).catch(showError); };
    list.append(b);
  }
  dlg.showModal();
}

function openInText(pos) {
  setView("testo");
  goTo(pos);
}

function boxActions(track, bx) {
  if (track.plain) {
    sheet(t("Traccia {name}", { name: track.name }), [
      [t("Apri nel Testo"), () => openInText(0)],
      [t("Dividi in sezioni"), splitIntoSections],
    ]);
    return;
  }
  sheet(t("Box {name} · {track}", { name: bx.name, track: track.name }), [
    [t("Apri nel Testo"), () => openInText(bx.start)],
    [t("Rinomina…"), async () => {
      const name = prompt(t("Nuovo nome del box"), bx.name);
      if (name) await structEdit("rename", { hstart: bx.hstart, name });
    }],
    [t("Sposta alla battuta…"), async () => {
      const bar = prompt(t("Battuta d'inizio"), String(bx.bar));
      if (bar && Number(bar) >= 1) await structEdit("move", { hstart: bx.hstart, bar: Math.round(Number(bar)) });
    }],
    [t("Duplica in fondo al brano"), () => structEdit("duplicate", { hstart: bx.hstart })],
    [t("Elimina"), () => structEdit("delete", { hstart: bx.hstart }), "danger"],
  ]);
}

function sectionActions(sec) {
  sheet(t("Sezione {name}", { name: sec.name || t("(senza nome)") }), [
    [t("Duplica la sezione in fondo al brano"), () => structEdit("section_duplicate", { beat: sec.beat })],
    [t("Rinomina la sezione…"), async () => {
      const name = prompt(t("Nuovo nome della sezione"), sec.name);
      if (name) await structEdit("section_rename", { beat: sec.beat, name });
    }],
    [t("Elimina la sezione"), () => structEdit("section_delete", { beat: sec.beat }), "danger"],
  ]);
}

async function splitIntoSections() {
  const name = prompt(t("Nome della prima sezione"), t("Strofa"));
  if (name) await structEdit("make_boxes", { name });
}

async function structEdit(op, args) {
  if (!state.doc) return;
  const before = state.doc.text;
  let r;
  try {
    r = (await call("box_edit", { args: [before, op, args] })).result;
  } catch (e) {
    $("structStatus").textContent = errorText(e);
    return;
  }
  if (state.doc.text !== before) return;           // cambiato nel frattempo
  struct.undo.push(before);
  if (struct.undo.length > 30) struct.undo.shift();
  await replaceDocText(r.text);
  $("structStatus").textContent = "";
  await showStructure();
}

async function undoStructure() {
  const previous = struct.undo.pop();
  if (previous == null || !state.doc) return;
  await replaceDocText(previous);
  await showStructure();
}

function setupStructure() {
  $("structUndo").onclick = () => undoStructure().catch(showError);
  $("structSplit").onclick = () => splitIntoSections().catch(showError);
  $("sheetClose").onclick = () => $("sheet").close();
}

// ------------------------------------------------------------ schermate

function setView(name) {
  document.body.className = "view-" + name;
  if (name === "partitura") showScore().catch(showError);
  if (name === "crea") showCrea().catch(showError);
  if (name === "struttura") showStructure().catch(showError);
  for (const b of document.querySelectorAll(".tabs button")) {
    if (b.dataset.view === name) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  try { localStorage.setItem("stmobile.view", name); } catch (e) {}
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
  for (const url of WORKLET_MODULES) await ctx.audioWorklet.addModule(url);
  const synth = new JSSynth.AudioWorkletNodeSynthesizer();
  synth.init(ctx.sampleRate, { midiChannelCount: 32 });
  const node = synth.createAudioNode(ctx, { outputChannelCount: [2] });
  node.connect(ctx.destination);
  const worklet_ms = ms(t0);

  const t1 = performance.now();
  const sfCached = await cached(SOUNDFONT_URL);
  const resp = await fetch(SOUNDFONT_URL);
  if (!resp.ok) throw new Error(t("SoundFont non trovato ({status})", { status: resp.status }));
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
  watchTransport(token);
  synth.waitForPlayerStopped().then(() => {
    if (token !== state.playToken) return;
    if (state.previewing) { stopPreview(); return; }
    state.playing = false;
    state.pausedTick = 0;
    setPlayButton();
    clearHighlight();
    showPosition(0);
    setStatus(t("Fine del brano"));
  });
}

async function play() {
  // Primo tocco: niente await prima di unlockInGesture (iOS).
  const tTap = performance.now();
  const resumed = unlockInGesture();
  if (state.previewing) return stopPreview();
  if (state.playing) return pause();
  state.stopAtBeat = null;
  try {
    await resumed;
    if (!state.doc) return;
    // testo cambiato dall'ultima analisi: si rianalizza prima di suonare
    if (!state.song || state.song.text !== state.doc.text) {
      state.pausedTick = 0;
      await analyze();
      if (!state.song) return;
    }
    normalizeEditor();
    if (!state.audioReady) {
      setStatus(t("Preparo il sintetizzatore e il SoundFont…"));
      state.audioReady = initAudio();
    }
    await state.audioReady;
    const loop = state.loop;
    if (loop.on && (state.pausedTick < loop.a * TICKS_PER_BEAT || state.pausedTick >= loop.b * TICKS_PER_BEAT)) {
      state.pausedTick = Math.round(loop.a * TICKS_PER_BEAT);
    }
    await startPlayer(state.pausedTick);
    const first = !state.firstPlayDone;
    state.firstPlayDone = true;
    Metrics.record("play", { first, tap_to_play_ms: ms(tTap), ctx_state: state.ctx.state, song: state.song.name });
    setStatus(t("Suona"));
    batteryProbe();
    requestAnimationFrame(frame);
  } catch (e) {
    console.error(e);
    if (state.song && state.song.text === (state.doc && state.doc.text)) {
      state.audioReady = null;
      setStatus(t("Errore audio: {message}", { message: e.message }), true);
    }
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
  setStatus(t("In pausa"));
}

function stop(reset) {
  if (state.previewing) stopPreview();
  if (state.synth && state.playing) {
    state.playToken++;
    state.synth.stopPlayer();
    state.synth.midiAllSoundsOff();
  }
  state.playing = false;
  if (reset) { state.pausedTick = 0; showPosition(0); }
  setPlayButton();
  clearHighlight();
}

// ---- anteprima della schermata Crea: un altro MIDI sullo stesso lettore;
// alla fine (o con ■) tornano il MIDI e la posizione del brano.

async function playPreview(midi, label = t("Anteprima della parte generata")) {
  if (!state.audioReady) {
    setStatus(t("Preparo il sintetizzatore e il SoundFont…"));
    state.audioReady = initAudio();
  }
  await state.audioReady;
  let from = 0;
  if (state.previewing) {
    from = await state.synth.retrievePlayerCurrentTick();     // rigenerata mentre suona: stesso punto
  } else {
    if (state.playing) await pause();
    state.savedMidi = state.midi;
    state.savedTick = state.pausedTick;
    state.previewing = true;
  }
  state.stopAtBeat = null;
  clearHighlight();
  state.midi = midi;
  state.synth.midiAllSoundsOff();
  await startPlayer(from);
  setStatus(label);
  setPreviewButton();
}

function stopPreview() {
  if (!state.previewing) return;
  state.playToken++;
  if (state.synth) { state.synth.stopPlayer(); state.synth.midiAllSoundsOff(); }
  state.playing = false;
  state.previewing = false;
  state.midi = state.savedMidi;
  state.pausedTick = state.savedTick || 0;
  setPlayButton();
  setPreviewButton();
  showPosition(state.pausedTick / TICKS_PER_BEAT);
  setStatus(t("Anteprima finita"));
}

function setPreviewButton() {
  const b = $("genListen");
  b.setAttribute("aria-pressed", String(!!state.previewing));
  b.lastChild.textContent = state.previewing ? t("Ferma") : t("Ascolta");
  b.firstChild.textContent = state.previewing ? "■ " : "▶ ";
}

function setPlayButton() {
  const b = $("play");
  b.textContent = state.playing ? "❚❚" : "▶";
  b.setAttribute("aria-label", state.playing ? t("Pausa") : t("Suona"));
}

async function setTranspose(semitones) {
  state.semitones = semitones;
  $("transOut").value = (semitones > 0 ? "+" : "") + semitones;
  $("trans").setAttribute("aria-valuetext", t("{n} semitoni", { n: $("transOut").value }));
  if (state.song) await renderMidi();
}

// ---- lettore completo: mute, solo, metronomo, avanzamento, loop A-B

// Le tracce da non sentire: con un solo attivo tutte le altre, altrimenti
// quelle in mute.
function silentTracks() {
  const names = state.song ? state.song.info.tracks.map((tr) => tr.name) : [];
  return state.solo.size ? names.filter((n) => !state.solo.has(n)) : names.filter((n) => state.muted.has(n));
}

// "" quando il MIDI e' quello del brano com'e' scritto
function midiKey() {
  const silent = silentTracks();
  if (!state.semitones && !silent.length && !state.metronome) return "";
  return JSON.stringify([state.semitones, silent, state.metronome]);
}

// Il MIDI con trasposizione, mute, solo e metronomo, fatto dal motore. Se
// sta suonando riparte dallo stesso punto: il brano non si rianalizza.
async function renderMidi() {
  const song = state.song;
  if (!song) return;
  const key = midiKey();
  if (key === state.midiKey) return;
  const r = await call("render", {
    key, semitones: state.semitones, muted: silentTracks(), metronome: state.metronome,
  });
  if (state.song !== song || r.key !== midiKey()) return;   // superata da un'altra modifica
  state.midiKey = key;
  if (state.previewing) { state.savedMidi = r.midi; return; }
  state.midi = r.midi;
  Metrics.record("lettore", { semitones: state.semitones, silent: silentTracks().length, metronome: state.metronome, ms: r.ms });
  if (state.playing && state.stopAtBeat == null) {
    const tick = await state.synth.retrievePlayerCurrentTick();
    state.synth.midiAllSoundsOff();
    await startPlayer(tick);
  }
}

function renderMixer() {
  const list = $("mixer");
  list.innerHTML = "";
  const tracks = state.song ? state.song.info.tracks : [];
  const silent = new Set(silentTracks());
  for (const track of tracks) {
    const li = document.createElement("li");
    li.classList.toggle("silent", silent.has(track.name));
    const name = document.createElement("span");
    name.className = "tname";
    name.textContent = track.name;
    if (track.instrument && track.instrument !== track.name) {
      const small = document.createElement("small");
      small.textContent = track.instrument;
      name.append(small);
    }
    const toggle = (label, set, aria) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.setAttribute("aria-label", `${aria} ${track.name}`);
      b.setAttribute("aria-pressed", String(set.has(track.name)));
      b.onclick = () => {
        if (set.has(track.name)) set.delete(track.name); else set.add(track.name);
        renderMixer();
        renderMidi().catch(showError);
      };
      return b;
    };
    li.append(name, toggle("M", state.muted, t("Mute")), toggle("S", state.solo, t("Solo")));
    list.append(li);
  }
}

function setTimeline(timeline) {
  const tl = timeline && timeline.bars && timeline.bars.length ? timeline : { length: 0, bars: [0] };
  state.timeline = tl;
  const seek = $("seek");
  seek.max = String(tl.length);
  seek.disabled = !(tl.length > 0);
  const loop = state.loop;
  if (loop.b != null && loop.b > tl.length + 1e-9) state.loop = { a: null, b: null, on: false };
  renderLoop();
  showPosition(state.pausedTick / TICKS_PER_BEAT);
}

// L'indice della battuta che contiene 'beat' (0 = la prima)
function barIndex(beat) {
  const bars = state.timeline.bars;
  let lo = 0, hi = bars.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (bars[mid] <= beat + 1e-9) lo = mid; else hi = mid - 1;
  }
  return lo;
}

function barNumber(beat) {
  return barIndex(beat) + 1;
}

function barEnd(i) {
  const bars = state.timeline.bars;
  return i + 1 < bars.length ? bars[i + 1] : state.timeline.length;
}

// "battuta 5/104"
function positionText(beat) {
  return t("battuta {n}/{total}", { n: barNumber(Math.max(0, beat)), total: state.timeline.bars.length });
}

function showPosition(beat) {
  const tl = state.timeline;
  if (!state.seeking) $("seek").value = String(Math.max(0, Math.min(beat, tl.length)));
  const where = tl.length > 0 ? positionText(beat) : "";
  $("pos").textContent = where + (where && state.playing ? ` · ${Math.round(state.bpm)} BPM` : "");
  $("seek").setAttribute("aria-valuetext", where);
}

// Il battito che si sente ora: il player e' avanti della latenza d'uscita;
// retrievePlayerBpm e' gia' il tempo effettivo (con la velocita').
function heardBeat(tick) {
  const ctx = state.ctx;
  const latency = ctx ? (ctx.outputLatency || 0) + (ctx.baseLatency || 0) : 0;
  return tick / TICKS_PER_BEAT - (state.playing ? latency * state.bpm / 60 : 0);
}

// Porta il lettore all'inizio della battuta che contiene 'beat'.
function seekTo(beat) {
  const start = state.timeline.bars[barIndex(beat)] || 0;
  const tick = Math.round(start * TICKS_PER_BEAT);
  state.stopAtBeat = null;
  lastKey = "";
  if (state.playing) {
    state.synth.midiAllNotesOff();
    state.synth.seekPlayer(tick);
  } else {
    state.pausedTick = tick;
    clearHighlight();
  }
  showPosition(start);
}

// A e B: inizio e fine della battuta che si sente (o di quella dove il
// lettore e' fermo).
async function currentBeat() {
  if (state.playing && state.synth) return heardBeat(await state.synth.retrievePlayerCurrentTick());
  return state.pausedTick / TICKS_PER_BEAT;
}

async function setLoopPoint(which) {
  if (!state.song) return;
  const i = barIndex(Math.max(0, await currentBeat()));
  const loop = state.loop;
  if (which === "a") {
    loop.a = state.timeline.bars[i];
    if (loop.b != null && loop.b <= loop.a) loop.b = barEnd(i);
  } else {
    loop.b = barEnd(i);
    if (loop.a == null || loop.a >= loop.b) loop.a = state.timeline.bars[i];
    loop.on = true;
  }
  if (loop.b == null) loop.on = false;
  renderLoop();
}

function renderLoop() {
  const { a, b, on } = state.loop;
  const out = $("loopOut");
  if (a == null) out.textContent = t("nessun tratto");
  else if (b == null) out.textContent = t("dalla battuta {n}…", { n: barNumber(a) });
  else {
    const first = barNumber(a), last = barNumber(b - 1e-6);
    out.textContent = first === last ? t("battuta {n}", { n: first }) : t("battute {first}–{last}", { first, last });
  }
  const ready = a != null && b != null;
  $("loopOn").disabled = !ready;
  $("loopOn").setAttribute("aria-pressed", String(ready && on));
}

// Mentre suona: barra di avanzamento, fine di "▶ battuta", ritorno da B ad
// A. Con un timer e non con il disegno dei fotogrammi
// (requestAnimationFrame), che si ferma quando la pagina non si vede.
async function watchTransport(token) {
  while (token === state.playToken && state.playing) {
    let tick;
    try { tick = await state.synth.retrievePlayerCurrentTick(); } catch (e) { return; }
    if (token !== state.playToken || !state.playing) return;
    let beat = tick / TICKS_PER_BEAT;
    const stop = state.stopAtBeat;
    const loop = state.loop;
    const looping = !stop && !state.previewing && loop.on && loop.a != null && loop.b != null;
    // Un controllo ogni 40 ms: se la fine (della battuta o del tratto) cade
    // prima del prossimo, si aspetta proprio fino a li'.
    const target = stop ? stop.beat : looping ? loop.b : null;
    if (target != null && beat < target) {
      const wait = (target - beat) * 60000 / (state.bpm || 120);
      if (wait < 45) {
        await new Promise((r) => setTimeout(r, Math.max(0, wait - 3)));
        if (token !== state.playToken || !state.playing) return;
        beat = target;
      }
    }
    if (stop) {
      if (beat >= stop.beat) {
        state.stopAtBeat = null;
        await pause();
        state.pausedTick = stop.restore;
        clearHighlight();
        showPosition(stop.restore / TICKS_PER_BEAT);
        setStatus(t("Fine della battuta"));
        return;
      }
    } else if (looping && beat >= loop.b) {
      state.synth.midiAllNotesOff();
      state.synth.seekPlayer(Math.round(loop.a * TICKS_PER_BEAT));
      lastKey = "";
    }
    if (!state.previewing) {
      showPosition(heardBeat(tick));
      scoreAt(heardBeat(tick));      // anche se i fotogrammi rallentano
    }
    await new Promise((r) => setTimeout(r, 40));
  }
}

function setSpeed(percent) {
  state.speed = percent / 100;
  $("speedOut").value = percent + "%";
  $("speed").setAttribute("aria-valuetext", percent + "%");
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
  clearScoreHighlight();
}

function rangeFor(node, cs, ce) {
  const off = state.song.offsets;
  const r = new Range();
  r.setStart(node, off ? off[cs] : cs);
  r.setEnd(node, off ? off[ce] : ce);
  return r;
}

async function frame() {
  if (!state.playing || state.previewing) return;
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
    const beat = heardBeat(tick);
    state.lastTick = tick;
    highlightAt(beat);
    scoreAt(beat);
  } catch (e) {
    console.warn(e);
  } finally {
    pollBusy = false;
  }
}

function highlightAt(beat) {
  const s = state.song.spans;
  // mappa non ancora pronta, o testo modificato mentre suona
  // (6 numeri per span: traccia, cs, ce, b0, durata, livello)
  if (!s || !state.doc || state.doc.text !== state.song.text) return;
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
    const box = new Highlight(...boxes.map((i) => rangeFor(node, s[i + 1], s[i + 2])));
    const note = new Highlight(...notes.map((i) => rangeFor(node, s[i + 1], s[i + 2])));
    box.priority = 2;     // sopra i colori della sintassi
    note.priority = 3;
    CSS.highlights.set("st-box", box);
    CSS.highlights.set("st-note", note);
  }
  const follow = Number($("follow").value);
  const fi = deepest.get(follow);
  if (fi !== undefined && fi !== lastFollow) {
    lastFollow = fi;
    scrollToRange(rangeFor(node, s[fi + 1], s[fi + 2]));
    if (!highlightApi) setStatus(t("Suona: {token}", { token: state.song.text.slice(s[fi + 1], s[fi + 2]) }));
  }
}

function scrollToRange(range, always = false) {
  const pre = $("text");
  const r = range.getBoundingClientRect();
  const box = pre.getBoundingClientRect();
  if (always || r.top < box.top + 8 || r.bottom > box.bottom - 8) {
    pre.scrollTop += r.top - box.top - box.height / 3;
  }
  if (r.left < box.left || r.right > box.right) {
    pre.scrollLeft += r.left - box.left - 40;
  }
}

// ------------------------------------------------------------ partitura

// Il MusicXML lo fa il motore (st_language.musicxml, come la vista
// Partitura di SoundText), le pagine SVG le disegna verovio nel suo worker
// (score-worker.js), che si avvia alla prima apertura della schermata.
// Durante l'ascolto la nota corrente si colora: la mappa dei tempi di
// verovio da' le note che suonano a ogni battito, la stessa misura del
// lettore (ritornelli sviluppati compresi).
const score = {
  worker: null, nextId: 1, pending: new Map(),
  key: "",            // cosa e' disegnato: testo, tracce, larghezza, scala
  rendering: null,    // Promise del disegno in corso
  timemap: null,      // [[battito, [id accesi], [id spenti]], ...]
  index: -1,          // ultimo evento della mappa applicato
  active: new Set(),  // id delle note colorate
  scale: 40,          // percentuale di verovio, cambia con − e ＋
  choice: null,       // "*" (tutte) o il nome della traccia scelta
};
const SCORE_SCALES = [25, 30, 35, 40, 50, 60, 75];

function scoreCall(msg) {
  if (!score.worker) {
    score.worker = new Worker("score-worker.js");
    score.worker.onmessage = (ev) => {
      const p = score.pending.get(ev.data.id);
      if (!p) return;
      score.pending.delete(ev.data.id);
      if (ev.data.error) p.reject(new Error(ev.data.error)); else p.resolve(ev.data);
    };
    score.worker.onerror = (ev) => {
      for (const p of score.pending.values()) p.reject(new Error(ev.message || "partitura non disponibile"));
      score.pending.clear();
      score.worker = null;
    };
  }
  const id = score.nextId++;
  return new Promise((resolve, reject) => {
    score.pending.set(id, { resolve, reject });
    score.worker.postMessage({ ...msg, id });
  });
}

function resetScore() {
  score.key = "";
  score.timemap = null;
  score.index = -1;
  score.active.clear();
  scoreMessage(t("Apri un brano per vederne la partitura."));
}

// Tutte le tracce se sono poche, altrimenti quella seguita dal lettore:
// sul telefono una partitura d'orchestra intera e' illeggibile.
function fillScoreTracks(tracks) {
  const sel = $("scoreTracks");
  const names = tracks.map((tr) => tr.name);
  sel.innerHTML = "";
  sel.add(new Option(t("Tutte le tracce ({n})", { n: tracks.length }), "*"));
  for (const n of names) sel.add(new Option(n, n));
  if (score.choice !== "*" && !names.includes(score.choice)) {
    score.choice = tracks.length <= 4 ? "*" : names[Number($("follow").value)] || "*";
  }
  sel.value = score.choice;
}

function scoreKey() {
  const width = $("score").clientWidth;
  return JSON.stringify([state.doc && state.doc.text, score.choice, width, score.scale]);
}

async function showScore() {
  if (!state.doc || !document.body.classList.contains("view-partitura")) return;
  if (score.rendering) return score.rendering;
  score.rendering = (async () => {
    try {
      // ridisegna finche' quello disegnato non e' l'ultimo chiesto
      while (scoreKey() !== score.key) await renderScore(scoreKey());
    } finally {
      score.rendering = null;
    }
  })();
  return score.rendering;
}

async function renderScore(key) {
  const box = $("score");
  const t0 = performance.now();
  const tracks = score.choice === "*" ? null : [score.choice];
  let song, xml, r;
  try {
    song = await analyze();
    if (!song) { score.key = key; return; }
    if (!score.timemap) scoreMessage(t("Disegno la partitura…"));
    if (!state.playing) setStatus(t("Disegno la partitura…"));
    xml = await call("musicxml", { tracks });
    // larghezza della pagina nelle unita' di verovio: lo SVG esce largo
    // pageWidth * scale / 100 pixel
    const width = Math.max(240, box.clientWidth - 16);
    r = await scoreCall({ cmd: "render", xml: xml.xml, scale: score.scale, pageWidth: Math.round(width * 100 / score.scale) });
  } catch (e) {
    score.key = key;
    scoreMessage(t("Partitura non disponibile: {message}", { message: errorText(e) }), true);
    return;
  }
  score.key = key;
  box.innerHTML = r.pages.join("");
  // per TalkBack e VoiceOver: le pagine sono figure, con un nome
  for (const svg of box.children) {
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", t("Partitura di {name}, pagina {n} di {total}",
                                     { name: song.name, n: [...box.children].indexOf(svg) + 1, total: r.pages.length }));
  }
  score.timemap = r.timemap;
  score.index = -1;
  score.active.clear();
  if (!state.playing) setStatus(t("Partitura: {n} pagine in {ms} ms", { n: r.pages.length, ms: ms(t0) }));
  Metrics.record("partitura", {
    song: song.name, tracks: tracks ? tracks.length : song.info.tracks.length, pages: r.pages.length,
    musicxml_ms: xml.ms, verovio_boot_ms: r.boot_ms, render_ms: r.render_ms, total_ms: ms(t0), verovio: r.version,
  });
}

function scoreMessage(text, error = false) {
  const p = document.createElement("p");
  p.className = error ? "hint error" : "hint";
  p.textContent = text;
  $("score").replaceChildren(p);
}

function clearScoreHighlight() {
  for (const id of score.active) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("playing");
  }
  score.active.clear();
  score.index = -1;
}

// Colora le note che suonano al battito 'beat'.
function scoreAt(beat) {
  const map = score.timemap;
  if (!map || !document.body.classList.contains("view-partitura")) return;
  // ultimo evento con battito <= beat (ricerca binaria)
  let lo = -1, hi = map.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (map[mid][0] <= beat + 1e-6) lo = mid; else hi = mid - 1;
  }
  if (lo === score.index) return;
  const next = new Set(lo < score.index ? [] : score.active);
  for (let i = lo < score.index ? 0 : score.index + 1; i <= lo; i++) {
    for (const id of map[i][2]) next.delete(id);
    for (const id of map[i][1]) next.add(id);
  }
  score.index = lo;
  let first = null;
  for (const id of score.active) {
    if (!next.has(id)) { const el = document.getElementById(id); if (el) el.classList.remove("playing"); }
  }
  for (const id of next) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.classList.add("playing");
    if (!score.active.has(id) && !first) first = el;
  }
  score.active = next;
  if (first) scrollScoreTo(first);
}

// Tiene in vista la nota che suona: quando esce dal riquadro, la sua riga
// va a un terzo dell'altezza.
function scrollScoreTo(el) {
  const box = $("score");
  const r = el.getBoundingClientRect();
  const b = box.getBoundingClientRect();
  if (r.top < b.top + 8 || r.bottom > b.bottom - 8) box.scrollTop += r.top - b.top - b.height / 3;
}

// Un tocco su una nota porta il lettore all'inizio della sua battuta.
function onScoreTap(ev) {
  const note = ev.target.closest && ev.target.closest("g.note");
  if (!note || !score.timemap) return;
  const hit = score.timemap.find((e) => e[1].includes(note.id));
  if (hit) seekTo(hit[0]);
}

function setScoreScale(step) {
  const i = SCORE_SCALES.indexOf(score.scale);
  score.scale = SCORE_SCALES[Math.max(0, Math.min(SCORE_SCALES.length - 1, i + step))];
  showScore().catch(showError);
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

function setStatus(text, error = false) {
  const el = $("status");
  el.textContent = text;
  el.classList.toggle("error", error);
}

async function loadExample(name) {
  await openExample(name, false);
}

// L'ultimo brano aperto, per riaprirlo all'avvio.
async function restoreLastDoc() {
  let last = null;
  try { last = JSON.parse(localStorage.getItem("stmobile.last") || "null"); } catch (e) {}
  if (last && last.kind === "song" && await Songs.get(last.id)) return openSong(last.id, false);
  if (last && last.kind === "example" && state.examples.includes(last.file)) return openExample(last.file, false);
  return null;
}

async function main() {
  const tPage = performance.now();
  const startedHidden = document.visibilityState === "hidden";
  await I18n.load();
  I18n.translate();
  setupLanguageChoice();
  $("engineState").textContent = t("avvio…");
  if (!window.isSecureContext) {
    // http:// fuori da localhost: niente service worker ne' AudioWorklet
    const warn = document.createElement("p");
    warn.id = "insecure";
    warn.textContent = t("Pagina non sicura: il testo si apre, ma l'audio e l'uso offline non funzionano. " +
      "Usa HTTPS, http://localhost, o in Chrome per Android il flag " +
      "chrome://flags/#unsafely-treat-insecure-origin-as-secure con {origin}.", { origin: location.origin });
    warn.style.cssText = "margin:4px 16px;padding:8px;border-radius:6px;background:#7a2e00;color:#fff;font-size:13px";
    $("view-brani").prepend(warn);
  }
  setupEditor();
  setupMusicBar();
  setupCrea();
  setupStructure();
  setupTransform();
  for (const b of document.querySelectorAll(".tabs button")) b.onclick = () => setView(b.dataset.view);
  let view = "brani";
  try {
    // senza un brano da riaprire si parte da Brani
    if (localStorage.getItem("stmobile.last") && localStorage.getItem("stmobile.last") !== "null") {
      view = localStorage.getItem("stmobile.view") || "brani";
    }
  } catch (e) {}
  setView(view);

  const sw = await serviceWorker();
  const coldCache = !(await cached("vendor/pyodide/pyodide.asm.wasm"));
  startWorker();
  const files = await (await fetch("bundle/files.json")).json();
  state.examples = files.examples;
  $("newSong").onclick = () => newSong().catch(showError);
  $("file").onchange = (ev) => {
    const f = ev.target.files[0];
    ev.target.value = "";
    if (f) openFile(f).catch(showError);
  };
  $("play").onclick = () => play();
  $("speed").oninput = (ev) => setSpeed(Number(ev.target.value));
  $("trans").onchange = (ev) => setTranspose(Number(ev.target.value)).catch(showError);
  $("trans").oninput = (ev) => { $("transOut").value = ev.target.value; };
  $("follow").onchange = () => { lastFollow = -1; };
  $("scoreTracks").onchange = (ev) => { score.choice = ev.target.value; showScore().catch(showError); };
  $("zoomOut").onclick = () => setScoreScale(-1);
  $("zoomIn").onclick = () => setScoreScale(1);
  $("score").addEventListener("click", onScoreTap);
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => showScore().catch(showError), 300);
  });
  const seek = $("seek");
  seek.oninput = () => {
    state.seeking = true;
    const beat = Number(seek.value);
    $("pos").textContent = positionText(beat);
  };
  seek.onchange = () => { state.seeking = false; seekTo(Number(seek.value)); };
  $("loopA").onclick = () => setLoopPoint("a").catch(showError);
  $("loopB").onclick = () => setLoopPoint("b").catch(showError);
  $("loopOn").onclick = () => { state.loop.on = !state.loop.on; renderLoop(); };
  $("metronome").onchange = (ev) => { state.metronome = ev.target.checked; renderMidi().catch(showError); };
  $("goto").onchange = (ev) => {
    if (ev.target.value !== "") goTo(Number(ev.target.value));
    ev.target.value = "";
  };
  $("warnButton").onclick = () => {
    const list = $("warnings");
    list.hidden = !list.hidden;
    $("warnButton").setAttribute("aria-expanded", String(!list.hidden));
  };
  // Schermo bloccato, app in background: il tick si chiede al player (non
  // quello dell'ultimo fotogramma, che in background non si aggiorna), cosi'
  // fra "hidden" e "visible" si vede se la musica e' andata avanti.
  const lifecycle = async (event) => {
    let tick = null;
    try { if (state.synth) tick = await state.synth.retrievePlayerCurrentTick(); } catch (e) {}
    Metrics.record("visibilita", { event, state: document.visibilityState, playing: state.playing,
                                   ctx_state: state.ctx ? state.ctx.state : null, tick });
    if (document.visibilityState === "hidden") saveDoc().catch(() => {});
  };
  document.addEventListener("visibilitychange", () => lifecycle("visibilitychange"));
  // Chrome: pagina congelata o ripresa (risparmio energetico, scheda in background)
  document.addEventListener("freeze", () => lifecycle("freeze"));
  document.addEventListener("resume", () => lifecycle("resume"));

  // La schermata Brani si usa subito, mentre il motore si avvia.
  await renderSongs();
  const restored = restoreLastDoc().catch(() => null);
  if (!state.doc) setStatus(t("Avvio del motore…"));

  try {
    const boot = await state.booted;
    Metrics.record("avvio", {
      cache: coldCache ? "senza cache (primo avvio)" : "con cache", service_worker: sw,
      page_to_ready_ms: ms(tPage), ...boot, ...Metrics.device(),
      // scheda ricaricata dal browser dopo averla scaricata in background
      discarded: document.wasDiscarded === true, started_hidden: startedHidden,
    });
    $("engineState").textContent = t("pronto in {s} s ({versions})",
                                     { s: (boot.total_ms / 1000).toLocaleString(I18n.locale, { maximumFractionDigits: 1 }), versions: boot.versions });
    call("transforms").then((r) => { bar.transforms = r.result; if (bar.page === 2) renderKeys(); }).catch(() => {});
    setTimeout(prefetchForOffline, 5000);
    await restored;
    if (!state.doc) {
      setStatus(t("Scegli un brano"));
      setView("brani");
    }
    if (new URLSearchParams(location.search).has("misura")) await automaticMeasure();
  } catch (e) {
    $("engineState").textContent = t("errore");
    showError(e);
  }
}

// La scelta della lingua (in fondo alla schermata Brani): l'app si
// ricarica nella nuova lingua.
function setupLanguageChoice() {
  const sel = $("language");
  for (const [code, name] of Object.entries(I18n.LANGUAGES)) sel.add(new Option(name, code));
  sel.value = I18n.language;
  sel.onchange = () => {
    saveDoc().catch(() => {}).finally(() => I18n.setLanguage(sel.value));
  };
}

// ?misura=1: analizza i due esempi della fase 0 e manda le misure con un
// POST a "misure" (il server di prova in mobile/misura_headless.py).
async function automaticMeasure() {
  for (const name of ["symphony_d_minor_box.st", "jazz_aaba.st", "symphony_d_minor_box.st"]) {
    await loadExample(name);
    await state.song.spansReady;
  }
  await measureMemory("fine della misura automatica");
  await fetch("misure", { method: "POST", body: JSON.stringify(Metrics.all()) }).catch(() => {});
}

function showError(e) {
  console.error(e);
  setStatus(shortError(e), true);
}

main();
