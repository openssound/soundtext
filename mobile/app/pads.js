// SoundText Mobile: i pad. Gli script di app/ sono caricati in ordine da index.html e condividono
// le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ pad degli accordi e della batteria
//
// Toccare e' piu' naturale che scrivere sul telefono. Due schermate a pad, a tempo col brano:
//  - gli accordi della tonalita' (nove pad: i gradi della scala e due colori). Si provano soli oppure si registra
//    con conteggio e metronomo: ogni tocco vale fino al tocco dopo, quantizzato alla battuta o alla meta'. Ogni pad ha sotto tre tasti per cambiare l'accordo (settima,
//    sospeso, rivolto); tenendo premuto un tasto l'accordo dura quanto lo si tiene. Il risultato e' una traccia di accordi.
//  - otto suoni di batteria su un giro di 1, 2 o 4 battute che si ripete: i colpi si sommano a ogni giro come in
//    una drum machine, a sedicesimi. Il risultato e' una traccia o un pattern (%Groove).
// I suoni partono subito dal tocco (note del sintetizzatore, senza passare dal file MIDI); il tempo registrato si
// prende dall'istante del tocco, non dal suono, meno la latenza di uscita stimata. Il testo ST lo scrive il motore
// (engine.pad_chords_text, pad_drums_text).

const pad = {
  kind: "chords", info: null, key: "C", bpm: 100, barBeats: 4, latency: 0,
  recording: false, t0Perf: 0, t0Audio: 0, countBeats: 4, nextClick: 0, timer: null, lastPos: -1,
  events: [], hits: [], loopBars: 1, text: "", down: new Map(), loops: 0,
};
// i nomi dei pad della batteria (scritti per intero perche' l'estrattore delle traduzioni li trovi)
const padDrumLabel = (name) => ({ kick: t("Cassa"), snare: t("Rullante"), hihat: t("Charleston"), hihat_open: t("Charleston aperto"),
                                  tom_hi: t("Tom alto"), tom2: t("Tom basso"), crash: t("Crash"), ride: t("Ride") })[name] || name;

// ---- audio

// Un contesto audio a bassa latenza (dentro il tocco): se ce n'e' uno per la riproduzione, si rifa'
function padOpenAudio() {
  if (state.ctx && state.ctxHint !== "interactive") {
    stop(true);
    resetSynth();
    try { state.ctx.close(); } catch (e) {}
    state.ctx = null;
  }
  state.ctxHint = "interactive";
  return unlockInGesture();
}

async function padReady() {
  await padOpenResume;
  if (!state.audioReady) {
    setPadStatus(t("Preparo il sintetizzatore e il SoundFont…"));
    state.audioReady = initAudio();
  }
  await state.audioReady;
  if ($("padStatus").textContent === t("Preparo il sintetizzatore e il SoundFont…")) setPadStatus("");
  const synth = state.synth;
  synth.midiProgramChange(0, 0);                    // pianoforte sul canale 1; le percussioni sono sul canale 10
  pad.latency = (state.ctx.baseLatency || 0) + (state.ctx.outputLatency || 0);
  Metrics.record("pad", { hint: state.ctxHint, base_latency_ms: Math.round((state.ctx.baseLatency || 0) * 1000),
                          output_latency_ms: Math.round((state.ctx.outputLatency || 0) * 1000), sample_rate: state.ctx.sampleRate });
  padInfoLine();
}
let padOpenResume = null;

function padBuzz() {
  if (navigator.vibrate && typeof vibrationOn === "function" && vibrationOn()) navigator.vibrate(8);
}

function padNotesOn(chan, notes, velocity = 96) {
  for (const n of notes) state.synth.midiNoteOn(chan, n, velocity);
}
function padNotesOff(chan, notes) {
  for (const n of notes) state.synth.midiNoteOff(chan, n);
}

// ---- il tempo

// il battito di adesso, dall'inizio del conteggio: i battiti prima di 0 sono il conteggio
function padBeatNow() {
  return ((performance.now() - pad.t0Perf) / 1000 - pad.latency) * pad.bpm / 60 - pad.countBeats;
}

function padInfoLine() {
  const ms = Math.round(pad.latency * 1000);
  $("padInfo").textContent = t("Tempo {bpm} BPM · battuta di {n} battiti · latenza stimata {ms} ms", { bpm: Math.round(pad.bpm), n: pad.barBeats, ms });
}

