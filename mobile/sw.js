// Service worker del prototipo: rende l'app usabile senza rete dopo il
// primo avvio e aggiunge le intestazioni COOP/COEP (isolamento
// cross-origin, per performance.measureUserAgentSpecificMemory).
//
// - pagina, script e bundle/: prima la rete, poi la cache (si vedono
//   subito le modifiche durante lo sviluppo, e funziona anche offline);
// - vendor/ (Pyodide, wheel, js-synthesizer, SoundFont): prima la cache,
//   messi in cache al primo uso. Il SoundFont si scarica solo al primo Play.
"use strict";

const CACHE = "stmobile-v138";            // pagina e bundle: si cambia a ogni versione
const VENDOR = "stmobile-vendor-v1";     // Pyodide, wheel, FluidSynth, SoundFont: restano
const KEEP = [CACHE, VENDOR, "stmobile-snapshot"];   // l'istantanea di Pyodide, gestita da worker.js
// I modelli della dettatura (50 MB l'uno) li conserva gia' Vosk nel suo
// archivio (IndexedDB) e non li richiede piu': tenerli anche qui
// raddoppierebbe lo spazio occupato sul telefono.
const VOICE_MODEL = /\/vendor\/vosk\/[^/]+\.tar\.gz$/;
// Lo stesso per il pacchetto orchestra (50 MB): lo tiene IndexedDB (soundfonts.js) dopo il download
const ORCHESTRA_PACK = /\/vendor\/soundfont\/soundtext-[a-z]+\.sf[23]$/;
const SHELL = [
  "./", "index.html", "diagnostica.html", "diagnostica.js", "style.css", "app/base.js", "app/text-edits.js", "app/editor.js", "app/voice.js", "app/fonts.js", "app/hum.js", "app/quick.js", "app/study.js", "app/backup.js", "app/access.js", "app/effects.js", "app/export.js", "app/pads.js", "app/exercises.js", "app/system.js", "app/songs-view.js", "app/create.js", "app/structure.js", "app/player.js", "app/score.js", "app/main.js",
  "metrics.js", "studio.js", "midicut.js", "svgsafe.js", "zip.js", "songs.js", "share.js", "progress.js", "fxchain.js", "soundfonts.js", "mp4.js", "wav.js", "export-worker.js", "worker.js", "score-worker.js", "voice-worklet.js", "i18n.js",
  "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "bundle/files.json",
  "bundle/engine.zip",
];

self.addEventListener("install", (ev) => {
  ev.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // dalla rete e non dalla cache HTTP del browser (GitHub Pages dice di tenere i file per qualche minuto): una
    // versione appena pubblicata non deve installarsi con i file della precedente
    const fresh = (urls) => urls.map((u) => new Request(u, { cache: "reload" }));
    await cache.addAll(fresh(SHELL));
    // gli esempi, anche quelli non ancora aperti
    const files = await (await cache.match("bundle/files.json")).json();
    await cache.addAll(fresh(files.examples.map((n) => "bundle/examples/" + encodeURIComponent(n))));
    // le traduzioni dell'interfaccia
    await cache.addAll(fresh((files.languages || []).map((l) => `bundle/locales/${l}.json`)));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (!KEEP.includes(name)) await caches.delete(name);
    }
    // i modelli della voce non stanno piu' in questa cache (vedi fetch)
    const vendor = await caches.open(VENDOR);
    for (const req of await vendor.keys()) {
      if (VOICE_MODEL.test(new URL(req.url).pathname)) await vendor.delete(req);
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
  if (VOICE_MODEL.test(url.pathname) || ORCHESTRA_PACK.test(url.pathname)) return;        // dalla rete, senza cache
  const scope = new URL(self.registration.scope);
  const path = url.pathname.slice(scope.pathname.length);
  const handler = path.startsWith("vendor/") ? cacheFirst : networkFirst;
  // Le intestazioni COOP/COEP servono solo alla pagina e ai worker: le altre
  // risposte restano quelle della cache, cosi' il browser puo' tenere il
  // WebAssembly gia' compilato (una Response ricreata perde il suo URL).
  const needsHeaders = req.mode === "navigate" || req.destination === "worker" || req.destination === "document";
  ev.respondWith(needsHeaders ? handler(req).then(isolated) : handler(req));
});
