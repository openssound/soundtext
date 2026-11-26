// SoundText Mobile: il rendering dell'audio fuori tempo, per l'esportazione. Lo stesso sintetizzatore
// del lettore (FluidSynth in WebAssembly con js-synthesizer), ma nella versione che calcola i campioni
// quando glieli si chiedono: piu' veloce del tempo reale e senza uscita audio, quindi senza rumori.
// Risponde con i canali sinistro e destro e, per ogni blocco, il tick del brano a quell'istante
// (serve alla clip video per tenere le immagini a tempo con l'audio).
"use strict";

importScripts("vendor/js-synthesizer/libfluidsynth-2.4.6-with-libsndfile.js", "vendor/js-synthesizer/js-synthesizer.js");

const BLOCK = 1024;

self.onmessage = async (ev) => {
  const { sf, fonts, reverb, midi, rate, fromTick, toTick, maxFrames, tailFrames, speed } = ev.data;
  let synth = null;
  try {
    await JSSynth.waitForReady();
    synth = new JSSynth.Synthesizer();
    synth.init(rate, { midiChannelCount: 32, ...(reverb || {}) });        // il riverbero del brano, come nel lettore
    await synth.loadSFont(sf);
    // i SoundFont dell'utente sopra quello incluso: il predefinito (banco 0) e quelli delle tracce (banco 1, 2...)
    for (const font of fonts || []) {
      const id = await synth.loadSFont(font.bytes);
      if (font.bank) synth.setSFontBankOffset(id, font.bank);
    }
    await synth.addSMFDataToPlayer(midi);
    if (speed && speed !== 1) synth.setPlayerTempo(0, speed);   // la velocita' del lettore (moltiplicatore del tempo del file)
    await synth.playPlayer();

    const lefts = [], rights = [], marks = [];
    const l = new Float32Array(BLOCK), r = new Float32Array(BLOCK);
    let frames = 0;
    // 'keep': prima dell'inizio del tratto si calcola e si butta (il sintetizzatore non sa saltare in
    // avanti senza guastarsi: cosi' anche le note tenute dal passaggio prima suonano come nel lettore)
    const take = (tick, keep) => {
      synth.render([l, r]);
      if (!keep) return;
      marks.push(tick);
      lefts.push(l.slice());
      rights.push(r.slice());
      frames += BLOCK;
      if (lefts.length % 80 === 0) self.postMessage({ type: "progress", frames });
    };
    // il file si legge quando il player comincia a suonare: i tick totali si sanno dopo il primo blocco
    take(0, fromTick <= 0);
    const total = await synth.retrievePlayerTotalTicks();
    const end = toTick == null ? total : Math.min(toTick, total);
    // la musica
    for (;;) {
      const tick = await synth.retrievePlayerCurrentTick();
      if (tick >= end - 1 || frames >= maxFrames) break;
      take(tick, tick >= fromTick);
    }
    // la coda: le note si spengono (il tratto tagliato a meta') e il riverbero finisce
    if (end < total || frames >= maxFrames) synth.midiAllNotesOff(-1);
    const tickAtEnd = await synth.retrievePlayerCurrentTick();
    let tail = 0;
    while (tail < tailFrames && (synth.isPlaying() || tail === 0)) {
      take(tickAtEnd, true);
      tail += BLOCK;
    }
    const length = Math.min(frames, maxFrames + tailFrames);
    const left = new Float32Array(length), right = new Float32Array(length);
    lefts.forEach((chunk, i) => { const at = i * BLOCK; if (at < length) left.set(chunk.subarray(0, Math.min(BLOCK, length - at)), at); });
    rights.forEach((chunk, i) => { const at = i * BLOCK; if (at < length) right.set(chunk.subarray(0, Math.min(BLOCK, length - at)), at); });
    synth.close();
    self.postMessage({ type: "done", left, right, marks: Float64Array.from(marks), block: BLOCK, rate, musicFrames: frames - tail }, [left.buffer, right.buffer]);
  } catch (e) {
    try { if (synth) synth.close(); } catch (e2) {}
    self.postMessage({ type: "error", message: String(e && e.message || e) });
  }
};
