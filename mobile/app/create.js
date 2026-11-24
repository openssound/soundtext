// SoundText Mobile: le schermate Crea e Trasforma. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ crea
//
// Giro armonico, batteria, basso e accompagnamento con i generatori di
// SoundText (engine.generate nel worker, gli stessi risultati delle
// finestre «Genera ...» del computer). Ogni modifica rigenera la parte (con
// lo stesso seme: «Un'altra» ne sceglie uno nuovo) e, se si sta ascoltando,
// l'anteprima riparte con la parte nuova. «Aggiungi al brano» mette la
// parte in una traccia nuova in fondo al file.

const gen = {
  kind: "progression",
  choices: null, choicesFor: null,   // engine.generator_choices del testo del brano
  values: {},                        // per generatore: i valori dei campi
  seeds: {},                         // per generatore: il seme
  text: "", textFor: "",             // ultima parte generata e per quali valori
  timer: null, busy: null,
  sections: null,                    // engine.structure_sections: le sezioni del brano, se ce ne sono
  intensities: {},                   // intensita' scelte per sezione (indice -> livello)
  arranged: null,                    // l'ultimo risultato di engine.arrange_song, per «Aggiungi»
};
const GEN_INTENSITY_LABELS = () => ({ intro: t("Intro"), light: t("Leggera"), normal: t("Normale"), build: t("Cresce"), full: t("Piena"),
                                       outro: t("Finale"), stop: t("Stop"), break: t("Break") });

// I campi di ogni generatore: [nome, tipo, etichetta, opzioni]. Le etichette
// sono quelle delle finestre di SoundText.
function genFields(kind) {
  const c = gen.choices;
  const opts = (list) => list.map((o) => [o.value, o.label]);
  const variability = ["variability", "range", t("Variabilità:")];
  const swing = ["swing", "swing", t("Swing (50 = dritto, 66 = terzinato):")];
  const bars = ["bars", "number", t("Battute:")];
  const intensity = ["intensity", "select", t("Intensità:"), opts(c.intensities)];
  const sources = c.sources.map((n) => [n, n]);
  const instruments = (k) => c.instruments[k].map((n) => [n, n]);
  if (kind === "progression") {
    const mode = /m$/.test(gen.values.progression?.key || c.key) ? "minor" : "major";
    return [
      ["key", "select", t("Tonalità:"), c.keys.map((k) => [k, k])],
      ["style", "select", t("Stile:"), opts(c.progression.filter((p) => p.mode === mode))],
      ["chord_bars", "select", t("Durata di ogni accordo:"), opts(c.chord_durations)],
      ["bars", "number", t("Battute (0 = un giro):")], ["instrument", "select", t("Strumento:"), instruments("progression")], variability,
      ["ending", "check", t("Cadenza finale")],
    ];
  }
  if (kind === "drums") {
    return [
      ["style", "select", t("Stile:"), opts(c.drums)], bars, intensity, variability,
      ["phrase_fills", "check", t("Fill a frasi")], ["ending", "check", t("Finale sull'ultima battuta")],
    ];
  }
  const common = [["source", "select", t("Accordi da:"), sources]];
  if (kind === "bass") {
    return [...common,
      ["style", "select", t("Stile:"), opts(c.bass)], ["instrument", "select", t("Strumento:"), instruments("bass")],
      bars, intensity, variability, swing,
      ["kick_track", "select", t("Segui la cassa di:"), [["", t("nessuna")], ...c.kick_tracks.map((n) => [n, n])]],
      ["performance", "check", t("Esecuzione dello strumento")],
    ];
  }
  return [...common,
    ["style", "select", t("Stile:"), opts(c.comping)], ["instrument", "select", t("Strumento:"), instruments("comping")],
    bars, intensity, variability, swing,
    ["voice_leading", "check", t("Rivolti vicini")], ["symbols", "check", t("Accordi come simboli")], ["performance", "check", t("Esecuzione dello strumento")],
  ];
}

