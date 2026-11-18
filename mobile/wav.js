// Un file WAV (PCM a 16 bit, stereo) da due canali di campioni: l'esportazione audio di SoundText Mobile.
// Si prova da Node con mobile/tests/wav.test.cjs.
"use strict";

const Wav = (() => {
  function encode(left, right, rate) {
    const frames = left.length;
    const out = new Uint8Array(44 + frames * 4);
    const view = new DataView(out.buffer);
    const text = (at, s) => { for (let i = 0; i < s.length; i++) out[at + i] = s.charCodeAt(i); };
    text(0, "RIFF"); view.setUint32(4, 36 + frames * 4, true); text(8, "WAVE");
    text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 2, true);
    view.setUint32(24, rate, true); view.setUint32(28, rate * 4, true); view.setUint16(32, 4, true); view.setUint16(34, 16, true);
    text(36, "data"); view.setUint32(40, frames * 4, true);
    const clip = (v) => (v >= 1 ? 32767 : v <= -1 ? -32768 : Math.round(v * 32767));
    for (let i = 0, at = 44; i < frames; i++, at += 4) {
      view.setInt16(at, clip(left[i]), true);
      view.setInt16(at + 2, clip(right[i]), true);
    }
    return out;
  }

  // una dissolvenza in uscita sugli ultimi 'frames' campioni (un tratto tagliato a meta' non fa «clic»)
  function fadeOut(channels, frames) {
    for (const data of channels) {
      const n = Math.min(frames, data.length);
      for (let i = 0; i < n; i++) data[data.length - n + i] *= 1 - (i + 1) / n;
    }
  }

  // il segnale si porta a un picco di 'target' (-1 dB): il SoundFont suona piano, e un file
  // che si sente appena non si condivide volentieri. Un segnale gia' forte resta com'e'.
  function normalize(channels, target = 0.89) {
    let peak = 0;
    for (const data of channels) for (let i = 0; i < data.length; i++) { const v = Math.abs(data[i]); if (v > peak) peak = v; }
    if (peak <= 0 || peak >= target) return 1;
    const gain = target / peak;
    for (const data of channels) for (let i = 0; i < data.length; i++) data[i] *= gain;
    return gain;
  }

  return { encode, fadeOut, normalize };
})();

if (typeof module !== "undefined") module.exports = { Wav };
