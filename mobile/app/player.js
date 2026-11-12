// SoundText Mobile: le schermate, l'audio e l'evidenziazione durante l'ascolto. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ schermate

function setView(name) {
  if (name !== "testo") stopVoice();
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
