// SoundText Mobile: un file MIDI che comincia da un punto qualsiasi del brano.
// Nel FluidSynth in WebAssembly, fluid_player_seek ferma il sintetizzatore («null function» nel thread audio),
// quindi per ripartire a meta' brano (riprendi dalla pausa, A-B, vai alla battuta) si da' al lettore un file
// accorciato: il tempo, gli strumenti, i volumi e il resto dei controlli restano all'istante 0, le note che
// cominciano prima del punto spariscono, il resto scorre indietro di 'tick'. Si prova da Node con mobile/tests/midicut.test.cjs.
"use strict";

const MidiCut = (() => {
  function readVar(b, at) {
    let v = 0, n = 0, c;
    do { c = b[at.i++]; v = v * 128 + (c & 127); n++; } while ((c & 128) && n < 4);
    return v;
  }

  function writeVar(out, v) {
    const bytes = [v & 127];
    while ((v = Math.floor(v / 128))) bytes.unshift((v & 127) | 128);
    for (const x of bytes) out.push(x);
  }

  const u32 = (b, i) => ((b[i] << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3]) >>> 0;
  const u16 = (b, i) => (b[i] << 8) | b[i + 1];

  // Gli eventi di una traccia: {t (assoluto), data: byte dell'evento, kind: "note" | "off" | "meta" | "other", key}
  function parseTrack(b, start, end) {
    const events = [];
    const at = { i: start };
    let t = 0, running = 0;
    while (at.i < end) {
      t += readVar(b, at);
      let status = b[at.i];
      if (status < 128) status = running; else at.i++;
      if (status === 0xff) {
        const type = b[at.i++];
        const len = readVar(b, at);
        events.push({ t, kind: "meta", type, data: [0xff, type, ...varBytes(len), ...b.subarray(at.i, at.i + len)] });
        at.i += len;
      } else if (status === 0xf0 || status === 0xf7) {
        const len = readVar(b, at);
        events.push({ t, kind: "sysex", data: [status, ...varBytes(len), ...b.subarray(at.i, at.i + len)] });
        at.i += len;
      } else {
        running = status;
        const type = status & 0xf0, size = (type === 0xc0 || type === 0xd0) ? 1 : 2;
        const d = [status, ...b.subarray(at.i, at.i + size)];
        at.i += size;
        const key = (status & 15) * 128 + d[1];
        if (type === 0x90 && d[2] > 0) events.push({ t, kind: "on", key, data: d });
        else if (type === 0x80 || type === 0x90) events.push({ t, kind: "off", key, data: d });
        else if (type === 0xa0) events.push({ t, kind: "poly", data: d });
        else events.push({ t, kind: "control", data: d });
      }
    }
    return events;
  }

  function varBytes(v) {
    const out = [];
    writeVar(out, v);
    return out;
  }

  // 'bytes' (Uint8Array) senza le note prima di 'tick' e con il resto spostato indietro di 'tick'
  function from(bytes, tick) {
    if (!(tick > 0)) return bytes;
    const header = bytes.subarray(0, 14);
    const count = u16(bytes, 10);
    const out = Array.from(header);
    let at = 14;
    for (let k = 0; k < count; k++) {
      const len = u32(bytes, at + 4);
      const events = parseTrack(bytes, at + 8, at + 8 + len);
      at += 8 + len;
      const head = [], tail = [];
      const dropped = new Set();                       // le note cominciate prima e ancora accese: anche il loro «off» sparisce
      let end = 0;
      for (const ev of events) {
        if (ev.kind === "meta" && ev.type === 0x2f) { end = ev.t; continue; }
        if (ev.t < tick) {
          if (ev.kind === "on") dropped.add(ev.key);
          else if (ev.kind === "off") dropped.delete(ev.key);
          else if (ev.kind !== "poly") head.push(ev);
        } else if (ev.kind === "off" && dropped.has(ev.key)) {
          dropped.delete(ev.key);
        } else {
          tail.push({ ...ev, t: ev.t - tick });
        }
      }
      const body = [];
      let last = 0;
      for (const ev of head.map((e) => ({ ...e, t: 0 })).concat(tail)) {
        writeVar(body, ev.t - last);
        last = ev.t;
        for (const x of ev.data) body.push(x);
      }
      writeVar(body, Math.max(0, end - tick - last));
      body.push(0xff, 0x2f, 0);
      out.push(0x4d, 0x54, 0x72, 0x6b, (body.length >>> 24) & 255, (body.length >>> 16) & 255, (body.length >>> 8) & 255, body.length & 255);
      for (const x of body) out.push(x);
    }
    return Uint8Array.from(out);
  }

  return { from, parseTrack, u16, u32 };
})();

if (typeof module !== "undefined") module.exports = { MidiCut };
