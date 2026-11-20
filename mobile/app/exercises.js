// SoundText Mobile: gli esercizi quotidiani. Gli script di app/ sono caricati in ordine da
// index.html e condividono le variabili globali (vedi app/base.js).
"use strict";

// ------------------------------------------------------------ esercizi
//
// Pochi minuti al giorno: intervalli, accordi, giri armonici, completa la battuta, trova l'errore e dettato
// ritmico. Ogni esercizio e' deciso da tipo, livello (1-3) e seme (engine.exercise), quindi e' infinito e
// ripetibile; la correzione la fa il motore dal seme (engine.exercise_check). I risultati e la serie di giorni
// restano sul telefono (progress.js). «La sessione di oggi» e' una domanda per tipo, con gli stessi semi per
// tutti nello stesso giorno.

const ex = { kinds: [], levels: {}, queue: [], index: 0, results: [], question: null, answered: false, grid: new Set(), timers: [], mode: "free" };
const EX_SESSION = 6;

// la serie con «giorno» o «giorni»
const exStreakText = (n) => n === 1 ? t("Serie: 1 giorno di fila") : t("Serie: {n} giorni di fila", { n });

// ---- il suono

function exStopSound() {
  for (const id of ex.timers) clearTimeout(id);
  ex.timers = [];
  if (state.synth) { try { state.synth.midiAllNotesOff(); } catch (e) {} }
}

async function exPlay(notes, bpm) {
  if (!notes || !notes.length) return;
  const resumed = unlockInGesture();                 // il tocco di Ascolta
  await resumed;
  if (!state.audioReady) state.audioReady = initAudio();
  await state.audioReady;
  exStopSound();
  const synth = state.synth;
  synth.midiProgramChange(0, 0);
  const beatMs = 60000 / (bpm || 80);
  for (const n of notes) {
    ex.timers.push(setTimeout(() => synth.midiNoteOn(n.ch, n.n, n.v), 60 + n.t * beatMs));
    ex.timers.push(setTimeout(() => synth.midiNoteOff(n.ch, n.n), 60 + (n.t + n.d) * beatMs));
  }
}

// ---- la schermata di partenza

function exDone() { return $("exDialog").dataset.screen; }

function exShow(screen) {
  $("exDialog").dataset.screen = screen;
  for (const id of ["exHome", "exQuestion", "exSummary"]) $(id).hidden = id !== "ex" + screen[0].toUpperCase() + screen.slice(1);
}

async function exSummaryData() {
  const results = await Progress.all().catch(() => []);
  return Progress.summary(results, Progress.dayKey());
}

async function exRefreshHome() {
  const data = await exSummaryData();
  $("exStreak").textContent = data.streak ? exStreakText(data.streak) : t("Comincia oggi la tua serie");
  $("exToday").textContent = t("Oggi: {done} esercizi, {correct} giusti", { done: data.today.done, correct: data.today.correct });
  const list = $("exKinds");
  list.innerHTML = "";
  for (const kind of ex.kinds) {
    const stats = data.perKind[kind.kind];
    const li = document.createElement("li");
    const text = document.createElement("div");
    text.className = "ex-kind";
    const title = document.createElement("strong");
    title.textContent = kind.label;
    const hint = document.createElement("small");
    hint.textContent = kind.hint + (stats ? " · " + t("{correct} giuste su {total}", { correct: stats.correct, total: stats.total }) : "");
    text.append(title, hint);
    const level = document.createElement("select");
    level.setAttribute("aria-label", t("Livello di {name}", { name: kind.label }));
    for (let l = 1; l <= kind.levels; l++) level.add(new Option(t("Livello {n}", { n: l }), String(l)));
    level.value = String(ex.levels[kind.kind] || 1);
    level.onchange = () => { ex.levels[kind.kind] = Number(level.value); Progress.setLevel(kind.kind, Number(level.value)).catch(() => {}); };
    const go = document.createElement("button");
    go.textContent = t("Allenati");
    go.onclick = () => exStart("free", [kind.kind]).catch(showError);
    li.append(text, level, go);
    list.append(li);
  }
}

async function openExercises() {
  ex.kinds = (await call("exercise_kinds")).result;
  for (const kind of ex.kinds) ex.levels[kind.kind] = await Progress.level(kind.kind).catch(() => 1);
  exShow("home");
  await exRefreshHome();
  $("exDialog").showModal();
}

function exClose() {
  exStopSound();
  $("exDialog").close();
  exRefreshBadge().catch(() => {});
}

// ---- una sessione

