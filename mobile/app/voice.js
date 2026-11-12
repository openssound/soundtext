// SoundText Mobile: la dettatura. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ dettatura
//
// Il microfono della barra musicale. Il riconoscimento e' Vosk
// (vendor/vosk/, WebAssembly): gira nel telefono, l'audio non esce dal
// dispositivo e dopo il primo scaricamento del modello funziona senza rete.
// Riconosce solo le parole della dettatura (engine.dictation_words); la
// frase diventa testo ST con core/dictation.py (engine.dictate).
//
// Una frase capita tutta entra subito nel testo, al cursore; se ha parole
// incerte o non capite aspetta una conferma («conferma», «cancella», o i
// tasti). I comandi («suona la battuta», «tempo novanta», «annulla»…) si
// eseguono subito. Ogni esito si legge nella riga di stato (role="status"):
// TalkBack e VoiceOver lo dicono.

const voice = {
  models: [],             // le lingue con un modello (bundle/files.json)
  model: null, modelLang: null,
  recognizer: null,
  audio: null,            // { stream, ctx, node } mentre si detta
  starting: false,
  pending: null,          // frase in attesa di conferma
  history: [],            // modifiche fatte a voce: { before, after, caret }
  caret: null, caretDoc: null,   // ultimo cursore nel testo, anche senza il fuoco
  ask: false,             // chiedi sempre conferma
};
const VOICE_OK = "stmobile.voice.ok";
const VOICE_ASK = "stmobile.voice.ask";
const VOICE_MIN_CONFIDENCE = 0.4;
const VOICE_LOAD_MS = 180000;       // tempo massimo per scaricare e aprire il modello
const VOICE_JOIN_MS = 6000;         // una frase spezzata da una pausa si ricompone entro questo tempo

function voiceSay(text, error = false) {
  const el = $("voiceStatus");
  el.classList.toggle("error", error);
  el.textContent = "";
  // un testo uguale al precedente va riletto
  setTimeout(() => { el.textContent = text; }, 30);
}

function voiceCaret() {
  const pre = $("text");
  const text = state.doc.text;
  if (document.activeElement === pre) {
    const pos = caretPos();
    if (pos !== null) return pos;
  }
  if (voice.caretDoc === state.doc && voice.caret !== null) return Math.min(voice.caret, text.length);
  return text.trimEnd().length;       // in fondo all'ultima riga scritta
}

// Una modifica del testo fatta a voce: si puo' annullare a voce.
async function voiceEdit(text, caret) {
  const before = state.doc.text;
  const focused = document.activeElement === $("text");
  const entry = { before, caret: voiceCaret() };
  await replaceDocText(text);
  entry.after = state.doc.text;
  voice.history.push(entry);
  if (voice.history.length > 50) voice.history.shift();
  voiceSetCaret(caret, focused);
}

function voiceSetCaret(caret, focused = document.activeElement === $("text")) {
  voice.caret = caret;
  voice.caretDoc = state.doc;
  if (focused) selectRange(caret, caret);
}

async function voiceUndo() {
  const last = voice.history[voice.history.length - 1];
  if (!last || last.after !== state.doc.text) {
    if (document.activeElement === $("text")) { document.execCommand("undo"); return true; }
    return false;
  }
  voice.history.pop();
  const focused = document.activeElement === $("text");
  await replaceDocText(last.before);
  voiceSetCaret(last.caret, focused);
  return true;
}

function flatItems(items) {
  return items.flatMap((it) => (it.children ? [it, ...flatItems(it.children)] : [it]));
}

const saidOf = (r) => r.items.filter((it) => it.kind !== "command" && it.kind !== "unknown").map((it) => it.said).join(", ");

function renderVoice(heard, r) {
  $("voiceHeard").textContent = heard ? `«${heard}»` : "";
  const box = $("voicePieces");
  box.innerHTML = "";
  for (const it of r ? r.items : []) {
    const span = document.createElement("span");
    span.textContent = it.kind === "command" ? `[${it.said}]` : (it.st || it.said);
    if (it.kind === "unknown") span.className = "unknown";
    else if (it.uncertain || (it.children && flatItems(it.children).some((c) => c.uncertain))) span.className = "uncertain";
    box.append(span, " ");
  }
  $("voiceConfirm").hidden = !voice.pending;
}

async function insertDictated(r) {
  const edit = TextEdits.insertPiece(state.doc.text, voiceCaret(), r.text);
  await voiceEdit(edit.text, edit.caret);
  voiceSay(t("Inserito: {what}", { what: saidOf(r) }));
}

async function confirmPending() {
  const r = voice.pending;
  if (!r) { voiceSay(t("Niente da confermare")); return; }
  voice.pending = null;
  $("voiceConfirm").hidden = true;
  await insertDictated(r);
}

