// SoundText Mobile: esportare l'audio e una clip video. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ esportare audio e clip
//
// L'audio si calcola fuori tempo (export-worker.js: lo stesso FluidSynth del lettore, senza il tempo reale),
// con le scelte del lettore (trasposizione, tracce mute o in solo, tratto A-B), e diventa un WAV oppure un
// M4A (AAC, con WebCodecs). La clip video e' un MP4 (H.264 + AAC, tutto con WebCodecs e il contenitore di
// mp4.js): le immagini si disegnano fotogramma per fotogramma su un canvas a tempo con l'audio. Dove WebCodecs
// manca, la clip si registra in tempo reale con MediaRecorder.

const exporter = { busy: false, caps: null };
const EXPORT_RATE = 44100;
const CLIP_FPS = 30;
const CLIP_SIZES = { vertical: [720, 1280], square: [720, 720] };
const CLIP_COLORS = { back: "#0b1420", back2: "#14263d", text: "#f2f6fb", dim: "#8fa3ba", accent: "#6cb2ff", note: "#ffd166" };

async function exportCapabilities() {
  if (exporter.caps) return exporter.caps;
  const caps = { aac: false, h264: false, recorder: typeof MediaRecorder !== "undefined" };
  try {
    if (typeof AudioEncoder !== "undefined") {
      caps.aac = !!(await AudioEncoder.isConfigSupported({ codec: "mp4a.40.2", sampleRate: EXPORT_RATE, numberOfChannels: 2, bitrate: 128000 })).supported;
    }
  } catch (e) {}
  try {
    if (typeof VideoEncoder !== "undefined" && typeof VideoFrame !== "undefined") {
      caps.h264 = !!(await VideoEncoder.isConfigSupported({ codec: "avc1.42001f", width: 720, height: 1280, bitrate: 3000000, framerate: CLIP_FPS,
                                                             avc: { format: "avc" } })).supported;
    }
  } catch (e) {}
  exporter.caps = caps;
  return caps;
}

// ---- il tratto e il MIDI

function exportRange() {
  const loop = state.loop;
  const part = $("exportRange").value === "loop" && loop.a != null && loop.b != null;
  return { fromBeat: part ? loop.a : 0, toBeat: part ? loop.b : null, part };
}

async function exportMidi() {
  const r = await call("render", { key: "export-" + Date.now(), semitones: state.semitones, muted: silentTracks(), metronome: false,
                                  banks: fontBanks(), sends: fxSends() });
  return r.midi;
}

// L'audio fuori tempo: {left, right, marks, block, rate} (vedi export-worker.js).
async function renderOffline(midi, { fromBeat, toBeat, seconds, tail }, progress) {
  const sf = await (await fetch(SOUNDFONT_URL)).arrayBuffer();
  // i SoundFont dell'utente: il predefinito e quelli delle tracce, ognuno col suo banco (come nel lettore)
  const extra = [];
  if (fonts.defaultId) extra.push({ bytes: await SoundFonts.get(fonts.defaultId), bank: 0 });
  for (const font of new Set(Object.values(docFonts()))) {
    if (font.id !== fonts.defaultId) extra.push({ bytes: await SoundFonts.get(font.id), bank: fontBank(font.id) });
  }
  return new Promise((resolve, reject) => {
    const worker = new Worker("export-worker.js");
    worker.onmessage = (ev) => {
      const msg = ev.data;
      if (msg.type === "progress") progress(msg.frames / EXPORT_RATE);
      else if (msg.type === "done") { worker.terminate(); resolve(msg); }
      else if (msg.type === "error") { worker.terminate(); reject(new Error(msg.message)); }
    };
    worker.onerror = (ev) => { worker.terminate(); reject(new Error(ev.message || "worker")); };
    const maxFrames = seconds ? Math.round(seconds * EXPORT_RATE) : 20 * 60 * EXPORT_RATE;
    worker.postMessage({
      sf, fonts: extra.filter((f) => f.bytes), reverb: reverbSettings(), midi: midi.slice().buffer, rate: EXPORT_RATE,
      fromTick: Math.round(fromBeat * TICKS_PER_BEAT), toTick: toBeat == null ? null : Math.round(toBeat * TICKS_PER_BEAT),
      maxFrames, tailFrames: Math.round((tail === undefined ? 2.5 : tail) * EXPORT_RATE),
    }, [sf, ...extra.filter((f) => f.bytes).map((f) => f.bytes)]);
  });
}

// ---- AAC in un M4A

