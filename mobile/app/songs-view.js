// SoundText Mobile: la schermata Brani. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ brani

function formatDate(time) {
  return new Date(time).toLocaleString(I18n.locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

async function renderSongs() {
  const list = await Songs.list().catch(() => []);
  const ul = $("mySongs");
  ul.innerHTML = "";
  $("noSongs").hidden = list.length > 0;
  for (const song of list) {
    ul.append(songItem(song.name, t("modificato {date}", { date: formatDate(song.updated) }),
                       state.doc && state.doc.kind === "song" && state.doc.id === song.id,
                       () => openSong(song.id), [
      [t("Rinomina"), () => renameSong(song.id)],
      [t("Duplica"), () => duplicate(song)],
      [t("Condividi"), () => share(song)],
      [t("Elimina"), () => deleteSong(song.id), "danger"],
    ]));
  }
  const ex = $("examples");
  ex.innerHTML = "";
  for (const file of state.examples) {
    ex.append(songItem(exampleTitle(file), t("sola lettura"),
                       state.doc && state.doc.kind === "example" && state.doc.file === file,
                       () => openExample(file, true), [
      [t("Crea una copia"), async () => duplicate(await exampleDoc(file))],
      [t("Condividi"), async () => share(await exampleDoc(file))],
    ]));
  }
}

function songItem(title, subtitle, current, onOpen, actions) {
  const li = document.createElement("li");
  if (current) li.classList.add("current");
  const open = document.createElement("button");
  open.className = "open";
  open.innerHTML = "<span></span><small></small>";
  open.firstChild.textContent = title;
  open.lastChild.textContent = subtitle;
  open.onclick = onOpen;
  const more = document.createElement("button");
  more.className = "more";
  more.textContent = "⋯";
  more.setAttribute("aria-label", t("Altre azioni per {name}", { name: title }));
  more.setAttribute("aria-expanded", "false");
  more.onclick = () => {
    const menu = li.querySelector(".menu");
    if (menu) { menu.remove(); li.classList.remove("has-menu"); more.setAttribute("aria-expanded", "false"); return; }
    const div = document.createElement("div");
    div.className = "menu";
    for (const [label, fn, cls] of actions) {
      const b = document.createElement("button");
      b.textContent = label;
      if (cls) b.className = cls;
      b.onclick = () => Promise.resolve(fn()).catch(showError);
      div.append(b);
    }
    li.classList.add("has-menu");
    li.append(div);
    more.setAttribute("aria-expanded", "true");
  };
  li.append(open, more);
  return li;
}

// Il nome di un esempio da mostrare: "jazz_1_evening_swing__sfz__plugin-areverb.st"
// diventa "jazz 1 evening swing" (dopo "__" ci sono i componenti usati).
function exampleTitle(file) {
  return file.replace(/\.st$/, "").split("__")[0].replace(/_/g, " ");
}

async function exampleDoc(file) {
  const bytes = new Uint8Array(await (await fetch("bundle/examples/" + encodeURIComponent(file))).arrayBuffer());
  const f = StFormat.fromBytes(bytes);
  return { kind: "example", file, name: exampleTitle(file), text: f.text, eol: f.eol, bom: f.bom };
}

async function openExample(file, show) {
  const doc = await exampleDoc(file);
  const ready = openDoc(doc);
  if (show) setView("testo");
  return ready;
}

async function openSong(id, show = true) {
  const song = await Songs.get(id);
  if (!song) return;
  const ready = openDoc({ kind: "song", id: song.id, name: song.name, text: song.text, eol: song.eol, bom: song.bom });
  if (show) setView("testo");
  return ready;
}

async function newSong() {
  const name = await Songs.freeName(t("Nuovo brano"));
  const song = await Songs.create({ name, text: newSongText(), source: "nuovo" });
  await openSong(song.id);
}

async function openFile(file) {
  const f = StFormat.fromBytes(new Uint8Array(await file.arrayBuffer()));
  const name = await Songs.freeName(StFormat.nameFromFile(file.name));
  const song = await Songs.create({ name, text: f.text, eol: f.eol, bom: f.bom, source: "file " + file.name });
  await openSong(song.id);
}

async function renameSong(id) {
  const song = await Songs.get(id);
  const name = prompt(t("Nuovo nome del brano"), song.name);
  if (!name || !name.trim() || name.trim() === song.name) return;
  song.name = await Songs.freeName(name.trim());
  await Songs.put(song);
  if (state.doc && state.doc.kind === "song" && state.doc.id === id) {
    state.doc.name = song.name;
    showDocTitle();
  }
  renderSongs();
}

async function duplicate(source) {
  const name = await Songs.freeName(source.name);
  const song = await Songs.create({ name, text: source.text, eol: source.eol, bom: source.bom,
                                    source: "copia di " + source.name });
  renderSongs();
  return song;
}

async function deleteSong(id) {
  const song = await Songs.get(id);
  if (!confirm(t("Eliminare «{name}»? Non si può annullare.", { name: song.name }))) return;
  await Songs.remove(id);
  if (state.doc && state.doc.kind === "song" && state.doc.id === id) {
    stop(true);
    state.doc = null;
    state.song = null;
    showText("");
    setEditable(false);
    clearCheck();
    showDocTitle();
    rememberDoc(null);
    $("play").disabled = true;
  }
  renderSongs();
}

// Condivide il .st (foglio di condivisione del telefono) o lo scarica.
async function share(song) {
  const fileName = StFormat.fileName(song.name);
  const file = new File([StFormat.toBytes(song)], fileName, { type: "text/plain" });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: song.name });
      return;
    } catch (e) {
      if (e.name === "AbortError") return;
    }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(file);
  a.download = fileName;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 10000);
}