function setPadStatus(text, error = false) {
  $("padStatus").textContent = text;
  $("padStatus").classList.toggle("error", error);
}

// un colpo di metronomo sull'orologio dell'audio
function padClickAt(beatIndex) {
  const when = pad.t0Audio + beatIndex * 60 / pad.bpm;
  humClick(state.ctx, when, beatIndex % pad.barBeats === 0);
}

// ---- il pannello

function padEnabled() {
  if (state.doc) return true;
  setStatus(t("Apri un brano per usare i pad."), true);
  return false;
}

async function openPads(kind) {
  if (!padEnabled()) return;
  padStopAll();
  pad.kind = kind;
  pad.events = []; pad.hits = []; pad.text = "";
  pad.recording = false;
  const bars = state.timeline.bars;
  pad.barBeats = bars.length > 1 ? Math.round(bars[1] - bars[0]) || 4 : 4;
  pad.bpm = (state.song && state.song.info.bpm) || 100;
  pad.latency = 0;
  const dialog = $("padDialog");
  dialog.dataset.kind = kind;
  $("padTitle").textContent = kind === "chords" ? t("Pad degli accordi") : t("Pad della batteria");
  $("padText").textContent = "";
  $("padChordOpts").hidden = kind !== "chords";
  $("padDrumOpts").hidden = kind !== "drums";
  setPadStatus("");
  padInfoLine();
  padOpenResume = padOpenAudio();                  // il tocco che apre il pannello: niente await prima
  dialog.showModal();
  padButtons();
  if (kind === "chords") {
    const choices = (await call("generator_choices", { args: [state.doc.text] })).result;
    const select = $("padKey");
    select.innerHTML = "";
    for (const k of choices.keys) select.add(new Option(k, k));
    pad.key = choices.keys.includes(choices.key) ? choices.key : "C";
    select.value = pad.key;
    await padLoadChords();
  } else {
    pad.info = (await call("pad_info", { args: ["C"] })).result;
    padBuildDrums();
  }
  await padReady().catch((e) => setPadStatus(shortError(e), true));
}

async function padLoadChords() {
  pad.info = (await call("pad_info", { args: [pad.key] })).result;
  padBuildChords();
}

function padStopAll() {
  clearInterval(pad.timer);
  pad.timer = null;
  pad.recording = false;
  for (const [, d] of pad.down) padNotesOff(d.chan, d.notes);
  pad.down.clear();
}

function padClose() {
  padStopAll();
  $("padDialog").close();
}

// ---- la griglia di pad

function padMake(label, small, index) {
  const b = document.createElement("button");
  b.className = "pad-btn";
  b.dataset.index = String(index);
  b.setAttribute("aria-label", small ? `${label}, ${small}` : label);
  const big = document.createElement("span");
  big.textContent = label;
  b.append(big);
  if (small) {
    const s = document.createElement("small");
    s.textContent = small;
    b.append(s);
  }
  return b;
}

// Ogni accordo e' un quadrato diviso in quattro parti uguali: l'accordo e le tre varianti (settima, sospeso, rivolto).
// Tenuto premuto, l'accordo dura quanto lo si tiene (il motore scrive la durata dal rilascio).
function padBuildChords() {
  const grid = $("padGrid");
  grid.className = "pad-grid chords";
  grid.innerHTML = "";
  pad.info.chords.forEach((chord, i) => {
    const cell = document.createElement("div");
    cell.className = "pad-chord";
    const variants = [
      [t("settima"), chord.seventh.symbol, chord.seventh.notes],
      [t("sospeso"), chord.sus.symbol, chord.sus.notes],
      [t("rivolto"), chord.inversion.text, chord.inversion.notes],
    ];
    const main = padMake(chord.symbol, chord.label, i);
    padWire(main, chord.symbol, chord.notes);
    cell.append(main);
    const row = document.createElement("div");
    row.className = "pad-variants";
    for (const [name, text, notes] of variants) {
      const v = document.createElement("button");
      v.className = "pad-btn pad-variant";
      v.setAttribute("aria-label", text === chord.inversion.text ? `${chord.symbol}, ${name}` : `${chord.symbol}, ${name}, ${text}`);
      v.textContent = name;
      padWire(v, text, notes);
      row.append(v);
    }
    cell.append(row);
    grid.append(cell);
  });
}

