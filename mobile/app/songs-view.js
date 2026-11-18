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
      [t("Condividi come link"), () => shareLink(song)],
      [t("Mostra QR code"), () => showQr(song)],
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
      [t("Condividi come link"), async () => shareLink(await exampleDoc(file))],
      [t("Mostra QR code"), async () => showQr(await exampleDoc(file))],
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

// ------------------------------------------------------------ link e QR code
//
// Il brano sta nel frammento del link (#v=1&b=...): non passa da nessun server.
// Vedi share.js.

async function songLink(song, bytes = StFormat.toBytes(song)) {
  const fragment = await ShareLink.makeFragment(song.name, bytes);
  return ShareLink.makeUrl(location.origin + location.pathname, fragment);
}

// Condivide il link (foglio di condivisione) o lo copia.
async function shareLink(song) {
  const url = await songLink(song);
  const long = url.length > ShareLink.LONG_LINK
    ? " " + t("Il link è lungo: alcune app lo tagliano. Se non si apre, manda il file .st.") : "";
  if (navigator.share) {
    try {
      await navigator.share({ title: song.name, url });
      return;
    } catch (e) {
      if (e.name === "AbortError") return;
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    setStatus(t("Link copiato ({n} caratteri).", { n: url.length }) + long);
  } catch (e) {
    prompt(t("Copia il link:"), url);
  }
}

// Il QR del link, per la lavagna o un altro telefono: senza commenti, per farlo stare.
async function showQr(song) {
  await state.booted;
  const bare = (await call("strip_comments", { args: [song.text] })).result;
  const url = await songLink(song, new TextEncoder().encode(bare));
  const qr = Qr.encode(new TextEncoder().encode(url));
  $("qrTitle").textContent = song.name;
  $("qrCanvas").hidden = !qr;
  if (qr) {
    Qr.draw($("qrCanvas"), qr, 840);
    $("qrCanvas").setAttribute("aria-label", t("QR code del brano {name}", { name: song.name }));
    $("qrHelp").textContent = t("Inquadralo con la fotocamera di un altro telefono. I commenti del brano non sono nel QR.");
  } else {
    // il motivo sta nella finestra stessa, non nella riga di stato del lettore
    $("qrHelp").textContent = t("Questo brano è troppo grande per un QR code ({n} byte, il massimo è {max}). " +
      "Usa «Condividi come link» o il file .st.", { n: new TextEncoder().encode(url).length, max: Qr.MAX_BYTES });
  }
  const dialog = $("qrDialog");
  dialog.showModal();
  $("qrClose").onclick = () => dialog.close();
}

// Il brano di un link aperto: si ascolta e si guarda in sola lettura; la prima
// modifica (o "Fai una copia") lo mette fra i brani dell'utente.
async function openSharedLink() {
  let shared;
  try {
    shared = await ShareLink.readFragment(location.hash);
  } catch (e) {
    const why = { formato: t("Questo link è di una versione di SoundText che l'app non conosce."),
                  grande: t("Il brano di questo link è troppo grande."),
                  dati: t("Il link non contiene un brano valido: forse è stato tagliato o modificato.") }[e.code];
    setStatus(why || shortError(e), true);
    return null;
  }
  if (!shared) return null;
  const f = StFormat.fromBytes(shared.bytes);
  const ready = openDoc({ kind: "link", name: shared.name, text: f.text, eol: f.eol, bom: f.bom });
  setEditable(false);                          // prima l'ascolto; per modificare si fa una copia
  setView("testo");
  return ready;
}

async function copyShared() {
  const doc = state.doc;
  if (!doc || doc.kind !== "link") return;
  const name = await Songs.freeName(doc.name);
  const song = await Songs.create({ name, text: doc.text, eol: doc.eol, bom: doc.bom, source: "link condiviso" });
  await openSong(song.id);
  setStatus(t("Copia salvata fra i tuoi brani"));
}