// kinds: i tipi in ordine; in «free» un tipo solo, domande a ripetizione
async function exStart(mode, kinds) {
  ex.mode = mode;
  const day = Progress.dayKey();
  ex.queue = mode === "daily"
    ? kinds.map((kind) => ({ kind, level: ex.levels[kind] || 1, seed: Progress.dailySeed(day, kind) }))
    : [{ kind: kinds[0], level: ex.levels[kinds[0]] || 1, seed: Math.floor(Math.random() * 1e6) }];
  ex.index = 0;
  ex.results = [];
  await exAsk();
}

async function exAsk() {
  const item = ex.queue[ex.index];
  ex.question = (await call("exercise", { args: [item.kind, item.level, item.seed] })).result;
  ex.answered = false;
  ex.grid = new Set();
  const kind = ex.kinds.find((k) => k.kind === item.kind);
  const total = ex.mode === "daily" ? ex.queue.length : 0;
  $("exProgress").textContent = ex.mode === "daily"
    ? t("Domanda {n} di {total} · {name}, livello {level}", { n: ex.index + 1, total, name: kind.label, level: item.level })
    : t("{name}, livello {level}", { name: kind.label, level: item.level });
  $("exPrompt").textContent = ex.question.prompt;
  $("exContext").textContent = ex.question.context || "";
  $("exFeedback").textContent = "";
  $("exFeedback").className = "ex-feedback";
  $("exNext").hidden = true;
  $("exCheck").hidden = ex.question.input !== "grid";
  $("exListen").hidden = !ex.question.notes.length;
  $("exListenAgain").hidden = true;
  exRenderInput();
  exShow("question");
  // letto a chi non vede: dove si e', la domanda e il suo contesto; il fuoco va sulla domanda
  announce(`${$("exProgress").textContent}. ${ex.question.prompt}. ${ex.question.context || ""}`);
  $("exPrompt").tabIndex = -1;
  $("exPrompt").focus({ preventScroll: true });
}

function exRenderInput() {
  const q = ex.question, box = $("exInput");
  box.innerHTML = "";
  box.className = "ex-input " + q.input;
  if (q.kind === "bar") {
    const bar = document.createElement("div");
    bar.className = "ex-bar";
    for (const item of q.items) {
      const chip = document.createElement("span");
      chip.className = "ex-chip" + (item.missing ? " missing" : "");
      chip.textContent = item.missing ? "?" : (item.rest ? t("pausa di {name}", { name: item.label }) : item.label);
      bar.append(chip);
    }
    box.append(bar);
  }
  if (q.input === "choice") {
    const grid = document.createElement("div");
    grid.className = "ex-choices";
    for (const c of q.choices) {
      const b = document.createElement("button");
      b.textContent = c.label;
      b.dataset.value = String(c.value);
      b.onclick = () => exAnswer(c.value, b);
      grid.append(b);
    }
    box.append(grid);
  } else if (q.input === "pick") {
    const row = document.createElement("div");
    row.className = "ex-picks";
    q.items.forEach((name, i) => {
      const b = document.createElement("button");
      b.textContent = name;
      b.setAttribute("aria-label", t("nota {n}: {name}", { n: i + 1, name }));
      b.onclick = () => exAnswer(i, b);
      row.append(b);
    });
    box.append(row);
  } else {
    const per = q.grid.per_bar, rows = q.grid.bars;
    for (let bar = 0; bar < rows; bar++) {
      const line = document.createElement("div");
      line.className = "ex-steps";
      line.style.gridTemplateColumns = `repeat(${per}, 1fr)`;
      for (let i = 0; i < per; i++) {
        const step = bar * per + i;
        const b = document.createElement("button");
        b.className = "ex-step" + (i % (per / 4) === 0 ? " beat" : "");
        b.setAttribute("aria-pressed", "false");
        b.setAttribute("aria-label", t("passo {n}", { n: step + 1 }));
        b.onclick = () => {
          if (ex.answered) return;
          if (ex.grid.has(step)) ex.grid.delete(step); else ex.grid.add(step);
          b.setAttribute("aria-pressed", String(ex.grid.has(step)));
        };
        line.append(b);
      }
      box.append(line);
    }
  }
}

