// Condividere un brano senza server: il .st compresso sta nel frammento di un
// link (#v=1&b=...&n=...), che il browser non manda a nessuno, e, se e' abbastanza
// piccolo, in un QR code. Niente librerie: la compressione e' quella del
// browser (CompressionStream) e il QR si calcola qui (versioni 1-40, livello di
// correzione L, modo "byte"). Si prova da Node con mobile/tests/share.test.cjs.
"use strict";

const ShareLink = (() => {
  const VERSION = 1;
  const MAX_BYTES = 1 << 20;            // dopo la decompressione: un link costruito apposta non blocca il telefono
  const MAX_FRAGMENT = 600000;          // caratteri del frammento che si accettano di leggere
  const LONG_LINK = 8000;               // oltre, alcune app di messaggistica rischiano di tagliarlo

  class ShareError extends Error {
    constructor(code, message) {
      super(message);
      this.code = code;                  // "formato" | "dati" | "grande"
    }
  }

  async function readAll(stream, limit) {
    const reader = stream.getReader();
    const chunks = [];
    let total = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.length;
      if (limit && total > limit) {
        reader.cancel().catch(() => {});
        throw new ShareError("grande", "troppo grande");
      }
      chunks.push(value);
    }
    const out = new Uint8Array(total);
    let at = 0;
    for (const c of chunks) { out.set(c, at); at += c.length; }
    return out;
  }

  const deflate = (bytes) => readAll(new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate-raw")));
  const inflate = (bytes) => readAll(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw")), MAX_BYTES);

  function toBase64Url(bytes) {
    let binary = "";
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function fromBase64Url(text) {
    if (!/^[A-Za-z0-9_-]*$/.test(text) || text.length % 4 === 1) throw new ShareError("dati", "dati non validi");
    const binary = atob(text.replace(/-/g, "+").replace(/_/g, "/"));
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
    return out;
  }

  // Il frammento di un brano: i byte del file (BOM e a capo compresi, cosi'
  // si riapre identico) e il nome.
  async function makeFragment(name, bytes) {
    if (bytes.length > MAX_BYTES) throw new ShareError("grande", "troppo grande");
    const packed = await deflate(bytes);
    return `v=${VERSION}&b=${toBase64Url(packed)}&n=${encodeURIComponent(name)}`;
  }

  // Cio' che c'e' in un frammento (con o senza il "#"): { name, bytes }.
  // null se non e' un brano condiviso; ShareError se lo e' ma non si legge.
  async function readFragment(hash) {
    const fragment = String(hash || "").replace(/^#/, "");
    if (!/(^|&)b=/.test(fragment)) return null;
    if (fragment.length > MAX_FRAGMENT) throw new ShareError("grande", "troppo grande");
    const params = new URLSearchParams(fragment);
    if (params.get("v") !== String(VERSION)) throw new ShareError("formato", "versione del link non riconosciuta");
    let bytes;
    try {
      bytes = await inflate(fromBase64Url(params.get("b")));
    } catch (e) {
      if (e instanceof ShareError) throw e;
      throw new ShareError("dati", "dati non validi");
    }
    return { name: (params.get("n") || "").trim() || "Brano", bytes };
  }

  const makeUrl = (base, fragment) => `${base.split("#")[0]}#${fragment}`;

  return { makeFragment, readFragment, makeUrl, ShareError, LONG_LINK, MAX_BYTES };
})();

// ------------------------------------------------------------ QR code
//
// Il QR di un testo (byte, correzione L, la versione piu' piccola che basta):
// il metodo del libro di Nayuki, scritto da capo qui. Restituisce
// { size, modules: [[bool]] } o null se non ci sta (al massimo 2953 byte).

const Qr = (() => {
  // codici di correzione per blocco e numero di blocchi, per versione 1-40, livello L
  const ECC_PER_BLOCK = [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30,
                         30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30];
  const BLOCKS = [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21,
                  22, 24, 25];

  const rawModules = (ver) => {
    let result = (16 * ver + 128) * ver + 64;
    if (ver >= 2) {
      const align = Math.floor(ver / 7) + 2;
      result -= (25 * align - 10) * align - 55;
      if (ver >= 7) result -= 36;
    }
    return result;
  };
  const dataCodewords = (ver) => Math.floor(rawModules(ver) / 8) - ECC_PER_BLOCK[ver] * BLOCKS[ver];

  // Reed-Solomon in GF(2^8), polinomio 0x11D
  function gfMultiply(x, y) {
    let z = 0;
    for (let i = 7; i >= 0; i--) {
      z = (z << 1) ^ ((z >>> 7) * 0x11D);
      z ^= ((y >>> i) & 1) * x;
    }
    return z;
  }

  function rsDivisor(degree) {
    const result = new Array(degree).fill(0);
    result[degree - 1] = 1;
    let root = 1;
    for (let i = 0; i < degree; i++) {
      for (let j = 0; j < result.length; j++) {
        result[j] = gfMultiply(result[j], root);
        if (j + 1 < result.length) result[j] ^= result[j + 1];
      }
      root = gfMultiply(root, 0x02);
    }
    return result;
  }

  function rsRemainder(data, divisor) {
    const result = divisor.map(() => 0);
    for (const b of data) {
      const factor = b ^ result.shift();
      result.push(0);
      divisor.forEach((coef, i) => { result[i] ^= gfMultiply(coef, factor); });
    }
    return result;
  }

  function dataBits(bytes, ver) {
    const bits = [];
    const push = (value, length) => { for (let i = length - 1; i >= 0; i--) bits.push((value >>> i) & 1); };
    push(0x4, 4);                                  // modo byte
    push(bytes.length, ver <= 9 ? 8 : 16);
    for (const b of bytes) push(b, 8);
    return { bits, push };
  }

  function codewordsFor(bytes) {
    for (let ver = 1; ver <= 40; ver++) {
      const capacity = dataCodewords(ver) * 8;
      const countBits = ver <= 9 ? 8 : 16;
      if (bytes.length >= 1 << countBits) continue;
      if (4 + countBits + bytes.length * 8 > capacity) continue;
      const { bits, push } = dataBits(bytes, ver);
      push(0, Math.min(4, capacity - bits.length));
      push(0, (8 - bits.length % 8) % 8);
      for (let pad = 0xEC; bits.length < capacity; pad ^= 0xEC ^ 0x11) push(pad, 8);
      const data = [];
      for (let i = 0; i < bits.length; i += 8) data.push(parseInt(bits.slice(i, i + 8).join(""), 2));
      return { ver, data };
    }
    return null;
  }

  function interleave(data, ver) {
    const numBlocks = BLOCKS[ver], eccLen = ECC_PER_BLOCK[ver];
    const raw = Math.floor(rawModules(ver) / 8);
    const shortBlocks = numBlocks - raw % numBlocks;
    const shortLen = Math.floor(raw / numBlocks);
    const divisor = rsDivisor(eccLen);
    const blocks = [];
    for (let i = 0, k = 0; i < numBlocks; i++) {
      const dat = data.slice(k, k + shortLen - eccLen + (i < shortBlocks ? 0 : 1));
      k += dat.length;
      const ecc = rsRemainder(dat, divisor);
      if (i < shortBlocks) dat.push(0);
      blocks.push(dat.concat(ecc));
    }
    const result = [];
    for (let i = 0; i < blocks[0].length; i++) {
      blocks.forEach((block, j) => {
        if (i !== shortLen - eccLen || j >= shortBlocks) result.push(block[i]);
      });
    }
    return result;
  }

  function alignPositions(ver) {
    if (ver === 1) return [];
    const count = Math.floor(ver / 7) + 2;
    const step = ver === 32 ? 26 : Math.ceil((ver * 4 + 4) / (count * 2 - 2)) * 2;
    const out = [6];
    for (let pos = ver * 4 + 17 - 7; out.length < count; pos -= step) out.splice(1, 0, pos);
    return out;
  }

  const MASKS = [
    (x, y) => (x + y) % 2 === 0,
    (x, y) => y % 2 === 0,
    (x, y) => x % 3 === 0,
    (x, y) => (x + y) % 3 === 0,
    (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0,
    (x, y) => x * y % 2 + x * y % 3 === 0,
    (x, y) => (x * y % 2 + x * y % 3) % 2 === 0,
    (x, y) => ((x + y) % 2 + x * y % 3) % 2 === 0,
  ];

  function build(ver, codewords, mask) {
    const size = ver * 4 + 17;
    const modules = Array.from({ length: size }, () => new Array(size).fill(false));
    const fixed = Array.from({ length: size }, () => new Array(size).fill(false));
    const set = (x, y, dark) => { modules[y][x] = dark; fixed[y][x] = true; };

    for (let i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
    const finder = (cx, cy) => {
      for (let dy = -4; dy <= 4; dy++) {
        for (let dx = -4; dx <= 4; dx++) {
          const x = cx + dx, y = cy + dy;
          if (x >= 0 && x < size && y >= 0 && y < size) {
            const dist = Math.max(Math.abs(dx), Math.abs(dy));
            set(x, y, dist !== 2 && dist !== 4);
          }
        }
      }
    };
    finder(3, 3); finder(size - 4, 3); finder(3, size - 4);
    const pos = alignPositions(ver);
    pos.forEach((px, i) => pos.forEach((py, j) => {
      if ((i === 0 && j === 0) || (i === 0 && j === pos.length - 1) || (i === pos.length - 1 && j === 0)) return;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(px + dx, py + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }));

    // i bit di formato (livello L = 01) e, da versione 7, quelli della versione
    const formatBits = (m) => {
      const data = (1 << 3) | m;
      let rem = data;
      for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
      return ((data << 10) | rem) ^ 0x5412;
    };
    const drawFormat = (m) => {
      const bits = formatBits(m);
      const bit = (i) => ((bits >>> i) & 1) !== 0;
      for (let i = 0; i <= 5; i++) set(8, i, bit(i));
      set(8, 7, bit(6)); set(8, 8, bit(7)); set(7, 8, bit(8));
      for (let i = 9; i < 15; i++) set(14 - i, 8, bit(i));
      for (let i = 0; i < 8; i++) set(size - 1 - i, 8, bit(i));
      for (let i = 8; i < 15; i++) set(8, size - 15 + i, bit(i));
      set(8, size - 8, true);
    };
    drawFormat(0);
    if (ver >= 7) {
      let rem = ver;
      for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1F25);
      const bits = (ver << 12) | rem;
      for (let i = 0; i < 18; i++) {
        const dark = ((bits >>> i) & 1) !== 0;
        const a = size - 11 + i % 3, b = Math.floor(i / 3);
        set(a, b, dark); set(b, a, dark);
      }
    }

    // i dati, a zig-zag da destra in basso
    let i = 0;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vert = 0; vert < size; vert++) {
        for (let j = 0; j < 2; j++) {
          const x = right - j;
          const upward = ((right + 1) & 2) === 0;
          const y = upward ? size - 1 - vert : vert;
          if (!fixed[y][x] && i < codewords.length * 8) {
            modules[y][x] = ((codewords[i >>> 3] >>> (7 - (i & 7))) & 1) !== 0;
            i++;
          }
        }
      }
    }

    const applyMask = (m) => {
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!fixed[y][x] && MASKS[m](x, y)) modules[y][x] = !modules[y][x];
    };

    if (mask === undefined) {
      let best = 0, bestScore = Infinity;
      for (let m = 0; m < 8; m++) {
        applyMask(m);
        drawFormat(m);
        const score = penalty(modules, size);
        if (score < bestScore) { best = m; bestScore = score; }
        applyMask(m);                              // la stessa maschera due volte la toglie
      }
      mask = best;
    }
    applyMask(mask);
    drawFormat(mask);
    return { size, modules, mask, ver, fixed };
  }

  // le quattro regole di penalita' della norma: serie lunghe, blocchi 2x2,
  // somiglianza con i quadrati di posizione, equilibrio fra chiari e scuri
  function penalty(m, size) {
    let total = 0;
    const lines = [];
    for (let a = 0; a < size; a++) {
      lines.push(m[a]);
      lines.push(m.map((row) => row[a]));
    }
    for (const line of lines) {
      let run = 1;
      for (let i = 1; i <= size; i++) {
        if (i < size && line[i] === line[i - 1]) run++;
        else { if (run >= 5) total += 3 + run - 5; run = 1; }
      }
      const text = line.map((v) => (v ? "1" : "0")).join("");
      for (const pattern of ["10111010000", "00001011101"]) {
        for (let at = text.indexOf(pattern); at !== -1; at = text.indexOf(pattern, at + 1)) total += 40;
      }
    }
    let dark = 0;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (m[y][x]) dark++;
        if (x < size - 1 && y < size - 1 && m[y][x] === m[y][x + 1] && m[y][x] === m[y + 1][x] && m[y][x] === m[y + 1][x + 1]) total += 3;
      }
    }
    total += (Math.ceil(Math.abs(dark * 20 - size * size * 10) / (size * size)) - 1) * 10;
    return total;
  }

  const MAX_BYTES = dataCodewords(40) - 3;        // 2953: meno modo e lunghezza

  // 'mask' (0-7) solo per le prove: di norma si sceglie la migliore
  function encode(bytes, mask) {
    const found = codewordsFor(bytes);
    if (!found) return null;
    return build(found.ver, interleave(found.data, found.ver), mask);
  }

  // Disegna il QR in un canvas, in nero su bianco (con i 4 moduli di margine che chiede la norma)
  function draw(canvas, qr, pixels) {
    const quiet = 4;
    const scale = Math.max(1, Math.floor(pixels / (qr.size + quiet * 2)));
    const side = (qr.size + quiet * 2) * scale;
    canvas.width = canvas.height = side;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, side, side);
    ctx.fillStyle = "#000";
    for (let y = 0; y < qr.size; y++) {
      for (let x = 0; x < qr.size; x++) if (qr.modules[y][x]) ctx.fillRect((x + quiet) * scale, (y + quiet) * scale, scale, scale);
    }
  }

  // per le prove: come sono fatti i blocchi di una versione
  const params = (ver) => ({ numBlocks: BLOCKS[ver], eccLen: ECC_PER_BLOCK[ver], raw: Math.floor(rawModules(ver) / 8),
                             dataCodewords: dataCodewords(ver) });

  return { encode, draw, params, MAX_BYTES };
})();

if (typeof module !== "undefined") module.exports = { ShareLink, Qr };
