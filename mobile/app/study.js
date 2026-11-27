// SoundText Mobile: modalita' studio. Tre strumenti: l'accordatore, «Suona con la base» (il microfono ascolta
// e ogni nota della partitura si valuta) e la vista accordi per chi suona dal vivo. Il calcolo (altezza delle
// note, valutazione) sta in studio.js, che si prova da Node; qui c'e' la parte con la pagina: microfono,
// finestre, suoni e vibrazioni. L'audio resta sul telefono. Per chi non vede: ogni colore ha anche un segno
// e un testo, e il risultato si legge in una regione aria-live.
"use strict";

// ------------------------------------------------------------ microfono (comune)

// Apre il microfono (da chiamare dentro un tocco) e passa a 'onBlock' i blocchi di campioni (4096 alla volta).
async function studioMic(onBlock) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error(t("Questo browser non dà il microfono alle pagine"));
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
    });
    if (navigator.audioSession) { try { navigator.audioSession.type = "play-and-record"; } catch (e) {} }
    await ctx.resume();
    let node = null;
    if (ctx.audioWorklet && window.AudioWorkletNode) {
      try {
        await ctx.audioWorklet.addModule("voice-worklet.js");
        node = new AudioWorkletNode(ctx, "voice-tap", { numberOfInputs: 1, numberOfOutputs: 0 });
        node.port.onmessage = (ev) => onBlock(ev.data, ctx.sampleRate);
      } catch (e) { node = null; }
    }
    if (!node) {
      node = ctx.createScriptProcessor(4096, 1, 1);
      node.onaudioprocess = (ev) => onBlock(ev.inputBuffer.getChannelData(0).slice(), ctx.sampleRate);
      node.connect(ctx.destination);
    }
    ctx.createMediaStreamSource(stream).connect(node);
    return {
      ctx,
      stop() {
        try { node.onaudioprocess = null; if (node.port) node.port.onmessage = null; } catch (e) {}
        stream.getTracks().forEach((tr) => tr.stop());
        ctx.close().catch(() => {});
        if (navigator.audioSession && $("audioSession").checked) { try { navigator.audioSession.type = "playback"; } catch (e) {} }
      },
    };
  } catch (e) {
    if (stream) stream.getTracks().forEach((tr) => tr.stop());
    ctx.close().catch(() => {});
    const denied = e && (e.name === "NotAllowedError" || e.name === "SecurityError");
    throw new Error(denied ? t("Microfono non permesso: consentilo nelle impostazioni del browser") : (e.message || String(e)));
  }
}

function noteLabel(midi) {
  return Studio.NAMES[((midi % 12) + 12) % 12] + (Math.floor(midi / 12) - 1);
}

// Un suono breve (anche per chi non vede i colori) e, se si puo', una vibrazione
function studioBeep(ctx, hz, seconds = 0.12) {
  try {
    const osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.frequency.value = hz;
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + seconds);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + seconds + 0.02);
  } catch (e) {}
}

function speak(text) {
  if (!window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = document.documentElement.lang || "it";
    window.speechSynthesis.speak(u);
  } catch (e) {}
}

// ------------------------------------------------------------ accordatore

const tuner = { mic: null, ctx: null, a4: 440, string: null, recent: [], silent: 0, inTune: false, lastBuzz: 0, spokeAt: 0,
                spokeNote: null, toneUntil: 0, last: null, tap: 0 };
const TUNER_A4 = "stmobile.tuner.a4";

function tunerStrings() {
  const preset = $("tunerPreset").value;
  return Studio.TUNINGS[preset] || [];
}

function tunerDescribe(n) {
  const name = n.name + n.octave;
  if (Math.abs(n.cents) <= 5) return t("{note}, intonata", { note: name });
  return n.cents < 0 ? t("{note}, calante di {cents} cent", { note: name, cents: -n.cents })
                    : t("{note}, crescente di {cents} cent", { note: name, cents: n.cents });
}

