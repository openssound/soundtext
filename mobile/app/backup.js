// SoundText Mobile: la copia di sicurezza dei brani e i dati sul telefono. I brani stanno solo nel browser del
// telefono (IndexedDB) e non passano da nessun server: se si cancellano i dati del sito, spariscono. Qui si
// esportano tutti in un .zip (un .st per brano, byte per byte), si importano da un .zip o da piu' .st, un
// promemoria avvisa quando e' ora di farne una copia, e l'archivio si chiede «persistente» al browser.
"use strict";

const BACKUP_KEY = "stmobile.backup";
const BACKUP_EVERY_SONGS = 10;
const BACKUP_EVERY_DAYS = 30;

// ---- lo stato del promemoria: { last, since, ids, off, iosShown }

function backupState() {
  try { return { last: 0, since: 0, ids: [], off: false, iosShown: false, ...JSON.parse(localStorage.getItem(BACKUP_KEY) || "{}") }; } catch (e) { return { last: 0, since: 0, ids: [], off: false, iosShown: false }; }
}

function backupSave(s) {
  try { localStorage.setItem(BACKUP_KEY, JSON.stringify(s)); } catch (e) {}
}

// Un brano nuovo o modificato: se ne tiene l'identita', per contarli
function backupNoteChange(id) {
  if (!id) return;
  const s = backupState();
  if (!s.ids.includes(id)) s.ids.push(id);
  if (!s.since) s.since = Date.now();
  backupSave(s);
}

// Serve un promemoria? (true quando ci sono 10 brani nuovi o modificati, o 30 giorni dall'ultima copia)
function backupDue(s = backupState(), now = Date.now()) {
  if (s.off || !s.ids.length) return false;
  if (s.ids.length >= BACKUP_EVERY_SONGS) return true;
  const from = s.last || s.since;
  return !!from && now - from >= BACKUP_EVERY_DAYS * 86400000;
}

function wrapSongsForBackup() {
  const put = Songs.put, create = Songs.create;
  Songs.put = async (song) => { const r = await put(song); backupNoteChange(r.id); return r; };
  Songs.create = async (fields) => { const r = await create(fields); backupNoteChange(r.id); return r; };
}

// ---- esportare

function backupFileName(now = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return `soundtext-brani-${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}.zip`;
}

// I brani come file dello zip: il nome del brano, uno per brano; due uguali diventano «Nome (2).st»
function backupFiles(songs) {
  const used = new Set(), files = [];
  for (const song of songs) {
    let name = StFormat.fileName(song.name), n = 2;
    while (used.has(name.toLowerCase())) name = StFormat.fileName(`${song.name} (${n++})`);
    used.add(name.toLowerCase());
    files.push({ name, data: StFormat.toBytes(song), date: song.updated });
  }
  return files;
}

async function exportAllSongs() {
  const songs = await Songs.list();
  if (!songs.length) { backupSay(t("Non ci sono ancora brani da salvare."), true); return; }
  const bytes = Zip.write(backupFiles(songs));
  const file = new File([bytes], backupFileName(), { type: "application/zip" });
  let done = false;
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try { await navigator.share({ files: [file], title: "SoundText" }); done = true; } catch (e) { if (e.name === "AbortError") return; }
  }
  if (!done) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(file);
    a.download = file.name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 30000);
  }
  const s = backupState();
  s.last = Date.now(); s.since = 0; s.ids = [];
  backupSave(s);
  const message = t("Copia fatta: {n} brani in {name}.", { n: songs.length, name: file.name });
  backupSay(message);
  announce(message);
  renderBackupNote();
}

// ---- importare

// Da file scelti (.zip o .st) ai brani da importare: [{ name, bytes }]
async function backupReadFiles(files) {
  const items = [];
  for (const file of files) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (/\.zip$/i.test(file.name) || (bytes[0] === 0x50 && bytes[1] === 0x4b)) {
      for (const entry of await Zip.read(bytes)) {
        if (/\.st$/i.test(entry.name)) items.push({ name: StFormat.nameFromFile(entry.name.split("/").pop()), bytes: entry.data });
      }
    } else {
      items.push({ name: StFormat.nameFromFile(file.name), bytes });
    }
  }
  return items;
}

