// SoundText Mobile: modalita' studio. Il calcolo e' qui, senza pagina, cosi' si prova da Node
// (mobile/tests/studio.test.cjs): riconoscimento dell'altezza di una nota (YIN), da frequenza a nota
// e cent, valutazione di quanto si e' suonato rispetto alla partitura.
"use strict";

const Studio = (() => {
  const NAMES = ["Do", "Do♯", "Re", "Re♯", "Mi", "Fa", "Fa♯", "Sol", "Sol♯", "La", "La♯", "Si"];

  // L'altezza (Hz) di un blocco di campioni con l'algoritmo YIN; 0 se non c'e' una nota chiara (silenzio, rumore).
  function detectPitch(x, rate, opts = {}) {
    const minHz = opts.minHz || 70, maxHz = opts.maxHz || 1400, threshold = opts.threshold || 0.15;
    const n = x.length;
    let energy = 0;
    for (let i = 0; i < n; i++) energy += x[i] * x[i];
    if (Math.sqrt(energy / n) < (opts.minRms || 0.01)) return { hz: 0, clarity: 0 };
    const tauMax = Math.min(Math.floor(rate / minHz), (n >> 1) - 1), tauMin = Math.max(2, Math.floor(rate / maxHz));
    const half = n >> 1;
    const d = new Float32Array(tauMax + 1);
    for (let tau = 1; tau <= tauMax; tau++) {
      let sum = 0;
      for (let i = 0; i < half; i++) { const diff = x[i] - x[i + tau]; sum += diff * diff; }
      d[tau] = sum;
    }
    let running = 0;
    for (let tau = 1; tau <= tauMax; tau++) {          // la differenza normalizzata a media cumulata
      running += d[tau];
      d[tau] = running ? d[tau] * tau / running : 1;
    }
    let tau = -1;
    for (let t = tauMin; t <= tauMax; t++) {
      if (d[t] < threshold) {
        while (t + 1 <= tauMax && d[t + 1] < d[t]) t++;
        tau = t;
        break;
      }
    }
    if (tau < 0) return { hz: 0, clarity: 0 };
    let better = tau;                                   // interpolazione parabolica
    if (tau > 1 && tau < tauMax) {
      const a = d[tau - 1], b = d[tau], c = d[tau + 1];
      const den = a - 2 * b + c;
      if (den) better = tau + (a - c) / (2 * den);
    }
    return { hz: rate / better, clarity: 1 - d[tau] };
  }

  const midiOf = (hz, a4 = 440) => 69 + 12 * Math.log2(hz / a4);
  const hzOf = (midi, a4 = 440) => a4 * Math.pow(2, (midi - 69) / 12);

  // La nota piu' vicina e lo scostamento in cent (negativo = calante)
  function noteOf(hz, a4 = 440) {
    const m = midiOf(hz, a4), near = Math.round(m);
    return { midi: near, name: NAMES[((near % 12) + 12) % 12], octave: Math.floor(near / 12) - 1, cents: Math.round((m - near) * 100) };
  }

  // Le corde delle accordature (note MIDI, dalla piu' grave)
  const TUNINGS = {
    chitarra: [40, 45, 50, 55, 59, 64], basso: [28, 33, 38, 43], violino: [55, 62, 69, 76], ukulele: [67, 60, 64, 69],
  };

  // L'altezza piu' vicina al bersaglio, ripiegata fra le ottave: chi canta un'ottava sotto non sbaglia nota
  function centsFrom(midi, target) {
    let c = (midi - target) * 100;
    c -= 1200 * Math.round(c / 1200);
    return c;
  }

  // frames: [{beat, midi}] (midi 0 = nessuna nota chiara), notes: [[inizio, durata, nota]] in battiti,
  // bars: l'inizio delle battute. Le note si leggono nei frame che cadono nella loro durata; 'lag' e' il
  // ritardo del suono (battiti) da togliere ai frame.
  function evaluate(notes, frames, opts = {}) {
    const bpm = opts.bpm || 120, bars = opts.bars || [0];
    const beatSec = 60 / bpm;
    const timeOk = (opts.timeOk || 0.15) / beatSec, timeNear = (opts.timeNear || 0.3) / beatSec;
    const lag = opts.lag || 0;
    const results = [];
    const sorted = frames.map((f) => ({ beat: f.beat - lag, midi: f.midi })).sort((a, b) => a.beat - b.beat);
    for (const [start, dur, target] of notes) {
      const end = start + dur;
      const inside = sorted.filter((f) => f.beat >= start - timeNear && f.beat < end + timeNear * 0.5);
      const voiced = inside.filter((f) => f.midi > 0);
      const during = voiced.filter((f) => f.beat >= start && f.beat < end);
      if (during.length < Math.max(1, Math.round(dur / (opts.frame || 0.1 / beatSec) * 0.3))) {
        results.push({ start, target, status: "missing", cents: null, delay: null });
        continue;
      }
      const errs = during.map((f) => centsFrom(f.midi, target)).sort((a, b) => a - b);
      const cents = errs[errs.length >> 1];                      // la mediana
      const onFrame = voiced.find((f) => Math.abs(centsFrom(f.midi, target)) < 75);
      const delay = onFrame ? (onFrame.beat - start) * beatSec : null;
      const absC = Math.abs(cents);
      const pitchGrade = absC <= 35 ? 2 : absC <= 75 ? 1 : 0;
      const dl = delay == null ? Infinity : Math.abs(delay);
      const timeGrade = dl <= timeOk * beatSec ? 2 : dl <= timeNear * beatSec ? 1 : 0;
      const status = pitchGrade === 0 || timeGrade === 0 ? "bad" : pitchGrade === 2 && timeGrade === 2 ? "ok" : "near";
      results.push({ start, target, status, cents: Math.round(cents), delay: delay == null ? null : Math.round(delay * 1000) / 1000, pitchGrade, timeGrade });
    }
    const n = results.length || 1;
    const share = (grade) => results.reduce((s, r) => s + (r.status === "missing" ? 0 : (r[grade] || 0) / 2), 0) / n;
    const barOf = (beat) => {
      let i = 0;
      while (i + 1 < bars.length && bars[i + 1] <= beat + 1e-9) i++;
      return i + 1;
    };
    const review = [...new Set(results.filter((r) => r.status !== "ok").map((r) => barOf(r.start)))];
    return {
      notes: results,
      intonation: Math.round(share("pitchGrade") * 100),
      timing: Math.round(share("timeGrade") * 100),
      okShare: results.filter((r) => r.status === "ok").length / n,
      review,
    };
  }

  // Una sigla di accordo trasposta (di 'semitones'): per il capotasto si mostra la forma da suonare
  function transposeChord(label, semitones) {
    const m = /^([A-G][#b]?)([^/]*)(?:\/([A-G][#b]?))?$/.exec(label);
    if (!m) return label;
    const sharp = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const flat = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
    const index = (r) => { const i = sharp.indexOf(r); return i >= 0 ? i : flat.indexOf(r); };
    const useFlat = m[1].includes("b") || (m[1] === "F" && semitones < 0);
    const shift = (r) => { const i = index(r); return i < 0 ? r : (useFlat ? flat : sharp)[(((i + semitones) % 12) + 12) % 12]; };
    return shift(m[1]) + m[2] + (m[3] ? "/" + shift(m[3]) : "");
  }

  return { detectPitch, midiOf, hzOf, noteOf, centsFrom, evaluate, transposeChord, TUNINGS, NAMES };
})();

if (typeof module !== "undefined") module.exports = { Studio };
