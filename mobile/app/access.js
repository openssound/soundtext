// SoundText Mobile: accessibilita' per chi non vede o vede poco. «Leggi» dice a voce la battuta sotto il cursore
// (la frase la fa il motore, speech.py); la navigazione per battuta e per sezione annuncia dove si arriva; un
// annuncio generico (announce) serve a tutte le schermate. Con uno screen reader la frase va in una regione
// aria-live, e la sintesi vocale del telefono si spegne con la casella «Leggi con la voce del telefono».
"use strict";

const SPEAK_VOICE = "stmobile.speak.voice";

// Un annuncio per lo screen reader, senza niente da vedere: la regione si svuota e si riempie, cosi' il testo
// uguale a quello di prima si legge lo stesso.
function announce(text) {
  const el = $("liveSay");
  if (!el) return;
  el.textContent = "";
  setTimeout(() => { el.textContent = text; }, 40);
}

const voiceOn = () => { try { return localStorage.getItem(SPEAK_VOICE) !== "no"; } catch (e) { return true; } };

// ---- «Leggi»

async function speakCaret() {
  if (!state.doc) return;
  await state.booted;
  const r = (await call("speak_at", { args: [state.doc.text, caretPos()] })).result;
  announce(r.text);
  if (voiceOn() && typeof speak === "function") speak(r.text);
  setStatus(r.text);
}

// ---- navigazione per battuta e per sezione

// Le sezioni del brano, senza ripetizioni di fila: [{ bar (1 = la prima), beat, name }]
async function sectionsOfSong() {
  const doc = state.doc;
  if (!doc) return [];
  if (!state.sectionsFor || state.sectionsFor.text !== doc.text) {
    let sections = [];
    try {
      sections = (await call("structure", { args: [doc.text] })).result.sections || [];
    } catch (e) { sections = []; }
    const merged = [];
    for (const s of sections) if (!merged.length || merged[merged.length - 1].name !== s.name) merged.push(s);
    state.sectionsFor = { text: doc.text, list: merged };
  }
  return state.sectionsFor.list;
}

function sectionAt(sections, beat) {
  let found = null;
  for (const s of sections) if (s.beat <= beat + 1e-6) found = s;
  return found;
}

// «battuta 6 di 32, Ritornello»
async function whereText(beat) {
  const bars = state.timeline.bars.length;
  const section = sectionAt(await sectionsOfSong(), beat);
  const base = t("battuta {n} di {total}", { n: barNumber(Math.max(0, beat)), total: bars });
  return section ? `${base}, ${section.name}` : base;
}

async function navAnnounce(beat) {
  const text = await whereText(beat);
  $("navSay").textContent = "";
  setTimeout(() => { $("navSay").textContent = text; }, 40);
}

async function navBar(delta) {
  if (!state.song || !state.timeline.bars.length) return;
  const here = Math.max(0, await currentBeat());
  const i = Math.max(0, Math.min(state.timeline.bars.length - 1, barIndex(here) + delta));
  const beat = state.timeline.bars[i];
  seekTo(beat);
  await navAnnounce(beat);
}

async function navSection(delta) {
  if (!state.song) return;
  const list = await sectionsOfSong();
  if (!list.length) { await navBar(delta > 0 ? 4 : -4); return; }
  const here = Math.max(0, await currentBeat());
  const current = sectionAt(list, here);
  let index = current ? list.indexOf(current) : 0;
  // «precedente» dentro la sezione torna al suo inizio
  if (delta < 0 && current && here - current.beat > 1e-6 && barIndex(here) > barIndex(current.beat)) index += 1;
  index = Math.max(0, Math.min(list.length - 1, index + delta));
  const beat = list[index].beat;
  seekTo(beat);
  await navAnnounce(beat);
}

async function navGoto() {
  if (!state.song) return;
  const total = state.timeline.bars.length;
  const answer = prompt(t("Vai alla battuta (1–{total})", { total }), String(barNumber(Math.max(0, await currentBeat()))));
  const n = parseInt(answer, 10);
  if (!n || n < 1 || n > total) return;
  const beat = state.timeline.bars[n - 1];
  seekTo(beat);
  await navAnnounce(beat);
}

// La barra di avanzamento dice dove e': battuta e sezione (per TalkBack e VoiceOver)
async function updateSeekSpoken(beat) {
  if (!state.song || state.timeline.length <= 0) return;
  $("seek").setAttribute("aria-valuetext", await whereText(beat));
}

function setupAccess() {
  const voice = $("speakVoice");
  voice.checked = voiceOn();
  voice.onchange = () => { try { localStorage.setItem(SPEAK_VOICE, voice.checked ? "si" : "no"); } catch (e) {} };
  $("speakKey").onclick = () => speakCaret().catch(showError);
  $("navPrevBar").onclick = () => navBar(-1).catch(showError);
  $("navNextBar").onclick = () => navBar(1).catch(showError);
  $("navPrevSection").onclick = () => navSection(-1).catch(showError);
  $("navNextSection").onclick = () => navSection(1).catch(showError);
  $("navGoto").onclick = () => navGoto().catch(showError);
  // sulla barra di avanzamento, spostarsi con i gesti dello screen reader dice dove si arriva
  $("seek").addEventListener("change", () => { updateSeekSpoken(parseFloat($("seek").value) || 0); });
}