async function encodeAac(left, right, rate, progress) {
  const samples = [];
  let config = null;
  const encoder = new AudioEncoder({
    output: (chunk, meta) => {
      if (meta && meta.decoderConfig && meta.decoderConfig.description && !config) config = new Uint8Array(meta.decoderConfig.description);
      const data = new Uint8Array(chunk.byteLength);
      chunk.copyTo(data);
      samples.push({ data, duration: chunk.duration ? Math.round(chunk.duration * rate / 1e6) : 1024 });
    },
    error: (e) => { throw e; },
  });
  encoder.configure({ codec: "mp4a.40.2", sampleRate: rate, numberOfChannels: 2, bitrate: 128000 });
  const step = 4096;
  for (let at = 0; at < left.length; at += step) {
    const n = Math.min(step, left.length - at);
    const planar = new Float32Array(n * 2);
    planar.set(left.subarray(at, at + n), 0);
    planar.set(right.subarray(at, at + n), n);
    const data = new AudioData({ format: "f32-planar", sampleRate: rate, numberOfFrames: n, numberOfChannels: 2,
                                 timestamp: Math.round(at * 1e6 / rate), data: planar });
    encoder.encode(data);
    data.close();
    if (encoder.encodeQueueSize > 6) await new Promise((r) => setTimeout(r, 0));
    if (progress && (at / step) % 20 === 0) progress(at / left.length);
  }
  await encoder.flush();
  encoder.close();
  if (!config) throw new Error(t("Questo browser non ha dato la descrizione dell'audio AAC."));
  return { sampleRate: rate, channels: 2, config, bitrate: 128000, samples };
}

// ---- file da consegnare

function fileBase() {
  return StFormat.fileName(state.doc ? state.doc.name : "SoundText").replace(/\.st$/, "");
}

async function deliver(bytes, name, type) {
  const blob = new Blob([bytes], { type });
  const file = new File([blob], name, { type });
  const size = (blob.size / 1048576).toLocaleString(I18n.locale, { maximumFractionDigits: 1 });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: state.doc ? state.doc.name : "SoundText" });
      return t("{name} condiviso ({size} MB).", { name, size });
    } catch (e) {
      if (e.name === "AbortError") return t("{name} pronto ({size} MB): condivisione annullata.", { name, size });
    }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 20000);
  return t("{name} scaricato ({size} MB).", { name, size });
}

// ---- l'audio

async function exportAudio(kind) {
  const range = exportRange();
  const progress = (s) => setExportStatus(t("Calcolo l'audio… {s} s", { s: Math.round(s) }));
  await analyze();
  const midi = await exportMidi();
  const out = await renderOffline(midi, { fromBeat: range.fromBeat, toBeat: range.toBeat, tail: range.part ? 0.8 : 2.5 }, progress);
  await applyMasterOffline(out);                // la catena master del brano
  const channels = [out.left, out.right];
  Wav.normalize(channels);
  if (range.part) Wav.fadeOut(channels, Math.round(EXPORT_RATE * 0.03));
  if (kind === "m4a") {
    setExportStatus(t("Comprimo in AAC…"));
    const audio = await encodeAac(out.left, out.right, out.rate, (p) => setExportStatus(t("Comprimo in AAC… {p}%", { p: Math.round(p * 100) })));
    return deliver(Mp4.mux({ audio }), fileBase() + ".m4a", "audio/mp4");
  }
  return deliver(Wav.encode(out.left, out.right, out.rate), fileBase() + ".wav", "audio/wav");
}

// ---- la clip

// Il blocco dell'audio che suona al secondo 't' -> il battito (tick interpolato fra i blocchi).
function beatAtSecond(out, seconds) {
  const index = (seconds * out.rate) / out.block;
  const i = Math.min(out.marks.length - 1, Math.max(0, Math.floor(index)));
  const next = Math.min(out.marks.length - 1, i + 1);
  const part = index - Math.floor(index);
  return (out.marks[i] + (out.marks[next] - out.marks[i]) * Math.min(1, Math.max(0, part))) / TICKS_PER_BEAT;
}

function clipModel(chart) {
  return { chart, title: state.doc.name, spans: state.song && state.song.spans, text: state.doc.text, total: state.timeline.length };
}

function chordIndexAt(chart, beat) {
  let found = -1;
  for (let i = 0; i < chart.length; i++) {
    if (chart[i][0] <= beat + 1e-6 && beat < chart[i][0] + chart[i][1] - 1e-6) { found = i; break; }
    if (chart[i][0] > beat) break;
  }
  return found;
}

