// Le modifiche del testo della barra musicale e della dettatura
// (mobile/app/text-edits.js): node --test mobile/tests/*.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { TextEdits } = require("../app/text-edits.js");

const SONG = "ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  8: c d e f | g a b c\n";
const END = SONG.length - 1;            // in fondo all'ultima riga

test("un pezzo nuovo prende lo spazio prima e dopo", () => {
  assert.deepEqual(TextEdits.insertPiece("  8: c", 6, "d e"), { text: "  8: c d e ", caret: 11 });
  // dopo uno spazio, una parentesi o un moltiplicatore non ne serve un altro
  assert.equal(TextEdits.insertPiece("  8: c ", 7, "d").text, "  8: c d ");
  assert.equal(TextEdits.insertPiece("  2(", 4, "c").text, "  2(c ");
  assert.equal(TextEdits.insertPiece("  8: 2", 6, "c").text, "  8: 2c ");
  // in mezzo al testo lo spazio dopo c'e' gia'
  assert.deepEqual(TextEdits.insertPiece("c e", 1, "d"), { text: "c d e", caret: 3 });
  assert.equal(TextEdits.insertPiece("", 0, "c").text, "c ");
});

test("tempo: cambia la riga e tiene il cursore sullo stesso carattere", () => {
  const r = TextEdits.setTempo(SONG, 90, END);
  assert.equal(r.text, SONG.replace("100", "90"));
  assert.equal(r.text[r.caret - 1], SONG[END - 1]);
  assert.equal(TextEdits.setTempo(SONG, 120, 3).caret, 3);         // cursore prima della riga
  assert.equal(TextEdits.setTempo("Tempo: 87.5 BPM\n", 60, 0).text, "Tempo: 60 BPM\n");
});

test("tempo: se manca la riga la aggiunge dopo ST:", () => {
  const r = TextEdits.setTempo("ST: 2.6\n\nPiano:\n  c\n", 72, 20);
  assert.equal(r.text, "ST: 2.6\nTempo: 72 BPM\n\nPiano:\n  c\n");
  assert.equal(r.caret, 20 + "Tempo: 72 BPM\n".length);
  assert.equal(TextEdits.setTempo("Piano:\n  c\n", 72, 0).text, "Tempo: 72 BPM\nPiano:\n  c\n");
});

test("ripeti: racchiude l'ultima battuta della riga", () => {
  assert.equal(TextEdits.wrapRepeat(SONG, END, 2).text, SONG.replace("| g a b c", "| 2(g a b c)"));
  // senza stanghette: tutta la riga, dopo il rientro e la griglia
  const one = "Piano:\n  8: c d e f ";
  assert.deepEqual(TextEdits.wrapRepeat(one, one.length, 3), { text: "Piano:\n  8: 3(c d e f) ", caret: one.length + 3 });
  assert.equal(TextEdits.wrapRepeat("Piano:\n  rel: 8: c d", 20, 2).text, "Piano:\n  rel: 8: 2(c d)");
  // niente da ripetere: riga vuota, o subito dopo una stanghetta
  assert.equal(TextEdits.wrapRepeat("Piano:\n  ", 9, 2), null);
  assert.equal(TextEdits.wrapRepeat("  c d | ", 8, 2), null);
});
