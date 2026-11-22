// SoundText Mobile: i SoundFont scelti dall'utente. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ SoundFont dell'utente
//
// Un file .sf2 dal telefono si tiene in IndexedDB (soundfonts.js) e si puo' usare come SoundFont
// predefinito (al posto di TimGM6mb, che resta caricato sotto, come riserva) e, traccia per traccia,
// dal mixer. FluidSynth tiene piu' SoundFont insieme: ogni SoundFont oltre al predefinito ha un suo
// scostamento di banco, e le note di una traccia scelgono il banco giusto con un Bank Select scritto nel
// MIDI dal motore (engine.midi_bytes con banks). Le percussioni suonano sempre dal predefinito.
// I file .sf3 (campioni in Ogg Vorbis) si leggono come gli .sf2: la FluidSynth e' quella con libsndfile.

const fonts = { list: [], defaultId: "", loaded: new Map(), busy: null, autoSounds: true, autoDownload: true };
const FONT_DEFAULT_KEY = "stmobile.soundfont";
const FONT_AUTO_KEY = "stmobile.autosounds";           // «Scegli da solo il pacchetto adatto al brano» (di partenza: si)
const FONT_AUTODL_KEY = "stmobile.autodownload";       // «Scarica da solo i pacchetti consigliati» (solo con il Wi-Fi; di partenza: si)
const FONT_BIG_BYTES = 80 * 1048576;

const fontMegabytes = (bytes) => (bytes / 1048576).toLocaleString(I18n.locale, { maximumFractionDigits: 1 });

async function loadFontList() {
  fonts.list = await SoundFonts.list().catch(() => []);
  let saved = "";
  try { saved = localStorage.getItem(FONT_DEFAULT_KEY) || ""; } catch (e) {}
  fonts.defaultId = fonts.list.some((f) => f.id === saved) ? saved : "";
  try {
    fonts.autoSounds = localStorage.getItem(FONT_AUTO_KEY) !== "no";
    fonts.autoDownload = localStorage.getItem(FONT_AUTODL_KEY) !== "no";
  } catch (e) {}
}

const fontByName = (name) => fonts.list.find((f) => f.name === name) || null;
// il banco di un SoundFont che non e' il predefinito: 1, 2, 3... nell'ordine dell'elenco
const fontBank = (id) => fonts.list.findIndex((f) => f.id === id) + 1;

// ------------------------------------------------------------ la scelta automatica dei suoni (docs, sezione 10)
//
// Per ogni strumento (programma General MIDI) vale il primo SoundFont che lo contiene: quello scelto a mano per la traccia, il
// predefinito dell'utente, poi i pacchetti scaricati, poi TimGM6mb. Se l'utente non ha scelto un predefinito, il pacchetto piu'
// adatto al brano diventa il suo predefinito e gli strumenti che quel pacchetto non ha vanno al pacchetto che li ha: si
// caricano solo i pacchetti che il brano usa davvero.

function installedPacks() {
  return PACKS.map((pack) => ({ pack, font: fonts.list.find((f) => f.name === pack.file) })).filter((x) => x.font);
}

// il genere di un brano fatto da «Un brano in 60 secondi» (nel commento «// quick: {...}»), o ""
function songGenre(doc = state.doc) {
  try {
    const m = /^\/\/ quick: (\{.*\})\s*$/m.exec(doc && doc.text || "");
    return m ? JSON.parse(m[1]).genre || "" : "";
  } catch (e) { return ""; }
}

