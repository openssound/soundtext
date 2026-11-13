// SoundText Mobile: l'avvio. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ avvio

function setStatus(text, error = false) {
  const el = $("status");
  el.textContent = text;
  el.classList.toggle("error", error);
}

async function loadExample(name) {
  await openExample(name, false);
}

// L'ultimo brano aperto, per riaprirlo all'avvio.
async function restoreLastDoc() {
  let last = null;
  try { last = JSON.parse(localStorage.getItem("stmobile.last") || "null"); } catch (e) {}
  if (last && last.kind === "song" && await Songs.get(last.id)) return openSong(last.id, false);
  if (last && last.kind === "example" && state.examples.includes(last.file)) return openExample(last.file, false);
  return null;
}

async function main() {
  const tPage = performance.now();
  const startedHidden = document.visibilityState === "hidden";
  await I18n.load();
  I18n.translate();
  setupLanguageChoice();
  $("engineState").textContent = t("avvio…");
  if (!window.isSecureContext) {
    // http:// fuori da localhost: niente service worker ne' AudioWorklet
    const warn = document.createElement("p");
    warn.id = "insecure";
    warn.textContent = t("Pagina non sicura: il testo si apre, ma l'audio e l'uso offline non funzionano. " +
      "Usa HTTPS, http://localhost, o in Chrome per Android il flag " +
      "chrome://flags/#unsafely-treat-insecure-origin-as-secure con {origin}.", { origin: location.origin });
    warn.style.cssText = "margin:4px 16px;padding:8px;border-radius:6px;background:#7a2e00;color:#fff;font-size:13px";
    $("view-brani").prepend(warn);
  }
  setupEditor();
  setupMusicBar();
  setupVoice();
  setupHum();
  setupCrea();
  setupStructure();
  setupTransform();
  for (const b of document.querySelectorAll(".tabs button")) b.onclick = () => setView(b.dataset.view);
  let view = "brani";
  try {
    // senza un brano da riaprire si parte da Brani
    if (localStorage.getItem("stmobile.last") && localStorage.getItem("stmobile.last") !== "null") {
      view = localStorage.getItem("stmobile.view") || "brani";
    }
  } catch (e) {}
  setView(view);

  const sw = await serviceWorker();
  const coldCache = !(await cached("vendor/pyodide/pyodide.asm.wasm"));
  startWorker();
  const files = await (await fetch("bundle/files.json")).json();
  state.examples = files.examples;
  voice.models = files.voice || [];
  $("newSong").onclick = () => newSong().catch(showError);
  $("file").onchange = (ev) => {
    const f = ev.target.files[0];
    ev.target.value = "";
    if (f) openFile(f).catch(showError);
  };
  $("play").onclick = () => play();
  $("speed").oninput = (ev) => setSpeed(Number(ev.target.value));
  $("trans").onchange = (ev) => setTranspose(Number(ev.target.value)).catch(showError);
  $("trans").oninput = (ev) => { $("transOut").value = ev.target.value; };
  $("follow").onchange = () => { lastFollow = -1; };
  $("scoreTracks").onchange = (ev) => { score.choice = ev.target.value; showScore().catch(showError); };
  $("zoomOut").onclick = () => setScoreScale(-1);
  $("zoomIn").onclick = () => setScoreScale(1);
  $("score").addEventListener("click", onScoreTap);
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => showScore().catch(showError), 300);
  });
  const seek = $("seek");
  seek.oninput = () => {
    state.seeking = true;
    const beat = Number(seek.value);
    $("pos").textContent = positionText(beat);
  };
  seek.onchange = () => { state.seeking = false; seekTo(Number(seek.value)); };
  $("loopA").onclick = () => setLoopPoint("a").catch(showError);
  $("loopB").onclick = () => setLoopPoint("b").catch(showError);
  $("loopOn").onclick = () => { state.loop.on = !state.loop.on; renderLoop(); };
  $("metronome").onchange = (ev) => { state.metronome = ev.target.checked; renderMidi().catch(showError); };
  $("goto").onchange = (ev) => {
    if (ev.target.value !== "") goTo(Number(ev.target.value));
    ev.target.value = "";
  };
  $("warnButton").onclick = () => {
    const list = $("warnings");
    list.hidden = !list.hidden;
    $("warnButton").setAttribute("aria-expanded", String(!list.hidden));
  };
  // Schermo bloccato, app in background: il tick si chiede al player (non
  // quello dell'ultimo fotogramma, che in background non si aggiorna), cosi'
  // fra "hidden" e "visible" si vede se la musica e' andata avanti.
  const lifecycle = async (event) => {
    let tick = null;
    try { if (state.synth) tick = await state.synth.retrievePlayerCurrentTick(); } catch (e) {}
    Metrics.record("visibilita", { event, state: document.visibilityState, playing: state.playing,
                                   ctx_state: state.ctx ? state.ctx.state : null, tick });
    if (document.visibilityState === "hidden") saveDoc().catch(() => {});
  };
  document.addEventListener("visibilitychange", () => lifecycle("visibilitychange"));
  // Chrome: pagina congelata o ripresa (risparmio energetico, scheda in background)
  document.addEventListener("freeze", () => lifecycle("freeze"));
  document.addEventListener("resume", () => lifecycle("resume"));

  // La schermata Brani si usa subito, mentre il motore si avvia.
  await renderSongs();
  const restored = restoreLastDoc().catch(() => null);
  if (!state.doc) setStatus(t("Avvio del motore…"));

  try {
    const boot = await state.booted;
    Metrics.record("avvio", {
      cache: coldCache ? "senza cache (primo avvio)" : "con cache", service_worker: sw,
      page_to_ready_ms: ms(tPage), ...boot, ...Metrics.device(),
      // scheda ricaricata dal browser dopo averla scaricata in background
      discarded: document.wasDiscarded === true, started_hidden: startedHidden,
    });
    $("engineState").textContent = t("pronto in {s} s ({versions})",
                                     { s: (boot.total_ms / 1000).toLocaleString(I18n.locale, { maximumFractionDigits: 1 }), versions: boot.versions });
    call("transforms").then((r) => { bar.transforms = r.result; if (bar.page === 3) renderKeys(); }).catch(() => {});
    setTimeout(prefetchForOffline, 5000);
    await restored;
    if (!state.doc) {
      setStatus(t("Scegli un brano"));
      setView("brani");
    }
    if (new URLSearchParams(location.search).has("misura")) await automaticMeasure();
  } catch (e) {
    $("engineState").textContent = t("errore");
    showError(e);
  }
}

// La scelta della lingua (in fondo alla schermata Brani): l'app si
// ricarica nella nuova lingua.
function setupLanguageChoice() {
  const sel = $("language");
  for (const [code, name] of Object.entries(I18n.LANGUAGES)) sel.add(new Option(name, code));
  sel.value = I18n.language;
  sel.onchange = () => {
    saveDoc().catch(() => {}).finally(() => I18n.setLanguage(sel.value));
  };
}

// ?misura=1: analizza i due esempi della fase 0 e manda le misure con un
// POST a "misure" (il server di prova in mobile/misura_headless.py).
async function automaticMeasure() {
  for (const name of ["symphony_d_minor_box.st", "jazz_aaba.st", "symphony_d_minor_box.st"]) {
    await loadExample(name);
    await state.song.spansReady;
  }
  await measureMemory("fine della misura automatica");
  await fetch("misure", { method: "POST", body: JSON.stringify(Metrics.all()) }).catch(() => {});
}

function showError(e) {
  console.error(e);
  setStatus(shortError(e), true);
}

main();