function genDefaults(kind) {
  const c = gen.choices;
  const songBars = c.bars > 0 ? Math.min(64, c.bars) : 8;
  const base = { variability: 35, intensity: "normal", swing: 50 };
  if (kind === "progression") {
    const mode = /m$/.test(c.key) ? "minor" : "major";
    return { ...base, key: c.key, style: c.progression.find((p) => p.mode === mode).value, chord_bars: 1,
             bars: 0, instrument: c.instruments.progression[0], ending: false };
  }
  if (kind === "drums") return { ...base, style: c.drums[0]?.value, bars: songBars, phrase_fills: true, ending: false };
  const source = c.sources[c.sources.length - 1] || "";
  if (kind === "bass") {
    return { ...base, source, style: c.bass[0].value, instrument: c.instruments.bass[0], bars: songBars,
             kick_track: "", performance: false };
  }
  return { ...base, source, style: c.comping[0].value, instrument: c.instruments.comping[0], bars: songBars,
           voice_leading: true, symbols: true, performance: false };
}

// Le parti seguono le sezioni del brano? (solo batteria, basso e accompagnamento, e se il brano ha sezioni)
function followActive() {
  return !!(gen.sections && gen.sections.sections.length && $("genFollow").checked && ["drums", "bass", "comping"].includes(gen.kind));
}

function arrangeOptions(parts) {
  const out = { parts, intensities: gen.intensities, replace: true };
  const d = gen.values.drums, b = gen.values.bass, c = gen.values.comping;
  const variability = (gen.values[parts.length === 1 ? parts[0] : "comping"] || { variability: 35 }).variability / 100;
  out.variability = variability;
  if (d && d.style) out.drum_style = d.style;
  if (b) { out.bass_style = b.style; out.bass_instrument = b.instrument; }
  if (c) { out.comping_style = c.style; out.comping_instrument = c.instrument; }
  const kind = parts.length === 1 ? parts[0] : null;
  if (kind && gen.seeds[kind] != null) out.seed = gen.seeds[kind];
  const swung = (kind ? [gen.values[kind]] : [c, b]).filter(Boolean).map((x) => Number(x.swing) || 50);
  const swing = Math.max(50, ...swung);                         // basso e accompagnamento: la batteria resta com'e'
  if (swing > 50) out.swing = swing;
  return out;
}

// La curva dell'energia (come core.quicksong.energy_levels): il livello di ogni sezione mobile, da leggero a pieno
function energyLevels(curve, count) {
  return Array.from({ length: count }, (_, pos) => {
    const e = count > 1 ? pos / (count - 1) : 1;
    const height = curve === "sale" ? e : curve === "cala" ? 1 - e : 1 - Math.abs(e - 0.7) / 0.7;
    return height < 0.34 ? "light" : height < 0.67 ? "normal" : "full";
  });
}

function applyEnergyCurve() {
  const curve = $("genEnergy").value;
  if (!curve || !gen.sections) return;
  const fixed = ["intro", "outro", "stop", "break"];
  const rows = [...$("genSections").children].map((li, i) => ({ li, section: gen.sections.sections[i] }))
    .filter((r) => !fixed.includes(r.li.querySelector("select").value));
  energyLevels(curve, rows.length).forEach((level, k) => {
    const { li, section } = rows[k];
    li.querySelector("select").value = level;
    gen.intensities[section.index] = level;
  });
  gen.textFor = "";
  scheduleGenerate(0);
}

