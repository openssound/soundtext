// SoundText Mobile: «Sentirla un'app». Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ sentirla un'app
//
// Cio' che fa sembrare l'app una vera app: le scorciatoie dell'icona (manifest), «Apri con SoundText» per i
// file .st e «Condividi verso SoundText» per link e testi, il titolo e i tasti sulla schermata di blocco e
// sulle cuffie (Media Session) e una leggera vibrazione sul metronomo.

const system = { sections: null, sectionsFor: null, buzzed: -1 };
const VIBRATE_KEY = "stmobile.vibrate";

// ---- le azioni che arrivano dall'indirizzo: ?azione=nuovo | veloce | idea | ultimo | condividi

// Un link di SoundText dentro un testo: «…#v=1&b=…»
function sharedLinkIn(...texts) {
  for (const text of texts) {
    const m = /#[^\s#]*\bb=[A-Za-z0-9_-]+[^\s#]*/.exec(text || "");
    if (m) return m[0];
  }
  return null;
}

// un testo ST ha le intestazioni del file o almeno una traccia («Piano:» e sotto le battute, rientrate)
const looksLikeSong = (text) => /^\s*(ST:|Tempo:|Metrica:)/m.test(text || "") || /^[A-Za-z_]\w*:[ \t]*\n[ \t]+\S/m.test(text || "");

// Condividi verso SoundText: un link di un brano (si apre) oppure un testo ST (si salva come brano)
async function receiveShared(params) {
  const title = params.get("title") || "", text = params.get("text") || "", url = params.get("url") || "";
  const link = sharedLinkIn(url, text, title);
  if (link) {
    location.hash = link;                          // hashchange -> openSharedLink
    return true;
  }
  if (looksLikeSong(text)) {
    const name = await Songs.freeName(title.trim() || t("Testo condiviso"));
    const song = await Songs.create({ name, text: text.replace(/\r\n/g, "\n"), source: "condiviso verso l'app" });
    await openSong(song.id);
    return true;
  }
  setStatus(t("Quello che hai condiviso non è un brano di SoundText."), true);
  return false;
}

// «Idea al volo»: un brano nuovo e vuoto con la finestra Canta pronta per canticchiare una melodia
async function ideaNow() {
  const name = await Songs.freeName(t("Idea"));
  const text = `// ${t("Idea al volo: canticchia una melodia e diventa testo.")}\n\nST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\nTonalita: C\n\nPiano:\n  `;
  const song = await Songs.create({ name, text, source: "idea al volo" });
  await openSong(song.id);
  await state.booted;
  for (let i = 0; i < 30 && !checks.last; i++) await new Promise((r) => setTimeout(r, 100));
  voice.caretDoc = state.doc;
  voice.caret = state.doc.text.length;             // in fondo, dentro la traccia Piano
  openHum();
}

async function runLaunchAction() {
  const params = new URLSearchParams(location.search);
  const action = params.get("azione");
  if (!action) return;
  history.replaceState(null, "", location.pathname + location.hash);      // la prossima volta non si ripete
  if (action === "nuovo") await newSong();
  else if (action === "veloce") { setView("brani"); await openQuick(); }
  else if (action === "idea") await ideaNow();
  else if (action === "ultimo") { if (state.doc) setView("testo"); }
  else if (action === "condividi") await receiveShared(params);
}

// «Apri con SoundText»: i file .st che il sistema consegna all'app
function setupLaunchFiles() {
  if (!("launchQueue" in window)) return;
  window.launchQueue.setConsumer(async (launch) => {
    for (const handle of launch.files || []) {
      try { await openFile(await handle.getFile()); } catch (e) { showError(e); }
    }
  });
}

// ---- la schermata di blocco e le cuffie

function updateMediaSession() {
  if (!("mediaSession" in navigator)) return;
  const doc = state.doc;
  try {
    navigator.mediaSession.metadata = doc ? new MediaMetadata({
      title: doc.name, artist: "SoundText",
      artwork: [{ src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
                { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" }],
    }) : null;
    navigator.mediaSession.playbackState = !doc ? "none" : state.playing ? "playing" : "paused";
  } catch (e) {}
}

// Le sezioni del brano (battito d'inizio); senza sezioni, un salto di otto battute
async function sectionStarts() {
  const doc = state.doc;
  if (system.sectionsFor !== doc.text) {
    system.sectionsFor = doc.text;
    try { system.sections = (await call("structure", { args: [doc.text] })).result.sections.map((s) => s.beat); }
    catch (e) { system.sections = []; }
  }
  if (system.sections.length > 1) return system.sections;
  return state.timeline.bars.filter((_, i) => i % 8 === 0);
}

// Avanti e indietro di una sezione. Indietro, dopo due battiti dentro la sezione, torna al suo inizio.
async function jumpSection(direction) {
  if (!state.doc || !state.song) return;
  const starts = await sectionStarts();
  const here = state.playing ? heardBeat(state.lastTick) : state.pausedTick / TICKS_PER_BEAT;
  let target;
  if (direction > 0) {
    target = starts.find((b) => b > here + 0.5);
    if (target === undefined) return;
  } else {
    const before = starts.filter((b) => b < here - 2);
    target = before.length ? before[before.length - 1] : 0;
  }
  seekTo(target);
}

function setupMediaSession() {
  if (!("mediaSession" in navigator)) return;
  const set = (action, handler) => { try { navigator.mediaSession.setActionHandler(action, handler); } catch (e) {} };
  set("play", () => { if (!state.playing) play(); });
  set("pause", () => { if (state.playing) pause(); });
  set("stop", () => stop(true));
  set("previoustrack", () => jumpSection(-1).catch(showError));
  set("nexttrack", () => jumpSection(1).catch(showError));
  updateMediaSession();
}

// ---- la vibrazione sul metronomo: un colpo leggero a ogni battito, piu' lungo all'inizio della battuta

const vibrationOn = () => { try { return localStorage.getItem(VIBRATE_KEY) !== "no"; } catch (e) { return true; } };

function buzzAt(beat) {
  if (!state.metronome || !navigator.vibrate || !vibrationOn()) return;
  const whole = Math.floor(beat + 1e-6);
  if (whole === system.buzzed) return;
  system.buzzed = whole;
  const bars = state.timeline.bars;
  navigator.vibrate(bars.some((b) => Math.abs(b - whole) < 1e-6) ? 22 : 10);
}

function setupVibration() {
  const box = $("vibrate");
  if (!navigator.vibrate) { box.closest("label").hidden = true; return; }
  box.checked = vibrationOn();
  box.onchange = () => { try { localStorage.setItem(VIBRATE_KEY, box.checked ? "si" : "no"); } catch (e) {} };
}

function setupSystem() {
  setupLaunchFiles();
  setupMediaSession();
  setupVibration();
}

if (typeof module !== "undefined") module.exports = { sharedLinkIn, looksLikeSong };
