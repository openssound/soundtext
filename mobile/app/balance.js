// SoundText Mobile: bilancia i volumi (core.auto_balance nel motore). Ogni traccia si suona da sola col calcolo fuori tempo
// dell'esportazione (export-worker.js: lo stesso FluidSynth e gli stessi SoundFont del lettore, con trasposizione e invii),
// se ne misura il volume dove suona e il motore porta il volume di ogni traccia (blocchi «Mixer» del testo) al livello del
// suo ruolo rispetto alla melodia. Col bottone del Lettore per i brani scritti a mano; da solo dopo un brano in 60 secondi.
// Gli script di app/ sono caricati in ordine da index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

const BALANCE_RATE = 11025;              // per misurare il volume basta: il calcolo e' quattro volte piu' veloce che a 44,1 kHz
const BALANCE_MAX_SECONDS = 120;         // un brano piu' lungo si misura sui primi due minuti
const balancer = { busy: false, before: null, after: null };

// Il volume (dB, RMS) dove la traccia suona: finestre di un decimo di secondo sopra -60 dB (come core.auto_balance.level_db)
function balanceLevelDb(left, right, rate) {
  const win = Math.max(1, Math.round(rate * 0.1));
  const n = Math.floor(left.length / win);
  const floor = Math.pow(10, -60 / 20);
  let sum = 0, count = 0;
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let j = i * win; j < (i + 1) * win; j++) {
      const x = 0.5 * (left[j] + right[j]);
      s += x * x;
    }
    const rms = Math.sqrt(s / win + 1e-12);
    if (rms > floor) { sum += rms * rms; count++; }
  }
  return count ? 20 * Math.log10(Math.sqrt(sum / count)) : null;
}

async function balanceVolumes({ automatic = false } = {}) {
  if (balancer.busy || !state.doc) return null;
  balancer.busy = true;
  $("balance").disabled = true;
  const t0 = performance.now();
  const doc = state.doc;
  const text = doc.text;
  const stale = () => state.doc !== doc || doc.text !== text;       // il brano e' cambiato nel frattempo: si lascia stare
  try {
    await analyze();
    if (stale() || !state.song) return null;
    const roles = (await call("balance_roles", { args: [text] })).result.roles;
    const names = Object.keys(roles);
    const all = state.song.info.tracks.map((tr) => tr.name);
    const levels = {};
    for (let i = 0; i < names.length; i++) {
      setStatus(t("Bilancio i volumi… {n} di {total}", { n: i + 1, total: names.length }));
      const r = await call("render", { key: "bilancia-" + i + "-" + Date.now(), semitones: state.semitones,
                                       muted: all.filter((name) => name !== names[i]), metronome: false,
                                       banks: fontBanks(), sends: fxSends() });
      if (stale()) return null;
      const out = await renderOffline(r.midi, { fromBeat: 0, toBeat: null, seconds: BALANCE_MAX_SECONDS, tail: 0.5,
                                                rate: BALANCE_RATE });
      levels[names[i]] = balanceLevelDb(out.left, out.right, out.rate);
      if (stale()) return null;
    }
    const res = (await call("balance_apply", { args: [text, levels] })).result;
    if (stale()) return null;
    const changed = Object.keys(res.changes);
    Metrics.record("bilancia", { automatic, tracks: names.length, changed: changed.length, ms: ms(t0) });
    if (!changed.length) {
      setStatus(t("I volumi erano già bilanciati."));
      return res;
    }
    const playing = state.playing && !state.previewing;
    const tick = playing ? await playerTick() : null;
    await replaceDocText(res.text);
    balancer.before = text;
    balancer.after = res.text;
    $("balanceUndo").hidden = false;
    if (playing) {                                        // si sente subito: il lettore riparte dallo stesso punto
      await analyze();
      state.synth.midiAllSoundsOff();
      await startPlayer(tick);
    }
    setStatus(t("Volumi bilanciati: {tracks}.", {
      tracks: changed.map((name) => `${name.replace(/_/g, " ")} ${res.changes[name][0]}→${res.changes[name][1]}`).join(", "),
    }));
    return res;
  } catch (e) {
    console.error(e);
    if (!automatic) setStatus(t("Non riesco a bilanciare i volumi ({message}).", { message: e.message || String(e) }), true);
    return null;
  } finally {
    balancer.busy = false;
    $("balance").disabled = false;
  }
}

// Annulla il bilanciamento: il testo di prima, se nel frattempo non e' cambiato altro
async function undoBalance() {
  $("balanceUndo").hidden = true;
  if (!state.doc || state.doc.text !== balancer.after || balancer.before == null) return;
  await replaceDocText(balancer.before);
  balancer.before = balancer.after = null;
  setStatus(t("Volumi come prima."));
}

function setupBalance() {
  $("balance").onclick = () => balanceVolumes().catch(showError);
  $("balanceUndo").onclick = () => undoBalance().catch(showError);
}