async function loadSections() {
  const text = state.doc ? state.doc.text : "";
  if (gen.sectionsFor === text) return;
  gen.sections = (await call("structure_sections", { args: [text] })).result;
  gen.sectionsFor = text;
  gen.intensities = {};
  const energy = $("genEnergy");
  if (!energy.options.length) {
    energy.add(new Option(t("a mano"), ""));
    energy.add(new Option(t("sale"), "sale"));
    energy.add(new Option(t("sale e poi cala"), "picco"));
    energy.add(new Option(t("cala"), "cala"));
    energy.onchange = applyEnergyCurve;
  }
  energy.value = "";
  const list = $("genSections"), preview = $("genPreviewSection");
  list.replaceChildren();
  preview.replaceChildren(new Option(t("tutto il brano"), ""));
  const labels = GEN_INTENSITY_LABELS();
  for (const s of gen.sections.sections) {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = `${s.name || t("(senza nome)")} · ${s.bars === 1 ? t("1 battuta") : t("{n} battute", { n: s.bars })}`;
    const select = document.createElement("select");
    select.setAttribute("aria-label", t("Intensità di {name}", { name: s.name }));
    for (const [value, label] of Object.entries(labels)) select.add(new Option(label, value));
    select.value = s.intensity;
    select.onchange = () => { gen.intensities[s.index] = select.value; gen.textFor = ""; scheduleGenerate(0); };
    li.append(name, select);
    list.append(li);
    preview.add(new Option(s.name || t("sezione {n}", { n: s.index + 1 }), String(s.index)));
  }
}

function renderFollowBox() {
  const has = !!(gen.sections && gen.sections.sections.length) && gen.kind !== "progression";
  $("genStructure").hidden = !has;
  $("genFollowBox").hidden = !has || !$("genFollow").checked;
  const exists = gen.sections && gen.sections.tracks && followActive() && gen.sections.tracks.includes(gen.kind === "drums" ? "Drums" : (gen.values[gen.kind] || {}).instrument);
  $("genAdd").textContent = exists ? t("Sostituisci la traccia") : t("Aggiungi al brano");
}

async function loadGenChoices() {
  const text = state.doc ? state.doc.text : "";
  if (gen.choices && gen.choicesFor === text) return;
  await state.booted;
  const c = (await call("generator_choices", { args: [text] })).result;
  gen.choices = c;
  gen.choicesFor = text;
  // i valori restano, ma la sorgente degli accordi deve esistere ancora
  for (const kind of Object.keys(gen.values)) {
    const v = gen.values[kind];
    if ("source" in v && !c.sources.includes(v.source)) v.source = c.sources[c.sources.length - 1] || "";
    if (v.kick_track && !c.kick_tracks.includes(v.kick_track)) v.kick_track = "";
  }
}

async function showCrea() {
  if (!document.body.classList.contains("view-crea")) return;
  const first = !gen.choices;
  if (first) $("genStatus").textContent = t("Carico…");
  try {
    await loadGenChoices();
  } catch (e) {
    $("genStatus").textContent = shortError(e);
    return;
  }
  if (first) $("genStatus").textContent = "";
  try { await loadSections(); } catch (e) { gen.sections = null; }
  renderGenForm();
  // l'accompagnamento non puo' avere lo strumento della traccia degli accordi (e' la sorgente, non si sostituisce)
  const chordTrack = gen.sections && gen.sections.track, comp = gen.values.comping;
  if (chordTrack && comp && comp.instrument === chordTrack && gen.choices) {
    comp.instrument = gen.choices.instruments.comping.find((n) => n !== chordTrack) || comp.instrument;
    if (gen.kind === "comping") renderGenForm();
  }
  renderFollowBox();
  scheduleGenerate(0);
}

async function setGenKind(kind) {
  if (state.previewing) stopPreview();
  gen.kind = kind;
  for (const b of document.querySelectorAll(".gentabs button")) {
    b.setAttribute("aria-selected", String(b.dataset.gen === kind));
  }
  $("genStatus").textContent = "";
  await showCrea();
}