// {defaultId, tracks: {traccia: id del SoundFont}, recommend: il pacchetto da proporre (non scaricato) o null}
function soundPlan(doc = state.doc) {
  const plan = { defaultId: "", tracks: {}, recommend: null };
  if (!fonts.autoSounds || fonts.defaultId || !doc || !state.song || !state.song.info) return plan;
  const tracks = state.song.info.tracks.filter((tr) => !tr.percussion && tr.program !== undefined);
  if (!tracks.length) return plan;
  const genrePack = PACK_FOR_GENRE[songGenre(doc)];
  const covered = (pack) => tracks.filter((tr) => pack.programs.includes(tr.program)).length;
  const score = (pack) => covered(pack) + (pack.id === genrePack ? 0.5 : 0);
  const have = installedPacks();
  const all = have.find((x) => x.pack.id === "completo");
  if (all) { plan.defaultId = all.font.id; return plan; }         // un file solo: copre tutto
  const ranked = have.slice().sort((a, b) => score(b.pack) - score(a.pack));
  if (ranked.length && covered(ranked[0].pack)) {
    plan.defaultId = ranked[0].font.id;
    for (const tr of tracks) {
      if (ranked[0].pack.programs.includes(tr.program)) continue;
      const other = ranked.find((x) => x.pack.programs.includes(tr.program));
      if (other) plan.tracks[tr.name] = other.font.id;
    }
  }
  // il pacchetto consigliato: quello che copre di piu' fra tutti, se copre almeno meta' del brano e non c'e' ancora
  const singles = PACKS.filter((p) => p.id !== "completo");
  const best = singles.slice().sort((a, b) => score(b) - score(a))[0];
  const bestInstalled = best && have.some((x) => x.pack.id === best.id);
  if (best && covered(best) * 2 >= tracks.length && !bestInstalled && !(plan.defaultId && covered(best) <= covered(ranked[0].pack))) plan.recommend = best;
  return plan;
}

// Il predefinito in uso: quello dell'utente o, in automatico, il pacchetto adatto al brano
function effectiveDefaultId() {
  return fonts.defaultId || soundPlan().defaultId;
}

// Le scelte del brano aperto: { traccia: SoundFont }, a mano e (se manca) automatiche, solo per i SoundFont che si hanno ancora
function docFonts(doc = state.doc) {
  const chosen = {};
  const plan = soundPlan(doc);
  for (const [track, id] of Object.entries(plan.tracks)) {
    const font = fonts.list.find((f) => f.id === id);
    if (font) chosen[track] = font;
  }
  if (!doc || !doc.fonts) return chosen;
  for (const [track, name] of Object.entries(doc.fonts)) {
    const font = fontByName(name);
    if (font) chosen[track] = font;
  }
  return chosen;
}

// I banchi da scrivere nel MIDI: { traccia: banco } per le tracce con un SoundFont diverso dal predefinito
function fontBanks(doc = state.doc) {
  const banks = {};
  const base = effectiveDefaultId();
  for (const [track, font] of Object.entries(docFonts(doc))) {
    if (font.id !== base) banks[track] = fontBank(font.id);
  }
  return banks;
}

// Cio' che serve al sintetizzatore ora: il predefinito dell'utente e i SoundFont delle tracce.
// Quelli che non servono piu' si scaricano dalla memoria.
async function syncFonts(synth) {
  const needed = new Map();                       // id -> banco (0 = predefinito)
  const base = effectiveDefaultId();
  if (base) needed.set(base, 0);
  for (const font of Object.values(docFonts())) if (!needed.has(font.id)) needed.set(font.id, fontBank(font.id));
  for (const [id, sfid] of [...fonts.loaded]) {
    if (!needed.has(id)) { synth.unloadSFont(sfid); fonts.loaded.delete(id); }
  }
  for (const [id, bank] of needed) {
    if (fonts.loaded.has(id)) continue;
    const meta = fonts.list.find((f) => f.id === id);
    showSoundsLoading(meta ? (meta.title || meta.name) : "");
    try {
      const bytes = await SoundFonts.get(id);
      if (!bytes) throw new Error("vuoto");
      const sfid = await synth.loadSFont(bytes.slice(0));
      if (bank) synth.setSFontBankOffset(sfid, bank);
      fonts.loaded.set(id, sfid);
    } catch (e) {
      console.error(e);
      setStatus(t("Il SoundFont «{name}» non si carica: suona il predefinito.", { name: meta ? meta.name : id }), true);
    } finally {
      hideSoundsLoading();
    }
  }
}