function roundedBox(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// Il testo ST intorno a quello che suona: righe con la nota corrente evidenziata
function drawTextView(ctx, w, h, beat, model, top, bottom) {
  const text = model.text;
  let cs = -1, ce = -1;
  const s = model.spans;
  if (s && s.length) {
    let bestLevel = -1;
    for (let i = 0; i < s.length; i += 6) {
      if (s[i + 3] <= beat + 1e-6 && beat < s[i + 3] + s[i + 4] - 1e-6 && s[i + 5] >= bestLevel) {
        bestLevel = s[i + 5]; cs = s[i + 1]; ce = s[i + 2];
      }
    }
  }
  const lines = text.split("\n");
  let line = 0;
  if (cs >= 0) { let n = 0; while (line < lines.length - 1 && n + lines[line].length + 1 <= cs) { n += lines[line].length + 1; line++; } }
  const size = Math.round(w / 30);
  ctx.font = `${size}px ui-monospace, Menlo, Consolas, monospace`;
  const charW = ctx.measureText("M").width;
  const rows = Math.max(3, Math.floor((bottom - top) / (size * 1.4)));
  const first = Math.max(0, Math.min(Math.max(0, lines.length - rows), line - Math.floor(rows / 2)));
  let offset = 0;
  for (let i = 0; i < first; i++) offset += lines[i].length + 1;
  const cols = Math.floor((w - 60) / charW);
  const activeCol = cs >= 0 && line >= first ? cs - (offset + lines.slice(first, line).reduce((n, l) => n + l.length + 1, 0)) : 0;
  const shift = Math.max(0, activeCol - Math.floor(cols * 0.6));
  for (let r = 0; r < rows && first + r < lines.length; r++) {
    const y = top + (r + 1) * size * 1.4;
    const row = lines[first + r];
    ctx.fillStyle = first + r === line ? CLIP_COLORS.text : CLIP_COLORS.dim;
    ctx.fillText(row.slice(shift, shift + cols), 30, y);
    if (first + r === line && cs >= 0) {
      const a = Math.max(0, activeCol - shift), b = Math.min(cols, activeCol - shift + (ce - cs));
      if (b > a) {
        ctx.fillStyle = CLIP_COLORS.note;
        ctx.globalAlpha = 0.35;
        ctx.fillRect(30 + a * charW, y - size * 1.05, (b - a) * charW, size * 1.3);
        ctx.globalAlpha = 1;
      }
    }
  }
}

// Gli accordi grandi: quello che suona e i prossimi
function drawChordsView(ctx, w, h, beat, model, top, bottom) {
  const chart = model.chart;
  const i = chordIndexAt(chart, beat);
  const mid = (top + bottom) / 2;
  ctx.textAlign = "center";
  if (!chart.length) {
    ctx.fillStyle = CLIP_COLORS.dim;
    ctx.font = `${Math.round(w / 18)}px system-ui, sans-serif`;
    ctx.fillText(t("Nel brano non ci sono accordi da mostrare"), w / 2, mid);
    ctx.textAlign = "left";
    return;
  }
  const current = i >= 0 ? chart[i][2] : "";
  ctx.fillStyle = CLIP_COLORS.accent;
  ctx.font = `700 ${Math.round(w / (current.length > 4 ? 3.4 : 2.6))}px system-ui, sans-serif`;
  ctx.fillText(current || "·", w / 2, mid + w / 12);
  // i prossimi, in fila e tutti dentro il quadro
  const upcoming = chart.slice(Math.max(0, i + 1), Math.max(0, i + 1) + 3).map((c) => c[2]);
  let size = Math.round(w / 11);
  const gap = w / 20;
  const widthOf = () => { ctx.font = `600 ${size}px system-ui, sans-serif`; return upcoming.reduce((n, label) => n + ctx.measureText(label).width, 0) + gap * Math.max(0, upcoming.length - 1); };
  while (size > 14 && widthOf() > w - 60) size -= 2;
  ctx.fillStyle = CLIP_COLORS.dim;
  ctx.textAlign = "left";
  let x = (w - widthOf()) / 2;
  for (const label of upcoming) {
    ctx.fillText(label, x, bottom - w / 20);
    x += ctx.measureText(label).width + gap;
  }
  ctx.textAlign = "left";
}

function drawClipFrame(ctx, w, h, beat, model, content, signature) {
  const back = ctx.createLinearGradient(0, 0, 0, h);
  back.addColorStop(0, CLIP_COLORS.back2);
  back.addColorStop(1, CLIP_COLORS.back);
  ctx.fillStyle = back;
  ctx.fillRect(0, 0, w, h);
  ctx.textAlign = "left";
  ctx.fillStyle = CLIP_COLORS.text;
  ctx.font = `700 ${Math.round(w / 13)}px system-ui, sans-serif`;
  ctx.fillText(model.title.length > 26 ? model.title.slice(0, 25) + "…" : model.title, 30, w / 8);
  const bar = barNumber(Math.max(0, beat));
  ctx.fillStyle = CLIP_COLORS.dim;
  ctx.font = `${Math.round(w / 24)}px system-ui, sans-serif`;
  ctx.fillText(t("battuta {n}/{total}", { n: bar, total: state.timeline.bars.length }), 30, w / 8 + w / 14);
  const top = w / 8 + w / 10, bottom = h - (signature ? w / 7 : w / 14);
  if (content === "text") drawTextView(ctx, w, h, beat, model, top, bottom);
  else drawChordsView(ctx, w, h, beat, model, top, bottom);
  // l'avanzamento
  const pos = model.total > 0 ? Math.min(1, Math.max(0, beat / model.total)) : 0;
  ctx.fillStyle = "rgba(255,255,255,0.15)";
  roundedBox(ctx, 30, h - w / 14 - 8, w - 60, 8, 4); ctx.fill();
  ctx.fillStyle = CLIP_COLORS.accent;
  roundedBox(ctx, 30, h - w / 14 - 8, Math.max(8, (w - 60) * pos), 8, 4); ctx.fill();
  if (signature) {
    ctx.fillStyle = CLIP_COLORS.dim;
    ctx.font = `${Math.round(w / 26)}px system-ui, sans-serif`;
    ctx.fillText(t("Fatto con SoundText") + " · " + location.host + location.pathname.replace(/\/$/, ""), 30, h - w / 40);
  }
}

async function encodeVideo(out, seconds, width, height, draw, progress) {
  const total = Math.floor(seconds * CLIP_FPS);
  const canvas = document.createElement("canvas");
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d");
  const samples = [];
  let config = null;
  const encoder = new VideoEncoder({
    output: (chunk, meta) => {
      if (meta && meta.decoderConfig && meta.decoderConfig.description && !config) config = new Uint8Array(meta.decoderConfig.description);
      const data = new Uint8Array(chunk.byteLength);
      chunk.copyTo(data);
      samples.push({ data, duration: Math.round(90000 / CLIP_FPS), key: chunk.type === "key" });
    },
    error: (e) => { throw e; },
  });
  encoder.configure({ codec: "avc1.42001f", width, height, bitrate: 3000000, framerate: CLIP_FPS, avc: { format: "avc" } });
  for (let i = 0; i < total; i++) {
    draw(ctx, width, height, beatAtSecond(out, i / CLIP_FPS));
    const frame = new VideoFrame(canvas, { timestamp: Math.round(i * 1e6 / CLIP_FPS) });
    encoder.encode(frame, { keyFrame: i % (CLIP_FPS * 2) === 0 });
    frame.close();
    if (encoder.encodeQueueSize > 4 || i % 15 === 0) {
      await new Promise((r) => setTimeout(r, 0));
      progress(i / total);
    }
  }
  await encoder.flush();
  encoder.close();
  if (!config) throw new Error(t("Questo browser non ha dato la descrizione del video H.264."));
  return { width, height, timescale: 90000, config, samples };
}

// Senza WebCodecs: si registra in tempo reale quello che suona e si disegna (MediaRecorder).
async function recordClipRealtime(out, seconds, width, height, draw, progress) {
  const canvas = document.createElement("canvas");
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d");
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: out.rate });
  const buffer = audioCtx.createBuffer(2, out.left.length, out.rate);
  buffer.copyToChannel(out.left, 0);
  buffer.copyToChannel(out.right, 1);
  const destination = audioCtx.createMediaStreamDestination();
  const source = audioCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(destination);
  const stream = new MediaStream([...canvas.captureStream(CLIP_FPS).getVideoTracks(), ...destination.stream.getAudioTracks()]);
  const kinds = ["video/mp4;codecs=avc1,mp4a.40.2", "video/mp4", "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
  const mime = kinds.find((k) => MediaRecorder.isTypeSupported(k)) || "";
  const recorder = new MediaRecorder(stream, mime ? { mimeType: mime, videoBitsPerSecond: 3000000 } : undefined);
  const chunks = [];
  recorder.ondataavailable = (ev) => { if (ev.data.size) chunks.push(ev.data); };
  const done = new Promise((resolve) => { recorder.onstop = resolve; });
  recorder.start(500);
  await audioCtx.resume();
  const t0 = audioCtx.currentTime;
  source.start();
  await new Promise((resolve) => {
    const tick = () => {
      const elapsed = audioCtx.currentTime - t0;
      draw(ctx, width, height, beatAtSecond(out, Math.min(elapsed, seconds)));
      progress(elapsed / seconds);
      if (elapsed >= seconds) resolve(); else requestAnimationFrame(tick);
    };
    tick();
  });
  recorder.stop();
  await done;
  audioCtx.close();
  const type = recorder.mimeType || mime || "video/webm";
  return { bytes: new Uint8Array(await new Blob(chunks, { type }).arrayBuffer()), type };
}

