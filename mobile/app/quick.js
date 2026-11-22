// SoundText Mobile: «Un brano in 60 secondi». Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ un brano in 60 secondi
//
// Genere, atmosfera e durata: il motore (engine.quick_song, quicksong.py) scrive un brano completo con i suoi
// generatori, un box per sezione e traccia; l'app lo salva fra i brani e lo fa suonare. Due modi:
//  - Semplificato (acceso di partenza): le schede dei generi con un'anteprima di qualche secondo, l'atmosfera, la durata;
//  - Dettagliato: in piu' tonalita', tempo, metrica, forma, organico, melodia, finale, modulazione, densita', un giro
//    scritto a mano e, dopo la generazione, ogni parte con il suo stile, il lucchetto e «Un'altra».
// Cio' che si sceglie a mano prevale sulla ricetta del genere; il resto lo decide la ricetta (campo vuoto). Passando da
// un modo all'altro i valori restano. Dopo la prima volta il brano e' sempre lo stesso: «Un'altra», «Sorprendimi» e le
// parti lo aggiornano senza riempire la lista dei brani.

const QUICK_STYLES_KEY = "stmobile.userstyles";
const quick = {
  choices: null, busy: false, simple: true, opts: {}, parts: {}, last: null, songId: null, lastName: "", preview: new Map(),
  previewing: null, resumed: null,
};
const QUICK_KEY = "stmobile.quick";
const QUICK_FIELDS = ["key", "bpm", "meter", "form", "ensemble", "melody", "ending", "modulation", "density", "chords", "seed", "bars", "loop", "compact", "human", "energy", "second_voice"];

// 64 s -> «1:04»
function formatClock(seconds) {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function quickSave() {
  try { localStorage.setItem(QUICK_KEY, JSON.stringify({ simple: quick.simple, opts: quick.opts })); } catch (e) {}
}

function quickLoad() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(QUICK_KEY) || "{}"); } catch (e) {}
  // la versione 1 salvava le scelte senza «opts»
  quick.simple = saved.simple !== false;
  quick.opts = saved.opts || (saved.genre ? saved : {});
  quick.opts.genre = quick.opts.genre || "pop";
  quick.opts.mood = quick.opts.mood || "allegra";
  quick.opts.duration = quick.opts.duration || 60;
}

const genreData = (id) => quick.choices.genres.find((g) => g.value === id);

// ---- i controlli

function quickFill(select, items, value, blank) {
  select.innerHTML = "";
  if (blank !== undefined) select.add(new Option(blank, ""));
  for (const item of items) select.add(new Option(item.label === undefined ? String(item) : item.label, String(item.value === undefined ? item : item.value)));
  select.value = value === undefined || value === null ? "" : String(value);
  if (select.value !== (value === undefined || value === null ? "" : String(value))) select.value = blank !== undefined ? "" : select.options[0].value;
}

function quickBuildGenres() {
  const box = $("quickGenres");
  box.innerHTML = "";
  for (const g of quick.choices.genres) {
    const card = document.createElement("div");
    card.className = "quick-card";
    const pick = document.createElement("button");
    pick.className = "quick-genre";
    pick.dataset.genre = g.value;
    pick.setAttribute("aria-pressed", String(g.value === quick.opts.genre));
    pick.textContent = g.label;
    pick.onclick = () => quickPickGenre(g.value);
    const play = document.createElement("button");
    play.className = "quick-preview";
    play.setAttribute("aria-label", t("Anteprima di {name}", { name: g.label }));
    play.textContent = "▶";
    play.onclick = () => quickPreview(g.value).catch(showError);
    card.append(pick, play);
    box.append(card);
  }
}

// letto subito a chi non vede: genere, atmosfera e durata scelti
function quickAnnounceChoice() {
  const genre = quick.choices.genres.find((g) => g.value === quick.opts.genre);
  const mood = quick.choices.moods.find((m) => m.value === quick.opts.mood);
  const dur = quick.choices.durations.find((d) => String(d.value) === String(quick.opts.duration));
  if (genre) $("quickAnnounce").textContent = t("Scelto: {genre}, atmosfera {mood}, durata {duration}.",
    { genre: genre.label, mood: mood ? mood.label : "", duration: dur ? dur.label : "" });
}