function renderGenForm() {
  const kind = gen.kind;
  const form = $("genForm");
  form.replaceChildren();
  if (!gen.choices) return;
  const values = gen.values[kind] || (gen.values[kind] = genDefaults(kind));
  for (const [name, type, label, options] of genFields(kind)) {
    const id = `gen-${name}`;
    let input;
    if (type === "select") {
      input = document.createElement("select");
      for (const [value, text] of options) input.add(new Option(text, String(value)));
      if (!options.some(([v]) => String(v) === String(values[name])) && options.length) values[name] = options[0][0];
      input.value = String(values[name] ?? "");
    } else if (type === "number") {
      input = document.createElement("input");
      input.type = "number";
      input.min = kind === "progression" ? "0" : "1";
      input.max = "256";
      input.inputMode = "numeric";
      input.value = String(values[name]);
    } else if (type === "swing") {
      input = document.createElement("input");
      input.type = "range";
      input.min = "50"; input.max = "80"; input.step = "1";
      input.value = String(values[name] ?? 50);
      input.setAttribute("aria-valuetext", String(values[name] ?? 50));
    } else if (type === "range") {
      input = document.createElement("input");
      input.type = "range";
      input.min = "0"; input.max = "100"; input.step = "5";
      input.value = String(values[name]);
      input.setAttribute("aria-valuetext", values[name] + "%");
    } else {
      input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !!values[name];
    }
    input.id = id;
    input.name = name;
    const lab = document.createElement("label");
    lab.htmlFor = id;
    lab.textContent = type === "range" ? `${label} ${values[name]}%` : type === "swing" ? `${label} ${values[name] ?? 50}` : label;
    if (type === "check") {
      const row = document.createElement("label");
      row.className = "check";
      row.append(input, " ", label);
      form.append(row);
    } else {
      form.append(lab, input);
    }
    const update = () => {
      let v = type === "check" ? input.checked : input.value;
      if (type === "number" || type === "range" || type === "swing") v = Number(v);
      if (name === "chord_bars") v = Number(v);
      values[name] = v;
      if (type === "range") { lab.textContent = `${label} ${v}%`; input.setAttribute("aria-valuetext", v + "%"); }
      if (type === "swing") { lab.textContent = `${label} ${v}`; input.setAttribute("aria-valuetext", String(v)); }
      if (name === "key") { renderGenForm(); }     // gli stili seguono il modo della tonalita'
      scheduleGenerate(type === "range" || type === "number" || type === "swing" ? 250 : 0);
    };
    input.addEventListener(type === "range" || type === "number" || type === "swing" ? "input" : "change", update);
  }
  if (kind !== "progression" && kind !== "drums" && !gen.choices.sources.length) {
    $("genStatus").textContent = t("Nel brano non c'è ancora una traccia con degli accordi da seguire.");
  }
}

// Le opzioni per engine.generate dai valori dei campi
function genOptions(kind) {
  const v = { ...gen.values[kind] };
  const out = { ...v, variability: v.variability / 100, seed: gen.seeds[kind] ?? null, track: t("Nuova traccia") };
  if (out.kick_track === "") delete out.kick_track;
  if (out.source === "") delete out.source;
  delete out.instrument;
  if (kind === "bass" || kind === "comping") out.instrument = v.instrument;
  return out;
}

function scheduleGenerate(delay = 150) {
  clearTimeout(gen.timer);
  gen.timer = setTimeout(() => generatePart().catch(showError), delay);
}

async function generatePart() {
  if (!state.doc || !gen.choices) return;
  const kind = gen.kind;
  const options = genOptions(kind);
  const key = JSON.stringify([state.doc.text, kind, options]);
  if (key === gen.textFor && gen.text) return gen.text;
  const status = $("genStatus");
  if (followActive()) return generateArranged(kind, key);
  gen.arranged = null;
  let r;
  try {
    r = (await call("generate", { args: [state.doc.text, kind, options] })).result;
  } catch (e) {
    if (gen.kind !== kind) return null;
    gen.text = "";
    gen.textFor = "";
    $("genText").textContent = "";
    status.textContent = errorText(e);
    $("genAdd").disabled = true;
    return null;
  }
  if (gen.kind !== kind || JSON.stringify([state.doc.text, kind, genOptions(kind)]) !== key) return null;  // superata
  gen.seeds[kind] = r.seed;
  gen.text = r.text;
  gen.textFor = JSON.stringify([state.doc.text, kind, genOptions(kind)]);
  $("genText").textContent = r.text;
  status.textContent = "";
  $("genAdd").disabled = false;
  if (state.previewing) listenToPart(true).catch(showError);    // l'anteprima segue le modifiche
  return r.text;
}