function discardPending() {
  voice.pending = null;
  renderVoice("", null);
  voiceSay(t("Scartato"));
}

// La frase riconosciuta: testo ST da inserire e comandi da eseguire.
async function onPhrase(result) {
  if (!state.doc) return;
  const words = result.result || [];
  const raw = result.text || "";
  const heard = raw.replace(/\[unk\]/g, " ").replace(/\s+/g, " ").trim();
  if (!heard) return;
  let r = (await call("dictate", { args: [state.doc.text, heard, I18n.language] })).result;
  // Una pausa in mezzo alla frase la spezza in due risultati: se il pezzo
  // prima non si era capito, si riprova con la frase intera.
  const carry = voice.carry;
  voice.carry = null;
  let shown = heard;
  if (carry && performance.now() - carry.at < VOICE_JOIN_MS) {
    const joined = carry.text + " " + heard;
    const rj = (await call("dictate", { args: [state.doc.text, joined, I18n.language] })).result;
    const nothing = !r.text && !r.commands.length;
    if (rj.unknown.length < carry.unknown + r.unknown.length || (nothing && (rj.text || rj.commands.length))) {
      r = rj;
      shown = joined;
    } else if (nothing) {
      shown = joined;
    }
  }
  // Mentre il brano suona il microfono sente la musica: valgono solo i comandi.
  const busy = state.playing || state.previewing;
  if (busy && !r.commands.length) return;
  const music = !busy && r.text;
  // parole saltate in mezzo alla frase, o capite male
  const gap = /\S\s+\[unk\]\s+\S/.test(raw);
  const low = words.some((w) => w.word !== "[unk]" && w.conf < VOICE_MIN_CONFIDENCE);
  const doubt = gap || low || r.unknown.length > 0 || flatItems(r.items).some((it) => it.uncertain && it.kind !== "command");
  if (music) {
    voice.pending = (voice.ask || doubt) ? r : null;
    renderVoice(shown, r);
    if (voice.pending) {
      voiceSay(t("Da confermare: {what}. Di' «conferma» o «cancella».", { what: saidOf(r) }));
    } else {
      await insertDictated(r);
    }
  } else if (!r.commands.length) {
    if (busy) return;
    voice.carry = { text: shown, unknown: r.unknown.length, at: performance.now() };
    renderVoice(shown, r);
    // parole di contorno da sole («inserisci…»): si aspetta il resto
    if (r.unknown.length) voiceSay(t("Non ho capito: {words}", { words: r.unknown.join(", ") }));
    return;
  } else {
    renderVoice(shown, r);
  }
  for (const c of r.commands) await runVoiceCommand(c);
}

async function runVoiceCommand(c) {
  const doc = state.doc;
  switch (c.command) {
    case "confirm":
      return confirmPending();
    case "delete_last":
    case "undo":
      if (voice.pending) return discardPending();
      if (await voiceUndo()) voiceSay(c.command === "undo" ? t("Annullato") : t("Cancellato"));
      else voiceSay(t("Niente da annullare"));
      return;
    case "play_bar":
      voiceSay(t("Suono la battuta"));
      return playBarAtCaret(true);
    case "play":
      if (state.playing) return;
      voiceSay(t("Suono"));
      return play();
    case "play_from_start":
      if (state.playing) await pause();
      state.pausedTick = 0;
      voiceSay(t("Suono dall'inizio"));
      return play();
    case "stop":
      if (state.previewing) stopPreview();
      else if (state.playing) await pause();
      voiceSay(t("Fermo"));
      return;
    case "tempo": {
      const bpm = Math.round(Number(c.value));
      if (!(bpm >= 20 && bpm <= 300)) { voiceSay(t("Tempo non valido: {n}", { n: c.value }), true); return; }
      const edit = TextEdits.setTempo(doc.text, bpm, voiceCaret());
      await voiceEdit(edit.text, edit.caret);
      voiceSay(t("Tempo {n}", { n: bpm }));
      return;
    }
    case "transpose": {
      const n = Math.max(-6, Math.min(6, state.semitones + Number(c.value)));
      $("trans").value = n;
      await setTranspose(n);
      voiceSay(t("Trasposizione: {n} semitoni", { n: $("transOut").value }));
      return;
    }
    case "goto_bar":
      return voiceGoToBar(Number(c.value));
    case "new_track": {
      const r = (await call("dictate_track", { args: [doc.text, String(c.value || ""), I18n.language] })).result;
      if (!r) { voiceSay(t("Non conosco lo strumento: {name}", { name: c.value || "?" }), true); return; }
      await voiceEdit(r.text, r.text.length);
      // la traccia nuova e' in fondo: si porta in vista
      const node = textNode();
      if (node) {
        const end = new Range();
        end.setStart(node, node.data.length);
        scrollToRange(end, true);
      }
      voiceSay(t("Nuova traccia: {name}", { name: r.name }));
      return;
    }
    case "repeat":
      return voiceRepeat(Number(c.value) || 2);
    case "end":
      return stopVoice();
  }
}