// Le atmosfere del genere scelto, e solo quelle (ogni genere ha le sue, vedi core/quicksong.py): se quella scelta non e' fra
// loro, si passa alla prima del genere
function quickFillMoods() {
  const g = genreData(quick.opts.genre);
  const items = g ? quick.choices.moods.filter((m) => g.moods.includes(m.value)) : quick.choices.moods;
  if (!items.some((m) => m.value === quick.opts.mood) && items.length) quick.opts.mood = items[0].value;
  quickFill($("quickMood"), items, quick.opts.mood);
}

// Le scelte che dipendono dalla ricetta del genere (organico, melodia, forma, metrica, tempo, stili delle parti) non passano a un
// altro genere: un punk non deve ereditare il flauto e il clarinetto dell'orchestra scelta per il brano di prima. Un organico
// diverso dalla ricetta si sceglie nei dettagli, per il brano che si sta facendo.
const QUICK_RECIPE_FIELDS = ["ensemble", "melody", "form", "meter", "bpm"];

function quickPickGenre(id) {
  if (quick.opts.genre !== id) {
    for (const f of QUICK_RECIPE_FIELDS) delete quick.opts[f];
    quick.parts = {};
    quickSyncRecipeFields();
  }
  quick.opts.genre = id;
  quickFillMoods();
  for (const b of document.querySelectorAll("#quickGenres .quick-genre")) b.setAttribute("aria-pressed", String(b.dataset.genre === id));
  quickDefaults();
  quickSave();
  quickAnnounceChoice();
}

// i campi dei dettagli tornano a «della ricetta» quando il genere cambia
function quickSyncRecipeFields() {
  for (const [id, name] of [["quickKey", "key"], ["quickMeter", "meter"], ["quickForm", "form"], ["quickEnsemble", "ensemble"], ["quickMelodyStyle", "melody"]]) {
    const el = $(id);
    if (el && !(name in quick.opts)) el.value = "";
  }
  if ($("quickBpm") && !("bpm" in quick.opts)) $("quickBpm").value = "";
}

// i valori che sceglie la ricetta, quando un campo e' vuoto
function quickDefaults() {
  const g = genreData(quick.opts.genre);
  if (!g) return;
  const hint = (id, text) => { $(id).setAttribute("placeholder", text); };
  hint("quickBpm", t("{n} (della ricetta)", { n: g.bpm }));
  for (const [id, blank] of [["quickKey", ""], ["quickMeter", g.meter], ["quickForm", g.form], ["quickEnsemble", g.ensemble], ["quickMelodyStyle", g.melody]]) {
    const first = $(id).options[0];
    if (first && first.value === "") first.textContent = blank ? t("{value} (della ricetta)", { value: quickLabelOf(id, blank) }) : t("della ricetta");
  }
}

function quickLabelOf(id, value) {
  const map = { quickMeter: null, quickForm: quick.choices.forms, quickEnsemble: quick.choices.ensembles, quickMelodyStyle: quick.choices.melodies };
  const list = map[id];
  if (!list) return String(value);
  const item = list.find((x) => x.value === value);
  return item ? item.label : String(value);
}

function quickBuildDetail() {
  const c = quick.choices, o = quick.opts;
  quickFill($("quickKey"), c.keys, o.key, t("della ricetta"));
  quickFill($("quickMeter"), c.meters, o.meter, t("della ricetta"));
  quickFill($("quickForm"), c.forms, o.form, t("della ricetta"));
  quickFill($("quickEnsemble"), c.ensembles, o.ensemble, t("della ricetta"));
  quickFill($("quickMelodyStyle"), c.melodies, o.melody, t("della ricetta"));
  quickFill($("quickEnding"), c.endings, o.ending || "cadenza");
  quickFill($("quickEnergy"), c.energies, o.energy, t("della ricetta"));
  $("quickBpm").value = o.bpm || "";
  $("quickModulation").checked = !!o.modulation;
  $("quickDensity").value = o.density === undefined ? 0.5 : o.density;
  $("quickHuman").value = o.human === undefined ? 1 : o.human;
  $("quickChords").value = o.chords || "";
  $("quickSeed").value = o.seed === undefined || o.seed === null ? "" : o.seed;
  $("quickSeconds").value = o.seconds || "";
  quickFill($("quickBars"), [8, 16, 32, 64].map((n) => ({ value: n, label: t("{n} battute", { n }) })), o.bars, t("a tempo"));
  $("quickLoop").checked = !!o.loop;
  $("quickCompact").checked = o.compact !== false;
  $("quickSecondVoice").checked = !!o.second_voice;
}