function tunerRender() {
  const n = tuner.last;
  $("tunerNote").textContent = n ? n.name + n.octave : "–";
  $("tunerCents").textContent = n ? (n.cents > 0 ? "+" : "") + n.cents + " cent" : "";
  const needle = $("tunerNeedle");
  needle.style.left = (n ? 50 + Math.max(-50, Math.min(50, n.cents)) : 50) + "%";
  needle.classList.toggle("ok", !!n && Math.abs(n.cents) <= 5);
  $("tunerFace").setAttribute("aria-label", n ? tunerDescribe(n) : t("Nota riconosciuta: tocca due volte per sentirla a voce"));
}

function tunerBlock(block, rate) {
  const now = performance.now();
  if (now < tuner.toneUntil) return;                       // si sta sentendo il tono di riferimento
  const r = Studio.detectPitch(block, rate, { minHz: 60 });
  if (!r.hz || r.clarity < 0.8) {
    if (++tuner.silent > 4) { tuner.last = null; tuner.recent = []; tuner.inTune = false; tunerRender(); }
    return;
  }
  tuner.silent = 0;
  let midi = Studio.midiOf(r.hz, tuner.a4);
  tuner.recent.push(midi);
  if (tuner.recent.length > 3) tuner.recent.shift();
  midi = [...tuner.recent].sort((a, b) => a - b)[tuner.recent.length >> 1];
  let n = Studio.noteOf(Studio.hzOf(midi, tuner.a4), tuner.a4);
  const strings = tunerStrings();
  if (strings.length) {                                     // la corda scelta, o la piu' vicina
    const target = tuner.string != null ? strings[tuner.string] : strings.reduce((b, s) => Math.abs(s - midi) < Math.abs(b - midi) ? s : b, strings[0]);
    n = { midi: target, name: Studio.NAMES[target % 12], octave: Math.floor(target / 12) - 1, cents: Math.round((midi - target) * 100) };
  }
  tuner.last = n;
  tunerRender();
  if ($("tunerBuzz").checked && navigator.vibrate) {      // impulsi che rallentano avvicinandosi alla nota giusta
    const gap = 160 + Math.min(Math.abs(n.cents), 50) * 14;
    if (Math.abs(n.cents) > 5 && now - tuner.lastBuzz > gap) { navigator.vibrate(30); tuner.lastBuzz = now; }
  }
  const good = Math.abs(n.cents) <= 5;
  if (good && !tuner.inTune) {                              // segnale chiaro: la corda e' intonata
    tuner.inTune = true;
    if (tuner.ctx) studioBeep(tuner.ctx, 1320, 0.25);
    if (navigator.vibrate && $("tunerBuzz").checked) navigator.vibrate(220);
    $("tunerSay").textContent = tunerDescribe(n);
  } else if (!good) {
    tuner.inTune = false;
  }
  if ($("tunerSpeak").checked && now - tuner.spokeAt > 2500) {
    tuner.spokeAt = now;
    speak(tunerDescribe(n));
  }
}

function tunerRead() {
  const text = tuner.last ? tunerDescribe(tuner.last) : t("Nessuna nota: suona una corda.");
  $("tunerSay").textContent = "";
  setTimeout(() => { $("tunerSay").textContent = text; }, 30);
  if ($("tunerSpeak").checked) speak(text);
}

async function tunerStart() {
  const button = $("tunerStart");
  if (tuner.mic) { tunerStop(); return; }
  button.disabled = true;
  try {
    if (state.playing) await pause();
    tuner.a4 = Math.max(415, Math.min(466, parseInt($("tunerA4").value, 10) || 440));
    $("tunerA4").value = String(tuner.a4);
    try { localStorage.setItem(TUNER_A4, String(tuner.a4)); } catch (e) {}
    tuner.mic = await studioMic((block, rate) => tunerBlock(block, rate));
    tuner.ctx = tuner.mic.ctx;
    $("tunerSay").textContent = t("Ascolto: suona una nota.");
    button.setAttribute("aria-pressed", "true");
    button.textContent = t("Ferma");
  } catch (e) {
    $("tunerSay").textContent = shortError(e);
  }
  button.disabled = false;
}