// Le parti come un box per sezione (engine.arrange_song): il testo mostrato e' quello dei box nuovi
async function generateArranged(kind, key) {
  const status = $("genStatus");
  const parts = [kind];
  let r;
  try {
    r = (await call("arrange_song", { args: [state.doc.text, arrangeOptions(parts)] })).result;
  } catch (e) {
    if (gen.kind !== kind) return null;
    gen.text = ""; gen.textFor = ""; gen.arranged = null;
    $("genText").textContent = "";
    status.textContent = errorText(e);
    $("genAdd").disabled = true;
    return null;
  }
  if (gen.kind !== kind) return null;
  gen.arranged = r;
  gen.seeds[kind] = r.seed;
  const name = r.tracks[0];
  const shown = (r.text.match(new RegExp(`^Box ${name} "[^\\n]*\\|[0-9.]+:\\n(?:[ \\t][^\\n]*\\n?)*`, "gm")) || []).join("\n");
  gen.text = shown;
  gen.textFor = key;
  $("genText").textContent = shown;
  status.textContent = t("{n} box, uno per sezione.", { n: (shown.match(/^Box /gm) || []).length });
  $("genAdd").disabled = false;
  if (state.previewing) listenToPart(true).catch(showError);
  return shown;
}

// Strumento e nome della traccia nuova
function genTrack(kind) {
  const v = gen.values[kind];
  if (kind === "drums") return { instrument: "Drums", name: null };
  if (kind === "progression") return { instrument: v.instrument, name: t("Accordi") };
  return { instrument: v.instrument, name: null };
}

// Il brano con la parte nuova in fondo
async function songWithPart() {
  if (followActive()) {
    await generatePart();
    if (!gen.arranged) throw new Error(errorText($("genStatus").textContent || t("Niente da aggiungere")));
    return { text: gen.arranged.text, name: gen.arranged.tracks[0] };
  }
  const part = await generatePart() || gen.text;
  if (!part) throw new Error(errorText($("genStatus").textContent || t("Niente da aggiungere")));
  const { instrument, name } = genTrack(gen.kind);
  return (await call("add_track", { args: [state.doc.text, instrument, part, name] })).result;
}

// ▶ Ascolta: il brano con la parte nuova, dall'inizio (o dal punto in cui
// era l'anteprima, se si sta rigenerando mentre suona)
async function listenToPart(again = false) {
  if (!again && state.previewing) { stopPreview(); return; }
  const resumed = again ? null : unlockInGesture();
  if (resumed) await resumed;
  const song = await songWithPart();
  const r = await call("preview", { text: song.text });
  let midi = r.midi;
  const from = $("genPreviewSection").value;
  if (followActive() && from !== "" && gen.sections.sections[Number(from)]) {          // una sezione sola: dal suo inizio
    midi = MidiCut.from(new Uint8Array(midi), Math.round(gen.sections.sections[Number(from)].beat * TICKS_PER_BEAT));
  }
  await playPreview(midi);
}

async function addPartToSong() {
  if (!state.doc) return;
  if (state.previewing) stopPreview();
  const { text, name } = await songWithPart();
  gen.undo = { before: state.doc.text, after: text };          // «Annulla l'aggiunta»
  await replaceDocText(text);
  $("genUndo").hidden = false;
  // Si resta in Crea, pronti per la parte dopo (giro -> batteria -> basso ->
  // accompagnamento): la traccia nuova si vede nel Testo e si sente con Play.
  const done = t("Traccia «{name}» aggiunta al brano", { name });
  setStatus(done);
  const order = GENERATOR_ORDER;
  const next = order[order.indexOf(gen.kind) + 1];
  gen.choices = null;                    // le tracce sono cambiate: nuove sorgenti di accordi
  gen.textFor = "";
  gen.sectionsFor = "";
  if (next) await setGenKind(next); else await showCrea();
  $("genStatus").textContent = done;
}

