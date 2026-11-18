// Misure del prototipo: in console e in localStorage, per la pagina
// diagnostica.html. Ogni voce: { kind, when, ...dati }.
"use strict";

const Metrics = (() => {
  const KEY = "stmobile.metrics";
  const MAX = 200;

  function all() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "[]");
    } catch (e) {
      return [];
    }
  }

  function record(kind, data) {
    const entry = { kind, when: new Date().toISOString(), ...data };
    console.info("[misura]", kind, entry);
    try {
      const list = all();
      list.push(entry);
      localStorage.setItem(KEY, JSON.stringify(list.slice(-MAX)));
    } catch (e) { /* archivio non disponibile: resta la console */ }
    return entry;
  }

  function clear() {
    try { localStorage.removeItem(KEY); } catch (e) {}
  }

  function device() {
    return {
      ua: navigator.userAgent,
      cores: navigator.hardwareConcurrency || null,
      ram_gb: navigator.deviceMemory || null,
      standalone: matchMedia("(display-mode: standalone)").matches || navigator.standalone === true,
      isolated: self.crossOriginIsolated === true,
    };
  }

  // Memoria della pagina: measureUserAgentSpecificMemory (Chrome, con
  // isolamento cross-origin: include worker e worklet), altrimenti
  // performance.memory (Chrome, solo il thread principale).
  async function pageMemory() {
    const out = {};
    if (self.crossOriginIsolated && performance.measureUserAgentSpecificMemory) {
      try {
        const m = await performance.measureUserAgentSpecificMemory();
        out.ua_specific_bytes = m.bytes;
      } catch (e) {
        out.ua_specific_error = String(e.message || e);
      }
    }
    if (performance.memory) {
      out.js_heap_used_bytes = performance.memory.usedJSHeapSize;
      out.js_heap_total_bytes = performance.memory.totalJSHeapSize;
    }
    return out;
  }

  return { all, record, clear, device, pageMemory };
})();
