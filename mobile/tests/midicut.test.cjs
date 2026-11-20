// Un MIDI che comincia da un punto qualsiasi: tempo e strumenti restano, le note prima del punto spariscono.
// Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { MidiCut } = require("../midicut.js");

function varLen(v) { const o = [v & 127]; while ((v = Math.floor(v / 128))) o.unshift((v & 127) | 128); return o; }

// un MIDI di formato 1 a mano: tempo 500000 (120 BPM), una traccia con strumento e quattro note
function smf() {
  const t0 = [0, 0xff, 0x51, 3, 7, 0xa1, 0x20, 0, 0xff, 0x2f, 0];
  const notes = [];
  const ev = (delta, ...d) => notes.push(...varLen(delta), ...d);
  ev(0, 0xc0, 5);                  // strumento
  ev(0, 0x90, 60, 90);             // do da 0 a 480
  ev(480, 0x80, 60, 0);
  ev(0, 0x90, 62, 90);             // re da 480 a 1440 (attraversa il punto 960)
  ev(960, 0x80, 62, 0);
  ev(0, 0x90, 64, 90);             // mi da 1440 a 1920
  ev(480, 0x80, 64, 0);
  ev(0, 0xff, 0x2f, 0);
  const trk = (body) => [0x4d, 0x54, 0x72, 0x6b, 0, 0, 0, body.length, ...body];
  const header = [0x4d, 0x54, 0x68, 0x64, 0, 0, 0, 6, 0, 1, 0, 2, 1, 0xe0];
  const t1 = trk(notes);
  t1[4] = (notes.length >>> 24) & 255; t1[5] = (notes.length >>> 16) & 255; t1[6] = (notes.length >>> 8) & 255; t1[7] = notes.length & 255;
  return Uint8Array.from([...header, ...trk(t0), ...t1]);
}

function tracks(bytes) {
  const out = [];
  let at = 14;
  while (at < bytes.length) {
    const len = MidiCut.u32(bytes, at + 4);
    out.push(MidiCut.parseTrack(bytes, at + 8, at + 8 + len));
    at += 8 + len;
  }
  return out;
}

test("da zero il file e' lo stesso", () => {
  const b = smf();
  assert.strictEqual(MidiCut.from(b, 0), b);
});

test("le note prima del punto spariscono, il resto scorre indietro, strumento e tempo restano", () => {
  const cut = MidiCut.from(smf(), 960);
  const [conductor, music] = tracks(cut);
  assert.ok(conductor.some((e) => e.kind === "meta" && e.type === 0x51 && e.t === 0));
  assert.ok(music.some((e) => e.kind === "control" && e.data[0] === 0xc0 && e.t === 0), "lo strumento");
  const ons = music.filter((e) => e.kind === "on").map((e) => [e.data[1], e.t]);
  assert.deepStrictEqual(ons, [[64, 480]]);                     // il mi, 480 dopo il nuovo inizio
  const offs = music.filter((e) => e.kind === "off").map((e) => [e.data[1], e.t]);
  assert.deepStrictEqual(offs, [[64, 960]]);                    // niente «off» orfano del re
  assert.ok(music.every((e, i) => i === 0 || e.t >= music[i - 1].t));
  assert.strictEqual(music[music.length - 1].type, 0x2f);
});

test("le tracce restano due e il file e' valido", () => {
  const cut = MidiCut.from(smf(), 480);
  assert.strictEqual(MidiCut.u16(cut, 10), 2);
  assert.strictEqual(tracks(cut).length, 2);
  const [, music] = tracks(cut);
  assert.deepStrictEqual(music.filter((e) => e.kind === "on").map((e) => [e.data[1], e.t]), [[62, 0], [64, 960]]);
});

test("oltre la fine non resta nessuna nota", () => {
  const [, music] = tracks(MidiCut.from(smf(), 5000));
  assert.strictEqual(music.filter((e) => e.kind === "on").length, 0);
});
