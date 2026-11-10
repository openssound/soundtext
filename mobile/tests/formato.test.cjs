// Un .st aperto e salvato senza modifiche resta identico byte per byte
// (criterio della fase 1). Si lancia con: node --test mobile/tests/
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { StFormat } = require("../songs.js");

const ROOT = path.join(__dirname, "..", "..");

function examples() {
  const dirs = [path.join(ROOT, "examples"), path.join(ROOT, "examples", "didattici")];
  return dirs.flatMap((d) => fs.readdirSync(d).filter((f) => f.endsWith(".st")).map((f) => path.join(d, f)));
}

test("gli esempi tornano identici", () => {
  const files = examples();
  assert.ok(files.length >= 10);
  for (const file of files) {
    const bytes = fs.readFileSync(file);
    const song = StFormat.fromBytes(bytes);
    assert.ok(!song.text.includes("\r"), file);
    assert.deepStrictEqual(Buffer.from(StFormat.toBytes(song)), bytes, file);
  }
});

test("a capo di Windows e BOM restano com'erano", () => {
  const original = Buffer.from("﻿ST: 2.6\r\nTempo: 90 BPM\r\n\r\nPiano:\r\n  4: c d e f |\r\n", "utf8");
  const song = StFormat.fromBytes(original);
  assert.strictEqual(song.eol, "\r\n");
  assert.strictEqual(song.bom, true);
  assert.strictEqual(song.text.split("\n")[0], "ST: 2.6");
  assert.deepStrictEqual(Buffer.from(StFormat.toBytes(song)), original);
});

test("una modifica tocca solo la parte cambiata", () => {
  const original = Buffer.from("// commento\r\nPiano:\r\n  4: c d e f |\r\n", "utf8");
  const song = StFormat.fromBytes(original);
  song.text = song.text.replace("c d e f", "g a b c*5");
  assert.strictEqual(Buffer.from(StFormat.toBytes(song)).toString("utf8"),
                     "// commento\r\nPiano:\r\n  4: g a b c*5 |\r\n");
});

test("nomi di file", () => {
  assert.strictEqual(StFormat.nameFromFile("Il mio brano.st"), "Il mio brano");
  assert.strictEqual(StFormat.fileName("Blues: in A/B"), "Blues- in A-B.st");
});
