// Il WAV e la dissolvenza di mobile/wav.js. Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { Wav } = require("../wav.js");

test("il WAV ha l'intestazione giusta e i campioni a 16 bit", () => {
  const left = Float32Array.of(0, 0.5, -0.5, 1, -1), right = Float32Array.of(1, 0, 2, -2, 0.25);
  const bytes = Wav.encode(left, right, 44100);
  const view = new DataView(bytes.buffer);
  assert.strictEqual(String.fromCharCode(...bytes.subarray(0, 4)), "RIFF");
  assert.strictEqual(String.fromCharCode(...bytes.subarray(8, 16)), "WAVEfmt ");
  assert.strictEqual(view.getUint32(4, true), bytes.length - 8);
  assert.strictEqual(view.getUint16(22, true), 2);                       // stereo
  assert.strictEqual(view.getUint32(24, true), 44100);
  assert.strictEqual(view.getUint32(40, true), 5 * 4);
  assert.strictEqual(bytes.length, 44 + 5 * 4);
  const sample = (i) => view.getInt16(44 + i * 2, true);
  assert.deepStrictEqual([0, 1, 2, 3, 4, 5].map(sample), [0, 32767, 16384, 0, -16383, 32767]);
  assert.strictEqual(sample(6), 32767);                                  // 1.0 resta al massimo
  assert.strictEqual(sample(7), -32768);                                 // -2.0, oltre l'intervallo: tagliato, non avvolto
  assert.strictEqual(sample(9), 8192);
});

test("la dissolvenza porta l'ultimo campione a zero e non tocca l'inizio", () => {
  const data = new Float32Array(100).fill(1);
  Wav.fadeOut([data], 20);
  assert.strictEqual(data[79], 1);
  assert.ok(data[80] < 1 && data[80] > 0.9);
  assert.strictEqual(data[99], 0);
  const short = new Float32Array(5).fill(1);
  Wav.fadeOut([short], 50);                                              // piu' lunga del segnale: non esce dai limiti
  assert.strictEqual(short[4], 0);
});

test("ffprobe legge il WAV", { skip: spawnSync("ffprobe", ["-version"], { stdio: "ignore" }).status !== 0 && "ffprobe non c'e'" }, () => {
  const rate = 48000;
  const left = new Float32Array(rate), right = new Float32Array(rate);
  for (let i = 0; i < rate; i++) { left[i] = Math.sin(2 * Math.PI * 440 * i / rate) * 0.5; right[i] = left[i]; }
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "stwav-")), "a.wav");
  fs.writeFileSync(file, Wav.encode(left, right, rate));
  const r = spawnSync("ffprobe", ["-v", "error", "-show_streams", "-of", "json", file], { encoding: "utf8" });
  const stream = JSON.parse(r.stdout).streams[0];
  assert.strictEqual(stream.codec_name, "pcm_s16le");
  assert.strictEqual(Number(stream.sample_rate), rate);
  assert.strictEqual(stream.channels, 2);
  assert.ok(Math.abs(Number(stream.duration) - 1) < 0.001);
});

test("la normalizzazione porta il picco a -1 dB e non rovina un segnale gia' forte", () => {
  const quiet = [Float32Array.of(0.1, -0.2, 0.05), Float32Array.of(0.02, 0.1, -0.1)];
  const gain = Wav.normalize(quiet);
  assert.ok(Math.abs(gain - 0.89 / 0.2) < 1e-6);
  assert.ok(Math.abs(Math.max(...quiet.flatMap((c) => [...c].map(Math.abs))) - 0.89) < 1e-6);
  const loud = [Float32Array.of(0.95, -0.5)];
  assert.strictEqual(Wav.normalize(loud), 1);
  assert.deepStrictEqual([...loud[0]].map((v) => +v.toFixed(2)), [0.95, -0.5]);
  assert.strictEqual(Wav.normalize([new Float32Array(10)]), 1);          // silenzio: niente da amplificare
});