// Le scelte a mano dai campi (vuoto = la ricetta)
function quickReadFields() {
  const o = quick.opts;
  const set = (name, value) => { if (value === "" || value === undefined || value === null || value === false) delete o[name]; else o[name] = value; };
  set("key", $("quickKey").value);
  set("meter", $("quickMeter").value);
  set("form", $("quickForm").value);
  set("ensemble", $("quickEnsemble").value);
  set("melody", $("quickMelodyStyle").value);
  set("energy", $("quickEnergy").value);
  o.ending = $("quickEnding").value || "cadenza";
  const bpm = Math.round(Number($("quickBpm").value));
  set("bpm", bpm ? Math.min(240, Math.max(40, bpm)) : "");
  set("modulation", $("quickModulation").checked);
  o.density = Number($("quickDensity").value);
  set("human", Number($("quickHuman").value) === 1 ? "" : Number($("quickHuman").value));
  set("chords", $("quickChords").value.trim());
  const seed = $("quickSeed").value.trim();
  set("seed", seed !== "" && Number.isFinite(Number(seed)) && Number(seed) >= 0 ? Math.floor(Number(seed)) : "");
  const seconds = Math.round(Number($("quickSeconds").value));
  set("seconds", seconds > 0 ? Math.min(600, Math.max(5, seconds)) : "");
  set("bars", Number($("quickBars").value) || "");
  set("loop", $("quickLoop").checked);
  set("compact", $("quickCompact").checked ? "" : false);
  set("second_voice", $("quickSecondVoice").checked);
  o.duration = Number($("quickDuration").value) || o.duration || 60;
  o.mood = $("quickMood").value || o.mood;
}

function quickShowMode() {
  $("quickSimple").checked = quick.simple;
  $("quickDetail").hidden = quick.simple;
  $("quickPartsBox").hidden = quick.simple || !quick.last;
}

// ---- l'anteprima di un genere: quindici secondi, sempre gli stessi

async function quickPreview(genre) {
  const resumed = unlockInGesture();               // il tocco
  if (quick.previewing === genre) { quickStopPreview(); return; }
  quickStopPreview();
  const req = quick.previewReq;                    // se nel frattempo si ferma o si parte con altro, questa anteprima non parte
  const g = genreData(genre);
  quick.opts.genre = genre;
  quickPickGenre(genre);
  const mood = g.moods.includes($("quickMood").value) ? $("quickMood").value : g.moods[0];
  const key = `${genre}/${mood}`;
  setQuickStatus(t("Preparo l'anteprima…"));
  if (!quick.preview.has(key)) {
    const made = (await call("quick_song", { args: [{ genre, mood, duration: 15, seed: 1 }] })).result;
    quick.preview.set(key, (await call("preview", { text: made.text })).midi);
  }
  await resumed;
  if (!state.audioReady) state.audioReady = initAudio();
  await state.audioReady;
  if (req !== quick.previewReq) return;
  if (state.playing) await pause();
  stopPreview();
  const synth = state.synth, midi = quick.preview.get(key);
  await synth.resetPlayer();
  await synth.addSMFDataToPlayer(midi.slice().buffer);
  await synth.playPlayer();
  quick.previewing = genre;
  setQuickStatus(t("Anteprima: {name}", { name: g.label }));
  synth.waitForPlayerStopped().then(() => { if (quick.previewing === genre) { quick.previewing = null; setQuickStatus(""); } });
}

