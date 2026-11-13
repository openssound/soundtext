// SoundText Mobile: il testo modificabile, i controlli del testo e la barra musicale. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

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
      if (bar.page === 3 || (bar.page === 0 && drumsAtCaret() !== bar.drums)) renderKeys();
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

const { wordBefore, needsSpaceBefore } = TextEdits;     // app/text-edits.js

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

// I pezzi della batteria, nell'ordine di st-language (PERCUSSION_MAP)
const DRUM_KEYS = ["kick", "snare", "hihat", "hihat_open", "tom1", "tom2", "floor", "crash", "ride",
                   "rimshot", "clap", "hihat_pedal", "cowbell", "tambourine"];

// Il blocco di musica (traccia, box o pattern) in cui sta il cursore, con
// la posizione del cursore; null fuori da ogni blocco, per esempio nel Mixer.
function musicBlockAtCaret() {
  if (!state.doc || !checks.last) return null;
  const pos = caretPos() ?? (voice.caretDoc === state.doc ? voice.caret : null);
  if (pos === null || pos === undefined) return null;
  let here = null;
  for (const b of checks.last.blocks) {
    if (b.start <= pos && (!here || b.start > here.start)) here = b;
  }
  if (!here) return null;
  // un'altra intestazione fra il blocco e il cursore: si e' in un blocco che non e' musica
  const lines = state.doc.text.slice(here.start, pos).split("\n").slice(1);
  if (lines.some((line) => /^[^\s/].*:\s*$/.test(line))) return null;
  return { ...here, pos };
}

// Il cursore e' in una traccia (o in un box) di percussioni?
function drumsAtCaret() {
  const here = musicBlockAtCaret();
  return !!(here && here.percussion);
}

function pageKeys(page) {
  if (page === 0 && bar.drums) {
    return [
      ...DRUM_KEYS.map((n) => K(n, () => insertToken(n), "", t("batteria: {name}", { name: n }))),
      K("r", () => insertToken("r"), "", t("pausa")),
    ];
  }
  if (page === 0) {
    return [
      ..."cdefgab".split("").map((n) => K(n, () => insertToken(n), "", t("nota {n}", { n: n.toUpperCase() }))),
      K("r", () => insertToken("r"), "", t("pausa")),
      SEP,
      K("#", () => attach("#"), "", t("diesis")), K("♭", () => attach("b"), "", t("bemolle")),
      ...[3, 4, 5, 6].map((o) => K("*" + o, () => attach("*" + o), "", t("ottava {n}", { n: o }))),
      K("~", () => attach("~"), "", t("legatura")),
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
    ];
  }
  if (page === 2) {
    const text = state.doc ? state.doc.text : "";
    const pos = caretPos() ?? text.length;
    return diatonicChords(keyAt(text, pos)).map((c) => K(c, () => insertToken(c), "", t("accordo {name}", { name: c })));
  }
  const patterns = (checks.last ? checks.last.blocks : []).filter((b) => b.kind === "pattern").map((b) => b.label);
  return [
    K("✦ " + t("Trasforma"), openTransform, "wide", t("Trasforma il richiamo di pattern sotto il cursore")),
    ...patterns.map((p) => K(p, () => insertToken(p), "", t("pattern {name}", { name: p }))),
    ...(patterns.length ? [SEP] : []),
    ...bar.transforms.map((f) => K(f.call, () => attach(f.call), "", f.help)),
  ];
}

function renderKeys() {
  bar.drums = drumsAtCaret();
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

// (before: dopo una dettatura il cursore e' dopo l'ultima nota, e si vuole
// la battuta appena scritta)
async function playBarAtCaret(before = false) {
  const resumed = unlockInGesture();
  if (!state.doc) return;
  const pos = caretPos() ?? (voice.caretDoc === state.doc ? voice.caret : null) ?? 0;
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
  let best = -1, next = -1, prev = -1;
  for (let i = 0; i < s.length; i += 6) {
    if (s[i + 1] <= pos && pos <= s[i + 2]) {
      if (best < 0 || s[i + 5] > s[best + 5]) best = i;
    } else if (s[i + 1] > pos && (next < 0 || s[i + 1] < s[next + 1])) {
      next = i;
    } else if (s[i + 2] < pos && (prev < 0 || s[i + 2] > s[prev + 2])) {
      prev = i;
    }
  }
  const at = best >= 0 ? best : (before && prev >= 0) || next < 0 ? prev : next;
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

// Annulla e ripeti: la storia e' quella del browser, la stessa della tastiera
// (i tasti scrivono con execCommand, vedi insertToken).
function historyStep(command) {
  if (!state.doc) return;
  const pre = $("text");
  if (document.activeElement !== pre) pre.focus();
  document.execCommand(command);
}

// A capo automatico: le battute lunghe restano nello schermo
const WRAP_KEY = "stmobile.wrap";
function setWrap(on) {
  $("text").classList.toggle("wrap", on);
  $("wrapToggle").setAttribute("aria-pressed", String(on));
  try { localStorage.setItem(WRAP_KEY, on ? "1" : "0"); } catch (e) {}
}

function setupMusicBar() {
  for (const b of document.querySelectorAll(".pages button")) b.onclick = () => setPage(Number(b.dataset.page));
  const run = (f) => () => Promise.resolve(f()).catch(showError);
  $("deleteKey").onclick = run(deleteToken);
  $("playBarKey").onclick = run(playBarAtCaret);
  $("undoKey").onclick = run(() => historyStep("undo"));
  $("redoKey").onclick = run(() => historyStep("redo"));
  let wrap = false;
  try { wrap = localStorage.getItem(WRAP_KEY) === "1"; } catch (e) {}
  setWrap(wrap);
  $("wrapToggle").onclick = () => setWrap(!$("text").classList.contains("wrap"));
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
      // gli accordi seguono la tonalita' al cursore, le note la traccia (batteria o no)
      if (bar.page === 2 || (bar.page === 0 && drumsAtCaret() !== bar.drums)) renderKeys();
    }
  });
  setPage(0);
}

function showMusicBar(on) {
  $("musicbar").hidden = !on;
}
