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
// I file .sf3 (campioni in Ogg Vorbis) questo FluidSynth non li legge: si dice chiaro.

const fonts = { list: [], defaultId: "", loaded: new Map(), busy: null };
const FONT_DEFAULT_KEY = "stmobile.soundfont";
const FONT_BIG_BYTES = 80 * 1048576;

const fontMegabytes = (bytes) => (bytes / 1048576).toLocaleString(I18n.locale, { maximumFractionDigits: 1 });

async function loadFontList() {
  fonts.list = await SoundFonts.list().catch(() => []);
  let saved = "";
  try { saved = localStorage.getItem(FONT_DEFAULT_KEY) || ""; } catch (e) {}
  fonts.defaultId = fonts.list.some((f) => f.id === saved) ? saved : "";
}

const fontByName = (name) => fonts.list.find((f) => f.name === name) || null;
// il banco di un SoundFont che non e' il predefinito: 1, 2, 3... nell'ordine dell'elenco
const fontBank = (id) => fonts.list.findIndex((f) => f.id === id) + 1;

// Le scelte del brano aperto: { traccia: nome del file }, solo per i SoundFont che si hanno ancora
function docFonts(doc = state.doc) {
  const chosen = {};
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
  for (const [track, font] of Object.entries(docFonts(doc))) {
    if (font.id !== fonts.defaultId) banks[track] = fontBank(font.id);
  }
  return banks;
}

// Cio' che serve al sintetizzatore ora: il predefinito dell'utente e i SoundFont delle tracce.
// Quelli che non servono piu' si scaricano dalla memoria.
async function syncFonts(synth) {
  const needed = new Map();                       // id -> banco (0 = predefinito)
  if (fonts.defaultId) needed.set(fonts.defaultId, 0);
  for (const font of Object.values(docFonts())) if (!needed.has(font.id)) needed.set(font.id, fontBank(font.id));
  for (const [id, sfid] of [...fonts.loaded]) {
    if (!needed.has(id)) { synth.unloadSFont(sfid); fonts.loaded.delete(id); }
  }
  for (const [id, bank] of needed) {
    if (fonts.loaded.has(id)) continue;
    const meta = fonts.list.find((f) => f.id === id);
    try {
      const bytes = await SoundFonts.get(id);
      if (!bytes) throw new Error("vuoto");
      const sfid = await synth.loadSFont(bytes.slice(0));
      if (bank) synth.setSFontBankOffset(sfid, bank);
      fonts.loaded.set(id, sfid);
    } catch (e) {
      console.error(e);
      setStatus(t("Il SoundFont «{name}» non si carica: suona il predefinito.", { name: meta ? meta.name : id }), true);
    }
  }
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
    if (e instanceof SoundFontError && e.code === "sf3") {
      fontSay(t("«{name}» è un SoundFont .sf3 (campioni compressi): il motore di SoundText Mobile non li legge. Serve un .sf2.", { name: file.name }), true);
    } else if (e instanceof SoundFontError) {
      fontSay(t("«{name}» non è un SoundFont .sf2.", { name: file.name }), true);
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

// ------------------------------------------------------------ il pacchetto orchestra
//
// Un SoundFont .sf2 leggero con archi, legni, ottoni, arpa, timpani e percussioni intonate (costruito da
// mobile/tools/costruisci_sf3.py dalle librerie CC0 VSCO 2 CE e VCSL). Si scarica a richiesta, mai al primo avvio,
// e dopo si usa come ogni altro SoundFont: predefinito sopra TimGM6mb, che resta per gli altri strumenti.
// Il file sta sullo stesso sito (vendor/soundfont/), con il suo SHA-256 in un file accanto.

const PACK_URL = "vendor/soundfont/soundtext-orchestra.sf2";
const PACK_INFO = "vendor/soundfont/soundtext-orchestra.json";
const PACK_NAME = "soundtext-orchestra.sf2";
const pack = { info: null, busy: false };

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

async function loadPackInfo() {
  try {
    const r = await fetch(PACK_INFO, { cache: "no-cache" });
    pack.info = r.ok ? await r.json() : null;
  } catch (e) {
    pack.info = null;                       // senza rete e mai scaricato: il pacchetto non si offre
  }
  renderPack();
}

function renderPack() {
  const box = $("sfPack");
  const installed = fonts.list.some((f) => f.name === PACK_NAME);
  box.hidden = !pack.info || installed;
  if (!pack.info) return;
  $("sfPackInfo").textContent = t("Archi, legni, ottoni, arpa, timpani e altri strumenti d'orchestra, più vicini al suono del computer. " +
    "{size} MB, licenza CC0 (VSCO 2 CE e VCSL). Si scarica una volta sola e resta sul telefono.", { size: fontMegabytes(pack.info.bytes) });
  $("sfPackGet").textContent = t("Scarica il pacchetto orchestra ({size} MB)", { size: fontMegabytes(pack.info.bytes) });
  $("sfPackGet").disabled = pack.busy;
}

async function downloadPack() {
  if (pack.busy || !pack.info) return;
  if (!confirm(t("Scarico il pacchetto orchestra: {size} MB. Meglio con il Wi-Fi. Continuo?", { size: fontMegabytes(pack.info.bytes) }))) return;
  pack.busy = true;
  renderPack();
  const bar = $("sfPackProgress");
  bar.hidden = false;
  bar.value = 0;
  try {
    const resp = await fetch(PACK_URL);
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
        bar.value = got / pack.info.bytes;
        fontSay(t("Scarico il pacchetto orchestra… {done} di {size} MB", { done: fontMegabytes(got), size: fontMegabytes(pack.info.bytes) }));
      }
    } else {
      chunks.push(new Uint8Array(await resp.arrayBuffer()));
    }
    const blob = new Blob(chunks);
    if (blob.size !== pack.info.bytes) throw new Error(t("Il file scaricato è incompleto: riprova."));
    fontSay(t("Controllo il file…"));
    if (hex(await crypto.subtle.digest("SHA-256", await blob.arrayBuffer())) !== pack.info.sha256) {
      throw new Error(t("Il file scaricato non è quello atteso (controllo SHA-256): riprova."));
    }
    await addFont(new File([blob], PACK_NAME));
    const added = fonts.list.find((f) => f.name === PACK_NAME);
    if (added) await setDefaultFont(added.id);
    fontSay(t("Pacchetto orchestra pronto: è il SoundFont predefinito. Lo senti dal prossimo Play."));
  } catch (e) {
    console.error(e);
    fontSay(t("Non riesco a scaricare il pacchetto: {message}", { message: e.message || String(e) }), true);
  }
  pack.busy = false;
  bar.hidden = true;
  renderPack();
}

async function setupFonts() {
  await loadFontList();
  renderFonts();
  $("sfPackGet").onclick = () => downloadPack().catch(showError);
  loadPackInfo();
  $("sfFile").onchange = (ev) => {
    const f = ev.target.files[0];
    ev.target.value = "";
    if (f) addFont(f);
  };
}
