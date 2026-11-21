// L'SVG della partitura ripulito: niente script, niente gestori on…, niente link fuori dalla pagina; un SVG di verovio
// normale resta uguale. Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { SvgSafe } = require("../svgsafe.js");

const GOOD = `<svg width="480px" height="1051px" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" overflow="visible" id="y95sv8a">
   <desc>Engraved by Verovio 6.3.0</desc>
   <defs>
      <g id="E050-y95sv8a">
         <path transform="scale(1,-1)" d="M441 -245c-23 -4 -48 -6 -76 -6" />
      </g>
   </defs>
   <style type="text/css">#y95sv8a g.dir {font-style:italic;}#y95sv8a path {stroke:currentColor}</style>
   <svg class="definition-scale" color="black" font-family="Times, serif" viewBox="0 0 12000 26260">
      <g class="page-margin" transform="translate(200, 400)">
         <use xlink:href="#E050-y95sv8a" transform="translate(10, 20) scale(0.72, 0.72)" />
         <text x="1105" y="5567" text-anchor="end" font-size="0px"><tspan class="text">Piano &amp; Co</tspan></text>
      </g>
   </svg>
</svg>`;

test("un SVG di verovio normale esce uguale", () => {
  assert.strictEqual(SvgSafe.clean(GOOD), GOOD.replace(/ \/>/g, " />"));
});

test("script e foreignObject spariscono con quello che contengono", () => {
  const dirty = `<svg><g><script>alert(1)</script><text>ok</text><foreignObject><div onclick="x()">x</div><script>y()</script></foreignObject><iframe src="https://e.x"></iframe></g></svg>`;
  assert.strictEqual(SvgSafe.clean(dirty), "<svg><g><text>ok</text></g></svg>");
  assert.ok(!/script|foreign|iframe|alert/i.test(SvgSafe.clean(dirty)));
});

test("i gestori on… spariscono da ogni elemento, anche se scritti storti", () => {
  for (const dirty of [`<svg onload=alert(1)><g/></svg>`, `<svg><g ONCLICK="a()" onmouseover='b()' id="x"/></svg>`,
                       `<svg><path d="M0 0" onerror = "c()"/></svg>`, `<svg><g\nonload="d()"\n/></svg>`]) {
    const out = SvgSafe.clean(dirty);
    assert.ok(!/on[a-z]+\s*=/i.test(out), out);
  }
  assert.ok(SvgSafe.clean(`<svg><g ONCLICK="a()" id="x"/></svg>`).includes('id="x"'));
});

test("un titolo come \">< svg onload=… > dentro il testo non esegue nulla", () => {
  const dirty = `<svg><text><tspan>"><svg onload=alert(1)></tspan></text></svg>`;
  const out = SvgSafe.clean(dirty);
  assert.ok(!/onload/i.test(out), out);
  const lone = SvgSafe.clean(`<svg><text>1 < 2</text></svg>`);
  assert.ok(lone.includes("&lt;") && !lone.includes("< 2"), lone);
});

test("i link: solo quelli dentro la pagina", () => {
  const out = SvgSafe.clean(`<svg><use xlink:href="#a"/><use href="#b"/><a xlink:href="javascript:alert(1)"><text>x</text></a>` +
    `<a href=" jav&#x61;script:alert(1)">y</a><a href="https://evil.example/">z</a><image href="data:text/html;base64,AAAA"/></svg>`);
  assert.ok(out.includes('xlink:href="#a"') && out.includes('href="#b"'));
  assert.ok(!/javascript|evil|data:|jav/i.test(out), out);
});

test("gli stili non caricano nulla da fuori", () => {
  const out = SvgSafe.clean(`<svg><style>@import url(https://e.x/a.css); g{fill:url(https://e.x/p.svg#a)} path{fill:url(#grad)}</style><g style="fill:url(http://e.x/y)" id="k"/></svg>`);
  assert.ok(!/e\.x|@import/.test(out), out);
  assert.ok(out.includes("url(#grad)") && out.includes('id="k"'), out);
});

test("istruzioni XML, DOCTYPE ed ENTITY spariscono", () => {
  const out = SvgSafe.clean(`<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg><text>&x;</text></svg>`);
  assert.ok(!/DOCTYPE|ENTITY|passwd|<\?xml/.test(out), out);
});

test("elementi tolti annidati e chiusure mancanti non lasciano resti", () => {
  const out = SvgSafe.clean(`<svg><foreignObject><foreignObject>a</foreignObject>b</foreignObject><g id="q"/><script>never closed`);
  assert.strictEqual(out, `<svg><g id="q" /></svg>`.replace("</svg>", ""));
});
