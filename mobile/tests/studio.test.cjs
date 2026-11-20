// Il riconoscimento dell'altezza e la valutazione della modalita' studio, su note sintetiche
// (nota giusta, crescente, in ritardo, mancante). Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { Studio } = require("../studio.js");

const RATE = 44100;

function tone(hz, seconds, amp = 0.4) {
  const x = new Float32Array(Math.round(seconds * RATE));
  for (let i = 0; i < x.length; i++) {
    const p = 2 * Math.PI * hz * i / RATE;
    x[i] = amp * (Math.sin(p) + 0.4 * Math.sin(2 * p) + 0.2 * Math.sin(3 * p)) / 1.6;
  }
  return x;
}

test("un La a 440 Hz entro 3 cent, anche con le armoniche", () => {
  for (const hz of [110, 220, 440, 880]) {
    const r = Studio.detectPitch(tone(hz, 0.1), RATE);
    assert.ok(r.hz > 0, String(hz));
    const n = Studio.noteOf(r.hz);
    assert.strictEqual(n.name, "La");
    assert.ok(Math.abs(Studio.midiOf(r.hz) - Studio.midiOf(hz)) * 100 < 3, `${hz}: ${r.hz}`);
  }
});

test("il silenzio e il rumore non sono una nota", () => {
  assert.strictEqual(Studio.detectPitch(new Float32Array(4096), RATE).hz, 0);
  let seed = 1;
  const noise = new Float32Array(4096).map(() => { seed = (seed * 16807) % 2147483647; return (seed / 2147483647 - 0.5) * 0.4; });
  assert.strictEqual(Studio.detectPitch(noise, RATE).hz, 0);
});

test("nota e scostamento in cent", () => {
  assert.deepStrictEqual(Studio.noteOf(440), { midi: 69, name: "La", octave: 4, cents: 0 });
  const flat = Studio.noteOf(440 * Math.pow(2, -10 / 1200));
  assert.strictEqual(flat.cents, -10);
  assert.strictEqual(Studio.noteOf(261.63).name, "Do");
  assert.ok(Math.abs(Studio.hzOf(69, 442) - 442) < 1e-9);
});

// una melodia di 8 battute a 120 BPM (mezzo secondo a battito): una nota a battito
const NOTES = [60, 62, 64, 65, 67, 65, 64, 62].map((m, i) => [i, 1, m]);
const BARS = [0, 4];

// i frame ogni 0,1 s, come li darebbe il microfono: 'sing' dice quale altezza (MIDI, con i cent) a ogni istante
function frames(sing) {
  const out = [];
  for (let s = 0; s < 4.0; s += 0.1) {
    const m = sing(s);
    if (!m) { out.push({ beat: s * 2, midi: 0 }); continue; }
    const r = Studio.detectPitch(tone(Studio.hzOf(m), 0.093), RATE);
    out.push({ beat: s * 2, midi: r.hz ? Studio.midiOf(r.hz) : 0 });
  }
  return out;
}

const run = (sing, extra = {}) => Studio.evaluate(NOTES, frames(sing), { bpm: 120, bars: BARS, ...extra });

test("una melodia intonata e a tempo e' quasi tutta verde", () => {
  const r = run((s) => NOTES[Math.min(7, Math.floor(s * 2))][2]);
  assert.ok(r.okShare >= 0.9, JSON.stringify(r.notes));
  assert.ok(r.intonation >= 90 && r.timing >= 90);
  assert.deepStrictEqual(r.review, []);
});

test("una nota sbagliata di proposito si colora nel punto giusto", () => {
  const r = run((s) => { const i = Math.min(7, Math.floor(s * 2)); return i === 5 ? NOTES[i][2] + 3 : NOTES[i][2]; });
  assert.strictEqual(r.notes[5].status, "bad");
  assert.ok(r.notes.filter((n, i) => i !== 5).every((n) => n.status === "ok"));
  assert.deepStrictEqual(r.review, [2]);
});

test("una nota crescente di 60 cent e' gialla, di mezzo tono e' rossa", () => {
  const r = run((s) => { const i = Math.min(7, Math.floor(s * 2)); return i === 2 ? NOTES[i][2] + 0.6 : i === 6 ? NOTES[i][2] + 1 : NOTES[i][2]; });
  assert.strictEqual(r.notes[2].status, "near");
  assert.strictEqual(r.notes[6].status, "bad");
});

test("una nota in ritardo non e' piu' verde", () => {
  const r = run((s) => { const i = Math.min(7, Math.floor((s - (s >= 1.5 && s < 2 ? 0.35 : 0)) * 2)); return NOTES[Math.max(0, i)][2]; });
  assert.notStrictEqual(r.notes[3].status, "ok");
  assert.ok(r.timing < 100);
});

test("una nota mancante e' segnata, e chi canta un'ottava sotto non sbaglia", () => {
  const r = run((s) => { const i = Math.min(7, Math.floor(s * 2)); return i === 4 ? 0 : NOTES[i][2] - 12; });
  assert.strictEqual(r.notes[4].status, "missing");
  assert.ok(r.notes.filter((n, i) => i !== 4).every((n) => n.status === "ok"));
  assert.deepStrictEqual(r.review, [2]);
});

test("il ritardo del suono si toglie con 'lag'", () => {
  const sing = (s) => { const i = Math.min(7, Math.floor((s - 0.25) * 2)); return i < 0 ? 0 : NOTES[i][2]; };
  const late = run(sing), fixed = run(sing, { lag: 0.5 });
  assert.ok(fixed.timing > late.timing);
});

test("le sigle si traspongono per il capotasto", () => {
  assert.strictEqual(Studio.transposeChord("Am7", 3), "Cm7");
  assert.strictEqual(Studio.transposeChord("G/B", -2), "F/A");
  assert.strictEqual(Studio.transposeChord("Bb", 2), "C");
  assert.strictEqual(Studio.transposeChord("F#m", -1), "Fm");
  assert.strictEqual(Studio.transposeChord("N.C.", 2), "N.C.");
});