function quickStopPreview() {
  quick.previewReq = (quick.previewReq || 0) + 1;
  if (quick.previewing && state.synth) { state.synth.stopPlayer(); state.synth.midiAllSoundsOff(); }
  quick.previewing = null;
}

function setQuickStatus(text, error = false) {
  $("quickStatus").textContent = text;
  $("quickStatus").classList.toggle("error", error);
}

// ---- le parti (modo dettagliato)

function quickRenderParts() {
  const list = $("quickParts");
  list.innerHTML = "";
  const last = quick.last;
  if (!last) return;
  const labels = Object.fromEntries(quick.choices.parts.map((p) => [p.value, p.label]));
  const styleLists = { drums: quick.choices.styles.drums, bass: quick.choices.styles.bass, comp: quick.choices.styles.comp, comp2: quick.choices.styles.comp,
                       horn: quick.choices.styles.comp, pad: quick.choices.styles.comp, progression: quick.choices.styles.progression };
  for (const part of ["progression", ...last.parts]) {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.className = "tname";
    name.textContent = labels[part];
    if (last.choices.instruments[part]) {
      const small = document.createElement("small");
      small.textContent = last.choices.instruments[part].replace(/_/g, " ");
      name.append(small);
    }
    li.append(name);
    const lists = styleLists[part];
    if (lists) {
      const select = document.createElement("select");
      select.setAttribute("aria-label", t("Stile di {name}", { name: labels[part] }));
      const chosen = (quick.parts[part] && quick.parts[part].style) || "";
      select.add(new Option(t("della ricetta"), ""));
      for (const item of lists) select.add(new Option(item.label, item.value));
      select.value = chosen;
      select.onchange = () => { (quick.parts[part] = quick.parts[part] || {}).style = select.value || undefined; quickRegenerate("part", part).catch(showError); };
      li.append(select);
    }
    const lock = document.createElement("label");
    lock.className = "quick-lock";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = !!(quick.parts[part] && quick.parts[part].locked);
    box.setAttribute("aria-label", t("Blocca {name}", { name: labels[part] }));
    box.onchange = () => { (quick.parts[part] = quick.parts[part] || {}).locked = box.checked; };
    lock.append(box, document.createTextNode("🔒"));
    li.append(lock);
    const again = document.createElement("button");
    again.textContent = t("Un'altra");
    again.setAttribute("aria-label", t("Un'altra {name}", { name: labels[part] }));
    again.onclick = () => quickRegenerate("part", part).catch(showError);
    li.append(again);
    const crea = document.createElement("button");
    crea.textContent = t("Apri in Crea");
    crea.setAttribute("aria-label", t("Apri {name} in Crea", { name: labels[part] }));
    crea.onclick = () => quickOpenPartInCrea(part).catch(showError);
    if (CREA_KIND[part]) li.append(crea);
    list.append(li);
  }
}

// ---- «Apri in Crea»: una parte del brano generato, con stile, strumento e seme, per lavorarci a fondo

const CREA_KIND = { progression: "progression", drums: "drums", bass: "bass", comp: "comping", comp2: "comping", horn: "comping", pad: "comping" };

async function quickOpenPartInCrea(part) {
  const kind = CREA_KIND[part], made = quick.last;
  if (!kind || !made) return;
  await loadGenChoices();
  const style = (quick.parts[part] && quick.parts[part].style) || (made.choices && made.choices.styles && made.choices.styles[part]) || "";
  const instrument = made.choices && made.choices.instruments && made.choices.instruments[part];
  const values = { ...genDefaults(kind), bars: made.bars };
  if (style) values.style = style;
  if (instrument && kind !== "drums" && kind !== "progression") values.instrument = instrument;
  if (kind === "progression") values.key = made.key;
  gen.values[kind] = values;
  const seed = made.seeds && made.seeds[part];
  if (seed != null) gen.seeds[kind] = seed;
  quickClose();
  setView("crea");
  $("genFollow").checked = false;                  // la parte com'e' nel brano, non spezzata per sezioni
  await setGenKind(kind);
  const message = t("{name} aperta in Crea: stile, strumento e seme sono quelli del brano.", { name: (quick.choices.parts.find((p) => p.value === part) || {}).label || part });
  $("genStatus").textContent = message;
  announce(message);
}