// L'attesa mentre i suoni si caricano (un SF3 si decomprime tutto all'apertura: da uno a diversi secondi): una striscia in
// cima alla pagina con il cerchio che gira, il Play fermo e l'annuncio per lo screen reader. Si puo' annidare.
const soundsLoading = { depth: 0, playWasDisabled: false };

function showSoundsLoading(name) {
  if (soundsLoading.depth++ === 0) {
    soundsLoading.playWasDisabled = $("play").disabled;
    $("play").disabled = true;
    $("play").setAttribute("aria-busy", "true");
    document.body.classList.add("loading-sounds");
  }
  $("soundsLoadingTitle").textContent = t("Carico i suoni…");
  $("soundsLoadingText").textContent = name
    ? t("«{name}»: aspetta qualche secondo, poi si suona.", { name })
    : t("Aspetta qualche secondo, poi si suona.");
  $("soundsLoading").hidden = false;
}

function hideSoundsLoading() {
  if (--soundsLoading.depth > 0) return;
  soundsLoading.depth = 0;
  $("soundsLoading").hidden = true;
  $("play").disabled = soundsLoading.playWasDisabled;
  $("play").removeAttribute("aria-busy");
  document.body.classList.remove("loading-sounds");
}

// ------------------------------------------------------------ il pacchetto consigliato per il brano

const packHintDismissed = new Set();               // i pacchetti che l'utente ha chiuso, fino al prossimo avvio

function onWifi() {
  const c = navigator.connection;
  return !!c && c.type === "wifi";
}

function renderPackHint() {
  const box = $("packHint");
  if (!box) return;
  const plan = soundPlan();
  const pack = plan.recommend && PACKS.find((p) => p.id === plan.recommend.id);
  box.hidden = true;
  if (!pack || !pack.info || packHintDismissed.has(pack.id) || packBusy) return;
  if (fonts.autoDownload && onWifi()) { downloadPack(pack, { auto: true }).catch(showError); return; }
  const size = fontMegabytes(pack.info.bytes);
  $("packHintText").textContent = t("Questo brano suona meglio con «{title}» ({size} MB).", { title: pack.title(), size });
  $("packHintGet").textContent = t("Scarica");
  $("packHintGet").onclick = () => { box.hidden = true; downloadPack(pack).catch(showError); };
  $("packHintClose").onclick = () => { packHintDismissed.add(pack.id); box.hidden = true; };
  box.hidden = false;
}

// Dopo aver cambiato il SoundFont predefinito: il sintetizzatore si rifa' al prossimo Play
function resetSynth() {
  if (state.playing) pause();
  if (state.synthNode) { try { state.synthNode.disconnect(); } catch (e) {} }
  if (state.fxChain) { state.fxChain.dispose(); state.fxChain = null; }
  // Un sintetizzatore nuovo vuole anche un contesto audio nuovo: il FluidSynth in WebAssembly vive nello spazio del
  // contesto, e ricrearlo nello stesso si rompe («null function» al caricamento del SoundFont). Il prossimo tocco
  // (unlockInGesture) ne crea uno.
  // Chiudere il contesto basta a liberare il sintetizzatore: synth.close() lo fa andare in crash
  // («memory access out of bounds» in _delete_fluid_player) mentre l'AudioWorklet lavora ancora.
  if (state.ctx) { try { state.ctx.close(); } catch (e) {} }
  state.ctx = null;
  state.synth = null;
  state.synthNode = null;
  state.audioReady = null;
  fonts.loaded.clear();
}

// ---- la schermata

