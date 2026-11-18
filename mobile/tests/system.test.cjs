// Condividi verso SoundText (mobile/app/system.js): riconoscere un link di un brano o un testo ST.
// Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { sharedLinkIn, looksLikeSong } = require("../app/system.js");

test("un link di un brano si trova nell'indirizzo o nel testo condiviso", () => {
  const link = "#v=1&b=AbC_-123&n=Il%20brano";
  assert.strictEqual(sharedLinkIn("https://openssound.github.io/soundtext/" + link), link);
  assert.strictEqual(sharedLinkIn("", "Guarda questo brano: https://x.test/app/" + link + " bello, vero?"), link);
  assert.strictEqual(sharedLinkIn("niente", "nemmeno qui #altro"), null);
  assert.strictEqual(sharedLinkIn(undefined, null), null);
  assert.strictEqual(sharedLinkIn("https://x.test/#solo-un-titolo"), null);
});

test("un testo ST si riconosce, un testo qualunque no", () => {
  for (const file of ["jazz_aaba.st", "14_trasformazioni.st"]) {
    const dir = fs.existsSync(path.join(__dirname, "..", "..", "examples", file)) ? "examples" : "examples";
    const p = path.join(__dirname, "..", "..", dir, file);
    if (fs.existsSync(p)) assert.ok(looksLikeSong(fs.readFileSync(p, "utf8")), file);
  }
  assert.ok(looksLikeSong("ST: 2.6\nTempo: 100 BPM\n"));
  assert.ok(looksLikeSong("Piano:\n  4: c d e f |\n"));
  assert.ok(!looksLikeSong("Ciao, ti mando la lista:\nlatte\nuova"));
  assert.ok(!looksLikeSong("Appunti:\nda comprare\n"));
  assert.ok(!looksLikeSong(""));
});
