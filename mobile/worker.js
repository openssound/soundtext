// Web Worker del motore: Pyodide con st-language e i moduli di core/ senza
// Qt (mobile/bundle/engine.zip); numpy si carica dopo, in background.
// Riceve il testo di un brano e restituisce il MIDI, la mappa eventi ->
// token e i tempi misurati.
//
// Avvio con istantanea: il primo avvio fa partire Python, importa il motore
// e salva in Cache Storage un'istantanea della memoria di Pyodide
// (makeMemorySnapshot, opzione sperimentale _makeSnapshot); gli avvii
// seguenti ripartono da li' (_loadSnapshot) senza rifare l'avvio
// dell'interprete ne' gli import. I file (Emscripten MEMFS) non sono
// nell'istantanea: si rimettono ogni volta da engine.zip e dalle wheel.

import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";

const INDEX_URL = new URL("vendor/pyodide/", self.location).href;
const SNAPSHOT_CACHE = "stmobile-snapshot";
const SITE_PACKAGES = "/lib/python3.14/site-packages";
// packaging serve a mido; st-language e mido sono le stesse versioni di
// requirements.txt (wheel in vendor/wheels, da scarica_vendor.sh)
const EXTRA_WHEELS = ["vendor/pyodide/packaging-26.1-py3-none-any.whl"];

// numpy non si carica all'avvio: lo importa solo core/effects.py (gli effetti
// audio, che qui non servono) e l'analisi non lo usa mai
// (tests/test_mobile_engine.py). Al suo posto un modulo sostituto che importa
// quello vero al primo uso; il pacchetto arriva dopo, in background (loadNumpyLater).
const LAZY_NUMPY = `
import importlib, sys, types

class _LazyNumpy(types.ModuleType):
    """numpy finche' nessuno lo usa davvero: al primo attributo letto
    importa il numpy vero (che deve essere gia' caricato da loadPackage)."""
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if sys.modules.get("numpy") is self:
            del sys.modules["numpy"]
        try:
            real = importlib.import_module("numpy")
        except ImportError:
            sys.modules["numpy"] = self
            raise ImportError("numpy non e' ancora caricato nel motore di SoundText Mobile")
        return getattr(real, name)

sys.modules.setdefault("numpy", _LazyNumpy("numpy"))
`;

const SETUP = `
import os, sys
os.environ["SOUNDTEXT_CONFIG_DIR"] = "/home/pyodide/.soundtext"
if "/app" not in sys.path:
    sys.path.insert(0, "/app")
`;

const ms = (t0) => Math.round(performance.now() - t0);
let py = null;
let engine = null;       // Engine Python del brano aperto
let numpyStarted = false;

function post(msg, transfer) {
  self.postMessage(msg, transfer || []);
}

function loadedBytes() {
  // Peso delle risorse caricate dal worker (dalla rete o dalla cache).
  let decoded = 0;
  for (const e of performance.getEntriesByType("resource")) decoded += e.decodedBodySize || 0;
  return { decoded };
}

async function fetchBuffer(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`${url}: ${resp.status}`);
  return resp.arrayBuffer();
}

// I file del motore: engine.zip in /app, le wheel in site-packages.
async function fetchFiles() {
  const files = await (await fetch("bundle/files.json")).json();
  const wheelNames = await (await fetch("vendor/wheels/wheels.json")).json();
  const urls = [...wheelNames.map((w) => "vendor/wheels/" + w), ...EXTRA_WHEELS];
  const [zip, ...wheels] = await Promise.all([fetchBuffer("bundle/engine.zip"), ...urls.map(fetchBuffer)]);
  return { zip, wheels, urls, coreModules: files.core_modules };
}

function installFiles(pyodide, f) {
  pyodide.unpackArchive(f.zip, "zip", { extractDir: "/app" });
  for (const w of f.wheels) pyodide.unpackArchive(w, "zip", { extractDir: SITE_PACKAGES });
}