// ---- stili personali del computer

async function quickInstallStyles(json) {
  const names = (await call("install_user_styles", { args: [json || ""] })).result;
  const total = Object.values(names).reduce((n, l) => n + l.length, 0);
  $("quickStylesInfo").textContent = total ? t("Stili personali: {n}.", { n: total }) + " " + Object.entries(names).filter(([, l]) => l.length).map(([k, l]) => `${k}: ${l.join(", ")}`).join(" · ") : "";
  $("quickStylesClear").hidden = !total;
  return total;
}

async function quickStylesFromStorage() {
  let json = "";
  try { json = localStorage.getItem(QUICK_STYLES_KEY) || ""; } catch (e) {}
  if (!json) return;
  try { await quickInstallStyles(json); } catch (e) { /* un file rovinato: si ignora */ }
}

async function quickImportStyles(file) {
  try {
    const json = await file.text();
    const total = await quickInstallStyles(json);
    try { localStorage.setItem(QUICK_STYLES_KEY, json); } catch (e) {}
    quick.choices = (await call("quick_choices")).result;                   // gli stili nuovi nelle liste
    quickSyncControls();
    setQuickStatus(total ? t("Stili personali importati: {n}.", { n: total }) : t("Nel file non ci sono stili."));
  } catch (e) {
    setQuickStatus(shortError(e), true);
  }
}

async function quickClearStyles() {
  try { localStorage.removeItem(QUICK_STYLES_KEY); } catch (e) {}
  await quickInstallStyles("");
  quick.choices = (await call("quick_choices")).result;
  quickSyncControls();
  setQuickStatus(t("Stili personali tolti."));
}

// ---- le tracce da cui partire con una melodia

function quickFillIdeaTracks() {
  const select = $("quickIdeaTrack");
  select.replaceChildren();
  const tracks = state.song ? state.song.info.tracks.filter((tr) => !tr.percussion) : [];
  for (const tr of tracks) select.add(new Option(tr.name, tr.name));
  $("quickIdea").disabled = !tracks.length;
  if (!tracks.length) select.add(new Option(t("nessuna: apri un brano con una melodia"), ""));
}

// ---- generare

// Le opzioni per il motore: le scelte a mano, la durata e i semi (le parti bloccate tengono il loro)
function quickEngineOptions(seedFor) {
  const o = { ...quick.opts };
  if (quick.simple) {                              // nella modalita' semplificata i dettagli (nascosti) non contano: vale la ricetta
    for (const k of Object.keys(o)) if (!["genre", "mood", "duration", "seed"].includes(k)) delete o[k];
  }
  const duration = o.seconds || o.duration;
  delete o.seconds;
  o.duration = o.bars || o.loop ? undefined : duration;
  const parts = {};
  for (const [part, spec] of Object.entries(quick.parts)) {
    if (spec.style) parts[part] = { ...(parts[part] || {}), style: spec.style };
    if (spec.locked && spec.seed !== undefined) parts[part] = { ...(parts[part] || {}), seed: spec.seed };
  }
  Object.assign(o, seedFor(parts));
  o.parts = parts;
  return o;
}

