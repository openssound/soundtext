// Link e QR code di SoundText Mobile (mobile/share.js). Si lancia con:
// node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const { Duplex } = require("node:stream");

// Node 18 non conosce "deflate-raw" (c'e' dalla 20.12): lo stesso flusso con zlib, solo per queste prove.
// I browser dei telefoni lo hanno (Chrome 103, Safari 16.4, Firefox 113).
for (const [name, make] of [["CompressionStream", zlib.createDeflateRaw], ["DecompressionStream", zlib.createInflateRaw]]) {
  let native = true;
  try { new globalThis[name]("deflate-raw"); } catch (e) { native = false; }
  if (!native) {
    globalThis[name] = class {
      constructor(format) {
        assert.strictEqual(format, "deflate-raw");
        const { readable, writable } = Duplex.toWeb(make());
        Object.assign(this, { readable, writable });
      }
    };
  }
}

const { StFormat } = require("../songs.js");
const { ShareLink, Qr } = require("../share.js");

const ROOT = path.join(__dirname, "..", "..");

function examples() {
  const dirs = [path.join(ROOT, "examples"), path.join(ROOT, "examples", "didattici")];
  return dirs.flatMap((d) => fs.readdirSync(d).filter((f) => f.endsWith(".st")).map((f) => path.join(d, f)));
}

// ------------------------------------------------------------ link

test("ogni esempio si condivide come link e si riapre identico byte per byte", async () => {
  for (const file of examples()) {
    const bytes = fs.readFileSync(file);
    const name = path.basename(file, ".st");
    const fragment = await ShareLink.makeFragment(name, new Uint8Array(bytes));
    assert.match(fragment, /^v=1&b=[A-Za-z0-9_-]+&n=/);
    const url = ShareLink.makeUrl("https://esempio.test/app/?x=1#vecchio", fragment);
    assert.ok(url.startsWith("https://esempio.test/app/?x=1#v=1&b="));
    const back = await ShareLink.readFragment(url.slice(url.indexOf("#")));
    assert.strictEqual(back.name, name, file);
    assert.deepStrictEqual(Buffer.from(back.bytes), bytes, file);
    // e dopo il passaggio dal formato dell'app, BOM e a capo restano
    assert.deepStrictEqual(Buffer.from(StFormat.toBytes(StFormat.fromBytes(back.bytes))), bytes, file);
  }
});

test("il nome con caratteri speciali e accenti arriva intatto", async () => {
  const name = "Città & «blues» 100%";
  const fragment = await ShareLink.makeFragment(name, new TextEncoder().encode("Piano:\n  1: C |\n"));
  assert.ok(!/[ &]n=.*[ «]/.test(fragment));
  assert.strictEqual((await ShareLink.readFragment(fragment)).name, name);
});

test("un link senza brano non e' un errore, uno rotto si segnala", async () => {
  assert.strictEqual(await ShareLink.readFragment(""), null);
  assert.strictEqual(await ShareLink.readFragment("#altra-cosa"), null);
  const reject = (fragment, code) => assert.rejects(ShareLink.readFragment(fragment), (e) => e instanceof ShareLink.ShareError && e.code === code);
  await reject("#v=2&b=AAAA", "formato");                       // versione che non conosciamo
  await reject("#b=AAAA", "formato");                           // senza versione
  await reject("#v=1&b=***", "dati");                           // non e' base64
  await reject("#v=1&b=A", "dati");                             // lunghezza impossibile
  await reject("#v=1&b=AAAAAAAA", "dati");                      // non e' un flusso deflate
  await reject("#v=1&b=" + "A".repeat(700000), "grande");       // frammento troppo lungo
});

test("un link che si espande a dismisura si ferma, senza leggere tutto", async () => {
  const bomb = new Uint8Array(20 * 1024 * 1024);                // 20 MB di zeri: compressi sono pochi kB
  const fragment = await ShareLink.makeFragment.call(null, "x", new Uint8Array(10)).then(() => null);
  assert.strictEqual(fragment, null);
  const packed = new Uint8Array(await new Response(new Blob([bomb]).stream().pipeThrough(new CompressionStream("deflate-raw"))).arrayBuffer());
  assert.ok(packed.length < 40000);
  let binary = "";
  for (let i = 0; i < packed.length; i += 0x8000) binary += String.fromCharCode(...packed.subarray(i, i + 0x8000));
  const b = Buffer.from(binary, "binary").toString("base64url");
  await assert.rejects(ShareLink.readFragment("#v=1&b=" + b), (e) => e.code === "grande");
  await assert.rejects(ShareLink.makeFragment("x", bomb), (e) => e.code === "grande");
});

