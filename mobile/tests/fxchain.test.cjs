// La catena di effetti master (mobile/fxchain.js), con un contesto Web Audio finto che registra i nodi e i
// collegamenti. Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { FxChain } = require("../fxchain.js");

function fakeContext() {
  const nodes = [];
  const param = (value = 0) => ({ value });
  const make = (type, extra = {}) => {
    const node = { kind: type, links: [], connect(to) { this.links.push(to); return to; }, ...extra };
    nodes.push(node);
    return node;
  };
  return {
    nodes, sampleRate: 8000,
    createGain: () => make("gain", { gain: param(1) }),
    createBiquadFilter: () => make("biquad", { frequency: param(), gain: param(), Q: param() }),
    createDynamicsCompressor: () => make("compressor", { threshold: param(), knee: param(), ratio: param(), attack: param(), release: param() }),
    createDelay: () => make("delay", { delayTime: param() }),
    createWaveShaper: () => make("shaper", { curve: null }),
    createConvolver: () => make("convolver", { buffer: null }),
    createOscillator: () => make("oscillator", { frequency: param(), start() { this.started = true; }, stop() { this.stopped = true; } }),
    createBuffer: (channels, length) => ({ channels, length, getChannelData: () => new Float32Array(length) }),
  };
}

const of = (ctx, kind) => ctx.nodes.filter((n) => n.kind === kind);

// tutto cio' che si raggiunge dall'ingresso arriva all'uscita
function reaches(from, to) {
  const seen = new Set();
  const walk = (n) => {
    if (n === to) return true;
    if (seen.has(n)) return false;
    seen.add(n);
    return n.links.some((m) => m && m.links && walk(m));
  };
  return walk(from);
}

test("compressore e limiter: soglia, rapporto e guadagno arrivano ai nodi", () => {
  const ctx = fakeContext();
  const fx = FxChain.build(ctx, [
    { kind: "compressore", params: { soglia: -14, rapporto: 2, attacco: 30, rilascio: 200, guadagno: 6 } },
    { kind: "limiter", params: { guadagno: 3, tetto: -1, rilascio: 100 } },
  ]);
  const [comp, lim] = of(ctx, "compressor");
  assert.deepStrictEqual([comp.threshold.value, comp.ratio.value, comp.attack.value, comp.release.value], [-14, 2, 0.03, 0.2]);
  assert.deepStrictEqual([lim.threshold.value, lim.ratio.value, lim.knee.value], [-1, 20, 0]);
  const gains = of(ctx, "gain").map((g) => g.gain.value);
  assert.ok(!gains.some((g) => Math.abs(g - Math.pow(10, 6 / 20)) < 1e-9), "il guadagno del compressore lo rimette il nodo da solo");
  assert.ok(gains.some((g) => Math.abs(g - Math.pow(10, 3 / 20)) < 1e-9), "guadagno del limiter (+3 dB)");
  assert.strictEqual(fx.count, 2);
  // il tetto morbido in fondo: sotto 0,8 non cambia il segnale, sopra non supera 0,96
  const [shaper] = of(ctx, "shaper");
  const mid = (shaper.curve.length - 1) / 2;
  assert.ok(Math.abs(shaper.curve[mid + Math.round(mid * 0.5)] - 0.5) < 1e-3);
  assert.ok(shaper.curve[shaper.curve.length - 1] < 0.96 && shaper.curve[0] > -0.96);
  assert.ok(shaper.curve[mid + Math.round(mid * 0.95)] > shaper.curve[mid + Math.round(mid * 0.85)]);              // sempre crescente
  assert.ok(reaches(fx.input, fx.output));
});

test("EQ a tre bande, filtri e volume", () => {
  const ctx = fakeContext();
  const fx = FxChain.build(ctx, [
    { kind: "eq", params: { bassi: 3, medi: -2, alti: 4 } },
    { kind: "passa_alto", params: { frequenza: 100, pendenza: 24 } },
    { kind: "passa_basso", params: { frequenza: 9000, pendenza: 12 } },
    { kind: "volume", params: { guadagno: -6 } },
  ]);
  const filters = of(ctx, "biquad");
  assert.strictEqual(filters.length, 3 + 2 + 1);                     // 24 dB/ott: due passi; 12: uno
  assert.deepStrictEqual(filters.map((f) => f.type), ["lowshelf", "peaking", "highshelf", "highpass", "highpass", "lowpass"]);
  assert.deepStrictEqual(filters.slice(0, 3).map((f) => f.gain.value), [3, -2, 4]);
  assert.deepStrictEqual(filters.slice(0, 3).map((f) => f.frequency.value), [120, 1000, 5000]);
  assert.ok(of(ctx, "gain").some((g) => Math.abs(g.gain.value - Math.pow(10, -6 / 20)) < 1e-9));
  assert.ok(reaches(fx.input, fx.output));
});

test("delay, riverbero e chorus mescolano il segnale pulito e quello trattato", () => {
  const ctx = fakeContext();
  const fx = FxChain.build(ctx, [
    { kind: "delay", seconds: 0.5, params: { ripetizioni: 40, mix: 30, tempo: 375, suddivisione: 3 } },
    { kind: "riverbero", params: { stanza: 50, smorzamento: 50, ampiezza: 100, mix: 20 } },
    { kind: "chorus", params: { velocita: 1, profondita: 40, mix: 50 } },
  ]);
  const [delay] = of(ctx, "delay");
  assert.strictEqual(delay.delayTime.value, 0.5);
  const [conv] = of(ctx, "convolver");
  assert.ok(conv.buffer && conv.buffer.length === Math.round(8000 * (0.3 + 0.5 * 2.2)));
  assert.strictEqual(of(ctx, "oscillator").length, 2);
  assert.ok(of(ctx, "oscillator").every((o) => o.started));
  assert.ok(reaches(fx.input, fx.output));
  fx.dispose();
  assert.ok(of(ctx, "oscillator").every((o) => o.stopped));
});

test("senza effetti da fare non c'e' catena; un tipo sconosciuto si salta", () => {
  assert.strictEqual(FxChain.build(fakeContext(), []), null);
  assert.strictEqual(FxChain.build(fakeContext(), [{ kind: "amplificatore", params: {} }]), null);
  const ctx = fakeContext();
  const fx = FxChain.build(ctx, [{ kind: "nam", params: {} }, { kind: "volume", params: { guadagno: 0 } }]);
  assert.strictEqual(fx.count, 1);
});
