// SoundText Mobile: la partitura e le misure di memoria e batteria. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

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
  if (!state.playing) setStatus(r.pages.length === 1 ? t("Partitura: 1 pagina") : t("Partitura: {n} pagine", { n: r.pages.length }));
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
