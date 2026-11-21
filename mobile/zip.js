// SoundText Mobile: un archivio .zip scritto e letto qui, senza librerie. Serve per la copia di sicurezza dei brani:
// ogni brano e' un .st, conservato com'e' (metodo «store», niente compressione: i .st sono piccoli e restano
// identici byte per byte). In lettura si accettano anche gli archivi compressi (deflate) fatti da altri
// programmi, con DecompressionStream. Si prova da Node con mobile/tests/zip.test.cjs, che fa leggere il risultato
// a `unzip` e a Python.
"use strict";

const Zip = (() => {
  const enc = new TextEncoder(), dec = new TextDecoder("utf-8");
  const TABLE = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();

  function crc32(bytes) {
    let c = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) c = TABLE[(c ^ bytes[i]) & 255] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }

  // data e ora DOS (1980-01-01 se non si dice)
  function dosTime(date) {
    if (!date) return { time: 0, day: (1 << 5) | 1 };
    const d = new Date(date);
    return { time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
             day: (Math.max(0, d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate() };
  }

  // files: [{ name, data: Uint8Array, date? }] -> Uint8Array
  function write(files) {
    const parts = [], central = [];
    let offset = 0;
    const push = (u8) => { parts.push(u8); offset += u8.length; };
    for (const f of files) {
      const name = enc.encode(f.name), crc = crc32(f.data), { time, day } = dosTime(f.date);
      const local = new DataView(new ArrayBuffer(30));
      local.setUint32(0, 0x04034b50, true); local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true);   // 0x0800: nomi in UTF-8
      local.setUint16(8, 0, true); local.setUint16(10, time, true); local.setUint16(12, day, true);
      local.setUint32(14, crc, true); local.setUint32(18, f.data.length, true); local.setUint32(22, f.data.length, true);
      local.setUint16(26, name.length, true); local.setUint16(28, 0, true);
      const start = offset;
      push(new Uint8Array(local.buffer)); push(name); push(f.data);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
      c.setUint16(10, 0, true); c.setUint16(12, time, true); c.setUint16(14, day, true);
      c.setUint32(16, crc, true); c.setUint32(20, f.data.length, true); c.setUint32(24, f.data.length, true);
      c.setUint16(28, name.length, true); c.setUint32(42, start, true);
      central.push(new Uint8Array(c.buffer), name);
    }
    const centralStart = offset;
    for (const u8 of central) push(u8);
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, offset - centralStart, true); end.setUint32(16, centralStart, true);
    push(new Uint8Array(end.buffer));
    const out = new Uint8Array(offset);
    let at = 0;
    for (const p of parts) { out.set(p, at); at += p.length; }
    return out;
  }

  async function inflate(data) {
    if (typeof DecompressionStream === "undefined" || typeof require !== "undefined") {
      try { return new Uint8Array(require("node:zlib").inflateRawSync(data)); } catch (e) { /* in un browser: DecompressionStream */ }
    }
    const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  // Uint8Array -> [{ name, data }] (le cartelle si saltano). Error se non e' uno zip o e' cifrato.
  async function read(bytes) {
    const v = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let end = -1;
    for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 22 - 65535); i--) if (v.getUint32(i, true) === 0x06054b50) { end = i; break; }
    if (end < 0) throw new Error("zip");
    const count = v.getUint16(end + 10, true);
    let at = v.getUint32(end + 16, true);
    const out = [];
    for (let n = 0; n < count; n++) {
      if (v.getUint32(at, true) !== 0x02014b50) throw new Error("zip");
      const flags = v.getUint16(at + 8, true), method = v.getUint16(at + 10, true);
      const csize = v.getUint32(at + 20, true), nameLen = v.getUint16(at + 28, true);
      const extraLen = v.getUint16(at + 30, true), commentLen = v.getUint16(at + 32, true), local = v.getUint32(at + 42, true);
      const name = dec.decode(bytes.subarray(at + 46, at + 46 + nameLen));
      at += 46 + nameLen + extraLen + commentLen;
      if (name.endsWith("/")) continue;
      if (flags & 1) throw new Error("cifrato");
      const dataAt = local + 30 + v.getUint16(local + 26, true) + v.getUint16(local + 28, true);
      const raw = bytes.subarray(dataAt, dataAt + csize);
      out.push({ name, data: method === 0 ? raw.slice() : method === 8 ? await inflate(raw) : (() => { throw new Error("metodo"); })() });
    }
    return out;
  }

  return { write, read, crc32 };
})();

if (typeof module !== "undefined") module.exports = { Zip };