function renderFonts() {
  const ul = $("sfList");
  ul.innerHTML = "";
  const row = (id, title, detail, extra) => {
    const li = document.createElement("li");
    const label = document.createElement("label");
    const radio = document.createElement("input");
    radio.type = "radio"; radio.name = "sfDefault"; radio.checked = fonts.defaultId === id;
    radio.onchange = () => setDefaultFont(id).catch(showError);
    const text = document.createElement("span");
    text.textContent = title;
    const small = document.createElement("small");
    small.textContent = detail;
    text.append(small);
    label.append(radio, text);
    li.append(label);
    if (extra) li.append(extra);
    ul.append(li);
  };
  row("", t("TimGM6mb (incluso)"), t("{size} MB · predefinito dell'app", { size: fontMegabytes(5969788) }));
  for (const f of fonts.list) {
    const del = document.createElement("button");
    del.textContent = t("Elimina");
    del.className = "danger";
    del.setAttribute("aria-label", t("Elimina il SoundFont {name}", { name: f.name }));
    del.onclick = () => removeFont(f.id).catch(showError);
    row(f.id, f.title && f.title !== f.name ? f.title : f.name, `${f.name} · ${t("{size} MB", { size: fontMegabytes(f.size) })}` +
        (f.size > FONT_BIG_BYTES ? " · " + t("grande: su un telefono con poca memoria può non caricarsi") : ""), del);
  }
  $("sfHint").hidden = fonts.list.length > 0;
  if (typeof renderPack === "function") renderPack();
}

function fontSay(text, error = false) {
  $("sfStatus").textContent = text;
  $("sfStatus").classList.toggle("error", error);
}

async function setDefaultFont(id) {
  fonts.defaultId = id;
  try { localStorage.setItem(FONT_DEFAULT_KEY, id); } catch (e) {}
  resetSynth();
  renderFonts();
  renderMixer();
  fontSay(id ? t("SoundFont predefinito cambiato: lo senti dal prossimo Play.") : t("Di nuovo il SoundFont incluso."));
}

async function addFont(file) {
  fontSay(t("Salvo «{name}»…", { name: file.name }));
  try {
    const meta = await SoundFonts.add(file);
    await loadFontList();
    // stesso file ricaricato: se era in uso, si ricarica anche nel sintetizzatore
    if (state.synth && fonts.loaded.has(meta.id)) resetSynth();
    renderFonts();
    renderMixer();
    fontSay(t("«{name}» è tra i tuoi SoundFont ({size} MB). Scegli «{title}» come predefinito o assegnalo a una traccia dal mixer.",
              { name: meta.name, size: fontMegabytes(meta.size), title: meta.title || meta.name }));
  } catch (e) {
    if (e instanceof SoundFontError) {
      fontSay(t("«{name}» non è un SoundFont .sf2 o .sf3.", { name: file.name }), true);
    } else {
      fontSay(t("Non riesco a salvare «{name}»: {message}", { name: file.name, message: e.message }), true);
    }
  }
}

async function removeFont(id) {
  const font = fonts.list.find((f) => f.id === id);
  if (!font || !confirm(t("Eliminare il SoundFont «{name}» dal telefono?", { name: font.name }))) return;
  await SoundFonts.remove(id);
  const wasDefault = fonts.defaultId === id;
  await loadFontList();
  if (wasDefault) { try { localStorage.setItem(FONT_DEFAULT_KEY, ""); } catch (e) {} }
  if (state.synth && (wasDefault || fonts.loaded.has(id))) resetSynth();
  renderFonts();
  renderMixer();
  renderMidi().catch(showError);
}

// Il menu di una traccia nel mixer: Predefinito o uno dei SoundFont dell'utente
function fontSelectFor(track) {
  if (!fonts.list.length || track.percussion) return null;
  const select = document.createElement("select");
  select.className = "sfsel";
  select.setAttribute("aria-label", t("SoundFont di {name}", { name: track.name }));
  select.add(new Option(t("SoundFont: predefinito"), ""));
  for (const f of fonts.list) select.add(new Option(f.title && f.title !== f.name ? f.title : f.name, f.name));
  select.value = (state.doc && state.doc.fonts && state.doc.fonts[track.name]) || "";
  if (select.value !== ((state.doc && state.doc.fonts && state.doc.fonts[track.name]) || "")) select.value = "";
  select.onchange = () => {
    const doc = state.doc;
    if (!doc) return;
    doc.fonts = doc.fonts || {};
    if (select.value) doc.fonts[track.name] = select.value; else delete doc.fonts[track.name];
    saveDoc().catch(() => {});
    renderMidi().catch(showError);
  };
  return select;
}

