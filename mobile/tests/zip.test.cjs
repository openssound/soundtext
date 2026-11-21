// Lo zip della copia di sicurezza: scritto qui e letto da unzip e da Python, e il contrario. Si lancia con:
// node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { Zip } = require("../zip.js");

const enc = new TextEncoder();
const FILES = [
  { name: "Brano uno.st", data: enc.encode("ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  4: c d e f |\n") },
  { name: "Città – è così.st", data: enc.encode("\uFEFFST: 2.6\r\nTempo: 90 BPM\r\n") },
  { name: "vuoto.st", data: new Uint8Array(0) },
];

function python(code, ...args) {
  return spawnSync("python3", ["-I", "-c", code, ...args], { encoding: "utf8" });
}

test("lo zip scritto qui si legge qui, byte per byte", async () => {
  const back = await Zip.read(Zip.write(FILES));
  assert.deepStrictEqual(back.map((f) => f.name), FILES.map((f) => f.name));
  back.forEach((f, i) => assert.deepStrictEqual(Buffer.from(f.data), Buffer.from(FILES[i].data)));
});

test("Python lo apre, controlla i CRC e vede gli stessi nomi e contenuti", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "zip-"));
  const file = path.join(dir, "copia.zip");
  fs.writeFileSync(file, Zip.write(FILES));
  const r = python("import sys, zipfile\nz = zipfile.ZipFile(sys.argv[1])\nassert z.testzip() is None\n" +
                   "print('|'.join(n + ':' + str(len(z.read(n))) for n in z.namelist()))", file);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.strictEqual(r.stdout.trim(), FILES.map((f) => f.name + ":" + f.data.length).join("|"));
  const un = spawnSync("unzip", ["-tq", file], { encoding: "utf8" });
  if (!un.error) assert.strictEqual(un.status, 0, un.stdout + un.stderr);
});

test("uno zip compresso fatto da Python (deflate) si legge", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "zip-"));
  const file = path.join(dir, "py.zip");
  const r = python("import sys, zipfile\nwith zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED) as z:\n" +
                   "    z.writestr('a.st', 'ST: 2.6\\n' * 200)\n    z.writestr('cartella/', '')\n    z.writestr('cartella/b.st', 'x')", file);
  assert.strictEqual(r.status, 0, r.stderr);
  const back = await Zip.read(new Uint8Array(fs.readFileSync(file)));
  assert.deepStrictEqual(back.map((f) => f.name), ["a.st", "cartella/b.st"]);
  assert.strictEqual(Buffer.from(back[0].data).toString(), "ST: 2.6\n".repeat(200));
});

test("un file che non e' uno zip dice di non esserlo", async () => {
  await assert.rejects(Zip.read(enc.encode("questo non e' uno zip")), /zip/);
});

test("lo stesso elenco da' lo stesso zip", () => {
  assert.deepStrictEqual(Buffer.from(Zip.write(FILES)), Buffer.from(Zip.write(FILES)));
});