function padWire(button, text, notes) {
  button.addEventListener("pointerdown", (ev) => padChordDown(ev, text, notes, button));
  for (const type of ["pointerup", "pointercancel"]) button.addEventListener(type, (ev) => padChordUp(ev));
  button.addEventListener("contextmenu", (ev) => ev.preventDefault());
}

function padBuildDrums() {
  const grid = $("padGrid");
  grid.className = "pad-grid drums";
  grid.innerHTML = "";
  pad.info.drums.forEach((drum, i) => {
    const b = padMake(padDrumLabel(drum.name), "", i);
    b.addEventListener("pointerdown", (ev) => padDrumDown(ev, drum, b));
    b.addEventListener("contextmenu", (ev) => ev.preventDefault());
    grid.append(b);
  });
}

function padFlash(button) {
  button.classList.add("down");
  setTimeout(() => button.classList.remove("down"), 120);
}

// ---- accordi

function padChordDown(ev, text, notes, button) {
  ev.preventDefault();
  if (!state.synth) return;
  const beat = padBeatNow();
  padBuzz();
  padFlash(button);
  try { button.setPointerCapture(ev.pointerId); } catch (e) {}          // il dito che esce dal pad lo rilascia lo stesso
  padNotesOn(0, notes);
  const record = pad.recording && beat >= -0.25 ? { beat: Math.max(0, beat), text } : null;
  if (record) pad.events.push(record);
  pad.down.set(ev.pointerId, { chan: 0, notes, record });
}

function padChordUp(ev) {
  const entry = pad.down.get(ev.pointerId);
  if (!entry) return;
  padNotesOff(entry.chan, entry.notes);
  if (entry.record && pad.recording) entry.record.end = Math.max(entry.record.beat, padBeatNow());   // la durata e' il tempo tenuto
  pad.down.delete(ev.pointerId);
}

// ---- batteria

function padDrumDown(ev, drum, button) {
  ev.preventDefault();
  if (!state.synth) return;
  padBuzz();
  padFlash(button);
  state.synth.midiNoteOn(9, drum.midi, 110);
  setTimeout(() => state.synth.midiNoteOff(9, drum.midi), 140);
  if (!pad.recording) return;
  const beat = padBeatNow();
  if (beat < -0.25) return;                          // il conteggio non si registra
  const loop = pad.loopBars * pad.barBeats;
  const snapped = Math.round(Math.max(0, beat) * 4) / 4;                  // a sedicesimi
  pad.hits.push({ beat: snapped % loop, name: drum.name, loop: Math.floor(snapped / loop + 1e-9) });
  padButtons();
}

// il giro che suona da solo: il metronomo (sull'orologio dell'audio) e i colpi gia' registrati
function padTick() {
  if (!pad.recording || !state.ctx) return;
  const ahead = state.ctx.currentTime + 0.12;
  const lastBeatIndex = Math.floor(((ahead - pad.t0Audio) * pad.bpm) / 60);
  while (pad.nextClick <= lastBeatIndex) { padClickAt(pad.nextClick); pad.nextClick++; }
  if (pad.kind !== "drums") return;
  const pos = padBeatNow(), loop = pad.loopBars * pad.barBeats;
  const from = pad.lastPos;
  pad.lastPos = pos;
  if (from < 0 && from !== -1 || pos < 0) return;
  for (const hit of pad.hits) {
    // il colpo suona quando il giro passa di li', dal giro dopo quello in cui e' stato registrato
    for (let k = Math.floor(from / loop); k <= Math.floor(pos / loop); k++) {
      const at = k * loop + hit.beat;
      if (k > hit.loop && at > from && at <= pos) {
        const drum = pad.info.drums.find((d) => d.name === hit.name);
        if (drum) {
          state.synth.midiNoteOn(9, drum.midi, 100);
          setTimeout(() => state.synth.midiNoteOff(9, drum.midi), 120);
        }
      }
    }
  }
}

// ---- registrare

async function padRecord() {
  if (pad.recording) { await padFinish(); return; }
  const resumed = unlockInGesture();                // il tocco
  await resumed;
  await padReady();
  pad.events = []; pad.hits = []; pad.text = "";
  pad.loopBars = Number($("padLoop").value) || 1;
  pad.countBeats = pad.barBeats;
  pad.t0Perf = performance.now() + 150;
  pad.t0Audio = state.ctx.currentTime + 0.15;
  pad.nextClick = 0;
  pad.lastPos = -1;
  pad.recording = true;
  $("padText").textContent = "";
  setPadStatus(t("Conteggio… poi suona: ogni tocco si registra a tempo."));
  clearInterval(pad.timer);
  pad.timer = setInterval(padTick, 10);
  padButtons();
}