// ------------------------------------------------------------ i pacchetti di strumenti
//
// Un SoundFont .sf3 (compresso) leggero per famiglia di strumenti, costruito da mobile/tools/costruisci_sf3.py dalle librerie
// libere (CC0 e CC BY): l'orchestra (archi, legni, ottoni, arpa, timpani), l'elettrico (piani elettrici, chitarre, bassi)... Si
// scaricano a richiesta, mai al primo avvio, e dopo si usano come ogni altro SoundFont: predefinito sopra TimGM6mb, che resta
// per gli altri strumenti, o assegnati a una traccia dal mixer. Ogni file sta sullo stesso sito (vendor/soundfont/), con il suo
// SHA-256 e l'elenco degli strumenti in un .json accanto.

const PACKS = [
  { id: "completo", programs: [0,1,4,5,6,9,11,12,13,14,16,17,18,21,24,25,26,27,28,29,30,32,33,34,35,36,38,39,40,41,42,43,44,45,46,47,48,49,56,57,58,59,60,61,65,66,68,70,71,72,73,80,81,88,89,90,95], replaces: ["soundtext-orchestra.sf2", "soundtext-orchestra.sf3", "soundtext-acustico.sf3", "soundtext-elettrico.sf3", "soundtext-elettronico.sf3"],
    title: () => t("Tutti gli strumenti"),
    what: () => t("Orchestra, acustico, elettrico ed elettronico in un solo file: ogni strumento ha il suo suono, senza scegliere un pacchetto."),
    license: () => t("licenze CC0, pubblico dominio e CC BY 3.0 (Greg Sullivan, Wurlitzer)") },
  { id: "orchestra", programs: [6,9,11,12,13,14,40,41,42,43,44,45,46,47,48,49,56,57,58,59,60,61,68,70,71,72,73], replaces: ["soundtext-orchestra.sf2"],       // la prima versione (46 MB): chi l'ha scaricata riceve quella compressa
    title: () => t("Pacchetto orchestra"),
    what: () => t("Archi, legni, ottoni, arpa, timpani e altri strumenti d'orchestra, più vicini al suono del computer."),
    license: () => t("licenza CC0 (VSCO 2 CE e VCSL)") },
  { id: "acustico", programs: [0,1,21,24,25,26,32,40,56,65,66,71],
    title: () => t("Pacchetto acustico"),
    what: () => t("Pianoforti, chitarre acustiche, contrabbasso, fisarmonica, sax, tromba, violino e clarinetto: per jazz, swing, bossa, country, ballata e valzer."),
    license: () => t("licenze CC0 e pubblico dominio") },
  { id: "elettrico", programs: [4,5,16,17,18,27,28,29,30,33,34,35,36],
    title: () => t("Pacchetto elettrico"),
    what: () => t("Piani elettrici, organi, chitarre pulite, stoppate e distorte e bassi: per rock, blues, funk, soul e pop elettrico."),
    license: () => t("licenze CC0 (FreePats) e CC BY 3.0 (Greg Sullivan, Wurlitzer)") },
  { id: "elettronico", programs: [38,39,80,81,88,89,90,95],
    title: () => t("Pacchetto elettronico"),
    what: () => t("Bassi, lead e pad sintetizzati: per elettronica, lo-fi, disco e pop."),
    license: () => t("suoni generati, senza licenze di terzi") },
];
for (const p of PACKS) { p.file = `soundtext-${p.id}.sf3`; p.url = `vendor/soundfont/${p.file}`; p.infoUrl = `vendor/soundfont/soundtext-${p.id}.json`; p.info = null; }
let packBusy = false;

