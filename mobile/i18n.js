// Lingue di SoundText Mobile: italiano (la lingua in cui sono scritti i
// testi), inglese, francese e spagnolo, come SoundText (core/i18n.py).
//
// Nel codice i testi si scrivono in italiano dentro t("..."), con i
// segnaposto {nome} come in Python: t("Battuta {n}", { n: 5 }). Nella
// pagina hanno l'attributo data-i18n (il testo dell'elemento) e si
// traducono anche aria-label, title e placeholder. Le traduzioni stanno nei
// cataloghi di SoundText (locales/<lingua>.json, {italiano: traduzione});
// mobile/build.py ne copia in bundle/locales/ solo le voci dell'app, e
// locales/extract.py raccoglie i testi da qui come da core/ e gui/.
//
// La lingua: quella scelta nell'app, altrimenti quella del telefono se e'
// fra le quattro, altrimenti l'inglese.
"use strict";

const I18n = (() => {
  const LANGUAGES = { it: "Italiano", en: "English", fr: "Français", es: "Español" };
  const KEY = "stmobile.lang";
  let language = "it";
  let catalog = {};

  function chosen() {
    try {
      const v = localStorage.getItem(KEY);
      if (v && v in LANGUAGES) return v;
    } catch (e) {}
    return null;
  }

  function detect() {
    const wanted = chosen();
    if (wanted) return wanted;
    for (const tag of navigator.languages || [navigator.language || ""]) {
      const code = String(tag).slice(0, 2).toLowerCase();
      if (code in LANGUAGES) return code;
    }
    return "en";
  }

  async function load() {
    language = detect();
    document.documentElement.lang = language;
    catalog = {};
    if (language !== "it") {
      try {
        const resp = await fetch(`bundle/locales/${language}.json`);
        if (resp.ok) catalog = await resp.json();
      } catch (e) {
        console.warn("traduzioni non caricate", e);
      }
    }
    return language;
  }

  function t(text, params) {
    let out = catalog[text] || text;
    if (params) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m));
    return out;
  }

  const ATTRIBUTES = ["aria-label", "title", "placeholder"];

  // Traduce la pagina (o una sua parte). Il testo italiano resta nei
  // data-*, cosi' si puo' tradurre di nuovo.
  function translate(root = document) {
    for (const el of root.querySelectorAll("[data-i18n]")) {
      if (!el.dataset.i18n) el.dataset.i18n = el.textContent.trim();
      el.textContent = t(el.dataset.i18n);
    }
    for (const attr of ATTRIBUTES) {
      const store = "i18n" + attr.replace(/(^|-)(\w)/g, (_m, _d, c) => c.toUpperCase());
      for (const el of root.querySelectorAll(`[${attr}]`)) {
        if (!(store in el.dataset)) el.dataset[store] = el.getAttribute(attr);
        el.setAttribute(attr, t(el.dataset[store]));
      }
    }
    if (document.title && root === document) document.title = t(document.title);
  }

  function setLanguage(code) {
    try { localStorage.setItem(KEY, code); } catch (e) {}
    location.reload();
  }

  return {
    LANGUAGES, load, t, translate, setLanguage,
    get language() { return language; },
    // per Intl (date, numeri)
    get locale() { return { it: "it-IT", en: "en-GB", fr: "fr-FR", es: "es-ES" }[language]; },
  };
})();

const t = I18n.t;

if (typeof module !== "undefined") module.exports = { I18n };