// mode: "new" (un brano nuovo), "again" (un'altra: nuovi semi tranne le parti bloccate), "part" (cambia una parte sola),
// "surprise" (una combinazione a caso fra quelle ammesse)
async function quickRegenerate(mode, part) {
  if (quick.busy) return;
  quick.busy = true;
  const resumed = unlockInGesture();               // il tocco: niente await prima (iOS)
  const tap = performance.now();
  quickStopPreview();
  quickReadFields();
  setQuickStatus(t("Compongo…"));
  for (const b of document.querySelectorAll("#quickDialog button")) b.disabled = true;
  try {
    if (mode === "surprise") {
      const pick = (await call("quick_surprise")).result;
      Object.assign(quick.opts, pick);
      delete quick.opts.seed;
      quick.parts = {};
      quickSyncControls();
    }
    // «Un'altra» e «Sorprendimi» vogliono sempre un brano diverso: un seme rimasto nel campo (o salvato da un brano aperto) non vale.
    // Solo «Crea» e «Parti da questa melodia» usano il seme scritto a mano, per rifare lo stesso brano.
    if (mode === "again" || mode === "surprise") { delete quick.opts.seed; $("quickSeed").value = ""; }
    const fresh = mode === "new" || mode === "again" || mode === "surprise" || mode === "idea";
    const options = quickEngineOptions((parts) => {
      if (mode === "part" && quick.last) {
        // una parte sola: tutte le altre tengono il seme di prima, e questa ne prende uno nuovo
        for (const p of ["progression", ...quick.last.parts]) {
          parts[p] = { ...(parts[p] || {}), seed: p === part ? Math.floor(Math.random() * 2 ** 31) : quick.last.seeds[p] };
        }
        return { seed: quick.last.seed };
      }
      return fresh && quick.opts.seed === undefined ? { seed: Math.floor(Math.random() * 2 ** 31) } : {};
    });
    // una melodia come punto di partenza: «Parti da questa melodia» (idea) e, dopo, «Un'altra» e le parti la tengono
    if (mode === "idea") quick.ideaSource = { text: state.doc.text, track: $("quickIdeaTrack").value };
    else if (mode === "new" || mode === "surprise") quick.ideaSource = null;
    const made = quick.ideaSource
      ? (await call("quick_from_melody", { args: [quick.ideaSource.text, quick.ideaSource.track, options] })).result
      : (await call("quick_song", { args: [options] })).result;
    await resumed;
    quick.last = made;
    for (const p of Object.keys(made.seeds)) (quick.parts[p] = quick.parts[p] || {}).seed = made.seeds[p];
    const composed = performance.now();
    await quickSaveSong(made);
    quickShowResult(made);
    await play();
    Metrics.record("brano_veloce", { genre: made.genre, mood: made.mood, mode, seed: made.seed, bars: made.bars, seconds: made.seconds,
                                     composed_ms: Math.round(composed - tap), to_sound_ms: Math.round(performance.now() - tap) });
  } catch (e) {
    setQuickStatus(shortError(e), true);
  } finally {
    for (const b of document.querySelectorAll("#quickDialog button")) b.disabled = false;
    quick.busy = false;
  }
}

// Il brano si salva la prima volta e poi si aggiorna: «Un'altra» non riempie la lista
async function quickSaveSong(made) {
  let song = quick.songId ? await Songs.get(quick.songId) : null;
  const source = "brano in 60 secondi, seme " + made.seed;
  if (!song) {
    song = await Songs.create({ name: await Songs.freeName(made.name), text: made.text, source });
    quick.songId = song.id;
  } else {
    song.text = made.text;
    song.source = source;
    if (song.name === quick.lastName) song.name = await Songs.freeName(made.name);   // il nome che gli avevo dato io, non quello dell'utente
    await Songs.put(song);
  }
  quick.lastName = song.name;
  await openSong(song.id, false);
  if (made.loop) {                                   // un loop suona senza fine
    state.loop = { a: 0, b: state.timeline.length, on: true };
    renderLoop();
  }
}

function quickShowResult(made) {
  const parts = [made.name, formatClock(made.seconds), made.key.replace(/m$/, " " + t("minore")), t("{n} BPM", { n: made.bpm }),
                 made.meter, t("{n} battute", { n: made.sections.reduce((n, s) => n + s.bars, 0) })];
  $("quickSummary").textContent = parts.join(" · ");
  $("quickFallback").textContent = made.fallback || "";
  $("quickFallback").hidden = !made.fallback;
  $("quickResult").hidden = false;
  if (typeof renderSoundsInUse === "function") renderSoundsInUse();     // «Suoni: ...» sotto il riepilogo
  quickShowMode();
  quickRenderParts();
  setQuickStatus(made.fallback ? "" : t("Pronto: {name}", { name: made.name }));
  $("quickDuration").value = String(quick.opts.duration);
  quickAnnounce(made);
}

// letto da chi non vede: genere e atmosfera scelti, durata vera, brano pronto
function quickAnnounce(made) {
  $("quickAnnounce").textContent = t("{name}, durata {clock}. Il brano è pronto.", { name: made.name, clock: formatClock(made.seconds) });
}