// Il pacchetto che ogni genere di «Un brano in 60 secondi» preferisce, quando piu' di uno copre gli strumenti (core/quicksong.py)
const PACK_FOR_GENRE = {
  rock: "elettrico", punk: "elettrico", metal: "elettrico", funk: "elettrico", soul: "elettrico", disco: "elettrico",
  blues: "elettrico", reggae: "elettrico", rocknroll: "elettrico",
  jazz: "acustico", swing: "acustico", bossa: "acustico", samba: "acustico", chacha: "acustico", country: "acustico",
  pop: "acustico", ballata: "acustico", valzer: "acustico", ballata68: "acustico", afro68: "acustico", balcanico78: "acustico",
  elettronica: "elettronico", lofi: "elettronico", orchestrale: "orchestra", marcia: "orchestra",
};

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

function buildPackBoxes() {
  const host = $("sfPacks");
  host.replaceChildren();
  for (const p of PACKS) {
    const box = document.createElement("div");
    box.className = "sf-pack";
    box.hidden = true;
    const title = document.createElement("strong");
    p.infoEl = document.createElement("p");
    p.infoEl.className = "hint";
    const label = document.createElement("label");
    label.className = "check";
    p.defaultEl = document.createElement("input");
    p.defaultEl.type = "checkbox";
    p.defaultEl.checked = false;                     // di partenza no: il pacchetto adatto lo sceglie il brano
    const span = document.createElement("span");
    span.textContent = t("Usalo come SoundFont predefinito dopo il download");
    label.append(p.defaultEl, document.createTextNode(" "), span);
    p.getEl = document.createElement("button");
    p.getEl.onclick = () => downloadPack(p).catch(showError);
    p.barEl = document.createElement("progress");
    p.barEl.max = 1;
    p.barEl.value = 0;
    p.barEl.hidden = true;
    p.barEl.setAttribute("aria-label", t("Avanzamento del download"));
    p.titleEl = title;
    p.boxEl = box;
    box.append(title, p.infoEl, label, p.getEl, p.barEl);
    host.append(box);
  }
}

async function loadPackInfo() {
  await Promise.all(PACKS.map(async (p) => {
    try {
      const r = await fetch(p.infoUrl, { cache: "no-cache" });
      p.info = r.ok ? await r.json() : null;
    } catch (e) {
      p.info = null;                        // senza rete e mai scaricato: il pacchetto non si offre
    }
  }));
  renderPack();
}

function renderPack() {
  for (const p of PACKS) {
    if (!p.boxEl) continue;                          // i riquadri si costruiscono in setupFonts
    const installed = fonts.list.some((f) => f.name === p.file);
    const legacy = (p.replaces || []).some((n) => fonts.list.some((f) => f.name === n));
    const allInOne = PACKS.find((x) => x.id === "completo");
    const coveredByAll = p.id !== "completo" && allInOne && fonts.list.some((f) => f.name === allInOne.file);
    p.boxEl.hidden = !p.info || installed || coveredByAll;
    if (!p.info) continue;
    const size = fontMegabytes(p.info.bytes);
    p.titleEl.textContent = p.title();
    p.infoEl.textContent = legacy && p.id === "orchestra"
      ? t("Una versione più leggera del pacchetto orchestra: stesso suono, {size} MB invece di 46. Sostituisce quella che hai sul telefono.", { size })
      : legacy
        ? `${p.what()} ${t("{size} MB, {license}. Sostituisce i pacchetti che hai sul telefono.", { size, license: p.license() })}`
        : `${p.what()} ${t("{size} MB, {license}. Si scarica una volta sola e resta sul telefono.", { size, license: p.license() })}`;
    p.getEl.textContent = t("Scarica «{title}» ({size} MB)", { title: p.title(), size });
    p.getEl.disabled = packBusy;
  }
}

