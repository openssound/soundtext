// SoundText Mobile: le modifiche del testo come funzioni pure (testo e
// posizione in ingresso, testo e cursore in uscita), senza toccare la
// pagina: le usano la barra musicale e la dettatura, e si provano con
// node --test (mobile/tests/text-edits.test.cjs).
"use strict";

const TextEdits = (() => {
  // La parola prima di pos (fino allo spazio)
  function wordBefore(text, pos) {
    let i = pos;
    while (i > 0 && !/\s/.test(text[i - 1])) i--;
    return text.slice(i, pos);
  }

  function needsSpaceBefore(text, pos) {
    if (pos === 0) return false;
    const prev = text[pos - 1];
    if (/\s/.test(prev) || prev === "(" || prev === "[") return false;
    return !/^\d+$/.test(wordBefore(text, pos));   // "2" + "c" = "2c": un moltiplicatore
  }

  // Un pezzo nuovo a pos, con lo spazio prima (se serve) e dopo.
  function insertPiece(text, pos, piece) {
    const after = text[pos];
    const s = (needsSpaceBefore(text, pos) ? " " : "") + piece + (after && /\s/.test(after) ? "" : " ");
    return { text: text.slice(0, pos) + s + text.slice(pos), caret: pos + s.length };
  }

  // «tempo novanta»: cambia la riga Tempo:, o la aggiunge dopo ST:. Il
  // cursore resta sullo stesso carattere.
  function setTempo(text, bpm, caret) {
    const m = /^([ \t]*Tempo:[ \t]*)(\d+(?:\.\d+)?)/m.exec(text);
    let out, at, delta;
    if (m) {
      at = m.index + m[1].length;
      out = text.slice(0, at) + bpm + text.slice(at + m[2].length);
      delta = String(bpm).length - m[2].length;
    } else {
      const st = /^ST:.*\n/m.exec(text);
      at = st ? st.index + st[0].length : 0;
      const line = `Tempo: ${bpm} BPM\n`;
      out = text.slice(0, at) + line + text.slice(at);
      delta = line.length;
    }
    return { text: out, caret: caret > at ? caret + delta : caret };
  }

  // «ripeti due volte» senza altro: l'ultima battuta della riga (da dopo
  // l'ultima stanghetta a pos) diventa N( … ). null se non c'e' niente.
  function wrapRepeat(text, pos, count) {
    const lineStart = text.lastIndexOf("\n", pos - 1) + 1;
    let end = pos;
    while (end > lineStart && /\s/.test(text[end - 1])) end--;
    let start = text.lastIndexOf("|", end - 1) + 1;
    if (start <= lineStart) {
      start = lineStart;
      // dopo il rientro e la griglia («8:», «rel:»)
      const head = /^(\s*(?:\S+:\s+)*)/.exec(text.slice(start, end));
      start += head[1].length;
    }
    while (start < end && /\s/.test(text[start])) start++;
    if (start >= end) return null;
    const group = `${count}(${text.slice(start, end)})`;
    return { text: text.slice(0, start) + group + text.slice(end), caret: start + group.length + (pos - end) };
  }

  return { wordBefore, needsSpaceBefore, insertPiece, setTempo, wrapRepeat };
})();

if (typeof module !== "undefined") module.exports = { TextEdits };
