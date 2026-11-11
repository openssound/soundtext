// Service worker del prototipo: rende l'app usabile senza rete dopo il
// primo avvio e aggiunge le intestazioni COOP/COEP (isolamento
// cross-origin, per performance.measureUserAgentSpecificMemory).
//
// - pagina, script e bundle/: prima la rete, poi la cache (si vedono
//   subito le modifiche durante lo sviluppo, e funziona anche offline);
// - vendor/ (Pyodide, wheel, js-synthesizer, SoundFont): prima la cache,
//   messi in cache al primo uso. Il SoundFont si scarica solo al primo Play.
"use strict";

const CACHE = "stmobile-v22";            // pagina e bundle: si cambia a ogni versione
const VENDOR = "stmobile-vendor-v1";     // Pyodide, wheel, FluidSynth, SoundFont: restano
const KEEP = [CACHE, VENDOR, "stmobile-snapshot"];   // l'istantanea di Pyodide, gestita da worker.js
const SHELL = [
  "./", "index.html", "diagnostica.html", "style.css", "app.js", "metrics.js", "songs.js", "worker.js", "score-worker.js", "i18n.js",
  "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "bundle/files.json",
  "bundle/engine.zip",
];

self.addEventListener("install", (ev) => {
  ev.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(SHELL);
    // gli esempi, anche quelli non ancora aperti
    const files = await (await cache.match("bundle/files.json")).json();
    await cache.addAll(files.examples.map((n) => "bundle/examples/" + encodeURIComponent(n)));
    // le traduzioni dell'interfaccia
    await cache.addAll((files.languages || []).map((l) => `bundle/locales/${l}.json`));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (!KEEP.includes(name)) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

function isolated(resp) {
  if (!resp || resp.status === 0 || resp.type === "opaque") return resp;
  const headers = new Headers(resp.headers);
  headers.set("Cross-Origin-Opener-Policy", "same-origin");
  headers.set("Cross-Origin-Embedder-Policy", "require-corp");
  headers.set("Cross-Origin-Resource-Policy", "same-origin");
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers });
}

async function cacheFirst(req) {
  const cache = await caches.open(VENDOR);
  const hit = await cache.match(req);
  if (hit) return hit;
  const resp = await fetch(req);
  if (resp.ok) await cache.put(req, resp.clone());
  return resp;
}

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const resp = await fetch(req, { cache: "no-cache" });
    if (resp.ok) await cache.put(req, resp.clone());
    return resp;
  } catch (e) {
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    throw e;
  }
}

self.addEventListener("fetch", (ev) => {
  const req = ev.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  const scope = new URL(self.registration.scope);
  const path = url.pathname.slice(scope.pathname.length);
  const handler = path.startsWith("vendor/") ? cacheFirst : networkFirst;
  // Le intestazioni COOP/COEP servono solo alla pagina e ai worker: le altre
  // risposte restano quelle della cache, cosi' il browser puo' tenere il
  // WebAssembly gia' compilato (una Response ricreata perde il suo URL).
  const needsHeaders = req.mode === "navigate" || req.destination === "worker" || req.destination === "document";
  ev.respondWith(needsHeaders ? handler(req).then(isolated) : handler(req));
});
