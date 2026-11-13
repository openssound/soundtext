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
};

// I campi di ogni generatore: [nome, tipo, etichetta, opzioni]. Le etichette
// sono quelle delle finestre di SoundText.
function genFields(kind) {
  const c = gen.choices;
  const opts = (list) => list.map((o) => [o.value, o.label]);
  const variability = ["variability", "range", t("Variabilità:")];
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
      bars, ["instrument", "select", t("Strumento:"), instruments("progression")], variability,
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
      bars, intensity, variability,
      ["kick_track", "select", t("Segui la cassa di:"), [["", t("nessuna")], ...c.kick_tracks.map((n) => [n, n])]],
      ["performance", "check", t("Esecuzione dello strumento")],
    ];
  }
  return [...common,
    ["style", "select", t("Stile:"), opts(c.comping)], ["instrument", "select", t("Strumento:"), instruments("comping")],
    bars, intensity, variability,
    ["voice_leading", "check", t("Rivolti vicini")], ["performance", "check", t("Esecuzione dello strumento")],
  ];
}

function genDefaults(kind) {
  const c = gen.choices;
  const songBars = c.bars > 0 ? Math.min(64, c.bars) : 8;
  const base = { variability: 35, intensity: "normal" };
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
           voice_leading: true, performance: false };
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
  renderGenForm();
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
    lab.textContent = type === "range" ? `${label} ${values[name]}%` : label;
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
      if (type === "number" || type === "range") v = Number(v);
      if (name === "chord_bars") v = Number(v);
      values[name] = v;
      if (type === "range") { lab.textContent = `${label} ${v}%`; input.setAttribute("aria-valuetext", v + "%"); }
      if (name === "key") { renderGenForm(); }     // gli stili seguono il modo della tonalita'
      scheduleGenerate(type === "range" || type === "number" ? 250 : 0);
    };
    input.addEventListener(type === "range" || type === "number" ? "input" : "change", update);
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

// Strumento e nome della traccia nuova
function genTrack(kind) {
  const v = gen.values[kind];
  if (kind === "drums") return { instrument: "Drums", name: null };
  if (kind === "progression") return { instrument: v.instrument, name: t("Accordi") };
  return { instrument: v.instrument, name: null };
}

// Il brano con la parte nuova in fondo
async function songWithPart() {
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
  await playPreview(r.midi);
}

async function addPartToSong() {
  if (!state.doc) return;
  if (state.previewing) stopPreview();
  const { text, name } = await songWithPart();
  await replaceDocText(text);
  // Si resta in Crea, pronti per la parte dopo (giro -> batteria -> basso ->
  // accompagnamento): la traccia nuova si vede nel Testo e si sente con Play.
  const done = t("Traccia «{name}» aggiunta al brano", { name });
  setStatus(done);
  const order = GENERATOR_ORDER;
  const next = order[order.indexOf(gen.kind) + 1];
  gen.choices = null;                    // le tracce sono cambiate: nuove sorgenti di accordi
  gen.textFor = "";
  if (next) await setGenKind(next); else await showCrea();
  $("genStatus").textContent = done;
}

const GENERATOR_ORDER = ["progression", "drums", "bass", "comping"];

function setupCrea() {
  $("genForm").addEventListener("submit", (ev) => ev.preventDefault());   // niente invio: i campi rigenerano la parte
  for (const b of document.querySelectorAll(".gentabs button")) b.onclick = () => setGenKind(b.dataset.gen).catch(showError);
  $("genAgain").onclick = () => { gen.seeds[gen.kind] = null; gen.textFor = ""; scheduleGenerate(0); };
  $("genListen").onclick = () => listenToPart().catch(showError);
  $("genAdd").onclick = () => addPartToSong().catch(showError);
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
    box.innerHTML = r.pages[0] || "";
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
