// I progressi degli esercizi di SoundText Mobile: i risultati si tengono sul telefono (IndexedDB), senza account, e
// da li' si ricavano la serie di giorni e il livello consigliato. Le funzioni che calcolano non toccano il browser
// (si provano da Node con mobile/tests/progress.test.cjs).
"use strict";

const Progress = (() => {
  const pad2 = (n) => String(n).padStart(2, "0");

  // il giorno di una data, nel fuso del telefono: "2026-11-18"
  function dayKey(date = new Date()) {
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
  }

  function previousDay(key) {
    const [y, m, d] = key.split("-").map(Number);
    return dayKey(new Date(y, m - 1, d - 1, 12));
  }

  // La serie: i giorni di fila, fino a oggi, con almeno un esercizio fatto. Se oggi non ne hai ancora fatti, la
  // serie non si interrompe: conta da ieri.
  function streak(days, today) {
    const set = new Set(days);
    let day = set.has(today) ? today : previousDay(today);
    let count = 0;
    while (set.has(day)) {
      count++;
      day = previousDay(day);
    }
    return count;
  }

  // Il livello consigliato dagli ultimi risultati di un tipo (veri e falsi, dal piu' vecchio): sale con almeno
  // 8 giusti su 10, scende con meno di 4 su 10; servono almeno 8 risposte.
  function suggestLevel(history, current) {
    const recent = history.slice(-10);
    if (recent.length < 8) return current;
    const right = recent.filter(Boolean).length / recent.length * 10;
    if (right >= 8 && current < 3) return current + 1;
    if (right < 4 && current > 1) return current - 1;
    return current;
  }

  // Un riassunto dei risultati: la serie, quanto fatto oggi, e per tipo quante risposte e quante giuste.
  function summary(results, today) {
    const days = [...new Set(results.map((r) => r.day))];
    const perKind = {};
    for (const r of results) {
      const k = perKind[r.kind] || (perKind[r.kind] = { total: 0, correct: 0, history: {} });
      k.total++;
      if (r.correct) k.correct++;
      (k.history[r.level] || (k.history[r.level] = [])).push(!!r.correct);
    }
    const doneToday = results.filter((r) => r.day === today);
    return { streak: streak(days, today), today: { done: doneToday.length, correct: doneToday.filter((r) => r.correct).length }, perKind };
  }

  // Un seme per tipo e giorno: gli esercizi del giorno sono gli stessi per chi li apre lo stesso giorno
  function dailySeed(day, kind) {
    let h = 2166136261;
    for (const ch of `${day}/${kind}`) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
    return h % 1000000;
  }

  // ---- l'archivio

  const DB = "soundtext-mobile-ex";
  let dbPromise = null;

  function open() {
    if (!dbPromise) {
      dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(DB, 1);
        req.onupgradeneeded = () => {
          req.result.createObjectStore("results", { autoIncrement: true });
          req.result.createObjectStore("meta");
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return dbPromise;
  }

  async function run(store, mode, fn) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, mode);
      const result = fn(tx.objectStore(store));
      tx.oncomplete = () => resolve(result && "result" in result ? result.result : result);
      tx.onerror = () => reject(tx.error);
    });
  }

  const record = (r) => run("results", "readwrite", (s) => s.add({ ...r, at: Date.now(), day: dayKey() }));
  const all = () => run("results", "readonly", (s) => s.getAll());
  const level = (kind) => run("meta", "readonly", (s) => s.get("level/" + kind)).then((v) => v || 1);
  const setLevel = (kind, value) => run("meta", "readwrite", (s) => s.put(value, "level/" + kind));

  return { dayKey, streak, suggestLevel, summary, dailySeed, record, all, level, setLevel };
})();

if (typeof module !== "undefined") module.exports = { Progress };