async function exportClip() {
  await analyze();
  if (state.song && state.song.spansReady) await state.song.spansReady;
  const range = exportRange();
  const wanted = Number($("clipSeconds").value);
  const [width, height] = CLIP_SIZES[$("clipFormat").value] || CLIP_SIZES.vertical;
  const content = $("clipContent").value;
  const caps = await exportCapabilities();
  const midi = await exportMidi();
  const chart = content === "chords" ? (await call("chord_chart", { args: [state.doc.text] })).result : [];
  const model = clipModel(chart);
  const signature = $("clipSignature").checked;
  const draw = (ctx, w, h, beat) => drawClipFrame(ctx, w, h, beat, model, content, signature);
  setExportStatus(t("Calcolo l'audio…"));
  const out = await renderOffline(midi, { fromBeat: range.fromBeat, toBeat: range.toBeat, seconds: wanted, tail: 0 },
                                  (s) => setExportStatus(t("Calcolo l'audio… {s} s", { s: Math.round(s) })));
  await applyMasterOffline(out);
  const seconds = Math.min(wanted, out.left.length / out.rate);
  Wav.normalize([out.left, out.right]);
  Wav.fadeOut([out.left, out.right], Math.round(EXPORT_RATE * 0.3));
  const name = fileBase() + "-clip";
  if (caps.h264 && caps.aac) {
    const video = await encodeVideo(out, seconds, width, height, draw, (p) => setExportStatus(t("Disegno e comprimo il video… {p}%", { p: Math.round(p * 100) })));
    setExportStatus(t("Comprimo l'audio…"));
    const audio = await encodeAac(out.left.subarray(0, Math.round(seconds * out.rate)), out.right.subarray(0, Math.round(seconds * out.rate)), out.rate);
    return deliver(Mp4.mux({ audio, video }), name + ".mp4", "video/mp4");
  }
  if (caps.recorder) {
    setExportStatus(t("Questo browser non comprime il video da solo: registro la clip in tempo reale ({s} s)…", { s: Math.round(seconds) }));
    const rec = await recordClipRealtime(out, seconds, width, height, draw, (p) => setExportStatus(t("Registro la clip… {p}%", { p: Math.round(p * 100) })));
    return deliver(rec.bytes, name + (rec.type.includes("mp4") ? ".mp4" : ".webm"), rec.type.split(";")[0]);
  }
  throw new Error(t("Questo browser non sa creare una clip video."));
}

