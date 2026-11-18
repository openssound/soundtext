// SoundText Mobile: gli effetti del brano. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ effetti
//
// Le tracce escono mischiate da un solo sintetizzatore, quindi gli effetti per traccia non si possono fare
// uno per uno. Si sentono due cose (engine.effects_plan):
//  - la catena master del brano (EQ, compressore, limiter, volume, filtri, delay, riverbero, chorus) con il
//    Web Audio, sul mix finale (fxchain.js);
//  - il riverbero e il chorus delle tracce, come invio al riverbero e al chorus di FluidSynth (CC 91 e 93
//    scritti nel MIDI), con un riverbero condiviso che ha la stanza, lo smorzamento e l'ampiezza medi.
// Amplificatori, NAM, plugin e gli altri effetti di traccia restano nel file e non si sentono. Un interruttore
// nel Lettore li esclude (per confrontare e per risparmiare batteria).

const EFFECTS_KEY = "stmobile.effects";

function effectsOn() {
  try { return localStorage.getItem(EFFECTS_KEY) !== "no"; } catch (e) { return true; }
}

// gli invii di riverbero e chorus per traccia, da scrivere nel MIDI
function fxSends() {
  return effectsOn() && state.fx ? state.fx.sends : {};
}

// il riverbero di FluidSynth per il brano: si decide quando si crea il sintetizzatore
function reverbSettings() {
  const r = effectsOn() && state.fx && state.fx.reverb;
  return r ? { reverbRoomSize: r.room, reverbDamp: r.damp, reverbWidth: r.width, reverbLevel: r.level } : {};
}

// un riverbero diverso (di piu' di un decimo) vuole un sintetizzatore nuovo
function reverbKey() {
  const s = reverbSettings();
  return Object.keys(s).length ? JSON.stringify(Object.values(s).map((v) => Math.round(v * 10))) : "";
}

// Il collegamento: sintetizzatore -> catena master -> uscita
function applyEffects() {
  const node = state.synthNode, ctx = state.ctx;
  if (!node || !ctx) return;
  try { node.disconnect(); } catch (e) {}
  if (state.fxChain) { state.fxChain.dispose(); state.fxChain = null; }
  const specs = effectsOn() && state.fx ? state.fx.master : [];
  const chain = specs.length ? FxChain.build(ctx, specs) : null;
  if (chain) {
    node.connect(chain.input);
    chain.output.connect(ctx.destination);
    state.fxChain = chain;
  } else {
    node.connect(ctx.destination);
  }
}

// Gli effetti del brano aperto, dal motore; si chiede dopo ogni analisi
async function loadEffectsPlan() {
  try {
    state.fx = (await call("effects")).plan;
  } catch (e) {
    state.fx = null;
  }
  applyEffects();
}

// L'esportazione: la catena master sul segnale calcolato fuori tempo (la coda del riverbero e del delay e' gia' nel segnale)
async function applyMasterOffline(out) {
  const specs = effectsOn() && state.fx ? state.fx.master : [];
  if (!specs.length || typeof OfflineAudioContext === "undefined") return;
  const frames = out.left.length;
  const ctx = new OfflineAudioContext(2, frames, out.rate);
  const buffer = ctx.createBuffer(2, frames, out.rate);
  buffer.copyToChannel(out.left, 0);
  buffer.copyToChannel(out.right, 1);
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  const chain = FxChain.build(ctx, specs);
  if (!chain) return;
  source.connect(chain.input);
  chain.output.connect(ctx.destination);
  source.start();
  const rendered = await ctx.startRendering();
  chain.dispose();
  out.left.set(rendered.getChannelData(0));
  out.right.set(rendered.getChannelData(1));
}

function setupEffects() {
  const box = $("effectsOn");
  box.checked = effectsOn();
  box.onchange = () => {
    try { localStorage.setItem(EFFECTS_KEY, box.checked ? "si" : "no"); } catch (e) {}
    if (state.audioReady && state.reverbKey !== reverbKey()) resetSynth(); else applyEffects();
    renderMidi().catch(showError);
  };
}