function tunerStop() {
  if (tuner.mic) tuner.mic.stop();
  tuner.mic = null;
  tuner.ctx = null;
  tuner.last = null;
  tuner.recent = [];
  tuner.inTune = false;
  $("tunerStart").setAttribute("aria-pressed", "false");
  $("tunerStart").textContent = t("Ascolta");
  tunerRender();
}

// Il tono di una corda, per accordare a orecchio (il microfono sta zitto mentre suona)
function tunerPlayString(i) {
  tuner.string = tuner.string === i ? null : i;
  renderTunerStrings();
  if (tuner.string == null) return;
  const midi = tunerStrings()[i];
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = tuner.ctx || (tuner.toneCtx = tuner.toneCtx || new Ctx());
  ctx.resume();
  const osc = ctx.createOscillator(), gain = ctx.createGain();
  osc.frequency.value = Studio.hzOf(midi, tuner.a4);
  gain.gain.setValueAtTime(0.0001, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime + 0.05);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 2);
  osc.connect(gain).connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 2.05);
  tuner.toneUntil = performance.now() + 2300;
  $("tunerSay").textContent = t("Corda scelta: {note}", { note: noteLabel(midi) });
}

function renderTunerStrings() {
  const box = $("tunerStrings");
  const strings = tunerStrings();
  box.hidden = !strings.length;
  box.innerHTML = "";
  strings.forEach((midi, i) => {
    const b = document.createElement("button");
    b.textContent = noteLabel(midi);
    b.setAttribute("aria-pressed", String(tuner.string === i));
    b.setAttribute("aria-label", t("Corda {n}: {note}", { n: i + 1, note: noteLabel(midi) }));
    b.onclick = () => tunerPlayString(i);
    box.append(b);
  });
}

function setupTuner() {
  const preset = $("tunerPreset");
  for (const [value, label] of [["", t("Libero (ogni nota)")], ["chitarra", t("Chitarra")], ["basso", t("Basso")],
                                ["violino", t("Violino")], ["ukulele", t("Ukulele")]]) {
    const o = document.createElement("option");
    o.value = value;
    o.textContent = label;
    preset.append(o);
  }
  preset.onchange = () => { tuner.string = null; renderTunerStrings(); };
  try { $("tunerA4").value = localStorage.getItem(TUNER_A4) || "440"; } catch (e) {}
  $("tunerOpen").onclick = () => { tuner.string = null; renderTunerStrings(); tunerRender(); $("tunerDialog").showModal(); };
  $("tunerStart").onclick = () => tunerStart();
  $("tunerRead").onclick = () => tunerRead();
  $("tunerClose").onclick = () => $("tunerDialog").close();
  $("tunerFace").onclick = () => {                           // due tocchi: la lettura
    const now = performance.now();
    if (now - tuner.tap < 450) tunerRead();
    tuner.tap = now;
  };
  $("tunerFace").onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); tunerRead(); } };
  $("tunerDialog").addEventListener("close", () => {
    tunerStop();
    if (tuner.toneCtx) { tuner.toneCtx.close().catch(() => {}); tuner.toneCtx = null; }
  });
}

// ------------------------------------------------------------ suona con la base

const study = { notes: [], track: null, mic: null, pairs: [], frames: [], graded: [], running: false, prevMuted: null, poll: null,
                chips: [], bars: [], from: 0, to: null, timers: [], wasPlaying: false };
const STUDY_MIC_LAG = 0.04;           // secondi: il ritardo del microfono, da togliere ai frame

function studySay(text, error = false) {
  const el = $("studyStatus");
  el.classList.toggle("error", error);
  el.textContent = text;
}

