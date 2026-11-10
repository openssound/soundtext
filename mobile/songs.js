// Archivio dei brani di SoundText Mobile: i .st dell'utente in IndexedDB,
// salvati come testo del file (vedi PIANO_FASE1.md: l'app modifica il testo,
// non riscrive il brano), cosi' un .st aperto e salvato senza modifiche
// resta identico byte per byte.
"use strict";

const StFormat = (() => {
  // Da byte a testo modificabile: si tengono il BOM e il tipo di a capo,
  // per restituire gli stessi byte all'esportazione.
  function fromBytes(bytes) {
    const raw = new TextDecoder("utf-8", { ignoreBOM: true }).decode(bytes);
    const bom = raw.startsWith("﻿");
    const body = bom ? raw.slice(1) : raw;
    const crlf = body.includes("\r\n");
    return { text: crlf ? body.replace(/\r\n/g, "\n") : body, eol: crlf ? "\r\n" : "\n", bom };
  }

  function toBytes(song) {
    const body = song.eol === "\r\n" ? song.text.replace(/\n/g, "\r\n") : song.text;
    return new TextEncoder().encode((song.bom ? "﻿" : "") + body);
  }

  // "Brano.st" -> "Brano"; i caratteri vietati nei nomi di file diventano "-"
  function nameFromFile(fileName) {
    return fileName.replace(/\.st$/i, "").trim() || "Brano";
  }

  function fileName(name) {
    return (name.replace(/[\\/:*?"<>|]+/g, "-").trim() || "Brano") + ".st";
  }

  return { fromBytes, toBytes, nameFromFile, fileName };
})();

const Songs = (() => {
  const DB = "soundtext-mobile";
  const STORE = "songs";
  let dbPromise = null;

  function open() {
    if (!dbPromise) {
      dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(DB, 1);
        req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "id" });
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return dbPromise;
  }

  async function tx(mode, fn) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const t = db.transaction(STORE, mode);
      const result = fn(t.objectStore(STORE));
      t.oncomplete = () => resolve(result && "result" in result ? result.result : result);
      t.onerror = () => reject(t.error);
    });
  }

  function newId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  // Brani ordinati dal piu' recente
  async function list() {
    const all = await tx("readonly", (s) => s.getAll());
    return all.sort((a, b) => b.updated - a.updated);
  }

  const get = (id) => tx("readonly", (s) => s.get(id));
  const remove = (id) => tx("readwrite", (s) => s.delete(id));

  async function put(song) {
    song.updated = Date.now();
    await tx("readwrite", (s) => s.put(song));
    return song;
  }

  // Un brano nuovo: { name, text, eol, bom, source }
  async function create(fields) {
    const now = Date.now();
    return put({ id: newId(), created: now, eol: "\n", bom: false, ...fields });
  }

  // Un nome libero: "Nome", poi "Nome (2)", "Nome (3)"...
  async function freeName(name) {
    const used = new Set((await list()).map((s) => s.name));
    if (!used.has(name)) return name;
    for (let n = 2; ; n++) if (!used.has(`${name} (${n})`)) return `${name} (${n})`;
  }

  return { list, get, put, create, remove, freeName };
})();

if (typeof module !== "undefined") module.exports = { StFormat };