async function exAnswer(value, button) {
  if (ex.answered) return;
  ex.answered = true;
  const item = ex.queue[ex.index], q = ex.question;
  const r = (await call("exercise_check", { args: [item.kind, item.level, item.seed, value] })).result;
  ex.results.push(r.correct);
  await Progress.record({ kind: item.kind, level: item.level, seed: item.seed, correct: r.correct }).catch(() => {});
  const fb = $("exFeedback");
  fb.className = "ex-feedback " + (r.correct ? "right" : "wrong");
  const so = ex.results.filter(Boolean).length;
  fb.textContent = (r.correct ? t("Giusto!") : t("Non proprio: era «{label}».", { label: r.answer_label }))
    + (ex.mode === "daily" ? " " + t("Finora {right} giuste su {total}.", { right: so, total: ex.results.length }) : "");
  if (button) button.classList.add(r.correct ? "right" : "wrong");
  if (!r.correct && q.input === "choice") {
    for (const b of document.querySelectorAll("#exInput .ex-choices button")) if (b.textContent === r.answer_label) b.classList.add("right");
  }
  if (!r.correct && q.input === "pick") {
    const right = document.querySelectorAll("#exInput .ex-picks button")[r.answer];
    if (right) right.classList.add("right");
  }
  if (q.input === "grid") {
    const steps = document.querySelectorAll("#exInput .ex-step");
    steps.forEach((b, i) => { if (r.answer.includes(i)) b.classList.add("expected"); });
  }
  ex.reveal = r.notes && r.notes.length ? r.notes : q.notes;
  $("exListenAgain").hidden = !ex.reveal.length;
  $("exListenAgain").textContent = item.kind === "bar" ? t("Ascolta la battuta completa") : item.kind === "error" ? t("Ascolta la melodia giusta") : t("Riascolta");
  $("exCheck").hidden = true;
  $("exNext").hidden = false;
  $("exNext").textContent = ex.mode === "daily" && ex.index + 1 >= ex.queue.length ? t("Vedi il risultato") : t("Avanti");
}

async function exNext() {
  exStopSound();
  if (ex.mode === "daily") {
    ex.index++;
    if (ex.index >= ex.queue.length) { await exFinish(); return; }
  } else {
    const item = ex.queue[0];
    ex.queue = [{ kind: item.kind, level: ex.levels[item.kind] || 1, seed: Math.floor(Math.random() * 1e6) }];
    ex.index = 0;
  }
  await exAsk();
}

// Il livello consigliato dopo una sessione: sale o scende secondo gli ultimi risultati
async function exAdjustLevels(kinds) {
  const data = await exSummaryData();
  const notes = [];
  for (const kind of kinds) {
    const level = ex.levels[kind] || 1;
    const history = (data.perKind[kind] && data.perKind[kind].history[level]) || [];
    const next = Progress.suggestLevel(history, level);
    if (next !== level) {
      ex.levels[kind] = next;
      await Progress.setLevel(kind, next).catch(() => {});
      const label = ex.kinds.find((k) => k.kind === kind).label;
      notes.push(next > level ? t("{name}: ora livello {n}", { name: label, n: next }) : t("{name}: torni al livello {n}", { name: label, n: next }));
    }
  }
  return notes;
}

async function exFinish() {
  const right = ex.results.filter(Boolean).length;
  const data = await exSummaryData();
  $("exScore").textContent = t("{right} giuste su {total}", { right, total: ex.results.length });
  $("exSummaryStreak").textContent = exStreakText(data.streak);
  const notes = await exAdjustLevels(ex.queue.map((q) => q.kind));
  $("exLevelNotes").textContent = notes.join(" · ");
  exShow("summary");
  announce(`${$("exScore").textContent}. ${$("exSummaryStreak").textContent}. ${notes.join(". ")}`);
  $("exScore").tabIndex = -1;
  $("exScore").focus({ preventScroll: true });
}

async function exBackHome() {
  exStopSound();
  exShow("home");
  await exRefreshHome();
}

// Il bottone nella schermata Brani: la serie, in breve
async function exRefreshBadge() {
  const data = await exSummaryData();
  $("exOpen").textContent = data.streak === 1 ? t("Esercizi di oggi · serie di 1 giorno")
    : data.streak ? t("Esercizi di oggi · serie di {n} giorni", { n: data.streak }) : t("Esercizi di oggi");
}

function setupExercises() {
  $("exOpen").onclick = () => openExercises().catch(showError);
  $("exClose").onclick = exClose;
  $("exDialog").addEventListener("cancel", exStopSound);
  $("exDaily").onclick = () => exStart("daily", ex.kinds.map((k) => k.kind)).catch(showError);
  $("exListen").onclick = () => exPlay(ex.question.notes, ex.question.bpm).catch(showError);
  $("exListenAgain").onclick = () => exPlay(ex.reveal, ex.question.bpm).catch(showError);
  $("exCheck").onclick = () => exAnswer([...ex.grid], null).catch(showError);
  $("exNext").onclick = () => exNext().catch(showError);
  $("exSummaryHome").onclick = () => exBackHome().catch(showError);
  $("exHomeFromQuestion").onclick = () => exBackHome().catch(showError);
  exRefreshBadge().catch(() => {});
}