function studyTracks() {
  return state.song ? state.song.info.tracks.filter((tr) => !tr.percussion) : [];
}

async function studyLoadNotes() {
  const name = $("studyTrack").value;
  study.track = name;
  study.notes = [];
  renderStudyNotes();
  if (!name) return;
  const notes = (await call("track_notes", { args: [state.doc.text, name] })).result;
  if ($("studyTrack").value !== name) return;
  study.notes = notes;
  renderStudyNotes();
  $("studyStart").disabled = !notes.length;
  studySay(notes.length ? t("{n} note da suonare.", { n: notes.length })
                        : t("Questa traccia non ha note da suonare a una voce: sceglierne un'altra."), !notes.length);
}

function studyWindow() {
  const loop = state.loop;
  if ($("studyLoop").checked && loop.a != null && loop.b != null) return [loop.a, loop.b];
  return [0, state.timeline.length];
}

function renderStudyNotes() {
  const list = $("studyNotes");
  const [from, to] = studyWindow();
  list.innerHTML = "";
  study.chips = [];
  list.hidden = !study.notes.length;
  study.notes.forEach((n, i) => {
    if (n[0] < from - 1e-6 || n[0] >= to - 1e-6) { study.chips.push(null); return; }
    const li = document.createElement("li");
    li.dataset.status = "wait";
    li.textContent = noteLabel(n[2]);
    const bar = document.createElement("small");
    bar.textContent = String(barNumber(n[0]));
    li.prepend(bar);
    li.setAttribute("aria-label", t("battuta {n}", { n: barNumber(n[0]) }) + ", " + noteLabel(n[2]));
    list.append(li);
    study.chips.push(li);
  });
}

const STUDY_MARK = { ok: "✓", near: "~", bad: "✗", missing: "–", wait: "" };
function studyWord(status) {
  return { ok: t("giusta"), near: t("quasi"), bad: t("sbagliata"), missing: t("mancante") }[status] || "";
}

function paintChip(i, r) {
  const li = study.chips[i];
  if (!li) return;
  li.dataset.status = r.status;
  li.textContent = noteLabel(r.target);
  const bar = document.createElement("small");
  bar.textContent = String(barNumber(r.start));
  li.prepend(bar);
  const mark = document.createElement("b");
  mark.textContent = STUDY_MARK[r.status];
  mark.setAttribute("aria-hidden", "true");
  li.append(mark);
  li.setAttribute("aria-label", `${t("battuta {n}", { n: barNumber(r.start) })}, ${noteLabel(r.target)}: ${studyWord(r.status)}`);
}

// Il battito in cui il microfono ha sentito 'perf' (ms), dalle posizioni lette del lettore
function studyBeatAt(perf) {
  const p = study.pairs;
  if (!p.length || perf < p[0].t - 60) return null;
  let i = p.length - 1;
  while (i > 0 && p[i].t > perf) i--;
  const a = p[i], b = p[i + 1];
  if (!b) return a.beat + (perf - a.t) / 1000 * (state.bpm || 120) / 60;
  const span = b.t - a.t;
  if (span <= 0 || Math.abs(b.beat - a.beat) > 1) return a.beat;      // un salto (il loop): niente interpolazione
  return a.beat + (b.beat - a.beat) * (perf - a.t) / span;
}

function studyBlock(block, rate) {
  if (!study.running) return;
  const perf = performance.now() - block.length / rate * 500 - STUDY_MIC_LAG * 1000;     // il centro del blocco
  const beat = studyBeatAt(perf);
  if (beat == null) return;
  const r = Studio.detectPitch(block, rate);
  study.frames.push({ beat, midi: r.hz && r.clarity >= 0.75 ? Studio.midiOf(r.hz) : 0 });
}

function studyOptions() {
  return { bpm: state.bpm || (state.song && state.song.info.bpm) || 120, bars: state.timeline.bars };
}

