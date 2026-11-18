// SoundText Mobile: la schermata Struttura. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ struttura
//
// Le sezioni del brano una sotto l'altra, le tracce in colonne (scorrono in
// orizzontale), i box nelle celle (engine.structure). Un tocco su un box o
// su una sezione apre le azioni; le modifiche (engine.box_edit) cambiano
// solo le intestazioni e i blocchi dei box. «Annulla» torna indietro di una
// modifica della Struttura.

const struct = { info: null, infoFor: null, undo: [] };

async function showStructure() {
  if (!document.body.classList.contains("view-struttura") || !state.doc) {
    if (!state.doc) $("structure").replaceChildren(hint(t("Apri un brano per vederne la struttura.")));
    return;
  }
  const text = state.doc.text;
  if (struct.infoFor !== text) {
    if (!struct.info) $("structure").replaceChildren(hint(t("Carico…")));
    await state.booted;
    try {
      struct.info = (await call("structure", { args: [text] })).result;
      struct.infoFor = text;
    } catch (e) {
      struct.info = null;
      $("structure").replaceChildren(hint(t("Struttura non disponibile: {message}", { message: errorText(e) }), true));
      return;
    }
  }
  renderStructure();
}

function hint(text, error = false) {
  const p = document.createElement("p");
  p.className = error ? "hint error" : "hint";
  p.style.padding = "0 16px";
  p.textContent = text;
  return p;
}

function renderStructure() {
  const info = struct.info;
  const box = $("structure");
  $("structUndo").disabled = struct.undo.length === 0;
  const plain = info.tracks.filter((tr) => tr.plain && tr.boxes.length);
  $("structSplit").hidden = plain.length === 0;
  if (!info.tracks.length) { box.replaceChildren(hint(t("Il brano non ha ancora tracce."))); return; }
  const sections = info.sections;
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  const corner = document.createElement("th");
  corner.className = "sec";
  corner.textContent = t("Sezione");
  head.append(corner);
  for (const tr of info.tracks) {
    const th = document.createElement("th");
    th.textContent = tr.name;
    th.title = tr.instrument;
    th.scope = "col";
    head.append(th);
  }
  const body = table.createTBody();
  sections.forEach((sec, i) => {
    const until = i + 1 < sections.length ? sections[i + 1].beat : Infinity;
    const row = body.insertRow();
    const th = document.createElement("th");
    th.className = "sec";
    th.scope = "row";
    const b = document.createElement("button");
    // l'ultima sezione arriva alla fine del brano
    const lastBar = i + 1 < sections.length ? sections[i + 1].bar - 1
      : info.bars.filter((b) => b < info.end - 1e-6).length;
    b.append(sec.name || t("(senza nome)"));
    const small = document.createElement("small");
    small.textContent = lastBar && lastBar > sec.bar ? t("battute {first}–{last}", { first: sec.bar, last: lastBar })
                                                     : t("battuta {n}", { n: sec.bar });
    b.append(small);
    b.setAttribute("aria-label", t("Sezione {name}, {where}", { name: sec.name || t("(senza nome)"), where: small.textContent }));
    b.onclick = () => sectionActions(sec);
    th.append(b);
    row.append(th);
    for (const tr of info.tracks) {
      const cell = row.insertCell();
      for (const bx of tr.boxes) {
        if (bx.beat < sec.beat - 1e-9 || bx.beat >= until - 1e-9) continue;
        const c = document.createElement("button");
        c.className = "box" + (tr.plain ? " plain" : "");
        c.append(tr.plain ? t("testo della traccia") : bx.name || "–");
        const sm = document.createElement("small");
        sm.textContent = bx.bars === 1 ? t("battuta {n}", { n: bx.bar })
                                       : t("battute {first}–{last}", { first: bx.bar, last: bx.bar + bx.bars - 1 });
        c.append(sm);
        c.setAttribute("aria-label", t("Box {name}, traccia {track}, {where}",
                                       { name: tr.plain ? t("testo della traccia") : bx.name, track: tr.name, where: sm.textContent }));
        c.onclick = () => boxActions(tr, bx);
        cell.append(c);
      }
    }
  });
  box.replaceChildren(table);
}

// Il foglio delle azioni (in basso, come sul telefono)
function sheet(title, actions, columns = false) {
  const dlg = $("sheet");
  $("sheetTitle").textContent = title;
  const list = $("sheetActions");
  list.classList.toggle("columns", columns);
  list.replaceChildren();
  for (const [label, run, cls] of actions) {
    const b = document.createElement("button");
    b.textContent = label;
    if (cls) b.className = cls;
    b.onclick = () => { dlg.close(); Promise.resolve(run()).catch(showError); };
    list.append(b);
  }
  dlg.showModal();
}

function openInText(pos) {
  setView("testo");
  goTo(pos);
}

function boxActions(track, bx) {
  if (track.plain) {
    sheet(t("Traccia {name}", { name: track.name }), [
      [t("Apri nel Testo"), () => openInText(0)],
      [t("Dividi in sezioni"), splitIntoSections],
    ]);
    return;
  }
  sheet(t("Box {name} · {track}", { name: bx.name, track: track.name }), [
    [t("Apri nel Testo"), () => openInText(bx.start)],
    [t("Rinomina…"), async () => {
      const name = prompt(t("Nuovo nome del box"), bx.name);
      if (name) await structEdit("rename", { hstart: bx.hstart, name });
    }],
    [t("Sposta alla battuta…"), async () => {
      const bar = prompt(t("Battuta d'inizio"), String(bx.bar));
      if (bar && Number(bar) >= 1) await structEdit("move", { hstart: bx.hstart, bar: Math.round(Number(bar)) });
    }],
    [t("Duplica in fondo al brano"), () => structEdit("duplicate", { hstart: bx.hstart })],
    [t("Elimina"), () => structEdit("delete", { hstart: bx.hstart }), "danger"],
  ]);
}

function sectionActions(sec) {
  sheet(t("Sezione {name}", { name: sec.name || t("(senza nome)") }), [
    [t("Duplica la sezione in fondo al brano"), () => structEdit("section_duplicate", { beat: sec.beat })],
    [t("Rinomina la sezione…"), async () => {
      const name = prompt(t("Nuovo nome della sezione"), sec.name);
      if (name) await structEdit("section_rename", { beat: sec.beat, name });
    }],
    [t("Elimina la sezione"), () => structEdit("section_delete", { beat: sec.beat }), "danger"],
  ]);
}

async function splitIntoSections() {
  const name = prompt(t("Nome della prima sezione"), t("Strofa"));
  if (name) await structEdit("make_boxes", { name });
}

async function structEdit(op, args) {
  if (!state.doc) return;
  const before = state.doc.text;
  let r;
  try {
    r = (await call("box_edit", { args: [before, op, args] })).result;
  } catch (e) {
    $("structStatus").textContent = errorText(e);
    return;
  }
  if (state.doc.text !== before) return;           // cambiato nel frattempo
  struct.undo.push(before);
  if (struct.undo.length > 30) struct.undo.shift();
  await replaceDocText(r.text);
  $("structStatus").textContent = "";
  await showStructure();
}

async function undoStructure() {
  const previous = struct.undo.pop();
  if (previous == null || !state.doc) return;
  await replaceDocText(previous);
  await showStructure();
}

function setupStructure() {
  $("structUndo").onclick = () => undoStructure().catch(showError);
  $("structSplit").onclick = () => splitIntoSections().catch(showError);
  $("sheetClose").onclick = () => $("sheet").close();
}