async function downloadPack(p, opts = {}) {
  if (packBusy || !p.info) return;
  if (!opts.auto && !confirm(t("Scarico «{title}»: {size} MB. Meglio con il Wi-Fi. Continuo?", { title: p.title(), size: fontMegabytes(p.info.bytes) }))) return;
  packBusy = true;
  renderPack();
  const bar = p.barEl;
  bar.hidden = false;
  bar.value = 0;
  try {
    const resp = await fetch(p.url);
    if (!resp.ok) throw new Error(t("Pacchetto non trovato ({status})", { status: resp.status }));
    const chunks = [];
    let got = 0;
    const reader = resp.body && resp.body.getReader ? resp.body.getReader() : null;
    if (reader) {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        got += value.length;
        bar.value = got / p.info.bytes;
        fontSay(t("Scarico «{title}»… {done} di {size} MB", { title: p.title(), done: fontMegabytes(got), size: fontMegabytes(p.info.bytes) }));
      }
    } else {
      chunks.push(new Uint8Array(await resp.arrayBuffer()));
    }
    const blob = new Blob(chunks);
    if (blob.size !== p.info.bytes) throw new Error(t("Il file scaricato è incompleto: riprova."));
    fontSay(t("Controllo il file…"));
    if (hex(await crypto.subtle.digest("SHA-256", await blob.arrayBuffer())) !== p.info.sha256) {
      throw new Error(t("Il file scaricato non è quello atteso (controllo SHA-256): riprova."));
    }
    const replaced = fonts.list.filter((f) => (p.replaces || []).includes(f.name));
    const legacyWasDefault = replaced.some((f) => fonts.defaultId === f.id);
    await addFont(new File([blob], p.file));
    const added = fonts.list.find((f) => f.name === p.file);
    if (replaced.length && added) {                // il nuovo file prende il posto dei vecchi: si libera lo spazio
      for (const f of replaced) await SoundFonts.remove(f.id);
      await loadFontList();
      if (state.synth) resetSynth();
    }
    if (added && (legacyWasDefault || (!opts.auto && p.defaultEl.checked))) {
      await setDefaultFont(added.id);
      fontSay(t("«{title}» pronto: è il SoundFont predefinito. Lo senti dal prossimo Play.", { title: p.title() }));
    } else {
      fontSay(t("«{title}» pronto. Sceglilo come predefinito dall'elenco, o assegnalo a una traccia dal mixer.", { title: p.title() }));
    }
  } catch (e) {
    console.error(e);
    fontSay(t("Non riesco a scaricare il pacchetto: {message}", { message: e.message || String(e) }), true);
  }
  packBusy = false;
  bar.hidden = true;
  renderPack();
  renderMidi().catch(showError);                // i banchi del MIDI seguono il pacchetto adatto al brano
  renderPackHint();
}

async function setupFonts() {
  buildPackBoxes();
  await loadFontList();
  renderFonts();
  $("sfAuto").checked = fonts.autoSounds;
  $("sfAutoDl").checked = fonts.autoDownload;
  $("sfAuto").onchange = () => {
    fonts.autoSounds = $("sfAuto").checked;
    try { localStorage.setItem(FONT_AUTO_KEY, fonts.autoSounds ? "si" : "no"); } catch (e) {}
    if (state.synth) resetSynth();
    renderMidi().catch(showError);
    renderPackHint();
  };
  $("sfAutoDl").onchange = () => {
    fonts.autoDownload = $("sfAutoDl").checked;
    try { localStorage.setItem(FONT_AUTODL_KEY, fonts.autoDownload ? "si" : "no"); } catch (e) {}
    renderPackHint();
  };
  loadPackInfo().then(renderPackHint);
  $("sfFile").onchange = (ev) => {
    const f = ev.target.files[0];
    ev.target.value = "";
    if (f) addFont(f);
  };
}
