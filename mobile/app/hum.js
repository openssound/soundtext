// SoundText Mobile: «Canta». Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ canta
//
// Si canticchia una melodia (o si fa un ritmo con la bocca, in una traccia
// di percussioni) e l'app la scrive in ST nella traccia del cursore. Un
// conteggio di una battuta da' il tempo del brano; poi si registra dal
// microfono, senza suoni dall'app. Le note le riconosce il motore con la
// stessa conversione di «Importa audio» di SoundText (engine.hum_to_text):
// l'audio resta sul telefono.

const hum = { track: null, pos: null, rec: null, result: null, busy: false };
const HUM_MAX_MS = 30000;          // una registrazione piu' lunga si ferma da sola
const HUM_GRID = "stmobile.hum.grid";

// La traccia (o il box) in cui sta il cursore
function humTarget() {
  const here = musicBlockAtCaret();
  if (!here || here.kind === "pattern") return null;
  return { name: here.kind === "box" ? here.label.split(" · ")[0] : here.label, percussion: !!here.percussion, pos: here.pos };
}

function humSay(text, error = false) {
  const el = $("humStatus");
  el.classList.toggle("error", error);
  el.textContent = text;
}

function humButtons() {
  const recording = !!hum.rec;
  const b = $("humRecord");
  b.textContent = recording ? t("Ferma") : hum.result ? t("Canta di nuovo") : t("Registra");
  b.setAttribute("aria-pressed", String(recording));
  b.disabled = hum.busy;
  $("humListen").disabled = recording || hum.busy || !hum.result;
  $("humInsert").disabled = recording || hum.busy || !hum.result;
  $("humGrid").disabled = recording || hum.busy;
}

function openHum() {
  if (!state.doc) return;
  const target = humTarget();
  if (!target) {
    setStatus(t("Metti il cursore nella traccia in cui vuoi cantare"), true);
    return;
  }
  if (voice.audio) stopVoice();
  hum.track = target.name;
  hum.pos = target.pos;
  hum.result = null;
  $("humTitle").textContent = t("Canta nella traccia «{name}»", { name: target.name });
  $("humHelp").textContent = target.percussion
    ? t("Fai il ritmo con la bocca: «bum» per la cassa, «ta» per il rullante, «ts» per il charleston.")
    : t("Canticchia la melodia dopo il conteggio, una sillaba per nota («ta ta ta»). Le note vanno nell'ottava dello strumento.");
  $("humText").textContent = "";
  humSay("");
  humButtons();
  $("humDialog").showModal();
}

// Un clic del conteggio a un istante del contesto audio
function humClick(ctx, when, accent) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.frequency.value = accent ? 1500 : 1000;
  gain.gain.setValueAtTime(0.5, when);
  gain.gain.exponentialRampToValueAtTime(0.001, when + 0.05);
  osc.connect(gain).connect(ctx.destination);
  osc.start(when);
  osc.stop(when + 0.06);
}

async function startHum() {
  // dentro il tocco: il contesto audio e il permesso del microfono
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  hum.busy = true;
  hum.result = null;
  $("humText").textContent = "";
  humButtons();
  let stream = null;
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error(t("Questo browser non dà il microfono alle pagine"));
    if (state.playing) await pause();
    if (state.previewing) stopPreview();
    humSay(t("Chiedo il microfono…"));
    // niente filtri per la voce parlata: cambiano l'altezza e tagliano le note tenute
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
    });
    if (navigator.audioSession) { try { navigator.audioSession.type = "play-and-record"; } catch (e) {} }
    await ctx.resume();
    const bpm = (state.song && state.song.info.bpm) || 100;
    const beats = 4;
    const first = ctx.currentTime + 0.25;
    for (let i = 0; i < beats; i++) humClick(ctx, first + i * 60 / bpm, i === 0);
    const from = first + beats * 60 / bpm - 0.08;      // si registra da un soffio prima dell'uno
    const chunks = [];
    const feed = (samples) => { if (ctx.currentTime >= from && hum.rec) chunks.push(samples.slice()); };
    let node = null;
    if (ctx.audioWorklet && window.AudioWorkletNode) {
      try {
        await ctx.audioWorklet.addModule("voice-worklet.js");
        node = new AudioWorkletNode(ctx, "voice-tap", { numberOfInputs: 1, numberOfOutputs: 0 });
        node.port.onmessage = (ev) => feed(ev.data);
      } catch (e) {
        console.warn("AudioWorklet non disponibile", e);
        node = null;
      }
    }
    if (!node) {
      node = ctx.createScriptProcessor(4096, 1, 1);
      node.onaudioprocess = (ev) => feed(ev.inputBuffer.getChannelData(0));
      node.connect(ctx.destination);
    }
    ctx.createMediaStreamSource(stream).connect(node);
    hum.rec = { ctx, stream, node, chunks, timers: [] };
    humSay(t("Conto una battuta a {bpm} BPM…", { bpm: Math.round(bpm) }));
    hum.rec.timers.push(setTimeout(() => { if (hum.rec) humSay(t("Registro: canta, poi tocca Ferma.")); },
                                   (from - ctx.currentTime) * 1000));
    hum.rec.timers.push(setTimeout(() => { if (hum.rec) stopHum().catch(showError); },
                                   (from - ctx.currentTime) * 1000 + HUM_MAX_MS));
  } catch (e) {
    console.error(e);
    if (stream) stream.getTracks().forEach((tr) => tr.stop());
    ctx.close().catch(() => {});
    hum.rec = null;
    const denied = e && (e.name === "NotAllowedError" || e.name === "SecurityError");
    humSay(denied ? t("Microfono non permesso: consentilo nelle impostazioni del browser")
                  : t("Registrazione non avviata: {message}", { message: e.message || String(e) }), true);
  }
  hum.busy = false;
  humButtons();
}