// Le note finite da un po': si valutano subito, per il colore e il suono mentre si suona
function studyGradeLive(beat) {
  const opts = studyOptions();
  const wait = 0.35 * opts.bpm / 60;
  study.notes.forEach((n, i) => {
    if (study.graded[i] || !study.chips[i] || beat < n[0] + n[1] + wait) return;
    study.graded[i] = true;
    const r = Studio.evaluate([n], study.frames, opts).notes[0];
    paintChip(i, r);
    if ((r.status === "bad" || r.status === "missing") && $("studyBeep").checked) {
      studyBeep();
    }
  });
  const now = study.notes.findIndex((n, i) => study.chips[i] && !study.graded[i]);
  if (now >= 0 && study.chips[now]) study.chips[now].scrollIntoView({ block: "nearest" });
}

function studyBeep() {
  if (state.ctx) studioBeep(state.ctx, 196, 0.14);
  if (navigator.vibrate) navigator.vibrate(60);
}

async function studyStart() {
  if (study.running) { await studyFinish(); return; }
  if (!state.doc || !study.notes.length) return;
  const resumed = unlockInGesture();                    // il tocco
  $("studyStart").disabled = true;
  $("studyResult").hidden = true;
  try {
    if (state.playing) await pause();
    study.mic = await studioMic((block, rate) => studyBlock(block, rate));
    await resumed;
    study.prevMuted = [...state.muted];
    state.muted.add(study.track);
    renderMixer();
    await renderMidi();
    const [from, to] = studyWindow();
    study.from = from;
    study.to = to;
    study.pairs = [];
    study.frames = [];
    study.graded = [];
    renderStudyNotes();
    state.pausedTick = Math.round(from * TICKS_PER_BEAT);
    state.stopAtBeat = null;
    if ($("studyLoop").checked && state.loop.a != null && state.loop.b != null) { state.loop.on = true; renderLoop(); }
    const bpm = (state.bpm || state.song.info.bpm || 120);
    const beats = state.timeline.bars.length > 1 ? Math.round(state.timeline.bars[1] - state.timeline.bars[0]) : 4;
    if ($("studyCount").checked) {
      studySay(t("Conto una battuta…"));
      const first = state.ctx.currentTime + 0.2;
      for (let i = 0; i < beats; i++) humClick(state.ctx, first + i * 60 / bpm, i === 0);
      await new Promise((r) => setTimeout(r, (0.2 + beats * 60 / bpm) * 1000));
    }
    study.running = true;
    study.wasPlaying = false;
    $("studyStart").setAttribute("aria-pressed", "true");
    $("studyStart").textContent = t("Ferma");
    $("studyStart").disabled = false;
    studySay(t("Suona!"));
    const startLoop = () => { if (study.poll == null) study.poll = setInterval(() => studyPoll().catch(showError), 40); };
    await play();
    startLoop();
  } catch (e) {
    console.error(e);
    studySay(shortError(e), true);
    studyCleanup();
    $("studyStart").disabled = false;
  }
}

async function studyPoll() {
  if (!study.running) return;
  if (!state.playing) {
    if (study.wasPlaying) await studyFinish();
    return;
  }
  study.wasPlaying = true;
  const tick = await playerTick();
  const beat = heardBeat(tick);
  study.pairs.push({ t: performance.now(), beat });
  if (study.pairs.length > 400) study.pairs.splice(0, 100);
  studyGradeLive(beat);
  if (study.to != null && !($("studyLoop").checked) && beat >= study.to) { await pause(); await studyFinish(); }
}

function studyCleanup() {
  study.running = false;
  if (study.poll != null) { clearInterval(study.poll); study.poll = null; }
  if (study.mic) { study.mic.stop(); study.mic = null; }
  if (study.prevMuted) {
    state.muted = new Set(study.prevMuted);
    study.prevMuted = null;
    renderMixer();
    renderMidi().catch(showError);
  }
  $("studyStart").setAttribute("aria-pressed", "false");
  $("studyStart").textContent = t("Comincia");
}

