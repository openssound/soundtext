// SoundText Mobile: ripulisce l'SVG della partitura prima di metterlo nella pagina. Le pagine di verovio contengono
// il testo del brano (titolo, nomi delle tracce, testo cantato), che puo' arrivare da un link: verovio lo
// protegge, e questa e' la seconda difesa. Toglie gli elementi che eseguono o caricano altro (script,
// foreignObject, iframe, object, embed, link, meta, base), ogni attributo on…, i link che non puntano dentro la
// pagina (#…), gli stili con url() esterni e le istruzioni XML. Lavora sul testo, senza DOM: si prova da Node con
// mobile/tests/svgsafe.test.cjs. Un SVG di verovio normale esce uguale.
"use strict";

const SvgSafe = (() => {
  const DROPPED = new Set(["script", "foreignobject", "iframe", "object", "embed", "link", "meta", "base", "applet", "frame", "frameset"]);
  const TOKEN = /<!--[\s\S]*?-->|<!\[CDATA\[[\s\S]*?\]\]>|<\?[\s\S]*?\?>|<![A-Za-z][^>]*>|<\/?([A-Za-z][\w:.-]*)((?:"[^"]*"|'[^']*'|[^'">])*)>|[^<]+|</g;
  const ATTR = /([^\s=\/>"']+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+))?/g;

  const unquote = (v) => (v == null ? "" : /^["']/.test(v) ? v.slice(1, -1) : v);
  // il valore come lo leggerebbe il browser: senza spazi e caratteri di controllo, minuscolo
  const plain = (v) => unquote(v).replace(/&#x?[0-9a-f]+;?/gi, "").replace(/[\u0000- \u007f-\u009f]+/g, "").toLowerCase();

  function cleanAttrs(raw) {
    let out = "";
    let m;
    ATTR.lastIndex = 0;
    while ((m = ATTR.exec(raw))) {
      const name = m[1], lower = name.toLowerCase();
      if (name === "/") continue;
      if (lower.startsWith("on")) continue;
      const value = m[2];
      if ((lower === "href" || lower === "xlink:href" || lower === "src" || lower === "action" || lower === "formaction") &&
          !plain(value).startsWith("#")) continue;
      if (lower === "style" && /url\s*\(|expression\s*\(|javascript:|@import|behavior/i.test(unquote(value))) continue;
      out += " " + name + (value == null ? "" : "=" + value);
    }
    return out;
  }

  function cleanStyle(css) {
    return css.replace(/@import[^;]*;?/gi, "").replace(/url\s*\(\s*(["']?)\s*(?!#)[^)]*\)/gi, "");
  }

  function clean(svg) {
    const out = [];
    let skipping = null, depth = 0, inStyle = false;
    let m;
    TOKEN.lastIndex = 0;
    while ((m = TOKEN.exec(String(svg)))) {
      const tok = m[0];
      const name = m[1] ? m[1].toLowerCase() : null;
      if (skipping) {                                    // dentro un elemento tolto: via tutto fino alla sua chiusura
        if (name === skipping) {
          if (tok.startsWith("</")) { if (--depth === 0) skipping = null; }
          else if (!/\/\s*>$/.test(tok)) depth++;
        }
        continue;
      }
      if (tok.startsWith("<!--") || tok.startsWith("<?") || /^<![A-Za-z]/.test(tok)) continue;     // commenti, istruzioni, DOCTYPE e ENTITY
      if (tok.startsWith("<![CDATA[")) { out.push(inStyle ? cleanStyle(tok) : tok); continue; }
      if (!name) {                                       // testo (o un "<" solo): il "<" si scrive come &lt;
        out.push(tok === "<" ? "&lt;" : inStyle ? cleanStyle(tok) : tok);
        continue;
      }
      if (DROPPED.has(name)) {
        if (!tok.startsWith("</") && !/\/\s*>$/.test(tok)) { skipping = name; depth = 1; }
        continue;
      }
      if (tok.startsWith("</")) {
        if (name === "style") inStyle = false;
        out.push(`</${m[1]}>`);
        continue;
      }
      if (name === "style") inStyle = !/\/\s*>$/.test(tok);
      const selfClosing = /\/\s*>$/.test(tok);
      out.push(`<${m[1]}${cleanAttrs(m[2].replace(/\/\s*$/, ""))}${selfClosing ? " /" : ""}>`);
    }
    return out.join("");
  }

  return { clean };
})();

if (typeof module !== "undefined") module.exports = { SvgSafe };
