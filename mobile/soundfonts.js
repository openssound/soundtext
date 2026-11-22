// I SoundFont dell'utente: riconoscere un file .sf2 o .sf3 (campioni compressi, che questo motore legge)
// e tenerli sul telefono, in IndexedDB, senza mandarli da nessuna parte. Si prova da Node con
// mobile/tests/soundfonts.test.cjs (la parte che legge l'intestazione).
"use strict";

class SoundFontError extends Error {
  constructor(code, message) {
    super(message || code);
    this.code = code;                      // "formato"
  }
}

const SoundFontInfo = (() => {
  // Dall'inizio del file (bastano i primi KB): { version: [maggiore, minore], name }.
  function inspect(bytes) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const tag = (at) => (at + 4 <= bytes.length ? String.fromCharCode(bytes[at], bytes[at + 1], bytes[at + 2], bytes[at + 3]) : "");
    if (bytes.length < 12 || tag(0) !== "RIFF" || tag(8) !== "sfbk") throw new SoundFontError("formato");
    let at = 12, info = null;
    while (at + 12 <= bytes.length && !info) {
      const size = view.getUint32(at + 4, true);
      if (tag(at) === "LIST" && tag(at + 8) === "INFO") info = [at + 12, at + 8 + size];
      else at += 8 + size + (size & 1);
    }
    if (!info) throw new SoundFontError("formato");
    let version = null, name = "";
    for (let p = info[0]; p + 8 <= Math.min(info[1], bytes.length);) {
      const id = tag(p), size = view.getUint32(p + 4, true);
      if (id === "ifil" && p + 12 <= bytes.length) version = [view.getUint16(p + 8, true), view.getUint16(p + 10, true)];
      if (id === "INAM") name = new TextDecoder("latin1").decode(bytes.subarray(p + 8, Math.min(bytes.length, p + 8 + size))).split("\0")[0].trim();
      p += 8 + size + (size & 1);
    }
    if (!version) throw new SoundFontError("formato");
    // un SF3 (versione 3) ha i campioni compressi in Ogg Vorbis: la FluidSynth di questo motore e' compilata con
    // libsndfile e li legge; una versione che non e' la 2 ne' la 3 non si conosce
    if (version[0] < 2 || version[0] > 3) throw new SoundFontError("formato");
    return { version, name };
  }
  return { inspect };
})();

// L'archivio: le informazioni e i dati stanno in due contenitori, cosi' l'elenco non legge decine di MB; i dati
// si salvano a pezzi di 32 MB, perche' Chromium non accetta un valore di IndexedDB sopra i 128 MB e un SoundFont
// come FluidR3 ne pesa 141.
const SoundFonts = (() => {
  const DB = "soundtext-mobile-sf";
  const CHUNK = 32 * 1048576;
  let dbPromise = null;

  function open() {
    if (!dbPromise) {
      dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(DB, 1);
        req.onupgradeneeded = () => {
          req.result.createObjectStore("meta", { keyPath: "id" });
          req.result.createObjectStore("data");                 // chiavi "id/numero del pezzo"
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return dbPromise;
  }

  async function run(stores, mode, fn) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(stores, mode);
      const result = fn(...stores.map((s) => tx.objectStore(s)));
      tx.oncomplete = () => resolve(result && "result" in result ? result.result : result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  }

  // Le informazioni di tutti, nell'ordine in cui sono stati aggiunti
  async function list() {
    const all = await run(["meta"], "readonly", (meta) => meta.getAll());
    return all.sort((a, b) => a.added - b.added);
  }

  async function get(id) {
    const meta = await run(["meta"], "readonly", (m) => m.get(id));
    if (!meta) return null;
    const out = new Uint8Array(meta.size);
    for (let n = 0; n < meta.chunks; n++) {
      const piece = await run(["data"], "readonly", (d) => d.get(`${id}/${n}`));
      if (!piece) return null;
      out.set(new Uint8Array(piece), n * CHUNK);
    }
    return out.buffer;
  }

  async function removeData(id, chunks) {
    await run(["data"], "readwrite", (d) => { for (let n = 0; n < chunks; n++) d.delete(`${id}/${n}`); });
  }

  // Aggiunge un file: stesso nome, stesso SoundFont (si sostituisce). SoundFontError se non e' un .sf2.
  async function add(file) {
    const head = new Uint8Array(await file.slice(0, 65536).arrayBuffer());
    const info = SoundFontInfo.inspect(head);
    const existing = (await list()).find((f) => f.name === file.name);
    const id = existing ? existing.id : Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const chunks = Math.max(1, Math.ceil(file.size / CHUNK));
    if (existing) await removeData(id, existing.chunks || 1);
    try {
      for (let n = 0; n < chunks; n++) {
        const piece = await file.slice(n * CHUNK, (n + 1) * CHUNK).arrayBuffer();
        await run(["data"], "readwrite", (d) => d.put(piece, `${id}/${n}`));
      }
    } catch (e) {
      await removeData(id, chunks).catch(() => {});             // niente pezzi orfani se lo spazio finisce
      throw e;
    }
    const meta = { id, name: file.name, title: info.name, size: file.size, chunks, added: existing ? existing.added : Date.now() };
    await run(["meta"], "readwrite", (m) => m.put(meta));       // il SoundFont esiste solo quando ci sono tutti i pezzi
    return meta;
  }

  async function remove(id) {
    const meta = await run(["meta"], "readonly", (m) => m.get(id));
    await run(["meta"], "readwrite", (m) => m.delete(id));
    if (meta) await removeData(id, meta.chunks || 1);
  }

  return { list, get, add, remove };
})();

if (typeof module !== "undefined") module.exports = { SoundFontInfo, SoundFontError };
