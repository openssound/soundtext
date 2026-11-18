// SoundText Mobile: «Un brano in 60 secondi». Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ un brano in 60 secondi
//
// Genere, atmosfera e durata: il motore (engine.quick_song) scrive un brano completo
// con i suoi generatori, un box per sezione e traccia; l'app lo salva fra i brani e
// lo fa suonare. Ogni volta il seme e' nuovo: premere di nuovo da' un altro brano.

const quick = { choices: null, busy: false };
const QUICK_KEY = "stmobile.quick";

function quickFill(select, items, saved) {
  select.innerHTML = "";
  for (const item of items) select.add(new Option(item.label, String(item.value)));
  if (saved !== undefined && items.some((i) => String(i.value) === String(saved))) select.value = String(saved);
}

async function openQuick() {
  const dialog = $("quickDialog");
  $("quickStatus").textContent = "";
  $("quickStatus").classList.remove("error");
  dialog.showModal();
  await state.booted;
  if (!quick.choices) quick.choices = (await call("quick_choices")).result;
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(QUICK_KEY) || "{}"); } catch (e) {}
  quickFill($("quickGenre"), quick.choices.genres, saved.genre);
  quickFill($("quickMood"), quick.choices.moods, saved.mood);
  quickFill($("quickDuration"), quick.choices.durations, saved.duration === undefined ? 60 : saved.duration);
  $("quickMake").disabled = false;
}

async function makeQuick() {
  if (quick.busy) return;
  quick.busy = true;
  const resumed = unlockInGesture();            // il tocco: niente await prima (iOS)
  const tap = performance.now();
  const choice = { genre: $("quickGenre").value, mood: $("quickMood").value, duration: Number($("quickDuration").value) };
  try { localStorage.setItem(QUICK_KEY, JSON.stringify(choice)); } catch (e) {}
  $("quickMake").disabled = true;
  $("quickStatus").classList.remove("error");
  $("quickStatus").textContent = t("Compongo…");
  try {
    await resumed;
    const made = (await call("quick_song", { args: [choice] })).result;
    const name = await Songs.freeName(made.name);
    const song = await Songs.create({ name, text: made.text, source: "brano in 60 secondi, seme " + made.seed });
    const composed = performance.now();
    $("quickDialog").close();
    await openSong(song.id);
    await play();
    Metrics.record("brano_veloce", { ...choice, seed: made.seed, bars: made.bars, composed_ms: Math.round(composed - tap),
                                     to_sound_ms: Math.round(performance.now() - tap) });
  } catch (e) {
    $("quickStatus").classList.add("error");
    $("quickStatus").textContent = shortError(e);
    $("quickMake").disabled = false;
  } finally {
    quick.busy = false;
  }
}

function setupQuick() {
  $("quickSong").onclick = () => openQuick().catch(showError);
  $("quickMake").onclick = () => makeQuick();
  $("quickClose").onclick = () => $("quickDialog").close();
}
