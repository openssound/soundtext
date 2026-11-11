// Partitura di SoundText Mobile: verovio (incisione musicale in
// WebAssembly, LGPL) impagina il MusicXML del motore in pagine SVG, in un
// worker suo, cosi' la pagina e l'evidenziazione non si fermano mentre
// disegna. Si carica solo alla prima apertura della schermata Partitura.
"use strict";

let toolkit = null;
let ready = null;

function boot() {
  if (!ready) {
    ready = new Promise((resolve, reject) => {
      try {
        importScripts("vendor/verovio/verovio-toolkit-wasm.js");
      } catch (e) {
        reject(e);
        return;
      }
      const start = () => {
        verovio.enableLog(verovio.LOG_OFF);
        toolkit = new verovio.toolkit();
        resolve(toolkit.getVersion());
      };
      if (verovio.module.calledRun) start();
      else verovio.module.onRuntimeInitialized = start;
    });
  }
  return ready;
}

// Le note che suonano a ogni battito: [battito, [id accesi], [id spenti]].
// La mappa dei tempi di verovio sviluppa i ritornelli: le ripetizioni hanno
// id "xxx-rend2", che si riportano alla nota disegnata.
function timemap() {
  const plain = (ids) => (ids || []).map((id) => id.replace(/-rend\d+$/, ""));
  return toolkit.renderToTimemap().map((e) => [e.qstamp, plain(e.on), plain(e.off)]);
}

self.onmessage = async (ev) => {
  const msg = ev.data;
  try {
    if (msg.cmd === "render") {
      const t0 = performance.now();
      const version = await boot();
      const boot_ms = Math.round(performance.now() - t0);
      const t1 = performance.now();
      toolkit.setOptions({
        pageWidth: msg.pageWidth, scale: msg.scale, adjustPageHeight: true,
        pageMarginLeft: 20, pageMarginRight: 20, pageMarginTop: 40, pageMarginBottom: 20,
        header: "none", footer: "none", breaks: "auto",
      });
      if (!toolkit.loadData(msg.xml)) throw new Error("verovio non ha potuto leggere la partitura");
      const pages = [];
      for (let n = 1; n <= toolkit.getPageCount(); n++) pages.push(toolkit.renderToSVG(n));
      const render_ms = Math.round(performance.now() - t1);
      self.postMessage({ id: msg.id, pages, timemap: timemap(), version, boot_ms, render_ms });
    }
  } catch (e) {
    self.postMessage({ id: msg.id, error: String(e && e.message || e) });
  }
};