// ---- la finestra

function setExportStatus(text, error = false) {
  $("exportStatus").textContent = text;
  $("exportStatus").classList.toggle("error", error);
}

async function runExport(job) {
  if (exporter.busy) return;
  exporter.busy = true;
  for (const b of document.querySelectorAll("#exportDialog button.job")) b.disabled = true;
  try {
    const started = performance.now();
    const message = await job();
    Metrics.record("esporta", { ms: Math.round(performance.now() - started) });
    setExportStatus(message);
  } catch (e) {
    console.error(e);
    setExportStatus(shortError(e), true);
  } finally {
    exporter.busy = false;
    for (const b of document.querySelectorAll("#exportDialog button.job")) b.disabled = false;
    refreshExport();
  }
}

async function refreshExport() {
  const caps = await exportCapabilities();
  const loop = state.loop;
  $("exportRange").querySelector("option[value=loop]").disabled = !(loop.a != null && loop.b != null);
  if ($("exportRange").selectedOptions[0].disabled) $("exportRange").value = "all";
  $("exportM4a").hidden = !caps.aac;
  $("exportClipNote").textContent = caps.h264 && caps.aac ? "" :
    caps.recorder ? t("Questo browser non comprime il video da solo: la clip si registra in tempo reale.") : t("Questo browser non sa creare clip video.");
  $("exportClipButton").disabled = exporter.busy || !(caps.recorder || (caps.h264 && caps.aac));
}

function setupExport() {
  $("exportOpen").onclick = () => {
    setExportStatus("");
    $("exportDialog").showModal();
    refreshExport();
  };
  $("exportClose").onclick = () => $("exportDialog").close();
  $("exportWav").onclick = () => runExport(() => exportAudio("wav"));
  $("exportM4a").onclick = () => runExport(() => exportAudio("m4a"));
  $("exportClipButton").onclick = () => runExport(exportClip);
}