// ------------------------------------------------------------ QR code

// capacita in byte, livello L, delle 40 versioni (tabella della norma)
const CAPACITY_L = [17, 32, 53, 78, 106, 134, 154, 192, 230, 271, 321, 367, 425, 458, 520, 586, 644, 718, 792, 858, 929, 1003, 1091, 1171,
                    1273, 1367, 1465, 1528, 1628, 1732, 1840, 1952, 2068, 2188, 2303, 2431, 2563, 2699, 2809, 2953];

test("le capacita delle 40 versioni sono quelle della norma", () => {
  CAPACITY_L.forEach((capacity, i) => {
    const ver = i + 1;
    const fits = (n) => Qr.encode(new Uint8Array(n)).size === ver * 4 + 17;
    assert.ok(fits(capacity), `versione ${ver}: ${capacity} byte ci devono stare`);
    if (ver < 40) assert.ok(!fits(capacity + 1), `versione ${ver}: ${capacity + 1} byte vanno nella successiva`);
  });
  assert.strictEqual(Qr.MAX_BYTES, 2953);
  assert.strictEqual(Qr.encode(new Uint8Array(2954)), null);
});

// Un lettore scritto a parte (campi di Galois con logaritmi, non il metodo dell'encoder): legge i
// bit di formato, toglie la maschera, rimette in ordine i blocchi, controlla che ogni blocco sia
// una parola valida del codice (sindromi nulle) e ne estrae i byte.
function readQr(qr) {
  const { size, modules, fixed, ver } = qr;
  const exp = new Array(512), log = new Array(256);
  for (let i = 0, x = 1; i < 255; i++) { exp[i] = x; log[x] = i; x <<= 1; if (x & 0x100) x ^= 0x11D; }
  for (let i = 255; i < 512; i++) exp[i] = exp[i - 255];
  const mul = (a, b) => (a && b ? exp[log[a] + log[b]] : 0);

  // formato: le due copie devono essere uguali; si legge il livello (01 = L) e la maschera
  const bit = (x, y) => (modules[y][x] ? 1 : 0);
  let copy1 = 0, copy2 = 0;
  const first = [[8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8], [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8]];
  first.forEach(([x, y], i) => { copy1 |= bit(x, y) << i; });
  for (let i = 0; i < 8; i++) copy2 |= bit(size - 1 - i, 8) << i;
  for (let i = 8; i < 15; i++) copy2 |= bit(8, size - 15 + i) << i;
  assert.strictEqual(copy1, copy2, "le due copie del formato");
  const format = copy1 ^ 0x5412;
  assert.strictEqual(format >> 13, 1, "livello L");
  let rem = format >> 10;                                        // controllo BCH: il resto deve tornare
  const data5 = format >> 10;
  rem = data5;
  for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  assert.strictEqual(((data5 << 10) | rem), format, "BCH del formato");
  const mask = (format >> 10) & 7;
  assert.strictEqual(mask, qr.mask);

  const masks = [(x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x, y) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
                 (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => x * y % 2 + x * y % 3 === 0,
                 (x, y) => (x * y % 2 + x * y % 3) % 2 === 0, (x, y) => ((x + y) % 2 + x * y % 3) % 2 === 0];
  const bits = [];
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < size; vert++) {
      for (let j = 0; j < 2; j++) {
        const x = right - j;
        const y = ((right + 1) & 2) === 0 ? size - 1 - vert : vert;
        if (!fixed[y][x]) bits.push(bit(x, y) ^ (masks[mask](x, y) ? 1 : 0));
      }
    }
  }
  const { numBlocks, eccLen, raw } = Qr.params(ver);
  const words = [];
  for (let i = 0; i + 8 <= raw * 8; i += 8) words.push(parseInt(bits.slice(i, i + 8).join(""), 2));
  assert.strictEqual(words.length, raw);

  const shortBlocks = numBlocks - raw % numBlocks, shortLen = Math.floor(raw / numBlocks);
  const blocks = Array.from({ length: numBlocks }, (_, b) => []);
  let at = 0;
  for (let i = 0; i < shortLen + 1; i++) {
    for (let b = 0; b < numBlocks; b++) {
      if (i === shortLen - eccLen && b < shortBlocks) continue;      // i blocchi corti non hanno questo byte
      blocks[b].push(words[at++]);
    }
  }
  assert.strictEqual(at, raw);
  const dataBytes = [];
  blocks.forEach((block, b) => {
    for (let j = 0; j < eccLen; j++) {                           // sindromi: il blocco valutato in alfa^j
      let s = 0;
      for (const c of block) s = mul(s, exp[j]) ^ c;
      assert.strictEqual(s, 0, `versione ${ver}, blocco ${b}: sindrome ${j}`);
    }
    dataBytes.push(...block.slice(0, block.length - eccLen));
  });
  const stream = dataBytes.map((v) => v.toString(2).padStart(8, "0")).join("");
  assert.strictEqual(stream.slice(0, 4), "0100", "modo byte");
  const countBits = ver <= 9 ? 8 : 16;
  const count = parseInt(stream.slice(4, 4 + countBits), 2);
  const out = [];
  for (let i = 0; i < count; i++) out.push(parseInt(stream.substr(4 + countBits + i * 8, 8), 2));
  return Uint8Array.from(out);
}