// «vai alla battuta 5»: il cursore sulla prima nota della battuta, nella
// traccia dove si trova (o nella prima).
async function voiceGoToBar(n) {
  if (!state.song || state.song.text !== state.doc.text) {
    try { if (!(await analyze())) return; } catch (e) { voiceSay(shortError(e), true); return; }
  }
  const song = state.song;
  await song.spansReady;
  const s = song.spans;
  const bars = state.timeline.bars;
  if (!s || !(n >= 1 && n <= bars.length)) { voiceSay(t("La battuta {n} non c'è", { n }), true); return; }
  const beat = bars[n - 1];
  const pos = voiceCaret();
  let track = -1;
  // la traccia del cursore: quella dell'ultima nota che comincia prima
  let before = -1;
  for (let i = 0; i < s.length; i += 6) {
    if (s[i + 1] <= pos && s[i + 1] > before) { before = s[i + 1]; track = s[i]; }
  }
  let best = -1;
  for (const only of track >= 0 ? [track, -1] : [-1]) {
    for (let i = 0; i < s.length; i += 6) {
      if (only >= 0 && s[i] !== only) continue;
      if (s[i + 3] < beat - 1e-6) continue;
      if (best < 0 || s[i + 3] < s[best + 3] - 1e-6 ||
          (Math.abs(s[i + 3] - s[best + 3]) < 1e-6 && s[i + 5] > s[best + 5])) best = i;
    }
    if (best >= 0) break;
  }
  if (best < 0) { voiceSay(t("La battuta {n} non c'è", { n }), true); return; }
  $("text").focus({ preventScroll: true });
  voiceSetCaret(s[best + 1], true);
  scrollToRange(getSelection().getRangeAt(0), true);
  voiceSay(t("Battuta {n}", { n }));
}

// «ripeti due volte» senza altro: l'ultima battuta della riga (da dopo
// l'ultima stanghetta al cursore) diventa N( … ).
async function voiceRepeat(count) {
  const edit = TextEdits.wrapRepeat(state.doc.text, voiceCaret(), count);
  if (!edit) { voiceSay(t("Niente da ripetere")); return; }
  await voiceEdit(edit.text, edit.caret);
  voiceSay(t("Ripetuto {n} volte", { n: count }));
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error(t("Non riesco a caricare {name}", { name: src })));
    document.head.append(s);
  });
}

function setMicButton() {
  const on = !!voice.audio;
  const b = $("mic");
  b.setAttribute("aria-pressed", String(on));
  b.setAttribute("aria-label", on ? t("Ferma la dettatura") : t("Detta"));
  b.title = b.getAttribute("aria-label");
  b.classList.toggle("busy", voice.starting);
  $("voice").hidden = !on && !voice.starting;
}

async function toggleVoice() {
  if (voice.starting) return;
  if (voice.audio) return stopVoice();
  if (!state.doc) return;
  if (!voice.models.includes(I18n.language)) {
    setStatus(t("La dettatura non è ancora disponibile in questa lingua"), true);
    return;
  }
  let ok = false;
  try { ok = localStorage.getItem(VOICE_OK) === "1"; } catch (e) {}
  if (!ok) { $("voiceIntro").showModal(); return; }
  return startVoice();
}