async function importSongs(files) {
  let items;
  try {
    items = await backupReadFiles(files);
  } catch (e) {
    backupSay(e.message === "cifrato" ? t("Questo archivio ha una password: non si può leggere.") : t("Non riesco a leggere l'archivio: non è uno zip valido."), true);
    return;
  }
  if (!items.length) { backupSay(t("Non ho trovato brani .st da importare."), true); return; }
  const existing = new Map((await Songs.list()).map((s) => [s.name, s]));
  const clashes = items.filter((it) => existing.has(it.name));
  let replace = false;
  if (clashes.length) {
    replace = confirm(t("{n} brani esistono già (per esempio «{name}»). OK li sostituisce con quelli importati; Annulla li tiene tutti e due, con un altro nome.",
                        { n: clashes.length, name: clashes[0].name }));
  }
  let added = 0, replaced = 0;
  for (const it of items) {
    const f = StFormat.fromBytes(it.bytes);
    const old = existing.get(it.name);
    if (old && replace) {
      await Songs.put({ ...old, text: f.text, eol: f.eol, bom: f.bom });
      replaced++;
    } else {
      const created = await Songs.create({ name: await Songs.freeName(it.name), text: f.text, eol: f.eol, bom: f.bom, source: "copia di sicurezza" });
      existing.set(created.name, created);
      added++;
    }
  }
  await renderSongs();
  const message = t("Importati {added} brani, sostituiti {replaced}.", { added, replaced });
  backupSay(message);
  announce(message);
}

// ---- il riquadro e i dati

function backupSay(text, error = false) {
  const el = $("backupStatus");
  el.textContent = text;
  el.classList.toggle("error", error);
}

function renderBackupNote() {
  const box = $("backupNote");
  const s = backupState();
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent) && !(navigator.standalone || (window.matchMedia && matchMedia("(display-mode: standalone)").matches));
  const due = backupDue(s);
  const showIos = ios && !s.iosShown;
  box.hidden = !(due || showIos);
  if (box.hidden) return;
  $("backupNoteText").textContent = due
    ? t("I tuoi brani sono solo su questo telefono. Vuoi farne una copia?")
    : t("Su iPhone, aggiungi SoundText alla schermata Home (Condividi, poi «Aggiungi a Home»): Safari può cancellare i dati dei siti che non si usano per un po'.");
  $("backupNoteDo").hidden = !due;
  $("backupNoteDo").onclick = () => exportAllSongs().catch(showError);
  $("backupNoteLater").onclick = () => {
    const st = backupState();
    if (due) { st.last = Date.now(); st.ids = []; st.since = 0; } else st.iosShown = true;
    backupSave(st);
    renderBackupNote();
  };
  $("backupNoteOff").hidden = !due;
  $("backupNoteOff").onclick = () => { const st = backupState(); st.off = true; backupSave(st); $("backupRemind").checked = false; renderBackupNote(); };
}

async function renderStorageInfo() {
  const lines = [];
  try {
    if (navigator.storage && navigator.storage.persist) {
      const persisted = (await navigator.storage.persisted()) || (await navigator.storage.persist());
      lines.push(persisted ? t("Archivio persistente: il browser non cancella i brani da solo.")
                           : t("Archivio non persistente: il browser potrebbe cancellare i dati se manca spazio. Fai una copia ogni tanto."));
    }
    if (navigator.storage && navigator.storage.estimate) {
      const e = await navigator.storage.estimate();
      if (e.usage != null) lines.push(t("Spazio usato dall'app: {used} MB su {quota} MB.", { used: (e.usage / 1048576).toFixed(1), quota: e.quota ? Math.round(e.quota / 1048576) : "?" }));
    }
  } catch (e) { /* senza queste informazioni si va avanti */ }
  $("storageInfo").textContent = lines.join(" ") || t("Il browser non dice quanto spazio usa l'app.");
}

function setupBackup() {
  wrapSongsForBackup();
  $("backupExport").onclick = () => exportAllSongs().catch((e) => backupSay(shortError(e), true));
  $("backupImportFile").onchange = (ev) => {
    const files = [...ev.target.files];
    ev.target.value = "";
    if (files.length) importSongs(files).catch((e) => backupSay(shortError(e), true));
  };
  const remind = $("backupRemind");
  remind.checked = !backupState().off;
  remind.onchange = () => { const s = backupState(); s.off = !remind.checked; backupSave(s); renderBackupNote(); };
  renderBackupNote();
  renderStorageInfo();
}