function quickSyncControls() {
  quickFillMoods();
  quickFill($("quickDuration"), quick.choices.durations, quick.opts.duration);
  for (const b of document.querySelectorAll("#quickGenres .quick-genre")) b.setAttribute("aria-pressed", String(b.dataset.genre === quick.opts.genre));
  quickBuildDetail();
  quickDefaults();
}

// «Parti da questo brano»: le scelte salvate nel brano aperto tornano nella finestra
async function quickFromDoc() {
  if (!state.doc) return;
  const saved = (await call("quick_read", { args: [state.doc.text] })).result;
  if (!saved) { setQuickStatus(t("Questo brano non è stato fatto da «Un brano in 60 secondi»."), true); return; }
  quick.opts = { genre: saved.genre, mood: saved.mood, duration: quick.opts.duration || 60, key: saved.key, bpm: saved.bpm, meter: saved.meter,
                 form: saved.form, ensemble: saved.ensemble, melody: saved.melody, ending: saved.ending, modulation: saved.modulation,
                 density: saved.density, chords: saved.chords || "", bars: saved.bars, loop: saved.loop, seed: saved.seed };
  quick.parts = {};
  for (const [p, seed] of Object.entries(saved.seeds || {})) quick.parts[p] = { seed, style: (saved.styles || {})[p], locked: false };
  quick.songId = null;
  quick.simple = false;
  quickSyncControls();
  quickShowMode();
  quickSave();
  setQuickStatus(t("Le scelte del brano sono qui: cambiale e crea."));
}

// ---- la finestra

async function openQuick() {
  const dialog = $("quickDialog");
  setQuickStatus("");
  dialog.showModal();
  await state.booted;
  if (!quick.choices) {
    quick.choices = (await call("quick_choices")).result;
    quickLoad();
    quickBuildGenres();
  }
  quick.songId = null;
  quick.last = null;
  quick.parts = {};
  quick.ideaSource = null;
  quickFillIdeaTracks();
  $("quickResult").hidden = true;
  quickSyncControls();
  quickShowMode();
  $("quickMake").disabled = false;
}

function quickClose() {
  quickStopPreview();
  quickReadFields();
  quickSave();
  $("quickDialog").close();
}

function setupQuick() {
  $("quickSong").onclick = () => openQuick().catch(showError);
  $("quickMake").onclick = () => quickRegenerate("new");
  $("quickAgain").onclick = () => quickRegenerate("again");
  $("quickSurprise").onclick = () => quickRegenerate("surprise");
  $("quickClose").onclick = quickClose;
  $("quickPlay").onclick = () => play();
  $("quickOpenCrea").onclick = () => { quickClose(); setView("crea"); };
  $("quickFromDoc").onclick = () => quickFromDoc().catch(showError);
  $("quickIdea").onclick = () => quickRegenerate("idea");
  $("quickStylesFile").onchange = (ev) => { const f = ev.target.files[0]; ev.target.value = ""; if (f) quickImportStyles(f); };
  $("quickStylesClear").onclick = () => quickClearStyles().catch(showError);
  state.booted && state.booted.then(() => quickStylesFromStorage()).catch(() => {});
  $("quickSimple").onchange = () => { quickReadFields(); quick.simple = $("quickSimple").checked; quickShowMode(); quickSave(); };
  $("quickMood").onchange = () => { quick.opts.mood = $("quickMood").value; quickSave(); quickAnnounceChoice(); };
  $("quickDuration").onchange = () => { quick.opts.duration = Number($("quickDuration").value); quickSave(); quickAnnounceChoice(); };
  for (const id of ["quickKey", "quickMeter", "quickForm", "quickEnsemble", "quickMelodyStyle", "quickEnding", "quickEnergy", "quickBpm", "quickModulation",
                    "quickDensity", "quickHuman", "quickChords", "quickSeed", "quickSeconds", "quickBars", "quickLoop", "quickCompact", "quickSecondVoice"]) {
    $(id).addEventListener("change", () => { quickReadFields(); quickSave(); });
  }
}