async function snapshotKey(f) {
  // cambia con engine.zip, le wheel, Pyodide e il browser (l'istantanea e'
  // la memoria del WebAssembly di questa versione)
  const parts = [new Uint8Array(f.zip), ...f.wheels.map((w) => new Uint8Array(w)),
                 new TextEncoder().encode(INDEX_URL + navigator.userAgent)];
  const all = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { all.set(p, at); at += p.length; }
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", all));
  const hex = [...hash.slice(0, 12)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return new URL("snapshot/" + hex + ".bin", self.location).href;
}

async function cachedSnapshot(key) {
  try {
    const hit = await (await caches.open(SNAPSHOT_CACHE)).match(key);
    return hit ? new Uint8Array(await hit.arrayBuffer()) : null;
  } catch (e) {
    return null;
  }
}

async function saveSnapshot(key, snap) {
  try {
    const cache = await caches.open(SNAPSHOT_CACHE);
    for (const k of await cache.keys()) await cache.delete(k);   // versioni vecchie
    await cache.put(key, new Response(snap, { headers: { "Content-Type": "application/octet-stream" } }));
    return true;
  } catch (e) {
    console.warn("istantanea non salvata", e);
    return false;
  }
}

async function bootFromSnapshot(f, snap) {
  const pyodide = await loadPyodide({ indexURL: INDEX_URL, _loadSnapshot: snap });
  installFiles(pyodide, f);
  pyodide.runPython(SETUP + "import engine");
  return pyodide;
}

async function bootFresh(f, makeSnapshot) {
  const pyodide = await loadPyodide({ indexURL: INDEX_URL, _makeSnapshot: makeSnapshot });
  installFiles(pyodide, f);
  // Tutti i moduli del bundle, anche quelli che core/ importa solo dentro le
  // funzioni (es. core.tempo_map): cosi' finiscono nell'istantanea.
  pyodide.runPython(LAZY_NUMPY + SETUP + `
import importlib, engine
for _name in ${JSON.stringify(f.coreModules)}:
    importlib.import_module(_name)
`);
  return pyodide;
}

async function boot(language) {
  const t = {};
  const t0 = performance.now();
  const f = await fetchFiles();
  t.files_ms = ms(t0);
  // In una pagina non sicura (http:// fuori da localhost) mancano
  // crypto.subtle e Cache Storage: niente istantanea, avvio normale.
  const canSnapshot = !!(self.isSecureContext && self.crypto && crypto.subtle && self.caches);
  const key = canSnapshot ? await snapshotKey(f) : null;
  const snap = key ? await cachedSnapshot(key) : null;
  let t1 = performance.now();
  t.snapshot = canSnapshot ? "creata" : "non disponibile (pagina non sicura)";
  if (snap) {
    try {
      py = await bootFromSnapshot(f, snap);
      t.snapshot = "caricata";
      t.snapshot_bytes = snap.byteLength;
    } catch (e) {
      console.warn("istantanea non utilizzabile, avvio normale", e);
      await caches.delete(SNAPSHOT_CACHE);
      py = null;
    }
  }
  if (!py) {
    py = await bootFresh(f, canSnapshot);
    t.python_ms = ms(t1);
    t1 = performance.now();
    if (canSnapshot) try {
      const made = py.makeMemorySnapshot();
      t.snapshot_bytes = made.byteLength;
      t.snapshot_make_ms = ms(t1);
      saveSnapshot(key, made);                 // senza aspettare
    } catch (e) {
      t.snapshot = "non disponibile: " + e.message;
    }
  } else {
    t.python_ms = ms(t1);
  }
  // La lingua dei messaggi del motore (avvisi, errori di notazione,
  // suggerimenti), dopo l'istantanea, che resta uguale per tutte le lingue.
  setLanguage(language);
  t.total_ms = ms(t0);
  t.versions = py.runPython(`
import sys
from importlib.metadata import version
"Python %s, st-language %s" % (sys.version.split()[0], version("st-language"))
`);
  t.network = loadedBytes();
  t.heap_bytes = wasmHeap();
  return t;
}

function setLanguage(language) {
  py.globals.set("_language", language || "it");
  py.runPython("from core import i18n as _i18n\n_i18n.set_language(_language)");
}

// numpy in background, dopo il primo brano aperto: prima occuperebbe il
// worker proprio mentre si apre il brano.
async function loadNumpyLater() {
  const t0 = performance.now();
  try {
    await py.loadPackage(["numpy"], { messageCallback: () => {} });
    post({ type: "numpy", ms: ms(t0) });
  } catch (e) {
    console.warn("numpy non caricato", e);
  }
}

function wasmHeap() {
  try {
    return py._module.HEAP8.buffer.byteLength;
  } catch (e) {
    return null;
  }
}

function toBytes(proxy) {
  const out = proxy.toJs();
  proxy.destroy();
  return out;
}

async function load(name, text) {
  const t0 = performance.now();
  if (engine) engine.destroy();
  engine = py.runPython("engine.Engine()");
  const info = engine.load(text, name).toJs({ dict_converter: Object.fromEntries });
  const midi = toBytes(engine.midi_bytes(0));
  const timeline = engine.timeline();
  info.timeline = timeline.toJs({ dict_converter: Object.fromEntries });
  timeline.destroy();
  const timings = engine.timings.toJs({ dict_converter: Object.fromEntries });
  timings.total_ms = ms(t0);
  return { info, midi, timings };
}

// La mappa per l'evidenziazione, chiesta dalla pagina dopo l'apertura:
// il brano si puo' gia' suonare mentre si calcola.
function spans() {
  const t0 = performance.now();
  const spansPy = py.runPython("lambda e: __import__('array').array('d', engine.flat_spans(e.highlight_spans())).tobytes()")(engine);
  const bytes = toBytes(spansPy);
  return { spans: new Float64Array(bytes.slice().buffer), ms: ms(t0) };
}

// comando -> funzione di engine.py (argomenti e risultato in JSON)
const CALLS = {
  complete: "complete", transforms: "transforms", bar: "bar_bounds",
  generate: "generate", generator_choices: "generator_choices", add_track: "add_track",
  structure: "structure", box_edit: "box_edit",
  transform_at: "transform_at", transform_preview: "transform_preview", transform_apply: "transform_apply",
  dictate: "dictate", dictation_words: "dictation_words", dictate_track: "dictate_track",
};

self.onmessage = async (ev) => {
  const msg = ev.data;
  try {
    if (msg.cmd === "boot") {
      post({ type: "booted", timings: await boot(msg.language) });
    } else if (msg.cmd === "load") {
      const r = await load(msg.name, msg.text);
      post({ type: "loaded", id: msg.id, ...r }, [r.midi.buffer]);
    } else if (msg.cmd === "spans") {
      const r = spans();
      post({ type: "spans", id: msg.id, ...r }, [r.spans.buffer]);
      if (!numpyStarted) { numpyStarted = true; loadNumpyLater(); }   // dopo il primo brano
    } else if (msg.cmd === "render") {
      // il MIDI che suona il lettore: trasposizione, tracce mute, metronomo
      const t0 = performance.now();
      const muted = py.toPy(msg.muted || []);
      const midi = toBytes(engine.midi_bytes(msg.semitones || 0, muted, !!msg.metronome));
      muted.destroy();
      post({ type: "midi", id: msg.id, midi, key: msg.key, ms: ms(t0) }, [midi.buffer]);
    } else if (msg.cmd === "preview") {
      // il MIDI di un altro testo (anteprima della schermata Crea), con un
      // motore a parte: quello del brano aperto resta com'e'
      const t0 = performance.now();
      const other = py.runPython("engine.Engine()");
      try {
        other.load(msg.text, "Anteprima").destroy();
        const midi = toBytes(other.midi_bytes(0));
        post({ type: "midi", id: msg.id, midi, ms: ms(t0) }, [midi.buffer]);
      } finally {
        other.destroy();
      }
    } else if (msg.cmd === "musicxml") {
      // la partitura delle tracce scelte (null: tutte), per verovio
      const t0 = performance.now();
      const names = msg.tracks ? py.toPy(msg.tracks) : null;
      const xml = names ? engine.musicxml(names) : engine.musicxml();   // null di JS non e' None
      if (names) names.destroy();
      post({ type: "musicxml", id: msg.id, xml, ms: ms(t0) });
    } else if (msg.cmd === "check") {
      // colori, avvisi e blocchi del testo dell'editor (engine.check_text)
      const t0 = performance.now();
      py.globals.set("_check_text", msg.text);
      const json = py.runPython(`
import json as _json
_r = engine.check_text(_check_text)
_r["categories"] = engine.syntax_categories()
_json.dumps(_r)
`);
      post({ type: "checked", id: msg.id, result: JSON.parse(json), ms: ms(t0) });
    } else if (CALLS[msg.cmd]) {
      // funzioni del motore con argomenti e risultato in JSON: barra musicale
      // (suggerimenti, funzioni sui pattern, battuta sotto il cursore) e
      // generatori (fase 2)
      const t0 = performance.now();
      py.globals.set("_args_json", JSON.stringify(msg.args || []));
      const json = py.runPython(`
import json as _json
_json.dumps(engine.${CALLS[msg.cmd]}(*_json.loads(_args_json)))
`);
      post({ type: msg.cmd, id: msg.id, result: JSON.parse(json), ms: ms(t0) });
    } else if (msg.cmd === "memory") {
      post({ type: "memory", id: msg.id, heap_bytes: wasmHeap() });
    }
  } catch (err) {
    post({ type: "error", id: msg.id, cmd: msg.cmd, message: String(err && err.message || err) });
  }
};