// Chiude microfono e contesto; restituisce i campioni registrati
function humRelease() {
  const rec = hum.rec;
  if (!rec) return null;
  hum.rec = null;
  rec.timers.forEach(clearTimeout);
  rec.node.onaudioprocess = null;
  if (rec.node.port) rec.node.port.onmessage = null;
  rec.stream.getTracks().forEach((tr) => tr.stop());
  const rate = rec.ctx.sampleRate;
  rec.ctx.close().catch(() => {});
  if (navigator.audioSession && $("audioSession").checked) { try { navigator.audioSession.type = "playback"; } catch (e) {} }
  const samples = new Float32Array(rec.chunks.reduce((n, c) => n + c.length, 0));
  let at = 0;
  for (const c of rec.chunks) { samples.set(c, at); at += c.length; }
  return { samples, rate };
}

async function stopHum() {
  const audio = humRelease();
  if (!audio) return;
  hum.busy = true;
  humButtons();
  humSay(t("Riconosco le note…"));
  try {
    await state.booted;
    const options = { track: hum.track, grid: $("humGrid").value };
    const r = (await call("hum", { samples: audio.samples, rate: audio.rate, text: state.doc.text, options })).result;
    if (r.error) {
      humSay(r.error, true);
    } else {
      hum.result = r;
      $("humText").textContent = r.text;
      humSay(t("Ecco che cosa ho capito: ascoltala o inseriscila."));
    }
  } catch (e) {
    humSay(shortError(e), true);
  }
  hum.busy = false;
  humButtons();
}

async function listenToHum() {
  if (state.previewing) { stopPreview(); return; }
  if (!hum.result) return;
  const resumed = unlockInGesture();
  if (resumed) await resumed;
  const r = await call("preview", { text: hum.result.preview });
  await playPreview(r.midi, t("Anteprima della melodia cantata"));
}

async function insertHum() {
  if (!hum.result || !state.doc) return;
  if (state.previewing) stopPreview();
  const body = hum.result.text;
  $("humDialog").close();
  const pre = $("text");
  pre.focus({ preventScroll: true });
  const pos = Math.min(hum.pos, state.doc.text.length);
  if (document.activeElement === pre && selectRange(pos, pos)) {
    insertToken(body);                      // come un tasto: si puo' annullare
  } else {
    await replaceDocText(TextEdits.insertPiece(state.doc.text, pos, body).text);
  }
  setStatus(t("Melodia inserita nella traccia «{name}»", { name: hum.track }));
}

function setupHum() {
  const grid = $("humGrid");
  try { grid.value = localStorage.getItem(HUM_GRID) || "8"; } catch (e) {}
  if (!grid.value) grid.value = "8";
  grid.onchange = () => { try { localStorage.setItem(HUM_GRID, grid.value); } catch (e) {} };
  $("humOpen").onclick = () => openHum();
  $("humRecord").onclick = () => (hum.rec ? stopHum() : startHum()).catch(showError);
  $("humListen").onclick = () => listenToHum().catch(showError);
  $("humInsert").onclick = () => insertHum().catch(showError);
  $("humClose").onclick = () => $("humDialog").close();
  $("humDialog").addEventListener("close", () => {
    humRelease();
    if (state.previewing) stopPreview();
  });
}