// «Arrangia tutto»: batteria, basso e accompagnamento su tutte le sezioni, in un tocco
async function arrangeAll() {
  if (!state.doc || !gen.sections || !gen.sections.sections.length) return;
  if (state.previewing) stopPreview();
  const status = $("genStatus");
  status.textContent = t("Arrangio il brano…");
  const options = arrangeOptions(["drums", "bass", "comping"]);
  options.replace = false;
  let r;
  try {
    r = (await call("arrange_song", { args: [state.doc.text, options] })).result;
  } catch (e) {
    if (!/c'è già|already|existe/i.test(errorText(e))) { status.textContent = errorText(e); return; }
    const names = ["Drums", options.bass_instrument || "Bass", options.comping_instrument || "Piano"].filter((n) => gen.sections.tracks.includes(n));
    if (!confirm(t("Sostituire le tracce {names}?", { names: names.join(", ") }))) { status.textContent = ""; return; }
    options.replace = true;
    try { r = (await call("arrange_song", { args: [state.doc.text, options] })).result; } catch (e2) { status.textContent = errorText(e2); return; }
  }
  gen.undo = { before: state.doc.text, after: r.text };
  await replaceDocText(r.text);
  $("genUndo").hidden = false;
  gen.choices = null; gen.textFor = ""; gen.sectionsFor = "";
  await showCrea();
  const done = t("Brano arrangiato: {names}.", { names: r.tracks.join(", ") });
  $("genStatus").textContent = done;
  setStatus(done);
  announce(done);
}

const GENERATOR_ORDER = ["progression", "drums", "bass", "comping"];

function setupCrea() {
  $("genForm").addEventListener("submit", (ev) => ev.preventDefault());   // niente invio: i campi rigenerano la parte
  for (const b of document.querySelectorAll(".gentabs button")) b.onclick = () => setGenKind(b.dataset.gen).catch(showError);
  $("genAgain").onclick = () => { gen.seeds[gen.kind] = null; gen.textFor = ""; scheduleGenerate(0); };
  $("genListen").onclick = () => listenToPart().catch(showError);
  $("genAdd").onclick = () => addPartToSong().catch(showError);
  $("genFollow").onchange = () => { renderFollowBox(); gen.textFor = ""; scheduleGenerate(0); };
  $("genPreviewSection").onchange = () => { if (state.previewing) listenToPart(true).catch(showError); };
  $("genArrangeAll").onclick = () => arrangeAll().catch(showError);
  $("genUndo").onclick = async () => {
    const u = gen.undo;
    $("genUndo").hidden = true;
    if (!u || !state.doc || state.doc.text !== u.after) { setStatus(t("Il brano è cambiato dopo l'aggiunta: non si può annullare da qui.")); return; }
    gen.undo = null;
    await replaceDocText(u.before);
    gen.choices = null; gen.textFor = "";
    await showCrea();
    setStatus(t("Aggiunta annullata"));
    announce(t("Aggiunta annullata"));
  };
}

// ------------------------------------------------------------ trasforma
//
// La finestra Trasforma di SoundText sul richiamo di pattern sotto il
// cursore (%Tema, %Tema.invert...): la catena di funzioni si scrive nel
// campo o si allunga con «Aggiungi una funzione»; a ogni modifica il
// motore dice cosa suona passo per passo, nel punto del brano dove sta
// (engine.transform_preview), e mostra prima e dopo in una piccola
// partitura da ascoltare. «Sostituisci» scrive il richiamo nuovo,
// «Scrivi le note» lo scrive per esteso nota per nota.

const tf = { pos: 0, text: "", result: null, timer: null };

function base64Bytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function openTransform() {
  if (!state.doc) return;
  const pos = caretPos() ?? 0;
  const ref = (await call("transform_at", { args: [state.doc.text, pos] })).result;
  if (!ref) { setStatus(t("Metti il cursore su un richiamo di pattern (%Nome).")); return; }
  tf.pos = pos;
  tf.text = state.doc.text;
  tf.result = null;
  $("tfTitle").textContent = t("Trasforma %{name}", { name: ref.pattern });
  $("tfToken").value = ref.token;
  const add = $("tfAdd");
  add.replaceChildren(new Option(t("Aggiungi una funzione…"), ""));
  for (const f of bar.transforms) add.add(new Option(f.ready, f.ready));
  $("tfHelp").textContent = "";
  $("tfStages").replaceChildren();
  $("tfError").textContent = "";
  $("tfBefore").replaceChildren();
  $("tfAfter").replaceChildren();
  $("transform").showModal();
  refreshTransform();
}

function scheduleTransform() {
  clearTimeout(tf.timer);
  tf.timer = setTimeout(() => refreshTransform().catch(showError), 300);
}

async function refreshTransform() {
  const token = $("tfToken").value.trim();
  const r = (await call("transform_preview", { args: [tf.text, tf.pos, token] })).result;
  if ($("tfToken").value.trim() !== token) return;            // superata
  tf.result = r;
  $("tfError").textContent = r.error || (r.warnings || []).join("\n");
  const ok = !r.error;
  $("tfReplace").disabled = !ok;
  $("tfFreeze").disabled = !ok;
  $("tfPlayAfter").disabled = !ok;
  const list = $("tfStages");
  list.replaceChildren();
  for (const [step, notes] of ok ? r.stages : []) {
    const li = document.createElement("li");
    const code = document.createElement("code");
    code.textContent = step;
    li.append(code, " → ", notes || "–");
    list.append(li);
  }
  if (!ok) { $("tfAfter").replaceChildren(); return; }
  await Promise.all([miniScore($("tfBefore"), r.xml_before), miniScore($("tfAfter"), r.xml_after)]);
}

// Una striscia di partitura (verovio, come la schermata Partitura)
async function miniScore(box, xml) {
  const width = Math.max(240, box.clientWidth || 300);
  try {
    const r = await scoreCall({ cmd: "render", xml, scale: 35, pageWidth: Math.round(width * 100 / 35) });
    box.innerHTML = SvgSafe.clean(r.pages[0] || "");
    const svg = box.querySelector("svg");
    if (svg) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", t("Partitura")); }
  } catch (e) {
    box.textContent = errorText(e);
  }
}

async function playTransform(which) {
  const resumed = unlockInGesture();
  await resumed;
  const r = tf.result;
  if (!r || r.error) return;
  await playPreview(base64Bytes(which === "before" ? r.midi_before : r.midi_after),
                    which === "before" ? t("Ascolto del pattern") : t("Ascolto del pattern con le funzioni"));
}

async function applyTransform(freeze) {
  const r = tf.result;
  if (!r || r.error || !state.doc) return;
  if (state.previewing) stopPreview();
  if (state.doc.text !== tf.text) { $("tfError").textContent = t("Il testo è cambiato: riapri Trasforma."); return; }
  let out;
  try {
    out = (await call("transform_apply", { args: [tf.text, tf.pos, r.token, freeze] })).result;
  } catch (e) {
    $("tfError").textContent = errorText(e);
    return;
  }
  $("transform").close();
  if (!freeze) {
    // come se lo si scrivesse: entra nell'annulla della tastiera
    selectRange(r.start, r.end);
    typeText(r.token);
  } else {
    await replaceDocText(out.text);
    goTo(out.start, out.end);
  }
  setStatus(freeze ? t("Note scritte per esteso") : t("Richiamo sostituito"));
}

function setupTransform() {
  $("tfToken").addEventListener("input", scheduleTransform);
  $("tfAdd").onchange = (ev) => {
    const call = ev.target.value;
    if (!call) return;
    const f = bar.transforms.find((x) => x.ready === call);
    $("tfHelp").textContent = f ? f.help : "";
    $("tfToken").value = $("tfToken").value.trim() + call;
    ev.target.value = "";
    refreshTransform().catch(showError);
  };
  $("tfPlayBefore").onclick = () => playTransform("before").catch(showError);
  $("tfPlayAfter").onclick = () => playTransform("after").catch(showError);
  $("tfReplace").onclick = () => applyTransform(false).catch(showError);
  $("tfFreeze").onclick = () => applyTransform(true).catch(showError);
  $("tfClose").onclick = () => $("transform").close();
  $("transform").addEventListener("close", () => { if (state.previewing) stopPreview(); });
}