async function studyFinish() {
  if (!study.running) return;
  if (state.playing) await pause();
  const frames = study.frames;
  studyCleanup();
  const notes = study.notes.filter((n, i) => study.chips[i]);
  if (!notes.length) { studySay(t("In questo tratto non ci sono note da suonare."), true); return; }
  const result = Studio.evaluate(notes, frames, studyOptions());
  let at = 0;
  study.notes.forEach((n, i) => { if (study.chips[i]) paintChip(i, result.notes[at++]); });
  const base = t("Intonazione {i} per cento, tempo {t} per cento.", { i: result.intonation, t: result.timing });
  const tail = result.review.length
    ? " " + t("Da ripassare: battute {bars}.", { bars: result.review.slice(0, 8).join(", ") })
      + (result.review.length > 8 ? " " + t("E altre {n}.", { n: result.review.length - 8 }) : "")
    : " " + t("Nessuna battuta da ripassare.");
  $("studyResult").hidden = false;
  $("studySummary").textContent = "";
  setTimeout(() => { $("studySummary").textContent = base + tail; }, 30);
  studySay("");
  const box = $("studyReview");
  box.innerHTML = "";
  for (const n of result.review.slice(0, 8)) {                // le prime otto: il resto si legge nel riepilogo
    const b = document.createElement("button");
    b.textContent = t("Ripassa la battuta {n}", { n });
    b.onclick = () => {                                 // un loop A-B su quella battuta
      const i = n - 1;
      state.loop = { a: state.timeline.bars[i], b: barEnd(i), on: true };
      renderLoop();
      $("studyLoop").checked = true;
      renderStudyNotes();
      studySay(t("Ripasso pronto: tocca Comincia."));
    };
    box.append(b);
  }
  Metrics.record("studio", { notes: notes.length, intonation: result.intonation, timing: result.timing, review: result.review.length });
}

async function openStudy() {
  const tracks = studyTracks();
  const select = $("studyTrack");
  select.innerHTML = "";
  for (const tr of tracks) {
    const o = document.createElement("option");
    o.value = tr.name;
    o.textContent = tr.name;
    select.append(o);
  }
  $("studyResult").hidden = true;
  $("studyStart").disabled = true;
  studySay(tracks.length ? "" : t("Il brano non ha tracce con note da suonare."), !tracks.length);
  const follow = $("follow").value;
  if (follow && tracks.some((tr) => tr.name === follow)) select.value = follow;
  $("studyDialog").showModal();
  if (tracks.length) await studyLoadNotes();
}

function setupStudyPlayAlong() {
  $("playAlongOpen").onclick = () => openStudy().catch(showError);
  $("studyTrack").onchange = () => studyLoadNotes().catch(showError);
  $("studyLoop").onchange = () => renderStudyNotes();
  $("studyStart").onclick = () => studyStart();
  $("studyClose").onclick = () => $("studyDialog").close();
  $("studyDialog").addEventListener("close", () => {
    if (study.running) { if (state.playing) pause(); studyCleanup(); }
  });
}

// ------------------------------------------------------------ vista accordi

const chart = { data: [], cells: [], bars: [], timer: null, wake: null, counting: false, lastBar: -1, lastBuzz: -1 };
const CHART_AWAKE = "stmobile.chart.awake";

// I nomi degli accordi di una battuta: quello che c'e' all'inizio e quelli che cambiano dentro
function chartBarLabels(i) {
  const bars = state.timeline.bars;
  const start = bars[i], end = i + 1 < bars.length ? bars[i + 1] : state.timeline.length;
  const labels = [];
  for (const [b, d, label] of chart.data) {
    // l'accordo che arriva dalla battuta prima e quelli che cominciano in questa; lo stesso di fila una volta sola
    if (b < end - 1e-6 && b + d > start + 1e-6 && labels[labels.length - 1] !== label) labels.push(label);
  }
  return labels;
}