test("il QR si legge: formato, blocchi di correzione e byte tornano per ogni versione e maschera", () => {
  for (let ver = 1; ver <= 40; ver++) {
    for (const length of new Set([CAPACITY_L[ver - 1], Math.max(1, CAPACITY_L[ver - 1] - 7)])) {
      const bytes = Uint8Array.from({ length }, (_, i) => (i * 131 + ver * 17) % 256);
      for (const mask of [undefined, ver % 8]) {
        const qr = Qr.encode(bytes, mask);
        assert.strictEqual(qr.ver, ver);
        assert.deepStrictEqual(readQr(qr), bytes, `versione ${ver}, ${length} byte, maschera ${mask}`);
      }
    }
  }
  for (let mask = 0; mask < 8; mask++) {
    const bytes = new TextEncoder().encode("https://openssound.github.io/soundtext/#v=1&b=AbCd");
    assert.deepStrictEqual(readQr(Qr.encode(bytes, mask)), bytes);
  }
});

test("i quadrati di posizione e le tacche sono al loro posto", () => {
  const qr = Qr.encode(new TextEncoder().encode("ciao"));
  assert.strictEqual(qr.size, 21);
  const row = (y, x0, n) => qr.modules[y].slice(x0, x0 + n).map((v) => (v ? 1 : 0)).join("");
  assert.strictEqual(row(0, 0, 7), "1111111");
  assert.strictEqual(row(1, 0, 7), "1000001");
  assert.strictEqual(row(3, 0, 7), "1011101");
  assert.strictEqual(row(0, 14, 7), "1111111");
  assert.strictEqual(row(14, 0, 7), "1111111");
  assert.strictEqual(row(6, 8, 5), "10101");                    // tacche di sincronia
  assert.ok(qr.modules[qr.size - 8][8]);                        // il modulo scuro fisso
});

test("quali esempi ci stanno in un QR, come link", async () => {
  const report = [];
  for (const file of examples()) {
    const text = fs.readFileSync(file, "utf8");
    const stripped = text.split("\n").map((l) => l.replace(/\s*\/\/.*$/, "")).filter((l, i, all) => l.trim() || (all[i - 1] || "").trim()).join("\n");
    const fragment = await ShareLink.makeFragment("x", new TextEncoder().encode(stripped));
    const url = ShareLink.makeUrl("https://openssound.github.io/soundtext/", fragment);
    report.push({ file: path.basename(file), qr: new TextEncoder().encode(url).length <= Qr.MAX_BYTES });
  }
  console.log("QR possibili:", report.filter((r) => r.qr).length, "su", report.length);
  assert.ok(report.some((r) => r.qr), "almeno un esempio ci sta");
  assert.ok(report.some((r) => !r.qr), "i piu' grandi no, e l'app lo dice");
});
