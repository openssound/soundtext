// L'intestazione dei SoundFont (mobile/soundfonts.js). Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { SoundFontInfo, SoundFontError } = require("../soundfonts.js");

// un'intestazione RIFF/sfbk minima: ifil, isng e INAM dentro LIST INFO
function header(major, minor, name = "Prova") {
  const le16 = (v) => [v & 255, v >> 8];
  const le32 = (v) => [v & 255, (v >> 8) & 255, (v >> 16) & 255, v >>> 24];
  const chunk = (id, body) => [...Buffer.from(id), ...le32(body.length), ...body, ...(body.length & 1 ? [0] : [])];
  const text = [...Buffer.from(name + "\0")];
  const info = [...Buffer.from("INFO"), ...chunk("ifil", [...le16(major), ...le16(minor)]), ...chunk("isng", [...Buffer.from("EMU8000\0")]),
                ...chunk("INAM", text)];
  const list = [...Buffer.from("LIST"), ...le32(info.length), ...info];
  return Uint8Array.from([...Buffer.from("RIFF"), ...le32(4 + list.length + 8), ...Buffer.from("sfbk"), ...list, ...Buffer.from("LIST"), 0, 0, 0, 0]);
}

test("un .sf2 si riconosce, con versione e nome", () => {
  assert.deepStrictEqual(SoundFontInfo.inspect(header(2, 1, "Il mio piano")), { version: [2, 1], name: "Il mio piano" });
  assert.deepStrictEqual(SoundFontInfo.inspect(header(2, 4, "Pari")).name, "Pari");       // nome di lunghezza pari: nessun riempimento
});

test("un .sf3 si rifiuta con un codice a parte, un file qualunque come formato sbagliato", () => {
  assert.throws(() => SoundFontInfo.inspect(header(3, 1)), (e) => e instanceof SoundFontError && e.code === "sf3");
  const bad = (bytes) => assert.throws(() => SoundFontInfo.inspect(bytes), (e) => e instanceof SoundFontError && e.code === "formato");
  bad(new Uint8Array(0));
  bad(Uint8Array.from([0x4d, 0x54, 0x68, 0x64, 0, 0, 0, 6, 0, 1, 0, 1, 1, 0xe0]));                        // un MIDI
  bad(Uint8Array.from([...Buffer.from("RIFF"), 0, 0, 0, 0, ...Buffer.from("WAVEfmt ")]));                              // un WAV
  bad(header(2, 1).subarray(0, 20));                                                        // troncato prima di ifil
});

test("i SoundFont veri del repository, se ci sono", () => {
  const dir = path.join(__dirname, "..", "..", "soundfonts");
  const read = (name) => {
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) return null;
    const fd = fs.openSync(file, "r");
    const buffer = Buffer.alloc(65536);
    const n = fs.readSync(fd, buffer, 0, 65536, 0);
    fs.closeSync(fd);
    return Uint8Array.from(buffer.subarray(0, n));
  };
  const tim = read("TimGM6mb.sf2"), muse = read("MuseScore_General.sf3");
  if (tim) assert.deepStrictEqual(SoundFontInfo.inspect(tim).version, [2, 1]);
  if (muse) assert.throws(() => SoundFontInfo.inspect(muse), (e) => e.code === "sf3");
});