async function padFinish() {
  const total = padBeatNow();
  clearInterval(pad.timer);
  pad.timer = null;
  pad.recording = false;
  padButtons();
  try {
    if (pad.kind === "chords") {
      const r = (await call("pad_chords_text", { args: [pad.events, { bar_beats: pad.barBeats, total_beats: Math.max(0, total), grid: $("padGrid2").value }] })).result;
      pad.text = r.text;
      setPadStatus(t("{n} accordi in {bars} battute.", { n: r.chords, bars: r.bars }));
    } else {
      const r = (await call("pad_drums_text", { args: [pad.hits.map((h) => ({ beat: h.beat, name: h.name })), { bars: pad.loopBars, bar_beats: pad.barBeats }] })).result;
      pad.text = r.text;
      setPadStatus(t("{n} colpi in {bars} battute.", { n: r.hits, bars: r.bars }));
    }
    $("padText").textContent = pad.text;
  } catch (e) {
    pad.text = "";
    $("padText").textContent = "";
    setPadStatus(errorText(e.message || String(e)), true);
  }
  padButtons();
}

function padButtons() {
  const has = !!pad.text;
  $("padRecord").textContent = pad.recording ? t("Fine") : t("Registra");
  $("padRecord").setAttribute("aria-pressed", String(pad.recording));
  $("padUndo").hidden = pad.kind !== "drums";
  $("padUndo").disabled = !pad.recording || !pad.hits.length;
  $("padClear").hidden = pad.kind !== "drums";
  $("padClear").disabled = !pad.recording || !pad.hits.length;
  $("padListen").disabled = !has || pad.recording;
  $("padAddTrack").disabled = !has || pad.recording;
  $("padAddPattern").hidden = pad.kind !== "drums";
  $("padAddPattern").disabled = !has || pad.recording;
}

// ---- cio' che si tocca diventa musica

// il corpo della traccia: gli accordi cosi' come sono; la batteria ripetuta fin dove arriva il brano
function padBody() {
  if (pad.kind === "chords") return { instrument: "Piano", name: "Accordi", body: pad.text };
  const lines = pad.text.replace(/^16:\s*/, "").split("\n");
  const songBars = Math.max(pad.loopBars, state.timeline.bars.length);
  const reps = Math.min(64, Math.max(1, Math.ceil(songBars / pad.loopBars)));
  return { instrument: "Drums", name: null, body: "16: " + Array.from({ length: reps }, () => lines.join("\n")).join("\n") };
}

async function padSong() {
  const { instrument, name, body } = padBody();
  return (await call("add_track", { args: [state.doc.text, instrument, body, name] })).result;
}

async function padAddTrack() {
  const { text, name } = await padSong();
  await replaceDocText(text);
  padClose();
  setStatus(t("Traccia «{name}» aggiunta al brano", { name }));
}

async function padAddPattern() {
  const r = (await call("add_pattern", { args: [state.doc.text, "Groove", pad.text] })).result;
  await replaceDocText(r.text);
  padClose();
  setStatus(t("Pattern %{name} aggiunto al brano: richiamalo in una traccia.", { name: r.name }));
}

async function padListen() {
  const resumed = unlockInGesture();
  await resumed;
  const song = await padSong();
  const r = await call("preview", { text: song.text });
  await playPreview(r.midi);
}

function setupPads() {
  $("padChordsOpen").onclick = () => openPads("chords").catch(showError);
  $("padDrumsOpen").onclick = () => openPads("drums").catch(showError);
  $("padClose").onclick = padClose;
  $("padDialog").addEventListener("cancel", () => padStopAll());
  $("padKey").onchange = () => { pad.key = $("padKey").value; padLoadChords().catch(showError); };
  $("padRecord").onclick = () => padRecord().catch((e) => setPadStatus(shortError(e), true));
  $("padUndo").onclick = () => { pad.hits.pop(); padButtons(); };
  $("padClear").onclick = () => { pad.hits = []; padButtons(); };
  $("padListen").onclick = () => padListen().catch((e) => setPadStatus(shortError(e), true));
  $("padAddTrack").onclick = () => padAddTrack().catch((e) => setPadStatus(shortError(e), true));
  $("padAddPattern").onclick = () => padAddPattern().catch((e) => setPadStatus(shortError(e), true));
}