function chartShape(label) {
  const capo = parseInt($("chartCapo").value, 10) || 0;
  return capo ? Studio.transposeChord(label, -capo) : label;
}

function chartRenderBars() {
  const box = $("chartBars");
  box.innerHTML = "";
  chart.cells = [];
  state.timeline.bars.forEach((_, i) => {
    const b = document.createElement("button");
    b.setAttribute("role", "listitem");
    const labels = chartBarLabels(i).map(chartShape);
    b.innerHTML = "";
    const n = document.createElement("small");
    n.textContent = String(i + 1);
    const c = document.createElement("span");
    c.textContent = labels.join(" ") || "·";
    if (labels.length > 2 || labels.join("").length > 9) b.classList.add("many");   // tante sigle: piu' piccole, su due righe
    b.append(n, c);
    b.setAttribute("aria-label", t("battuta {n}", { n: i + 1 }) + ": " + (labels.join(", ") || t("nessun accordo")));
    b.onclick = () => { seekTo(state.timeline.bars[i]); chartUpdate().catch(showError); };
    box.append(b);
    chart.cells.push(b);
  });
  chart.lastBar = -1;
}

function chordAt(beat) {
  let now = null, next = null;
  for (const c of chart.data) {
    if (c[0] <= beat + 1e-6) now = c; else { next = c; break; }
  }
  return { now, next };
}

async function chartUpdate() {
  if (chart.counting) return;
  const beat = Math.max(0, await currentBeat());
  const { now, next } = chordAt(beat);
  $("chartNow").textContent = now ? chartShape(now[2]) : "–";
  $("chartNext").textContent = next ? t("poi {chord}", { chord: chartShape(next[2]) }) : "";
  const i = barIndex(beat);
  if (i !== chart.lastBar) {
    if (chart.cells[chart.lastBar]) chart.cells[chart.lastBar].removeAttribute("aria-current");
    const cell = chart.cells[i];
    if (cell) { cell.setAttribute("aria-current", "true"); cell.scrollIntoView({ block: "center", behavior: "smooth" }); }
    chart.lastBar = i;
  }
  const whole = Math.floor(beat + 1e-6);
  if (state.playing && $("chartBuzz").checked && navigator.vibrate && whole !== chart.lastBuzz) {
    chart.lastBuzz = whole;
    navigator.vibrate(state.timeline.bars.some((b) => Math.abs(b - whole) < 1e-6) ? 30 : 12);
  }
  const play = $("chartPlay");
  const label = state.playing ? t("Pausa") : t("Suona");
  play.textContent = state.playing ? "⏸" : "▶";
  play.setAttribute("aria-label", label);
}

async function chartPlay() {
  if (state.playing) { await pause(); chartAnnounce(t("In pausa")); return chartUpdate(); }
  const resumed = unlockInGesture();
  const bars = parseInt($("chartCount").value, 10) || 0;
  if (bars > 0 && state.song) {
    const bpm = state.bpm || state.song.info.bpm || 120;
    const perBar = state.timeline.bars.length > 1 ? Math.round(state.timeline.bars[1] - state.timeline.bars[0]) : 4;
    await resumed;
    chart.counting = true;
    const total = bars * perBar;
    const first = state.ctx.currentTime + 0.15;
    for (let i = 0; i < total; i++) humClick(state.ctx, first + i * 60 / bpm, i % perBar === 0);
    for (let i = 0; i < total; i++) {
      $("chartNow").textContent = String((i % perBar) + 1);
      if (navigator.vibrate && $("chartBuzz").checked) navigator.vibrate(i % perBar === 0 ? 30 : 12);
      await new Promise((r) => setTimeout(r, 60000 / bpm));
    }
    chart.counting = false;
  }
  await play();
  chartAnnounce(t("Suona"));
}

