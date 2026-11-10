// Web Worker del motore: Pyodide con numpy, st-language e i moduli di core/
// senza Qt (mobile/bundle/engine.zip). Riceve il testo di un brano e
// restituisce il MIDI, la mappa eventi -> token e i tempi misurati.


import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";

const ms = (t0) => Math.round(performance.now() - t0);
let py = null;
let engine = null;       // Engine Python del brano aperto

function post(msg, transfer) {
  self.postMessage(msg, transfer || []);
}

function networkBytes() {
  // Byte arrivati dalla rete per le risorse caricate dal worker: 0 quando
  // tutto viene dalla cache (del service worker o del browser).
  let transfer = 0, decoded = 0;
  for (const e of performance.getEntriesByType("resource")) {
    transfer += e.transferSize || 0;
    decoded += e.decodedBodySize || 0;
  }
  return { transfer, decoded };
}

async function boot() {
  const t = {};
  const t0 = performance.now();
  py = await loadPyodide({ indexURL: new URL("vendor/pyodide/", self.location).href });
  t.pyodide_ms = ms(t0);

  let t1 = performance.now();
  await py.loadPackage(["numpy", "packaging"], { messageCallback: () => {} });
  t.numpy_ms = ms(t1);

  t1 = performance.now();
  // st-language e mido: le stesse versioni di requirements.txt, dalle wheel
  // scaricate in vendor/wheels (scarica_vendor.sh), senza dipendenze.
  const wheels = await (await fetch("vendor/wheels/wheels.json")).json();
  await py.loadPackage(wheels.map((w) => new URL("vendor/wheels/" + w, self.location).href),
                       { messageCallback: () => {} });
  t.wheels_ms = ms(t1);

  t1 = performance.now();
  const zip = await (await fetch("bundle/engine.zip")).arrayBuffer();
  py.unpackArchive(zip, "zip", { extractDir: "/app" });
  await py.runPythonAsync(`
import os, sys
os.environ["SOUNDTEXT_CONFIG_DIR"] = "/home/pyodide/.soundtext"
sys.path.insert(0, "/app")
import engine
import importlib
for _name in engine.ENGINE_MODULES:
    importlib.import_module(_name)
`);
  t.engine_import_ms = ms(t1);
  t.total_ms = ms(t0);
  t.versions = py.runPython(`
import sys, numpy, st_language
from importlib.metadata import version
"Python %s, numpy %s, st-language %s" % (sys.version.split()[0], numpy.__version__, version("st-language"))
`);
  t.network = networkBytes();
  t.heap_bytes = wasmHeap();
  return t;
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
  const spansPy = py.runPython("lambda e: __import__('array').array('d', engine.flat_spans(e.highlight_spans())).tobytes()")(engine);
  const spanBytes = toBytes(spansPy);
  const spans = new Float64Array(spanBytes.slice().buffer);
  const timings = engine.timings.toJs({ dict_converter: Object.fromEntries });
  timings.total_ms = ms(t0);
  return { info, midi, spans, timings };
}

self.onmessage = async (ev) => {
  const msg = ev.data;
  try {
    if (msg.cmd === "boot") {
      post({ type: "booted", timings: await boot() });
    } else if (msg.cmd === "load") {
      const r = await load(msg.name, msg.text);
      post({ type: "loaded", id: msg.id, ...r }, [r.midi.buffer, r.spans.buffer]);
    } else if (msg.cmd === "transpose") {
      const t0 = performance.now();
      const midi = toBytes(engine.midi_bytes(msg.semitones));
      post({ type: "midi", id: msg.id, midi, semitones: msg.semitones, ms: ms(t0) }, [midi.buffer]);
    } else if (msg.cmd === "memory") {
      post({ type: "memory", id: msg.id, heap_bytes: wasmHeap() });
    }
  } catch (err) {
    post({ type: "error", id: msg.id, cmd: msg.cmd, message: String(err && err.message || err) });
  }
};
