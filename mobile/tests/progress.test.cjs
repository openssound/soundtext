// Serie di giorni, livello consigliato e riassunto dei progressi (mobile/progress.js).
// Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { Progress } = require("../progress.js");

test("la serie conta i giorni di fila fino a oggi, e non si spezza se oggi non hai ancora fatto niente", () => {
  const days = ["2026-11-14", "2026-11-16", "2026-11-17", "2026-11-18"];
  assert.strictEqual(Progress.streak(days, "2026-11-18"), 3);              // 16, 17, 18; il 15 manca
  assert.strictEqual(Progress.streak(days.slice(0, 3), "2026-11-18"), 2);  // oggi niente: da ieri 17, 16
  assert.strictEqual(Progress.streak(days.slice(0, 3), "2026-11-19"), 0);  // due giorni fermi: si ricomincia
  assert.strictEqual(Progress.streak([], "2026-11-18"), 0);
  assert.strictEqual(Progress.streak(["2026-02-27", "2026-02-28", "2026-03-01"], "2026-03-01"), 3);   // a cavallo del mese
  assert.strictEqual(Progress.streak(["2025-12-31", "2026-01-01"], "2026-01-01"), 2);                  // e dell'anno
});

test("il giorno si scrive nel fuso del telefono", () => {
  assert.strictEqual(Progress.dayKey(new Date(2026, 10, 18, 23, 59)), "2026-11-18");
  assert.strictEqual(Progress.dayKey(new Date(2026, 0, 5, 0, 1)), "2026-01-05");
});

test("il livello sale con 8 giusti su 10 e scende con meno di 4, ma servono almeno 8 risposte", () => {
  const rep = (right, wrong) => [...Array(right).fill(true), ...Array(wrong).fill(false)];
  assert.strictEqual(Progress.suggestLevel(rep(8, 2), 1), 2);
  assert.strictEqual(Progress.suggestLevel(rep(10, 0), 3), 3);              // non oltre il 3
  assert.strictEqual(Progress.suggestLevel(rep(3, 7), 2), 1);
  assert.strictEqual(Progress.suggestLevel(rep(3, 7), 1), 1);               // non sotto l'1
  assert.strictEqual(Progress.suggestLevel(rep(5, 5), 2), 2);
  assert.strictEqual(Progress.suggestLevel(rep(7, 0), 1), 1);               // poche risposte: nessun cambio
  assert.strictEqual(Progress.suggestLevel([...rep(0, 20), ...rep(8, 2)], 1), 2);   // contano solo le ultime 10
});

test("il riassunto: serie, oggi e per tipo", () => {
  const r = (day, kind, level, correct) => ({ day, kind, level, correct });
  const s = Progress.summary([r("2026-11-17", "chords", 1, true), r("2026-11-18", "chords", 1, false), r("2026-11-18", "bar", 2, true)], "2026-11-18");
  assert.strictEqual(s.streak, 2);
  assert.deepStrictEqual(s.today, { done: 2, correct: 1 });
  assert.deepStrictEqual([s.perKind.chords.total, s.perKind.chords.correct, s.perKind.bar.total], [2, 1, 1]);
  assert.deepStrictEqual(s.perKind.chords.history[1], [true, false]);
});

test("gli esercizi del giorno sono gli stessi per lo stesso giorno e cambiano da un giorno all'altro", () => {
  assert.strictEqual(Progress.dailySeed("2026-11-18", "chords"), Progress.dailySeed("2026-11-18", "chords"));
  assert.notStrictEqual(Progress.dailySeed("2026-11-18", "chords"), Progress.dailySeed("2026-11-19", "chords"));
  assert.notStrictEqual(Progress.dailySeed("2026-11-18", "chords"), Progress.dailySeed("2026-11-18", "bar"));
  const seeds = new Set(Array.from({ length: 60 }, (_, i) => Progress.dailySeed(`2026-12-${String(i % 28 + 1).padStart(2, "0")}`, "k" + i)));
  assert.ok(seeds.size > 50 && [...seeds].every((s) => s >= 0 && s < 1000000));
});