function chartAnnounce(text) {
  const el = $("chartAnnounce");
  el.textContent = "";
  setTimeout(() => { el.textContent = text; }, 30);
}

function chartStep(delta) {
  const i = Math.max(0, Math.min(state.timeline.bars.length - 1, barIndex(Math.max(0, state.playing ? heardBeat(state.lastTick || 0) : state.pausedTick / TICKS_PER_BEAT)) + delta));
  seekTo(state.timeline.bars[i]);
  const labels = chartBarLabels(i).map(chartShape);
  chartAnnounce(t("battuta {n}", { n: i + 1 }) + ": " + (labels.join(", ") || t("nessun accordo")));
  chartUpdate().catch(showError);
}

async function chartWake(on) {
  try {
    if (chart.wake) { await chart.wake.release(); chart.wake = null; }
    if (on && navigator.wakeLock && document.visibilityState === "visible") chart.wake = await navigator.wakeLock.request("screen");
  } catch (e) { chart.wake = null; }
}

async function openChart() {
  if (!state.doc) return;
  $("chartNow").textContent = "…";
  $("chartNext").textContent = "";
  $("chartDialog").showModal();
  chart.data = (await call("chord_chart", { args: [state.doc.text] })).result;
  if (!chart.data.length) {
    $("chartNow").textContent = t("Questo brano non ha accordi");
  }
  chartRenderBars();
  await chartWake($("chartAwake").checked);
  clearInterval(chart.timer);
  chart.timer = setInterval(() => chartUpdate().catch(() => {}), 120);
  await chartUpdate();
  $("chartNow").focus();
}

function closeChart() {
  clearInterval(chart.timer);
  chart.timer = null;
  chart.counting = false;
  chartWake(false);
}

function setupChart() {
  const capo = $("chartCapo");
  for (let i = 0; i <= 7; i++) {
    const o = document.createElement("option");
    o.value = String(i);
    o.textContent = i ? t("capotasto {n}", { n: i }) : t("nessuno");
    capo.append(o);
  }
  try { $("chartAwake").checked = localStorage.getItem(CHART_AWAKE) !== "no"; } catch (e) {}
  capo.onchange = () => { chartRenderBars(); chartUpdate().catch(showError); };
  $("chartAwake").onchange = () => {
    try { localStorage.setItem(CHART_AWAKE, $("chartAwake").checked ? "si" : "no"); } catch (e) {}
    chartWake($("chartAwake").checked);
  };
  $("chartOpen").onclick = () => openChart().catch(showError);
  $("chartPlay").onclick = () => chartPlay().catch(showError);
  $("chartPrev").onclick = () => chartStep(-1);
  $("chartNextBar").onclick = () => chartStep(1);
  $("chartClose").onclick = () => $("chartDialog").close();
  $("chartDialog").addEventListener("close", closeChart);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && $("chartDialog").open && $("chartAwake").checked) chartWake(true);
  });
  // un pedale Bluetooth si presenta come una tastiera: spazio avvia, le frecce girano pagina
  $("chartDialog").addEventListener("keydown", (ev) => {
    const tag = ev.target.tagName;
    if (tag === "SELECT" || tag === "INPUT") return;
    const onButton = tag === "BUTTON";
    if ((ev.key === " " || ev.key === "Enter") && !onButton) { ev.preventDefault(); chartPlay().catch(showError); }
    else if (ev.key === "ArrowRight" || ev.key === "ArrowDown") { ev.preventDefault(); chartStep(1); }
    else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") { ev.preventDefault(); chartStep(-1); }
    else if (ev.key === "PageDown") { ev.preventDefault(); chartStep(4); }
    else if (ev.key === "PageUp") { ev.preventDefault(); chartStep(-4); }
  });
}

function setupStudy() {
  setupTuner();
  setupStudyPlayAlong();
  setupChart();
}