async function startVoice() {
  // dentro il tocco: il contesto audio e il permesso del microfono
  unlockInGesture();
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  voice.starting = true;
  voice.pending = null;
  renderVoice("", null);
  setMicButton();
  let stream = null;
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error(t("Questo browser non dà il microfono alle pagine"));
    voiceSay(t("Chiedo il microfono…"));
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
    if (navigator.audioSession) { try { navigator.audioSession.type = "play-and-record"; } catch (e) {} }
    const lang = I18n.language;
    if (!voice.model || voice.modelLang !== lang) {
      voiceSay(t("Preparo il riconoscimento della voce (la prima volta scarica 50 MB)…"));
      if (!window.Vosk) await loadScript("vendor/vosk/vosk.js");
      await state.booted;
      if (voice.model) voice.model.terminate();
      // se il worker di Vosk non parte la promessa non si chiude mai: un limite
      voice.model = await Promise.race([
        Vosk.createModel(`vendor/vosk/${lang}.tar.gz`),
        new Promise((_r, reject) => setTimeout(() => reject(new Error(t("il modello della voce non si è caricato"))), VOICE_LOAD_MS)),
      ]);
      voice.modelLang = lang;
    }
    const words = (await call("dictation_words", { args: [state.doc.text, lang] })).result;
    const recognizer = new voice.model.KaldiRecognizer(ctx.sampleRate, JSON.stringify(words));
    recognizer.setWords(true);
    recognizer.on("partialresult", (m) => {
      const partial = (m.result.partial || "").replace(/\[unk\]/g, "").trim();
      if (partial) $("voiceHeard").textContent = partial + "…";
    });
    recognizer.on("result", (m) => { onPhrase(m.result).catch((e) => voiceSay(shortError(e), true)); });
    await ctx.resume();
    const node = await voiceTap(ctx, recognizer);
    ctx.createMediaStreamSource(stream).connect(node);
    if (node.onaudioprocess) node.connect(ctx.destination);     // ScriptProcessor gira solo se collegato
    voice.recognizer = recognizer;
    voice.audio = { stream, ctx, node };
    voice.history = [];
    voiceSay(t("Ti ascolto: detta una frase e fai una pausa."));
  } catch (e) {
    console.error(e);
    if (stream) stream.getTracks().forEach((tr) => tr.stop());
    ctx.close().catch(() => {});
    const denied = e && (e.name === "NotAllowedError" || e.name === "SecurityError");
    voice.starting = false;
    setMicButton();
    setStatus(denied ? t("Microfono non permesso: consentilo nelle impostazioni del browser")
                     : t("Dettatura non avviata: {message}", { message: e.message || String(e) }), true);
    return;
  }
  voice.starting = false;
  setMicButton();
}

// Il nodo che porta l'audio del microfono al riconoscitore: un AudioWorklet
// (voice-worklet.js), o ScriptProcessor dove il worklet non c'e'.
async function voiceTap(ctx, recognizer) {
  const feed = (samples) => { try { recognizer.acceptWaveformFloat(samples, ctx.sampleRate); } catch (e) { console.warn(e); } };
  if (ctx.audioWorklet && window.AudioWorkletNode) {
    try {
      await ctx.audioWorklet.addModule("voice-worklet.js");
      const node = new AudioWorkletNode(ctx, "voice-tap", { numberOfInputs: 1, numberOfOutputs: 0 });
      node.port.onmessage = (ev) => feed(ev.data);
      return node;
    } catch (e) {
      console.warn("AudioWorklet della dettatura non disponibile", e);
    }
  }
  const node = ctx.createScriptProcessor(4096, 1, 1);
  node.onaudioprocess = (ev) => feed(ev.inputBuffer.getChannelData(0));
  return node;
}

function stopVoice() {
  const a = voice.audio;
  if (!a) return;
  voice.audio = null;
  a.node.onaudioprocess = null;
  if (a.node.port) a.node.port.onmessage = null;
  a.stream.getTracks().forEach((tr) => tr.stop());
  a.ctx.close().catch(() => {});
  if (voice.recognizer) { try { voice.recognizer.remove(); } catch (e) {} voice.recognizer = null; }
  voice.pending = null;
  if (navigator.audioSession && $("audioSession").checked) { try { navigator.audioSession.type = "playback"; } catch (e) {} }
  setMicButton();
  setStatus(t("Dettatura finita"));
}

function setupVoice() {
  $("mic").onclick = () => toggleVoice().catch(showError);
  try { voice.ask = localStorage.getItem(VOICE_ASK) === "1"; } catch (e) {}
  const ask = $("voiceAsk");
  ask.setAttribute("aria-pressed", String(voice.ask));
  ask.onclick = () => {
    voice.ask = !voice.ask;
    ask.setAttribute("aria-pressed", String(voice.ask));
    try { localStorage.setItem(VOICE_ASK, voice.ask ? "1" : "0"); } catch (e) {}
  };
  $("voiceInsert").onclick = () => confirmPending().catch(showError);
  $("voiceDiscard").onclick = discardPending;
  $("voiceIntroStart").onclick = () => {
    try { localStorage.setItem(VOICE_OK, "1"); } catch (e) {}
    $("voiceIntro").close();
    startVoice().catch(showError);
  };
  $("voiceIntroClose").onclick = () => $("voiceIntro").close();
  document.addEventListener("selectionchange", () => {
    if (document.activeElement === $("text") && state.doc) {
      const pos = caretPos();
      if (pos !== null) { voice.caret = pos; voice.caretDoc = state.doc; }
    }
  });
  // il microfono non resta acceso con l'app in background
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") stopVoice(); });
  setMicButton();
}
