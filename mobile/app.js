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

// ------------------------------------------------------------ documento
//
// state.doc e' il brano aperto: { kind: "song" | "example", id, file, name,
// text, eol, bom }. Gli esempi sono in sola lettura: la prima modifica ne
// crea una copia fra i brani dell'utente. state.song e' l'ultima analisi del
// motore (il testo analizzato e' state.song.text): se il testo cambia, si
// rianalizza al prossimo Play.

const NEW_SONG_TEXT = `// Nuovo brano: scrivi qui la tua musica.
// Ogni traccia comincia con il suo nome e i due punti; le battute si separano con |

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
  $("badge").textContent = "esempio: le modifiche creano una copia";
}

// Analizza il testo attuale, se non e' gia' quello analizzato.
async function analyze() {
  const doc = state.doc;
  if (!doc) return null;
  const text = doc.text;
  if (state.song && state.song.text === text) return state.song;
  if (state.analyzing && state.analyzing.text === text) return state.analyzing.promise;
  const promise = (async () => {
    setStatus("Analisi…");
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
    state.midi = r.midi;
    state.midiKey = "";
    state.bpm = (r.info.bpm || 120) * state.speed;
    fillFollow(r.info.tracks);
    setTimeline(r.info.timeline);
    renderMixer();
    // trasposizione, mute, solo e metronomo restano dopo una modifica del testo
    if (midiKey() !== "") await renderMidi();
    const t = r.timings;
    // roundtrip_ms: dalla richiesta al brano pronto da suonare
    Metrics.record("analisi", {
      song: doc.name, chars: text.length, tracks: r.info.tracks.length,
      parse_ms: Math.round(t.parse_s * 1000), midi_ms: Math.round(t.midi_s * 1000),
      worker_total_ms: t.total_ms, roundtrip_ms: roundtrip,
    });
    setStatus(`${r.info.tracks.length} tracce, pronto in ${roundtrip} ms`);
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
function shortError(e) {
  const lines = String(e && e.message || e).trim().split("\n").filter(Boolean);
  return "Errore: " + (lines[lines.length - 1] || "sconosciuto").replace(/^\w*(Error|Exception): /, "");
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
  tracks.forEach((t, i) => sel.add(new Option(t.name, String(i))));
  const melodic = tracks.findIndex((t) => !t.percussion);
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
    setStatus("Copia salvata fra i tuoi brani");
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
  const warn = new Highlight(...c.warnings.filter((w) => w.end > w.start).map((w) => range(w.start, w.end)));
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
  button.setAttribute("aria-label", `${warnings.length} avvisi nel testo`);
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
    where.textContent = `riga ${lineOf(text, w.start)}`;
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
  if (warnings.length) setStatus(`${warnings.length} ${warnings.length === 1 ? "avviso" : "avvisi"} nel testo`);
}

function renderBlocks(blocks) {
  const sel = $("goto");
  sel.innerHTML = '<option value="">Vai a…</option>';
  const groups = { track: "Tracce", box: "Box", pattern: "Pattern" };
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
  const common = [SEP, K("⌫", deleteToken, "wide", "Cancella il token"), K("▶ battuta", playBarAtCaret, "wide play-bar")];
  if (page === 0) {
    return [
      ..."cdefgab".split("").map((n) => K(n, () => insertToken(n))),
      K("r", () => insertToken("r"), "", "pausa"),
      SEP,
      K("#", () => attach("#"), "", "diesis"), K("♭", () => attach("b"), "", "bemolle"),
      K("*3", () => attach("*3")), K("*4", () => attach("*4")), K("*5", () => attach("*5")), K("*6", () => attach("*6")),
      K("~", () => attach("~"), "", "legatura"),
      ...common,
    ];
  }
  if (page === 1) {
    return [
      ...["1:", "2:", "4:", "8:", "16:", "8T:"].map((g) => K(g, () => insertToken(g))),
      SEP,
      ...["2", "3", "4"].map((m) => K(m, () => insertToken(m, false), "", "moltiplicatore " + m)),
      SEP,
      K("|", () => insertToken("|"), "", "stanghetta"),
      K("(", () => insertToken("(", false)), K(")", () => attach(")")),
      K("[", () => insertToken("[", false)), K("]", () => attach("]")),
      ...common,
    ];
  }
  const text = state.doc ? state.doc.text : "";
  const pos = caretPos() ?? text.length;
  const patterns = (checks.last ? checks.last.blocks : []).filter((b) => b.kind === "pattern").map((b) => b.label);
  return [
    ...diatonicChords(keyAt(text, pos)).map((c) => K(c, () => insertToken(c))),
    SEP,
    ...patterns.map((p) => K(p, () => insertToken(p))),
    ...(patterns.length ? [SEP] : []),
    ...bar.transforms.map((t) => K(t.call, () => attach(t.call), "", t.help)),
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
    if (k.aria) { b.title = k.aria; b.setAttribute("aria-label", k.aria === k.label ? k.label : `${k.label}, ${k.aria}`); }
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
  if (at < 0) { setStatus("Il cursore non è su una nota da suonare"); return; }
  const [start, end] = (await call("bar", { args: [song.text, s[at + 3]] })).result;
  if (!state.audioReady) {
    setStatus("Preparo il sintetizzatore e il SoundFont…");
    state.audioReady = initAudio();
  }
  await state.audioReady;
  const keep = state.pausedTick;
  const stop = { beat: end, restore: keep };
  state.stopAtBeat = stop;
  await startPlayer(Math.round(start * TICKS_PER_BEAT));
  setStatus(`Battuta ${barNumber(start)}`);
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

function formatDate(t) {
  return new Date(t).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

async function renderSongs() {
  const list = await Songs.list().catch(() => []);
  const ul = $("mySongs");
  ul.innerHTML = "";
  $("noSongs").hidden = list.length > 0;
  for (const song of list) {
    ul.append(songItem(song.name, `modificato ${formatDate(song.updated)}`,
                       state.doc && state.doc.kind === "song" && state.doc.id === song.id,
                       () => openSong(song.id), [
      ["Rinomina", () => renameSong(song.id)],
      ["Duplica", () => duplicate(song)],
      ["Condividi", () => share(song)],
      ["Elimina", () => deleteSong(song.id), "danger"],
    ]));
  }
  const ex = $("examples");
  ex.innerHTML = "";
  for (const file of state.examples) {
    ex.append(songItem(file.replace(/\.st$/, ""), "sola lettura",
                       state.doc && state.doc.kind === "example" && state.doc.file === file,
                       () => openExample(file, true), [
      ["Crea una copia", async () => duplicate(await exampleDoc(file))],
      ["Condividi", async () => share(await exampleDoc(file))],
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
  more.setAttribute("aria-label", "Altre azioni per " + title);
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

async function exampleDoc(file) {
  const bytes = new Uint8Array(await (await fetch("bundle/examples/" + encodeURIComponent(file))).arrayBuffer());
  const f = StFormat.fromBytes(bytes);
  return { kind: "example", file, name: file.replace(/\.st$/, ""), text: f.text, eol: f.eol, bom: f.bom };
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
  const name = await Songs.freeName("Nuovo brano");
  const song = await Songs.create({ name, text: NEW_SONG_TEXT, source: "nuovo" });
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
  const name = prompt("Nuovo nome del brano", song.name);
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
  if (!confirm(`Eliminare «${song.name}»? Non si può annullare.`)) return;
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

// ------------------------------------------------------------ schermate

function setView(name) {
  document.body.className = "view-" + name;
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
  watchTransport(token);
  synth.waitForPlayerStopped().then(() => {
    if (token !== state.playToken) return;
    state.playing = false;
    state.pausedTick = 0;
    setPlayButton();
    clearHighlight();
    showPosition(0);
    setStatus("Fine del brano");
  });
}

async function play() {
  // Primo tocco: niente await prima di unlockInGesture (iOS).
  const tTap = performance.now();
  const resumed = unlockInGesture();
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
      setStatus("Preparo il sintetizzatore e il SoundFont…");
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
    setStatus("Suona");
    batteryProbe();
    requestAnimationFrame(frame);
  } catch (e) {
    console.error(e);
    if (state.song && state.song.text === (state.doc && state.doc.text)) {
      state.audioReady = null;
      setStatus("Errore audio: " + e.message, true);
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
  setStatus("In pausa");
}

function stop(reset) {
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

function setPlayButton() {
  const b = $("play");
  b.textContent = state.playing ? "❚❚" : "▶";
  b.setAttribute("aria-label", state.playing ? "Pausa" : "Suona");
}

async function setTranspose(semitones) {
  state.semitones = semitones;
  $("transOut").value = (semitones > 0 ? "+" : "") + semitones;
  if (state.song) await renderMidi();
}

// ---- lettore completo: mute, solo, metronomo, avanzamento, loop A-B

// Le tracce da non sentire: con un solo attivo tutte le altre, altrimenti
// quelle in mute.
function silentTracks() {
  const names = state.song ? state.song.info.tracks.map((t) => t.name) : [];
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
  state.midi = r.midi;
  state.midiKey = key;
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
  for (const t of tracks) {
    const li = document.createElement("li");
    li.classList.toggle("silent", silent.has(t.name));
    const name = document.createElement("span");
    name.className = "tname";
    name.textContent = t.name;
    if (t.instrument && t.instrument !== t.name) {
      const small = document.createElement("small");
      small.textContent = t.instrument;
      name.append(small);
    }
    const toggle = (label, set, aria) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.setAttribute("aria-label", `${aria} ${t.name}`);
      b.setAttribute("aria-pressed", String(set.has(t.name)));
      b.onclick = () => {
        if (set.has(t.name)) set.delete(t.name); else set.add(t.name);
        renderMixer();
        renderMidi().catch(showError);
      };
      return b;
    };
    li.append(name, toggle("M", state.muted, "Mute"), toggle("S", state.solo, "Solo"));
    list.append(li);
  }
}

function setTimeline(timeline) {
  const t = timeline && timeline.bars && timeline.bars.length ? timeline : { length: 0, bars: [0] };
  state.timeline = t;
  const seek = $("seek");
  seek.max = String(t.length);
  seek.disabled = !(t.length > 0);
  const loop = state.loop;
  if (loop.b != null && loop.b > t.length + 1e-9) state.loop = { a: null, b: null, on: false };
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

function showPosition(beat) {
  const t = state.timeline;
  if (!state.seeking) $("seek").value = String(Math.max(0, Math.min(beat, t.length)));
  $("pos").textContent = t.length > 0
    ? `battuta ${barNumber(Math.max(0, beat))}/${t.bars.length}` + (state.playing ? ` · ${Math.round(state.bpm)} BPM` : "")
    : "";
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
  if (a == null) out.textContent = "nessun tratto";
  else if (b == null) out.textContent = `dalla battuta ${barNumber(a)}…`;
  else {
    const first = barNumber(a), last = barNumber(b - 1e-6);
    out.textContent = first === last ? `battuta ${first}` : `battute ${first}–${last}`;
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
    const looping = !stop && loop.on && loop.a != null && loop.b != null;
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
        setStatus("Fine della battuta");
        return;
      }
    } else if (looping && beat >= loop.b) {
      state.synth.midiAllNotesOff();
      state.synth.seekPlayer(Math.round(loop.a * TICKS_PER_BEAT));
      lastKey = "";
    }
    showPosition(heardBeat(tick));
    await new Promise((r) => setTimeout(r, 40));
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
    const beat = heardBeat(tick);
    state.lastTick = tick;
    highlightAt(beat);
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
    if (!highlightApi) setStatus("Suona: " + state.song.text.slice(s[fi + 1], s[fi + 2]));
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
  if (!window.isSecureContext) {
    // http:// fuori da localhost: niente service worker ne' AudioWorklet
    const warn = document.createElement("p");
    warn.id = "insecure";
    warn.textContent = "Pagina non sicura: il testo si apre, ma l'audio e l'uso offline non funzionano. " +
      "Usa HTTPS, http://localhost, o in Chrome per Android il flag " +
      "chrome://flags/#unsafely-treat-insecure-origin-as-secure con " + location.origin + ".";
    warn.style.cssText = "margin:4px 16px;padding:8px;border-radius:6px;background:#7a2e00;color:#fff;font-size:13px";
    $("view-brani").prepend(warn);
  }
  setupEditor();
  setupMusicBar();
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
  const seek = $("seek");
  seek.oninput = () => {
    state.seeking = true;
    const beat = Number(seek.value);
    $("pos").textContent = `battuta ${barNumber(beat)}/${state.timeline.bars.length}`;
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
  if (!state.doc) setStatus("Avvio del motore…");

  try {
    const t = await state.booted;
    Metrics.record("avvio", {
      cache: coldCache ? "senza cache (primo avvio)" : "con cache", service_worker: sw,
      page_to_ready_ms: ms(tPage), ...t, ...Metrics.device(),
      // scheda ricaricata dal browser dopo averla scaricata in background
      discarded: document.wasDiscarded === true, started_hidden: startedHidden,
    });
    $("engineState").textContent = `pronto in ${(t.total_ms / 1000).toFixed(1)} s (${t.versions})`;
    call("transforms").then((r) => { bar.transforms = r.result; if (bar.page === 2) renderKeys(); }).catch(() => {});
    await restored;
    if (!state.doc) {
      setStatus("Scegli un brano");
      setView("brani");
    }
    if (new URLSearchParams(location.search).has("misura")) await automaticMeasure();
  } catch (e) {
    $("engineState").textContent = "errore";
    showError(e);
  }
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
