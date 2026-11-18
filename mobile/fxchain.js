// La catena master di un brano con il Web Audio: gli effetti sul mix finale (EQ, compressore, limiter, volume,
// filtri, delay, riverbero, chorus), nell'ordine del file. I parametri sono quelli del piano che da' il motore
// (engine.effects_plan). Il Web Audio non fa gli stessi calcoli di SoundText sul computer: e' un'approssimazione
// che si sente ma non coincide. Funziona sia su un AudioContext (lettore) sia su un OfflineAudioContext
// (esportazione). Si prova da Node con mobile/tests/fxchain.test.cjs, con un contesto finto.
"use strict";

const FxChain = (() => {
  const dB = (v) => Math.pow(10, v / 20);

  // Un'impulso per il riverbero: rumore che si spegne, piu' scuro con lo smorzamento
  function impulse(ctx, seconds, damping) {
    const length = Math.max(1, Math.round(ctx.sampleRate * seconds));
    const buffer = ctx.createBuffer(2, length, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const data = buffer.getChannelData(c);
      let low = 0;
      const smooth = 0.05 + (1 - damping) * 0.9;          // 1 = nessun smorzamento delle alte
      let seed = 12345 + c * 777;
      for (let i = 0; i < length; i++) {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        const noise = (seed / 4294967296) * 2 - 1;
        low += (noise - low) * smooth;
        data[i] = low * Math.pow(1 - i / length, 3);
      }
    }
    return buffer;
  }

  const chain = (stages) => {
    for (let i = 0; i + 1 < stages.length; i++) stages[i].out.connect(stages[i + 1].in);
    return { in: stages[0].in, out: stages[stages.length - 1].out };
  };
  const single = (node) => ({ in: node, out: node });

  function biquad(ctx, type, frequency, gain, q) {
    const f = ctx.createBiquadFilter();
    f.type = type;
    f.frequency.value = frequency;
    if (gain !== undefined) f.gain.value = gain;
    if (q !== undefined) f.Q.value = q;
    return single(f);
  }

  function gainNode(ctx, value) {
    const g = ctx.createGain();
    g.gain.value = value;
    return single(g);
  }

  function compressor(ctx, threshold, ratio, attack, release, knee) {
    const c = ctx.createDynamicsCompressor();
    c.threshold.value = threshold;
    c.knee.value = knee;
    c.ratio.value = ratio;
    c.attack.value = attack;
    c.release.value = release;
    return single(c);
  }

  // Un effetto "in parallelo": il segnale pulito piu' quello trattato, mescolati
  function parallel(ctx, dry, wetPath, wet) {
    const input = ctx.createGain(), output = ctx.createGain();
    const dryGain = ctx.createGain(), wetGain = ctx.createGain();
    dryGain.gain.value = dry;
    wetGain.gain.value = wet;
    input.connect(dryGain); dryGain.connect(output);
    input.connect(wetPath.in); wetPath.out.connect(wetGain); wetGain.connect(output);
    return { in: input, out: output };
  }

  function stage(ctx, spec, keep) {
    const p = spec.params || {};
    switch (spec.kind) {
      case "volume":
        return gainNode(ctx, dB(p.guadagno));
      case "eq":
        return chain([biquad(ctx, "lowshelf", 120, p.bassi), biquad(ctx, "peaking", 1000, p.medi, 0.9), biquad(ctx, "highshelf", 5000, p.alti)]);
      case "passa_alto":
      case "passa_basso": {
        const type = spec.kind === "passa_alto" ? "highpass" : "lowpass";
        const stages = [biquad(ctx, type, p.frequenza, undefined, 0.707)];
        if (p.pendenza >= 18) stages.push(biquad(ctx, type, p.frequenza, undefined, 0.707));       // 18 e 24 dB/ott: due passi
        return chain(stages);
      }
      case "compressore":
        // il DynamicsCompressorNode rimette da solo il volume che toglie: il parametro «guadagno» non si aggiunge
        return compressor(ctx, p.soglia, p.rapporto, p.attacco / 1000, p.rilascio / 1000, 6);
      case "limiter":
        return chain([gainNode(ctx, dB(p.guadagno)), compressor(ctx, p.tetto, 20, 0.003, p.rilascio / 1000, 0)]);
      case "delay": {
        const delay = ctx.createDelay(3);
        delay.delayTime.value = Math.min(3, Math.max(0.01, spec.seconds || p.tempo / 1000));
        const feedback = ctx.createGain();
        feedback.gain.value = Math.min(0.9, p.ripetizioni / 100);
        delay.connect(feedback); feedback.connect(delay);
        return parallel(ctx, 1, single(delay), p.mix / 100);
      }
      case "riverbero": {
        const convolver = ctx.createConvolver();
        convolver.buffer = impulse(ctx, 0.3 + (p.stanza / 100) * 2.2, p.smorzamento / 100);
        return parallel(ctx, 1 - p.mix / 250, single(convolver), (p.mix / 100) * 0.8);
      }
      case "chorus": {
        const wetIn = ctx.createGain(), wetOut = ctx.createGain();
        [0.020, 0.027].forEach((base, i) => {
          const d = ctx.createDelay(0.1);
          d.delayTime.value = base;
          const lfo = ctx.createOscillator();
          lfo.frequency.value = p.velocita * (i ? 1.13 : 1);
          const depth = ctx.createGain();
          depth.gain.value = (p.profondita / 100) * 0.006;
          lfo.connect(depth); depth.connect(d.delayTime);
          lfo.start();
          keep.push(lfo);
          wetIn.connect(d); d.connect(wetOut);
        });
        return parallel(ctx, 1, { in: wetIn, out: wetOut }, (p.mix / 100) * 0.7);
      }
      default:
        return null;
    }
  }

  // In fondo, un tetto morbido: i picchi che il limiter lascia passare non diventano distorsione dura
  // (sotto 0,8 il segnale non cambia; sopra si piega verso 0,95).
  function safety(ctx) {
    const shaper = ctx.createWaveShaper();
    const points = 2049;
    const curve = new Float32Array(points);
    for (let i = 0; i < points; i++) {
      const x = (i / (points - 1)) * 2 - 1, a = Math.abs(x);
      curve[i] = Math.sign(x) * (a <= 0.8 ? a : 0.8 + 0.2 * Math.tanh((a - 0.8) / 0.2));
    }
    shaper.curve = curve;
    return single(shaper);
  }

  // specs: gli effetti nell'ordine. Restituisce { input, output, dispose } oppure null se non c'e' niente da fare.
  function build(ctx, specs) {
    const keep = [];
    const stages = [];
    for (const spec of specs || []) {
      const s = stage(ctx, spec, keep);
      if (s) stages.push(s);
    }
    if (!stages.length) return null;
    const input = ctx.createGain(), output = ctx.createGain();
    const wired = chain([single(input), ...stages, safety(ctx), single(output)]);
    return {
      input: wired.in, output: wired.out, count: stages.length,
      dispose() { for (const o of keep) { try { o.stop(); } catch (e) {} } },
    };
  }

  return { build };
})();

if (typeof module !== "undefined") module.exports = { FxChain };
