"""
Genera la guida PDF «Dal primo accordo al WAV» in italiano e in inglese, nella
radice del repository, dagli screenshot di docs/guida_brano/<lingua>/ (vedi
shots.py). Un solo testo per le due lingue: T(italiano, inglese) per la prosa,
ui("...") per i nomi di menu e pulsanti, presi dalle traduzioni del programma
(locales/), cosi' coincidono con quello che si vede sullo schermo.

Richiede reportlab (solo per rigenerare la guida, non per il programma):
    python3 docs/guida_brano/make_pdf.py          # tutte e due le lingue
    python3 docs/guida_brano/make_pdf.py en       # solo l'inglese
"""
import datetime
import json
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak, Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUTPUT = {"it": "SoundText_Guida_dal_primo_accordo_al_WAV.pdf",
          "en": "SoundText_Guide_from_first_chord_to_WAV.pdf"}
VERSION = "1.14"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DV-BI", os.path.join(FONT_DIR, "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFont(TTFont("DVM", os.path.join(FONT_DIR, "DejaVuSansMono.ttf")))
registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

ACCENT = colors.HexColor("#3d7bab")
TIP_BG = colors.HexColor("#fff7e0")
TIP_BORDER = colors.HexColor("#e8c96d")
WARN_BG = colors.HexColor("#fdecec")
WARN_BORDER = colors.HexColor("#e05555")
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#f2f2f2")

base = ParagraphStyle("base", fontName="DV", fontSize=10, leading=14.5, spaceAfter=5)
small = ParagraphStyle("small", parent=base, fontSize=8.5, leading=11.5, textColor=GREY)
caption = ParagraphStyle("caption", parent=small, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
h1 = ParagraphStyle("h1", fontName="DV-B", fontSize=18, leading=23, textColor=ACCENT, spaceBefore=4, spaceAfter=10)
h2 = ParagraphStyle("h2", fontName="DV-B", fontSize=12.5, leading=16, textColor=colors.black,
                    spaceBefore=10, spaceAfter=5)
code = ParagraphStyle("code", fontName="DVM", fontSize=9, leading=12.5, backColor=LIGHT,
                      borderPadding=(5, 6, 5, 6), spaceBefore=4, spaceAfter=9, leftIndent=6, rightIndent=6)
cell = ParagraphStyle("cell", parent=base, fontSize=9, leading=12, spaceAfter=0)
cell_b = ParagraphStyle("cell_b", parent=cell, fontName="DV-B", textColor=colors.white)
toc1 = ParagraphStyle("toc1", fontName="DV", fontSize=10.5, leading=17, leftIndent=0)

W = A4[0] - 4 * cm     # larghezza utile

# ------------------------------------------------------------------ lingua

LANG = "it"
_catalog = {}
_normalized = {}
missing = set()


def set_language(lang):
    global LANG, _catalog, _normalized
    LANG = lang
    _catalog, _normalized = {}, {}
    if lang != "it":
        with open(os.path.join(ROOT, "locales", f"{lang}.json"), encoding="utf-8") as f:
            _catalog = {k: v for k, v in json.load(f).items() if v}
        _normalized = {_norm(k): v for k, v in _catalog.items()}


def _norm(text):
    """La forma di confronto: senza &, icone iniziali, due punti e puntini finali."""
    text = text.replace("&", "").replace("…", "...").strip()
    text = text.lstrip("?🎲▶↺ ").rstrip(":").strip()
    return text[:-3].rstrip() if text.endswith("...") else text


def T(it, en):
    """La prosa nella lingua della guida."""
    return it if LANG == "it" else en


def ui(text):
    """Un testo dell'interfaccia com'e' sullo schermo nella lingua della guida."""
    if LANG == "it":
        return text.rstrip(":")
    if text in _catalog:
        return _catalog[text].replace("&", "").rstrip(":")
    if _norm(text) not in _normalized:
        missing.add(text)
        return text
    out = _normalized[_norm(text)].replace("&", "").strip()
    out = out.lstrip("?🎲↺ ").rstrip(":").strip()     # come e' scritto nel testo della guida
    if text.endswith(("...", "…")) and not out.endswith(("...", "…")):
        out += "..."
    if text.startswith("▶") and not out.startswith("▶"):
        out = "▶ " + out
    return out


def b(text):
    """Un comando dell'interfaccia in grassetto."""
    return f"<b>{ui(text)}</b>"


def path(*parts):
    """Un percorso di menu: Progetto → Esporta → Mix audio (WAV)..."""
    return "<b>" + " → ".join(ui(p) for p in parts) + "</b>"


def mono(text):
    return f"<font name='DVM'>{text}</font>"


# ------------------------------------------------------------------ impaginazione

class Doc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))


def title():
    return T("SoundText — Dal primo accordo al WAV", "SoundText — From the first chord to the WAV")


def page_decor(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("DV", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(2 * cm, 1.2 * cm, title())
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
        canvas.setStrokeColor(colors.HexColor("#dddddd"))
        canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


def P(text, style=base):
    return Paragraph(text, style)


def steps(items, start=1):
    return ListFlowable([ListItem(P(t), leftIndent=16, value=i) for i, t in enumerate(items, start)],
                        bulletType="1", start=start, bulletFontName="DV-B", bulletFontSize=10,
                        leftIndent=16, bulletColor=ACCENT, spaceAfter=6)


def bullets(items):
    return ListFlowable([ListItem(P(t), leftIndent=12) for t in items], bulletType="bullet", start="•",
                        leftIndent=12, bulletFontName="DV", spaceAfter=6)


def box(heading, text, bg=TIP_BG, border=TIP_BORDER):
    content = [P(f"<b>{heading}</b>", ParagraphStyle("bt", parent=base, spaceAfter=2))]
    for t in (text if isinstance(text, list) else [text]):
        content.append(P(t, ParagraphStyle("bb", parent=base, spaceAfter=2)))
    t = Table([[content]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 8)])


def tip(text, heading=None):
    return box(heading or T("Consiglio", "Tip"), text)


def warn(text, heading=None):
    return box(heading or T("Attenzione", "Watch out"), text, WARN_BG, WARN_BORDER)


def table(rows, widths, header=True):
    data = [[P(c, cell_b if header and i == 0 else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
    for i in range(1 if header else 0, len(rows)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7f9fb")))
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 10)])


def img(name, width_cm, text):
    image_path = os.path.join(HERE, LANG, name)
    iw, ih = ImageReader(image_path).getSize()
    w = min(width_cm * cm, W)
    h = w * ih / iw
    frame = Table([[Image(image_path, width=w, height=h)]], colWidths=[w + 2])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return KeepTogether([Spacer(1, 4), frame, P(text, caption)])


def chapter(text):
    # Pagina nuova solo se nella corrente resta poco spazio.
    return [CondPageBreak(9 * cm), Spacer(1, 8), P(text, h1)]


def section(text, room=5):
    return [CondPageBreak(room * cm), P(text, h2)]


# ------------------------------------------------------------------ il testo

def build_story():
    N = {  # i nomi del brano, come in shots.py
        "song": T("Il mio primo brano", "My first song"), "file": T("Il_mio_primo_brano", "My_first_song"),
        "chords": T("Accordi", "Chords"), "drums": T("Batteria", "Drums"), "bass": T("Basso", "Bass"),
        "guitar": T("ChitarraElettrica", "ElectricGuitar"), "voice": T("Voce", "Vocals"),
        "verse": T("Strofa", "Verse"), "chorus": T("Ritornello", "Chorus"), "verse2": T("Strofa 2", "Verse 2"),
        "groove_full": T("Groove pieno", "Full groove"), "melody": T("Melodia", "Melody"),
    }
    story = []

    # -------------------------------------------------------------- copertina
    story += [
        Spacer(1, 4 * cm),
        P("SoundText", ParagraphStyle("c0", fontName="DV-B", fontSize=34, leading=40, textColor=ACCENT,
                                      alignment=TA_CENTER)),
        Spacer(1, 0.6 * cm),
        P(T("Dal primo accordo al WAV", "From the first chord to the WAV"),
          ParagraphStyle("c1", fontName="DV-B", fontSize=22, leading=28, alignment=TA_CENTER)),
        Spacer(1, 0.4 * cm),
        P(T("Guida pratica per costruire un brano dall'inizio alla fine:<br/>accordi, batteria, basso, chitarra, "
            "voce, effetti, amplificatore, plugin, mastering ed export audio",
            "A hands-on guide to building a song from start to finish:<br/>chords, drums, bass, guitar, vocals, "
            "effects, amplifier, plugins, mastering and audio export"),
          ParagraphStyle("c2", parent=base, fontSize=12, leading=18, alignment=TA_CENTER, textColor=GREY)),
        Spacer(1, 1.2 * cm),
    ]
    cover = os.path.join(HERE, LANG, "01_struttura.png")
    iw, ih = ImageReader(cover).getSize()
    story.append(Image(cover, width=W, height=W * ih / iw))
    today = datetime.date.today()
    story += [Spacer(1, 1.5 * cm),
              P(T(f"SoundText {VERSION} · edizione del {today.strftime('%d/%m/%Y')}",
                  f"SoundText {VERSION} · edition of {today.strftime('%Y-%m-%d')}"),
                ParagraphStyle("c3", parent=small, alignment=TA_CENTER))]

    # -------------------------------------------------------------- indice
    story += [PageBreak(), P(T("Indice", "Contents"), ParagraphStyle("hi", parent=h1))]
    toc = TableOfContents()
    toc.levelStyles = [toc1]
    toc.dotsMinLevel = 0
    story.append(toc)

    # -------------------------------------------------------------- 1
    story += [PageBreak(), P(T("1. Che cosa costruiremo", "1. What we will build"), h1)]
    story += [
        P(T("In questa guida costruiamo, passo dopo passo, un brano completo e lo trasformiamo in un file audio "
            "<b>WAV</b> pronto da ascoltare ovunque, da mandare a un amico o da caricare online. Useremo quasi "
            "tutto quello che SoundText mette a disposizione: i generatori automatici, la scrittura a mano delle "
            "note, la registrazione, il mixer, gli effetti, l'amplificatore per chitarra e il mastering.",
            "In this guide we build a complete song step by step and turn it into a <b>WAV</b> audio file, ready "
            "to play anywhere, send to a friend or upload online. We will use almost everything SoundText offers: "
            "the generators, writing notes by hand, recording, the mixer, effects, the guitar amplifier and "
            "mastering.")),
        P(T(f"Il brano d'esempio si chiama <b>«{N['song']}»</b>:",
            f"The example song is called <b>“{N['song']}”</b>:")),
        table([[T("Elemento", "Item"), T("Scelta", "Choice")],
               [T("Tonalità", "Key"), T("La minore (Am)", "A minor (Am)")],
               [T("Tempo e metrica", "Tempo and meter"), "100 BPM, 4/4"],
               [T("Struttura", "Form"), T(f"{N['verse']} (8 battute) → {N['chorus']} (8 battute) → {N['verse2']} "
                                          "(8 battute)",
                                          f"{N['verse']} (8 bars) → {N['chorus']} (8 bars) → {N['verse2']} (8 bars)")],
               [T("Tracce", "Tracks"), T("Accordi (pianoforte), Batteria, Basso, Chitarra elettrica con "
                                         "amplificatore, Voce (registrata) o melodia scritta",
                                         "Chords (piano), Drums, Bass, Electric guitar through an amplifier, "
                                         "Vocals (recorded) or a written melody")],
               [T("Risultato", "Result"), T("Un file WAV a 48 kHz / 24 bit, con effetti e mastering",
                                            "A 48 kHz / 24-bit WAV file, with effects and mastering")]],
              [0.28, 0.72]),
        *section(T("Il percorso, in sintesi:", "The route at a glance:")),
        table([[T("Passo", "Step"), T("Che cosa si fa", "What you do"), T("Capitolo", "Chapter")],
               ["1", T("Installare e preparare i suoni", "Install SoundText and get the sounds"), "2"],
               ["2", T("Creare il progetto: tempo, metrica, tonalità, salvataggio",
                       "Create the project: tempo, meter, key, save"), "3"],
               ["3", T("Scrivere il giro di accordi (strofa e ritornello)",
                       "Write the chord progression (verse and chorus)"), "4"],
               ["4", T("Aggiungere batteria e basso, oppure arrangiare tutto in un colpo",
                       "Add drums and bass, or arrange everything at once"), "5"],
               ["5", T("Aggiungere la chitarra elettrica", "Add the electric guitar"), "6"],
               ["6", T("Melodia: scriverla a mano, suonarla o registrare la voce",
                       "Melody: write it, play it or record your voice"), "7"],
               ["7", T("Ascoltare, sistemare la struttura, bilanciare i volumi",
                       "Listen, fix the form, balance the levels"), "8"],
               ["8", T("Effetti sulle tracce", "Track effects"), "9"],
               ["9", T("Amplificatore o profilo NAM sulla chitarra", "Amplifier or NAM profile on the guitar"), "10"],
               ["10", T("Mastering del mix finale", "Master the final mix"), "11"],
               ["11", T("Esportare il WAV", "Export the WAV"), "12"],
               ["12", T("Facoltativo: suoni da studio con programmi esterni (re-amping)",
                        "Optional: studio sounds with other programs (re-amping)"), "13"],
               ["13", T("Facoltativo: plugin VST3 e LV2, strumenti SFZ", "Optional: VST3 and LV2 plugins, SFZ "
                                                                        "instruments"), "14"]],
              [0.1, 0.72, 0.18]),
        tip([T("Non serve seguire tutto alla lettera: ogni capitolo sta in piedi da solo. Se hai già un brano, "
               "puoi saltare direttamente agli effetti (capitolo 9) o all'esportazione (capitolo 12).",
               "You don't have to follow everything to the letter: each chapter stands on its own. If you already "
               "have a song, jump straight to effects (chapter 9) or export (chapter 12)."),
             T(f"Qualunque comando si trova anche con <b>Ctrl+K</b> ({b('Cerca un comando...')}): scrivi cosa "
               "vuoi fare («esporta», «registra», «basso»...) e premi Invio.",
               f"Any command can also be found with <b>Ctrl+K</b> ({b('Cerca un comando...')}): type what you "
               "want to do (“export”, “record”, “bass”...) and press Enter."),
             T("Ogni passo si vede anche nella serie di video tutorial (in inglese, con i sottotitoli in "
               "italiano): youtube.com/playlist?list=PLbVfXEqrD3P4",
               "Every step is also shown in the video tutorial series (English, with subtitles in Italian, "
               "French and Spanish): youtube.com/playlist?list=PLbVfXEqrD3P4")],
            T("Tre cose utili fin da subito", "Three useful things from the start")),
    ]

    # -------------------------------------------------------------- 2
    story += chapter(T("2. Prima di cominciare", "2. Before you start"))
    story += [
        P(T("Per installare SoundText segui le istruzioni del README su GitHub (github.com/openssound/soundtext) "
            "o l'episodio 1 dei video: su Linux c'è l'AppImage, il pacchetto portable e lo script di "
            "installazione; su Windows e macOS l'installer o lo script.",
            "To install SoundText, follow the README on GitHub (github.com/openssound/soundtext) or episode 1 "
            "of the videos: on Linux there are the AppImage, the portable package and the install script; on "
            "Windows and macOS the installer or the script.")),
        *section(T("I suoni", "The sounds")),
        P(T("SoundText suona le tracce scritte (note e accordi) con un <b>SoundFont</b> General MIDI, un file "
            "<b>.sf2</b> o <b>.sf3</b> con i suoni degli strumenti. Non è incluso nel programma: al primo avvio, "
            "se non ne trova uno, SoundText propone di scaricare <b>FluidR3 GM</b> (gratuito, circa 150 MB).",
            "SoundText plays written tracks (notes and chords) with a General MIDI <b>SoundFont</b>, an "
            "<b>.sf2</b> or <b>.sf3</b> file holding the instrument sounds. It isn't bundled: at first start, if it "
            "can't find one, SoundText offers to download <b>FluidR3 GM</b> (free, about 150 MB).")),
        steps([
            T(f"Rispondi <b>Sì</b>: si apre {path('Suoni', 'Scarica e installa...')} con FluidR3 GM già "
              f"spuntato. Premi {b('Installa')} e aspetta la fine del download.",
              f"Answer <b>Yes</b>: {path('Suoni', 'Scarica e installa...')} opens with FluidR3 GM already "
              f"ticked. Press {b('Installa')} and wait for the download to finish."),
            T(f"Se hai già un SoundFont, indicalo con {path('Suoni', 'SoundFont', 'Scegli SoundFont (.sf2/.sf3)...')}"
              ". La scelta viene ricordata.",
              f"If you already have a SoundFont, pick it with "
              f"{path('Suoni', 'SoundFont', 'Scegli SoundFont (.sf2/.sf3)...')}. The choice is remembered."),
            T(f"Per una prova: {path('Progetto', 'Apri esempio...')}, scegli un esempio e premi <b>Play</b>.",
              f"To check: {path('Progetto', 'Apri esempio...')}, pick an example and press <b>Play</b>."),
        ]),
        img("11_scarica.png", 14, T("«Scarica e installa»: SoundFont, strumenti campionati SFZ, profili NAM e "
                                    "casse IR per la chitarra, plugin gratuiti e motori, tutto dalla stessa finestra.",
                                    "“Download and install”: SoundFonts, SFZ sampled instruments, NAM profiles and "
                                    "cabinet IRs for the guitar, free plugins and engines, all from one window.")),
        P(T("La stessa finestra scarica anche il resto che useremo: gli <b>strumenti campionati SFZ</b> "
            "(capitolo 14), i <b>profili NAM</b> e le <b>casse IR</b> per l'amplificatore (capitolo 10), i "
            "<b>plugin gratuiti</b> e il motore dello strumento SFZ interno. Quello che è già installato si salta, "
            "e un download interrotto riprende la volta dopo.",
            "The same window downloads everything else we will use: <b>SFZ sampled instruments</b> (chapter 14), "
            "<b>NAM profiles</b> and <b>cabinet IRs</b> for the amplifier (chapter 10), <b>free plugins</b> and the "
            "engine of the built-in SFZ instrument. Anything already installed is skipped, and an interrupted "
            "download resumes next time.")),
        tip([T("Usa le <b>cuffie</b> o delle casse decenti: gli effetti (soprattutto riverbero, compressore e "
               "limiter) si giudicano male dagli altoparlanti di un portatile.",
               "Use <b>headphones</b> or decent speakers: effects (especially reverb, compressor and limiter) are "
               "hard to judge on laptop speakers."),
             T(f"La lingua dell'interfaccia si cambia in {path('Opzioni', 'Lingua')} (italiano, inglese, francese, "
               f"spagnolo), il tema in {path('Opzioni', 'Tema')}.",
               f"The interface language is set in {path('Opzioni', 'Lingua')} (English, Italian, French, "
               f"Spanish), the theme in {path('Opzioni', 'Tema')}.")]),
    ]

    # -------------------------------------------------------------- 3
    story += chapter(T("3. Il progetto e la finestra", "3. The project and the window"))
    story += [
        steps([
            T(f"{path('Progetto', 'Nuovo')} (<b>Ctrl+N</b>).", f"{path('Progetto', 'Nuovo')} (<b>Ctrl+N</b>)."),
            T("Nella barra dei comandi, riquadro <b>Tempo / Metrica / Levare / Tonalità</b>: imposta <b>100 BPM</b>, "
              "<b>4/4</b> e <b>Am</b>. La tonalità viene proposta dai generatori.",
              f"In the command bar, the <b>{ui('Tempo')} / {ui('Metrica')} / {ui('Levare')} / {ui("Tonalita'")}"
              "</b> box: set <b>100 BPM</b>, <b>4/4</b> and <b>Am</b>. The generators will suggest that key."),
            T(f"Salva subito: {path('Progetto', 'Salva')} (<b>Ctrl+S</b>), per esempio come "
              f"<b>{N['file']}.st</b>.",
              f"Save right away: {path('Progetto', 'Salva')} (<b>Ctrl+S</b>), for example as "
              f"<b>{N['file']}.st</b>."),
            T(f"Controlla di essere nella vista {b('Struttura')} (pulsante in alto a destra; è la vista iniziale).",
              f"Make sure you are in the {b('Struttura')} view (button at the top right; it's the starting view)."),
        ]),
        tip(T(f"Salvare all'inizio non è un vezzo: le registrazioni e i file audio importati finiscono nella "
              f"cartella <b>{N['file']}_audio/</b> accanto al file .st. Da qui in poi premi <b>Ctrl+S</b> ogni "
              "tanto, e ricorda che <b>Ctrl+Z</b> annulla qualunque modifica. Se il programma si chiude male, al "
              "riavvio propone di recuperare il lavoro non salvato.",
              f"Saving early matters: recordings and imported audio files go into the <b>{N['file']}_audio/</b> "
              "folder next to the .st file. From here on press <b>Ctrl+S</b> now and then, and remember that "
              "<b>Ctrl+Z</b> undoes any change. If the program closes unexpectedly, it offers to recover your "
              "unsaved work at the next start.")),
        img("01_struttura.png", 17, T(f"La vista Struttura del brano finito: una riga per traccia, i box "
                                      f"({N['verse']}, {N['chorus']}, {N['verse2']}) sull'asse del tempo, le "
                                      "testate delle tracce a sinistra e la riga del Master in fondo.",
                                      f"The Structure view of the finished song: one row per track, the boxes "
                                      f"({N['verse']}, {N['chorus']}, {N['verse2']}) along the timeline, the track "
                                      "headers on the left and the Master row at the bottom.")),
        *section(T("Le parti della finestra", "The parts of the window")),
        bullets([
            T("<b>Barra dei comandi</b>: torna all'inizio, <b>Play</b>/Pausa (<b>Spazio</b> o F5), Stop (F6), "
              "<b>●</b> Registra, loop A-B, metronomo e velocità d'ascolto; il display con tempo trascorso e "
              f"battuta; tempo, metrica, levare e tonalità; le viste {b('Struttura')} e {b('Testo')}; a destra "
              f"{b('Cerca un comando...')}.",
              "<b>Command bar</b>: back to start, <b>Play</b>/Pause (<b>Space</b> or F5), Stop (F6), <b>●</b> "
              "Record, A-B loop, metronome and listening speed; the display with elapsed time and bar; tempo, "
              f"meter, pickup and key; the {b('Struttura')} and {b('Testo')} views; on the right "
              f"{b('Cerca un comando...')}."),
            T("<b>Testate delle tracce</b> (a sinistra): nome e strumento, <b>M</b> (Mute), <b>S</b> (Solo), "
              "<b>●</b> per registrare (tracce audio), <b>FX</b> (effetti), il menu <b>⋯</b> con tutte le azioni "
              "della traccia e due manopole: <b>Vol</b> e <b>Pan</b>.",
              "<b>Track headers</b> (left): name and instrument, <b>M</b> (Mute), <b>S</b> (Solo), <b>●</b> to "
              "record (audio tracks), <b>FX</b> (effects), the <b>⋯</b> menu with every track action and two "
              "knobs: <b>Vol</b> and <b>Pan</b>."),
            T("<b>Righe con i box</b>: ogni box è un pezzo di musica con un nome. Si trascina nel tempo, si apre "
              "con un doppio click, il tasto destro dà tutte le azioni (ascolta, duplica, rinomina, trasponi, "
              "taglia/copia/incolla, elimina).",
              "<b>Rows of boxes</b>: each box is a named piece of music. Drag it along the timeline, double-click "
              "to open it, right-click for every action (listen, duplicate, rename, transpose, cut/copy/paste, "
              "delete)."),
            T("<b>Righello</b> in alto, con i nomi delle sezioni: clic per spostare la testina (il prossimo Play "
              "parte da lì).",
              "<b>Ruler</b> at the top, with the section names: click to move the playhead (the next Play starts "
              "there)."),
            T("<b>Riga del Master</b> in fondo: il pulsante <b>FX</b> del master, il volume generale, il "
              "misuratore di livello con la spia <b>CLIP</b>; accanto, la barra di avanzamento (clic per saltare).",
              "<b>Master row</b> at the bottom: the master <b>FX</b> button, the overall volume, the level meter "
              "with the <b>CLIP</b> light; next to it, the progress bar (click to jump)."),
            T(f"<b>{ui('Come si usa')}</b>, sopra le testate: le scorciatoie della vista Struttura.",
              f"<b>{ui('Come si usa')}</b>, above the headers: the shortcuts of the Structure view."),
        ]),
    ]

    # -------------------------------------------------------------- 4
    story += chapter(T("4. Gli accordi: il giro armonico", "4. The chords: the progression"))
    story += [
        P(T("Gli accordi sono la base su cui si appoggiano basso e chitarra: si parte da qui. SoundText li scrive "
            "per te a partire da uno stile.",
            "The chords are what bass and guitar lean on, so we start here. SoundText writes them for you from "
            "a style.")),
        steps([
            T(f"Clicca {b('+ Aggiungi traccia')} (sotto l'ultima testata) e, nella sezione "
              f"{b('Genera una traccia')}, scegli {b('Giro armonico...')}",
              f"Click {b('+ Aggiungi traccia')} (below the last header) and, in the {b('Genera una traccia')} "
              f"section, choose {b('Giro armonico...')}"),
            T(f"Nel dialogo: <b>Tonalità</b> Am (già proposta), <b>Stile</b> {b('Pop minore (i-VI-III-VII)')}, "
              f"<b>Durata di ogni accordo</b> 1 battuta, <b>Battute</b> 8.",
              f"In the dialog: <b>Key</b> Am (already suggested), <b>Style</b> {b('Pop minore (i-VI-III-VII)')}, "
              f"<b>{ui('Durata di ogni accordo:')}</b> 1 bar, <b>Bars</b> 8."),
            T(f"Premi {b('▶ Ascolta')}. Se non ti convince premi {b('Nuova variazione')}, oppure cambia stile.",
              f"Press {b('▶ Ascolta')}. If you don't like it press {b('Nuova variazione')}, or change the style."),
            T(f"Premi <b>OK</b>: nasce la traccia <b>{N['chords']}</b> (pianoforte) con un box di 8 battute.",
              f"Press <b>OK</b>: the <b>{N['chords']}</b> track (piano) appears with an 8-bar box."),
            T(f"Tasto destro sul box → {b('Rinomina...')} → «{N['verse']}».",
              f"Right-click the box → {b('Rinomina...')} → “{N['verse']}”."),
        ]),
        img("02_giro.png", 12.5, T("Il dialogo del giro armonico: stile, durata degli accordi, battute, "
                                   "variabilità e l'anteprima modificabile. «Ascolta» fa sentire il risultato "
                                   "prima di confermare.",
                                   "The progression dialog: style, chord length, bars, variability and the "
                                   "editable preview. “Listen” plays the result before you confirm.")),
        *section(T("Il ritornello", "The chorus")),
        steps([
            T(f"Tasto destro sul nome della traccia <b>{N['chords']}</b> → "
              f"{b('Genera giro armonico in questa traccia...')}",
              f"Right-click the <b>{N['chords']}</b> track name → {b('Genera giro armonico in questa traccia...')}"),
            T(f"Stile {b('Minore epico (i-VI-VII-i)')}, 8 battute, <b>OK</b>: il nuovo box viene messo subito dopo "
              f"la strofa. Rinominalo «{N['chorus']}».",
              f"Style {b('Minore epico (i-VI-VII-i)')}, 8 bars, <b>OK</b>: the new box goes right after the verse. "
              f"Rename it “{N['chorus']}”."),
            T(f"Seleziona il box «{N['verse']}» e premi <b>Ctrl+D</b> (Duplica): la copia va nel primo spazio libero, "
              f"cioè dopo il ritornello. Rinominala «{N['verse2']}».",
              f"Select the “{N['verse']}” box and press <b>Ctrl+D</b> (Duplicate): the copy goes into the first "
              f"free space, after the chorus. Rename it “{N['verse2']}”."),
        ]),
        tip(T("Usa nomi come Intro, Strofa, Pre-ritornello, Ritornello, Ponte, Finale: «Arrangia il brano» "
              "(capitolo 5) ne ricava l'intensità di ogni sezione.",
              "Use names like Intro, Verse, Pre-chorus, Chorus, Bridge, Outro: “Arrange the song” (chapter 5) "
              "reads each section's intensity from them."), T("Nomi che contano", "Names that matter")),
        *section(T("Variabilità, cadenza e anteprima", "Variability, cadence and preview")),
        P(T(f"A 0% lo stile viene scritto così com'è; alzando la <b>Variabilità</b> compaiono accordi più ricchi "
            f"(settime, sus), dominanti secondarie e sostituzioni. I preset <b>Fedele</b>, <b>Musicista</b> e "
            f"<b>Creativo</b> sono buoni punti di partenza. {b('Cadenza finale')} chiude il giro sulla tonica. Il "
            f"testo nell'anteprima si può modificare a mano prima di premere OK, e "
            f"{b('Rigenera queste')} cambia solo le battute indicate.",
            f"At 0% the style is written as is; raising <b>Variability</b> brings richer chords (sevenths, sus), "
            f"secondary dominants and substitutions. The presets <b>{ui('Fedele')}</b>, <b>{ui('Musicista')}</b> "
            f"and <b>{ui('Creativo')}</b> are good starting points. {b('Cadenza finale')} ends the progression on "
            f"the tonic. You can edit the preview text by hand before pressing OK, and {b('Rigenera queste')} "
            "changes only the bars you choose.")),
        tip(T(f"Vuoi vedere cosa c'è dentro un box? Doppio click: si apre l'editor con il testo, per esempio "
              f"{mono('4: 4Am 4F 4C 4G')} (griglia a quarti, ogni accordo dura 4 quarti = una battuta). Nel "
              "capitolo 7 vediamo come si legge questa scrittura.",
              f"Want to see what's inside a box? Double-click it: the editor opens with the text, for example "
              f"{mono('4: 4Am 4F 4C 4G')} (a quarter-note grid, each chord lasts 4 quarters = one bar). Chapter 7 "
              "explains how to read it.")),
    ]

    # -------------------------------------------------------------- 5
    story += chapter(T("5. Batteria e basso", "5. Drums and bass"))
    story += [
        *section(T("Batteria: strofe leggere, ritornello pieno", "Drums: light verses, full chorus")),
        steps([
            T(f"{b('+ Aggiungi traccia')} → {b('Batteria...')}", f"{b('+ Aggiungi traccia')} → {b('Batteria...')}"),
            T(f"<b>Stile</b> Rock, <b>Battute</b> 8, {b('Fill ogni N battute')} 4, {b('Fill a frasi')} spuntato, "
              f"<b>Intensità</b> {b('Leggera (strofa, intro)')}. Ascolta con {b('Con le altre tracce')} spuntato "
              "per sentirla insieme agli accordi, poi <b>OK</b>.",
              f"<b>Style</b> Rock, <b>Bars</b> 8, {b('Fill ogni N battute')} 4, {b('Fill a frasi')} ticked, "
              f"<b>Intensity</b> {b('Leggera (strofa, intro)')}. Listen with {b('Con le altre tracce')} ticked to "
              "hear it with the chords, then <b>OK</b>."),
            T(f"Tasto destro sul nome della traccia <b>{N['drums']}</b> → {b('Genera batteria in questa traccia...')}"
              f": 8 battute con <b>Intensità</b> {b('Piena (ritornello)')}: passa al ride, suona più forte e apre "
              f"con un crash. Il box va dopo il primo: rinominalo «{N['groove_full']}».",
              f"Right-click the <b>{N['drums']}</b> track name → {b('Genera batteria in questa traccia...')}: "
              f"8 bars with <b>Intensity</b> {b('Piena (ritornello)')}: it moves to the ride, plays louder and "
              f"opens with a crash. The box goes after the first one: rename it “{N['groove_full']}”."),
            T(f"Per la {N['verse2']} duplica il primo box (<b>Ctrl+D</b>), oppure generane uno nuovo con "
              f"{b('Finale sull' + chr(39) + 'ultima battuta')} spuntato per chiudere il brano con un colpo di crash.",
              f"For {N['verse2']} duplicate the first box (<b>Ctrl+D</b>), or generate a new one with "
              f"{b('Finale sull' + chr(39) + 'ultima battuta')} ticked to end the song on a crash."),
        ]),
        img("03_batteria.png", 12, T("Il dialogo della batteria: stile, battute, fill, intensità e variabilità. "
                                     "L'anteprima è il testo della batteria (kick, snare, hihat...), modificabile.",
                                     "The drum dialog: style, bars, fills, intensity and variability. The preview "
                                     "is the drum text (kick, snare, hihat...), and you can edit it.")),
        *section(T("Basso: segue gli accordi da solo", "Bass: it follows the chords by itself")),
        steps([
            T(f"{b('+ Aggiungi traccia')} → {b('Basso dagli accordi...')} (è attivo solo quando il brano ha una "
              "traccia di accordi).",
              f"{b('+ Aggiungi traccia')} → {b('Basso dagli accordi...')} (available only once the song has a "
              "chord track)."),
            T(f"<b>Accordi da</b>: {N['chords']}. <b>Stile</b>: {b('Fondamentale/quinta')} (semplice e solido) "
              f"oppure {b('Ottave')} per un ritornello più mosso. <b>OK</b>.",
              f"<b>Chords from</b>: {N['chords']}. <b>Style</b>: {b('Fondamentale/quinta')} (simple and solid) or "
              f"{b('Ottave')} for a busier chorus. <b>OK</b>."),
            T(f"Il basso copre tutto il giro: {N['verse'].lower()}, {N['chorus'].lower()} e {N['verse2'].lower()}.",
              f"The bass covers the whole progression: {N['verse'].lower()}, {N['chorus'].lower()} and "
              f"{N['verse2'].lower()}."),
        ]),
        tip([T(f"<b>Rigenera solo alcune battute</b>: se una battuta non ti piace, indica «da N a M» sotto "
               f"l'anteprima e premi {b('Rigenera queste')}: cambiano solo quelle.",
               f"<b>Regenerate only some bars</b>: if a bar doesn't work, set “from N to M” below the preview and "
               f"press {b('Rigenera queste')}: only those change."),
             T("<b>Shift+Spazio</b> ascolta solo il box selezionato; <b>Spazio</b> tutto il brano.",
               "<b>Shift+Space</b> plays only the selected box; <b>Space</b> the whole song.")],
            T("Per rifinire", "Fine-tuning")),
        *section(T("La via veloce: Arrangia il brano", "The fast lane: Arrange the song"), 8),
        P(T(f"Se hai già la traccia degli accordi divisa in sezioni, {path('Componi', 'Arrangia il brano...')} "
            "scrive in un colpo batteria, basso e accompagnamento per tutto il brano, sezione per sezione: "
            "l'intensità di ognuna viene dal nome del box (strofa leggera, ritornello pieno) e si può cambiare "
            "nella tabella. Poi ogni box si ritocca come quelli generati a mano.",
            f"If your chord track is already split into sections, {path('Componi', 'Arrangia il brano...')} "
            "writes drums, bass and comping for the whole song in one go, section by section: each section's "
            "intensity comes from the box name (light verse, full chorus) and can be changed in the table. "
            "Then you refine each box like the ones you generated by hand.")),
        img("10_arrangia.png", 12, T("«Arrangia il brano»: stili di batteria, basso e accompagnamento, e "
                                     "l'intensità di ogni sezione.",
                                     "“Arrange the song”: drum, bass and comping styles, and each section's "
                                     "intensity.")),
    ]

    # -------------------------------------------------------------- 6
    story += chapter(T("6. La chitarra elettrica", "6. The electric guitar"))
    story += [
        P(T("Per usare bene l'amplificatore (capitolo 10) serve un suono di chitarra elettrica <b>pulito</b>: "
            "sarà l'amplificatore di SoundText a distorcerlo, come succede con una chitarra vera collegata a un "
            "amplificatore.",
            "To get the most out of the amplifier (chapter 10) you need a <b>clean</b> electric guitar sound: "
            "SoundText's amplifier will distort it, just like a real guitar plugged into an amp.")),
        *section(T("Creare lo strumento", "Create the instrument")),
        steps([
            T(f"{path('Suoni', 'Gestisci strumenti...')} → {b('+ Nuovo strumento')}.",
              f"{path('Suoni', 'Gestisci strumenti...')} → {b('+ Nuovo strumento')}."),
            T(f"<b>Nome nel programma</b>: {N['guitar']} (una parola, senza spazi).",
              f"<b>Name in the program</b>: {N['guitar']} (one word, no spaces)."),
            T(f"{b('Suono General MIDI:')} digita «clean» e scegli <b>Electric Guitar (clean)</b>. Ottava, "
              "estensione e voicing vengono compilati da soli. <b>OK</b>.",
              f"{b('Suono General MIDI:')} type “clean” and choose <b>Electric Guitar (clean)</b>. Octave, range "
              "and voicing are filled in for you. <b>OK</b>."),
        ]),
        warn(T("Non scegliere «Overdriven Guitar» o «Distortion Guitar» se poi userai l'amplificatore: "
               "distorceresti due volte, con un suono impastato e confuso.",
               "Don't pick “Overdriven Guitar” or “Distortion Guitar” if you are going to use the amplifier: you "
               "would distort twice, with a muddy, confused sound.")),
        *section(T("Generare l'accompagnamento", "Generate the comping")),
        steps([
            T(f"{b('+ Aggiungi traccia')} → {b('Accompagnamento o riff...')} e scegli <b>{N['guitar']}</b> come "
              "strumento (polifonico = accompagnamento).",
              f"{b('+ Aggiungi traccia')} → {b('Accompagnamento o riff...')} and choose <b>{N['guitar']}</b> as "
              "the instrument (polyphonic = comping)."),
            T(f"<b>Accordi da</b>: {N['chords']}. <b>Stile</b>: {b('Accordi battuti (comping)')}. Lascia spuntato "
              f"{b('Rivolti vicini')}: gli accordi si muovono il meno possibile, come li suonerebbe un chitarrista.",
              f"<b>Chords from</b>: {N['chords']}. <b>Style</b>: {b('Accordi battuti (comping)')}. Leave "
              f"{b('Rivolti vicini')} ticked: the chords move as little as possible, the way a guitarist would "
              "play them."),
            T(f"{b('▶ Ascolta')}, poi <b>OK</b>. Per ora suonerà pulita: l'amplificatore arriva nel capitolo 10.",
              f"{b('▶ Ascolta')}, then <b>OK</b>. For now it sounds clean: the amplifier comes in chapter 10."),
        ]),
        tip([T("Un suono più vero: in «Scarica e installa» c'è la <b>Chitarra elettrica pulita FreePats</b>, "
               "campionata. Installala insieme al motore SFZ interno e assegnala alla traccia come strumento SFZ "
               "(capitolo 14).",
               "A more realistic sound: “Download and install” has the sampled <b>FreePats clean electric "
               "guitar</b>. Install it together with the built-in SFZ engine and assign it to the track as an SFZ "
               "instrument (chapter 14)."),
             T("Hai una chitarra vera? Crea invece una <b>traccia audio</b> e registrala collegata all'ingresso "
               "<b>INST/Hi-Z</b> della scheda audio, senza amplificatore: si registra il suono pulito e "
               "l'amplificatore di SoundText lo lavora dopo, e puoi cambiarlo quando vuoi senza rifare la ripresa.",
               "Have a real guitar? Create an <b>audio track</b> instead and record it through the <b>INST/Hi-Z</b> "
               "input of your audio interface, without an amp: you record the clean sound, SoundText's amplifier "
               "shapes it afterwards, and you can change it any time without re-recording.")]),
    ]

    # -------------------------------------------------------------- 7
    story += chapter(T("7. La melodia: scritta, suonata o registrata", "7. The melody: written, played or recorded"))
    story += [
        *section(T("Strada A: scrivere le note", "Route A: write the notes")),
        steps([
            T(f"{b('+ Aggiungi traccia')} → {b('Traccia con strumento...')} (<b>Ctrl+T</b>): nome "
              f"«{N['melody']}», strumento Trumpet (o flauto, sax, violino...).",
              f"{b('+ Aggiungi traccia')} → {b('Traccia con strumento...')} (<b>Ctrl+T</b>): name "
              f"“{N['melody']}”, instrument Trumpet (or flute, sax, violin...)."),
            T("Doppio click sulla riga della traccia, all'inizio della strofa: si apre l'editor di un nuovo box.",
              "Double-click the track's row at the start of the verse: the editor of a new box opens."),
            T("Scrivi le note (vedi sotto), premi <b>▶ Play</b> nell'editor per ascoltarle, poi <b>OK</b>.",
              "Type the notes (see below), press <b>▶ Play</b> in the editor to hear them, then <b>OK</b>."),
        ]),
        *section(T("La scrittura di SoundText in cinque minuti", "SoundText notation in five minutes"), 9),
        table([[T("Scrivi", "Write"), T("Significa", "Means"), T("Esempio", "Example")],
               [mono("c d e f g a b"), T("Note (do re mi fa sol la si)", "Notes"), mono("c e g")],
               [mono("*n"), T("Ottava della nota", "Octave of the note"), mono("a*4 c*5")],
               [f"{mono('#')}, {mono('b')}", T("Diesis e bemolle", "Sharp and flat"), mono("f# eb")],
               [mono("N:"), T("Griglia: 4 = quarti, 8 = ottavi, 16 = sedicesimi",
                              "Grid: 4 = quarters, 8 = eighths, 16 = sixteenths"), mono("8:")],
               [T("numero davanti", "number in front"), T("Durata in unità di griglia", "Length in grid units"),
                mono("2c*5") + T(" (due ottavi)", " (two eighths)")],
               [f"{mono('r')}, {mono('Nr')}", T("Pausa", "Rest"), mono("2r")],
               [f"{mono('N@')}, {mono('mf@')}", T("Volume delle note (velocity o dinamica)",
                                                  "Note volume (velocity or dynamic)"),
                f"{mono('90@')}, {mono('p@')}"],
               [mono("[...]"), T("Note insieme", "Notes together"), mono("[c e g]")],
               [T("Maiuscola", "Capital letter"), T("Accordo", "Chord"), mono("Am F C G7")],
               [mono("N(...)"), T("Ripete N volte", "Repeat N times"), mono("2(c d e)")]],
              [0.24, 0.48, 0.28]),
        P(T("Una frase per la strofa in La minore, a ottavi:", "A verse phrase in A minor, in eighths:")),
        P("8: 90@ a*4 c*5 e*5 d*5 2c*5 a*4 2r<br/>8: 100@ e*5 e*5 d*5 c*5 4a*4 4r", code),
        P(T(f"E una frase che cresce di volume ({mono('p@ &gt;&gt; ... f@')} è un crescendo):",
            f"And a phrase that grows louder ({mono('p@ &gt;&gt; ... f@')} is a crescendo):")),
        P("4: p@ &gt;&gt; a*4 c*5 e*5 f@ 4e*5", code),
        P(T("I colori dell'editor ti dicono come il programma legge il testo (note, accordi, pause...), un "
            "errore viene segnalato battuta per battuta prima di confermare, e un autocompletamento suggerisce "
            "accordi, stili e percussioni. Tutta la notazione è nella guida completa (<b>F1</b>).",
            "The editor's colors show how the program reads the text (notes, chords, rests...), mistakes are "
            "flagged bar by bar before you confirm, and autocomplete suggests chords, styles and percussion. The "
            "full notation is in the user guide (<b>F1</b>).")),
        *section(T("Strada B: suonarla con la tastiera", "Route B: play it on the keyboard")),
        P(T(f"Seleziona la traccia e scegli {path('Traccia', 'Suona con la tastiera in questa traccia...')}: suoni "
            "con la tastiera del computer o con una <b>tastiera MIDI</b> collegata (dinamica, accordi, pedale del "
            "sustain e pitch bend), e le note suonate diventano testo nella traccia, quantizzate sulla griglia che "
            "scegli.",
            f"Select the track and choose {path('Traccia', 'Suona con la tastiera in questa traccia...')}: play on "
            "the computer keyboard or a connected <b>MIDI keyboard</b> (dynamics, chords, sustain pedal and pitch "
            "bend), and what you play becomes text in the track, quantized to the grid you choose.")),
        *section(T("Strada C: registrare la voce", "Route C: record your voice"), 7),
        steps([
            T(f"{b('+ Aggiungi traccia')} → {b('Traccia audio (voce, chitarra, tastiera)...')}, nome "
              f"«{N['voice']}».",
              f"{b('+ Aggiungi traccia')} → {b('Traccia audio (voce, chitarra, tastiera)...')}, name "
              f"“{N['voice']}”."),
            T("Clicca sul righello dove vuoi iniziare, poi il pulsante rosso <b>●</b> della traccia (o "
              "<b>Ctrl+R</b>).",
              "Click the ruler where you want to start, then the track's red <b>●</b> button (or <b>Ctrl+R</b>)."),
            T(f"Nel dialogo: {b('Scheda audio')}, {b('Cosa registri')} e {b('Ingresso')}. Regola il gain sulla "
              "scheda perché le parti più forti arrivino tra <b>−12 e −6 dB</b> senza accendere la spia rossa.",
              f"In the dialog: {b('Scheda audio')}, {b('Cosa registri')} and {b('Ingresso')}. Set the gain on your "
              "interface so the loudest parts land between <b>−12 and −6 dB</b> without lighting the red clip "
              "light."),
            T(f"{b('Conteggio (battute):')} 1 o 2 battute, <b>● Registra</b>, canta, <b>■ Stop</b>. Riascolta con "
              f"<b>▶</b> insieme al brano e, se va bene, {b('Tieni la ripresa')}: diventa una clip nella traccia.",
              f"{b('Conteggio (battute):')} 1 or 2 bars, <b>● Record</b>, sing, <b>■ Stop</b>. Play it back with <b>▶</b> "
              f"along with the song and, if it works, {b('Tieni la ripresa')}: it becomes a clip in the track."),
        ]),
        tip([T("Per sentirti senza ritardo usa il <b>monitoraggio diretto</b> della scheda audio (tasto o "
               "manopola «direct monitor»): SoundText manda in cuffia solo il brano.",
               "To hear yourself without delay use your interface's <b>direct monitoring</b> (“direct monitor” "
               "switch or knob): SoundText sends only the song to your headphones."),
             T(f"La prima volta usa {b('Calibra...')} nel dialogo: con la compensazione della latenza la ripresa "
               "risulta perfettamente a tempo.",
               f"The first time, use {b('Calibra...')} in the dialog: with latency compensation the take lands "
               "exactly in time."),
             T("Una clip si accorcia trascinandone i bordi e si divide con <b>S</b> nel punto della testina.",
               "Trim a clip by dragging its edges, split it with <b>S</b> at the playhead.")],
            T("Registrare bene", "Recording well")),
        P(T(f"Hai una registrazione e vuoi le note? {path('Traccia', 'Importa in questa traccia', 'Audio → notazione (microfono o file)...')} "
            "converte una melodia registrata da sola in testo da correggere (episodio 9 dei video).",
            f"Got a recording and want the notes? "
            f"{path('Traccia', 'Importa in questa traccia', 'Audio → notazione (microfono o file)...')} turns a solo "
            "melody into text you then check (episode 9 of the videos)."), small),
    ]

    # -------------------------------------------------------------- 8
    story += chapter(T("8. Ascoltare, sistemare, bilanciare", "8. Listen, fix, balance"))
    story += [
        *section(T("Ascolto", "Listening")),
        bullets([
            T("<b>Spazio</b> (o F5): Play/Pausa del brano; <b>F6</b>: Stop; clic sul righello per saltare.",
              "<b>Space</b> (or F5): Play/Pause the song; <b>F6</b>: Stop; click the ruler to jump."),
            T("<b>Loop A-B</b>: durante l'ascolto <b>Ctrl+[</b> fissa l'inizio e <b>Ctrl+]</b> la fine; "
              "<b>Ctrl+L</b> accende e spegne il loop. Ottimo per lavorare sul ritornello.",
              "<b>A-B loop</b>: while playing, <b>Ctrl+[</b> sets the start and <b>Ctrl+]</b> the end; <b>Ctrl+L</b> "
              "turns the loop on and off. Great for working on the chorus."),
            T("<b>Shift+Spazio</b>: solo il box selezionato. Il <b>metronomo</b> è nella barra dei comandi, "
              f"accanto alla {b('Velocita' + chr(39) + ' d' + chr(39) + 'ascolto')} (rallenta senza cambiare "
              "l'intonazione).",
              "<b>Shift+Space</b>: only the selected box. The <b>metronome</b> is in the command bar, next to the "
              f"{b('Velocita' + chr(39) + ' d' + chr(39) + 'ascolto')} (slows down without changing the pitch)."),
        ]),
        *section(T("Struttura", "Form")),
        bullets([
            T("Trascina i box per spostarli nel tempo (si agganciano alla battuta).",
              "Drag boxes to move them in time (they snap to the bar)."),
            T(f"<b>Ctrl+D</b> duplica, <b>Canc</b> elimina, tasto destro → {b('Trasponi...')} per cambiare "
              "tonalità a un box.",
              f"<b>Ctrl+D</b> duplicates, <b>Del</b> deletes, right-click → {b('Trasponi...')} to transpose a "
              "box."),
            T("Per spostare un box su un'altra traccia: tasto destro → Taglia, poi tasto destro sulla riga di "
              "destinazione → Incolla qui.",
              "To move a box to another track: right-click → Cut, then right-click the destination row → Paste "
              "here."),
        ]),
        *section(T("Il bilanciamento (mix)", "Balancing (the mix)")),
        P(T("Ogni testata ha due manopole: <b>Vol</b> (0–200%, 100% = volume originale) e <b>Pan</b> "
            "(sinistra/destra, C = centro). Trascinale col mouse o usa la rotellina; doppio click per tornare al "
            "valore di partenza.",
            "Each header has two knobs: <b>Vol</b> (0–200%, 100% = original level) and <b>Pan</b> (left/right, "
            "C = center). Drag them or use the mouse wheel; double-click to reset.")),
        table([[T("Traccia", "Track"), T("Volume indicativo", "Suggested volume"), T("Pan indicativo",
                                                                                       "Suggested pan")],
               [N["drums"], "90–100%", T("centro", "center")],
               [N["bass"], "90–110%", T("centro", "center")],
               [T("Accordi (piano)", "Chords (piano)"), "70–85%", T("leggermente a sinistra", "slightly left")],
               [T("Chitarra elettrica", "Electric guitar"), "75–90%", T("leggermente a destra", "slightly right")],
               [T("Voce o melodia", "Vocals or melody"), "100–120%", T("centro", "center")]], [0.36, 0.32, 0.32]),
        tip([T("Regola i volumi <b>prima</b> degli effetti, e ricontrollali dopo: compressore e amplificatore "
               "cambiano il volume percepito. <b>S</b> (Solo) su una traccia per ascoltarla da sola, <b>M</b> (Mute) "
               "per zittirla.",
               "Set levels <b>before</b> effects and check them again afterwards: compressor and amplifier change "
               "the perceived volume. <b>S</b> (Solo) on a track to hear it alone, <b>M</b> (Mute) to silence it."),
             T(f"{path('Riproduzione', 'Analizza livelli...')} controlla tutto il brano e indica le tracce che "
               "saturano (la spia <b>CLIP</b> del Master si accende).",
               f"{path('Riproduzione', 'Analizza livelli...')} checks the whole song and points out the tracks "
               "that clip (the Master's <b>CLIP</b> light turns on).")]),
    ]

    # -------------------------------------------------------------- 9
    story += chapter(T("9. Gli effetti sulle tracce", "9. Track effects"))
    story += [
        P(T("Ogni traccia, di note o audio, ha un pulsante <b>FX</b> nella testata. Premendolo si apre in fondo "
            "alla finestra il <b>pannello Effetti</b> di quella traccia. Il pulsante si accende quando la traccia ha "
            "effetti e ne mostra il numero (es. <b>FX 4</b>).",
            "Every track, notes or audio, has an <b>FX</b> button in its header. It opens the track's <b>Effects "
            "panel</b> at the bottom of the window. The button lights up when the track has effects and shows how "
            "many (e.g. <b>FX 4</b>).")),
        img("05_invio_rapido.png", 17, T(f"Il pannello Effetti della traccia {N['chords']}: la card «Invio rapido» "
                                         "con riverbero, chorus e ambiente. A destra, «+ Effetto» aggiunge la catena.",
                                         f"The Effects panel of the {N['chords']} track: the “Quick send” card "
                                         "with reverb, chorus and room. On the right, “+ Effect” builds the "
                                         "chain.")),
        *section(T("Invio rapido (solo tracce di note)", "Quick send (note tracks only)")),
        P(T(f"<b>Riverbero</b> e <b>Chorus</b> del synth, da 0 a 100%, e l'<b>Ambiente</b> del riverbero, uno per "
            f"tutto il brano. Nella <b>Stanza piccola</b> predefinita il riverbero si sente appena: per il nostro "
            f"brano scegli <b>Sala</b> e dai il 20–30% di riverbero agli accordi.",
            f"Synth <b>{ui('Riverbero')}</b> and <b>{ui('Chorus')}</b>, 0 to 100%, and the reverb "
            f"<b>{ui('Ambiente')}</b>, one for the whole song. In the default <b>{ui('Stanza piccola')}</b> the "
            f"reverb is barely audible: for our song choose <b>{ui('Sala')}</b> and give the chords 20–30% "
            "reverb.")),
        *section(T("La catena di effetti", "The effect chain")),
        P(T(f"{b('+ Effetto')} aggiunge un effetto in fondo alla catena; il suono passa da sinistra a destra. Ogni "
            "effetto è una <b>card</b>:",
            f"{b('+ Effetto')} adds an effect at the end of the chain; the sound flows from left to right. Each "
            "effect is a <b>card</b>:")),
        bullets([
            T("il pulsante di <b>accensione</b> (in alto a sinistra) lo spegne senza perdere le regolazioni;",
              "the <b>power</b> button (top left) bypasses it without losing the settings;"),
            T("<b>◀ ▶</b> lo spostano nella catena, <b>✕</b> lo toglie;",
              "<b>◀ ▶</b> move it in the chain, <b>✕</b> removes it;"),
            T("il menu dei <b>preset</b>: scegline uno, poi ritocca le manopole;",
              "the <b>preset</b> menu: pick one, then adjust the knobs;"),
            T("le <b>manopole</b>: trascinale col mouse o usa la rotellina; doppio click per tornare al predefinito.",
              "the <b>knobs</b>: drag them or use the mouse wheel; double-click to reset."),
        ]),
        table([[T("Famiglia", "Family"), T("Effetti", "Effects")],
               [ui("Dinamica"), ", ".join(ui(x) for x in ("Compressore", "Limiter", "Noise gate", "Riduzione rumore",
                                                          "Volume"))],
               [ui("Tono"), ", ".join(ui(x) for x in ("EQ a 3 bande", "Filtro passa-alto", "Filtro passa-basso"))],
               [ui("Saturazione"), ", ".join(ui(x) for x in ("Amplificatore", "Profilo NAM", "Distorsione"))],
               [ui("Spazio"), ", ".join(ui(x) for x in ("Delay", "Riverbero", "Chorus", "Phaser"))],
               [ui("Plugin"), T("Gli effetti VST3, AU (macOS) e LV2 installati (capitolo 14)",
                                "The installed VST3, AU (macOS) and LV2 effects (chapter 14)")]], [0.25, 0.75]),
        *section(T("Il loop di calibrazione", "The calibration loop")),
        P(T(f"Aprendo il pannello, SoundText sceglie un tratto di <b>10 secondi</b> (dal box selezionato o dalla "
            f"testina) e lo imposta come loop sul righello. Premi {b('▶ Ascolta il loop')}: il tratto si ripete e "
            "<b>ogni ritocco si sente dal giro successivo</b>, senza aspettare.",
            f"When the panel opens, SoundText picks a <b>10-second</b> stretch (from the selected box or the "
            f"playhead) and sets it as the loop on the ruler. Press {b('▶ Ascolta il loop')}: the stretch repeats "
            "and <b>every tweak is heard from the next pass</b>, with no waiting.")),
        bullets([
            T(f"<b>Loop</b>: da 2 a 30 secondi; {b('Con le altre tracce')}: senti la traccia nel mix "
              "(consigliato) o da sola;",
              f"<b>Loop</b>: 2 to 30 seconds; {b('Con le altre tracce')}: hear the track in the mix (recommended) "
              "or alone;"),
            T(f"{b('Prima / Dopo')}: premuto, senti la traccia senza la catena: il modo più onesto per capire se "
              "un effetto migliora davvero;",
              f"{b('Prima / Dopo')}: held down, you hear the track without the chain: the most honest way to tell "
              "whether an effect really helps;"),
            T(f"{b('Annulla modifiche')}: torna a com'era all'apertura del pannello; {b('Copia su...')}: copia la "
              "catena su un'altra traccia (o sul master);",
              f"{b('Annulla modifiche')}: back to how it was when the panel opened; {b('Copia su...')}: copies the "
              "chain to another track (or the master);"),
            T("<b>✕</b>: chiude; il loop di prima torna com'era e gli effetti vengono applicati a tutta la traccia "
              "in sottofondo.",
              "<b>✕</b>: closes; the previous loop comes back and the effects are applied to the whole track in "
              "the background."),
        ]),
        *section(T("Ricette per il nostro brano", "Recipes for our song"), 7),
        table([[T("Traccia", "Track"), T("Catena consigliata (nell'ordine)", "Suggested chain (in order)"),
                T("Perché", "Why")],
               [N["bass"], f"{ui('Compressore')} «{ui('Basso')}»", T("Livello costante, basso più presente",
                                                                     "Steady level, more present bass")],
               [N["drums"], f"{ui('Compressore')} «{ui('Batteria')}» → {ui('EQ a 3 bande')} «{ui('Più presenza')}»",
                T("Più compatta e incisiva", "Tighter and punchier")],
               [N["chords"], T(f"{ui('EQ a 3 bande')} «{ui('Più calore')}» + Invio rapido riverbero 25%, ambiente "
                               f"{ui('Sala')}",
                               f"{ui('EQ a 3 bande')} “{ui('Più calore')}” + Quick send reverb 25%, room "
                               f"{ui('Sala')}"),
                T("Morbidi e dietro alla voce", "Soft, sitting behind the vocals")],
               [T("Voce registrata", "Recorded vocals"),
                " → ".join(f"{ui(k)} «{ui(p)}»" for k, p in (("Filtro passa-alto", "Voce"), ("Noise gate", "Voce"),
                                                             ("Compressore", "Voce"), ("EQ a 3 bande", "Più presenza"),
                                                             ("Delay", "A tempo 1/4"), ("Riverbero", "Stanza"))),
                T("Pulita, costante, davanti, con un po' di spazio", "Clean, steady, upfront, with some space")],
               [T("Melodia scritta", "Written melody"), f"{ui('Riverbero')} «{ui('Sala')}» (mix 15–20%)",
                T("Meno «finta», più ambiente", "Less “fake”, more ambience")]],
              [0.18, 0.52, 0.30]),
        tip([T(f"<b>Delay a tempo</b>: nel delay, menu {b('A tempo')} → 1/4, 1/8 puntato... Le ripetizioni cadono "
               "a tempo col BPM del brano; la manopola Tempo si spegne e mostra i millisecondi (a 100 BPM, 1/8 "
               "puntato = 450 ms).",
               f"<b>Delay in time</b>: in the delay, the {b('A tempo')} menu → 1/4, dotted 1/8... The repeats fall "
               "in time with the song's BPM; the Time knob turns off and shows the milliseconds (at 100 BPM, dotted "
               "1/8 = 450 ms)."),
             T(f"Pochi effetti, fatti bene: prova sempre con {b('Prima / Dopo')}.",
               f"Few effects, done well: always check with {b('Prima / Dopo')}.")],
            T("Due consigli", "Two tips")),
    ]

    # -------------------------------------------------------------- 10
    story += chapter(T("10. L'amplificatore per chitarra", "10. The guitar amplifier"))
    story += [
        P(T(f"L'<b>Amplificatore</b> è un amplificatore da chitarra completo: preamplificatore (la distorsione), "
            f"controlli di tono e cassa. Lo applichiamo alla traccia {N['guitar']}.",
            f"The <b>{ui('Amplificatore')}</b> is a complete guitar amp: preamp (the distortion), tone controls "
            f"and cabinet. We apply it to the {N['guitar']} track.")),
        steps([
            T(f"Premi <b>FX</b> sulla traccia <b>{N['guitar']}</b>.", f"Press <b>FX</b> on the <b>{N['guitar']}</b> "
                                                                       "track."),
            T(f"{b('+ Effetto')} → {b('Saturazione')} → {b('Amplificatore')}.",
              f"{b('+ Effetto')} → {b('Saturazione')} → {b('Amplificatore')}."),
            T(f"{b('▶ Ascolta il loop')}, poi scegli il preset {b('Rock classico')} (modello British, cassa 4×12 "
              "chiusa).",
              f"{b('▶ Ascolta il loop')}, then choose the {b('Rock classico')} preset (British model, closed 4×12 "
              "cabinet)."),
            T(f"Completa la catena: {b('Noise gate')} «{ui('Chitarra')}» <b>prima</b> dell'amplificatore (usa ◀ per "
              f"spostarlo), poi {b('Delay')} «{ui('A tempo 1/8 puntato')}» e {b('Riverbero')} «{ui('Sala')}» "
              "<b>dopo</b>.",
              f"Complete the chain: {b('Noise gate')} “{ui('Chitarra')}” <b>before</b> the amp (use ◀ to move "
              f"it), then {b('Delay')} “{ui('A tempo 1/8 puntato')}” and {b('Riverbero')} “{ui('Sala')}” "
              "<b>after</b> it."),
            T(f"Confronta con {b('Prima / Dopo')}, sistema <b>Livello</b> e volume della traccia, chiudi con ✕.",
              f"Compare with {b('Prima / Dopo')}, adjust <b>{ui('Livello')}</b> and the track volume, close with "
              "✕."),
        ]),
        img("04_effetti_chitarra.png", 17, T("La catena della chitarra: Noise gate → Amplificatore (Rock classico: "
                                             "British, 4×12 chiusa) → Delay a tempo 1/8 puntato → Riverbero Sala.",
                                             "The guitar chain: Noise gate → Amplifier (Classic rock: British, "
                                             "closed 4×12) → Delay in time, dotted 1/8 → Hall reverb.")),
        *section(T("Preset, modelli e casse", "Presets, models and cabinets")),
        P(T(f"I preset sono cinque punti di partenza: {', '.join(ui(x) for x in ('Pulito brillante', 'Blues', 'Vintage', 'Rock classico', 'Metal'))}. "
            "Ognuno sceglie modello, cassa e manopole; poi si ritocca.",
            f"The presets are five starting points: "
            f"{', '.join(ui(x) for x in ('Pulito brillante', 'Blues', 'Vintage', 'Rock classico', 'Metal'))}. "
            "Each sets model, cabinet and knobs; then you adjust.")),
        table([[T("Modello", "Model"), T("Carattere", "Character"), T("Toni", "Tone stack"), T("Per", "For")],
               [ui("Pulito"), T("Quasi senza saturazione", "Almost no saturation"), "Fender",
                T("Funk, pop, arpeggi, jazz", "Funk, pop, arpeggios, jazz")],
               [ui("Crunch"), T("Saturazione morbida che risponde al tocco", "Soft saturation that follows your "
                                                                             "touch"), "Fender",
                T("Blues, rock leggero", "Blues, light rock")],
               [ui("British"), T("Medi in evidenza, due stadi di saturazione", "Forward mids, two gain stages"),
                "Marshall", T("Rock classico, hard rock", "Classic rock, hard rock")],
               [ui("High gain"), T("Bassi stretti, molta saturazione", "Tight lows, lots of gain"), "Marshall",
                T("Metal, rock moderno", "Metal, modern rock")]],
              [0.16, 0.42, 0.14, 0.28]),
        table([[T("Cassa", "Cabinet"), T("Suono", "Sound")],
               [ui("Combo 1×12"), T("Equilibrata, aperta: la scelta più versatile", "Balanced, open: the most "
                                                                                      "versatile choice")],
               [ui("2×12"), T("Più piena, medi più scolpiti", "Fuller, more sculpted mids")],
               [ui("4×12 chiusa"), T("Più corpo e «botta» sui bassi: rock e metal", "More body and low-end punch: "
                                                                                     "rock and metal")],
               [ui("Vintage 1×10"), T("Più sottile e nasale, anni '50–'60", "Thinner and nasal, 1950s–60s")],
               [ui("Nessuna"), T("Il suono diretto dell'amplificatore, senza cassa (raramente utile)",
                                 "The amp's direct sound, no cabinet (rarely useful)")],
               [ui("File IR…"), T("La risposta all'impulso di una cassa vera, da un file WAV (vedi sotto)",
                                  "The impulse response of a real cabinet, from a WAV file (see below)")]],
              [0.25, 0.75]),
        *section(T("Le manopole", "The knobs")),
        bullets([
            T("<b>Guadagno</b>: quanto distorce. Poco = crunch, tanto = saturazione piena.",
              f"<b>{ui('Guadagno')}</b>: how much it distorts. A little = crunch, a lot = full saturation."),
            T("<b>Bassi, Medi, Alti</b> (0–10): il circuito dei toni degli amplificatori veri (Fender o Marshall, "
              "secondo il modello). Si influenzano a vicenda come negli originali. Per far «uscire» la chitarra nel "
              "mix alza i <b>Medi</b>, non il volume; per il metal abbassali (3 o meno).",
              f"<b>{ui('Bassi')}, {ui('Medi')}, {ui('Alti')}</b> (0–10): the tone stack of real amps (Fender or "
              "Marshall, depending on the model). They interact as in the originals. To make the guitar cut "
              f"through the mix raise the <b>{ui('Medi')}</b>, not the volume; for metal lower them (3 or less)."),
            T("<b>Presenza</b> (0–10): gli acuti dopo lo stadio finale, per dare «aria» e mordente.",
              f"<b>{ui('Presenza')}</b> (0–10): the highs after the power stage, for air and bite."),
            T("<b>Potenza</b> (0–100%): quanto si spinge lo stadio finale a valvole: calore e un po' di "
              "compressione sugli accordi tenuti. 30–50% è il suono di un amplificatore suonato a volume.",
              f"<b>{ui('Potenza')}</b> (0–100%): how hard the tube power stage is driven: warmth and a little "
              "compression on held chords. 30–50% is the sound of an amp played loud."),
            T("<b>Livello</b>: il volume d'uscita. Più guadagno significa più volume: abbassa il Livello mentre "
              "sali col Guadagno.",
              f"<b>{ui('Livello')}</b>: the output volume. More gain means more volume: lower the level as you "
              "raise the gain."),
        ]),
        tip([T("<b>L'ordine conta</b>: noise gate → amplificatore → delay → riverbero, come nelle pedaliere vere.",
               "<b>Order matters</b>: noise gate → amp → delay → reverb, as on a real pedalboard."),
             T("<b>Suona con il plettro, non con la manopola</b>: l'amplificatore risponde al tocco. Con le tracce a "
               f"note lo stesso effetto lo danno le dinamiche ({mono('p@')}, {mono('f@')}).",
               "<b>Play with the pick, not the knob</b>: the amp responds to your touch. On note tracks the "
               f"dynamics do the same ({mono('p@')}, {mono('f@')})."),
             T("<b>Meno guadagno di quanto pensi</b>: da solo un suono molto distorto impressiona, nel mix diventa "
               "un impasto. Nel ritornello con batteria e basso spesso basta il Crunch.",
               "<b>Less gain than you think</b>: a very distorted sound is impressive alone, but turns to mush in "
               "the mix. In a chorus with drums and bass, Crunch is often enough.")],
            T("I segreti di un buon suono", "Secrets of a good tone")),
        *section(T("Un amplificatore vero: i profili NAM", "A real amplifier: NAM profiles"), 7),
        P(T("<b>Neural Amp Modeler</b> (NAM) «cattura» un amplificatore o un pedale vero con una rete neurale: il "
            f"risultato è un <b>profilo</b>, un file {mono('.nam')}, che ne riproduce il suono con grande fedeltà. "
            "SoundText li usa con l'effetto <b>Profilo NAM</b>, su Linux, Windows e macOS.",
            "<b>Neural Amp Modeler</b> (NAM) “captures” a real amp or pedal with a neural network: the result is a "
            f"<b>profile</b>, a {mono('.nam')} file, that reproduces its sound very faithfully. SoundText uses them "
            f"with the <b>{ui('Profilo NAM')}</b> effect, on Linux, Windows and macOS.")),
        steps([
            T(f"{path('Suoni', 'Scarica e installa...')}, categoria <b>Amplificatori per chitarra (NAM)</b>: spunta "
              "<b>Profili NAM consigliati</b> (34 amplificatori e pedali famosi) e <b>Casse IR per gli amplificatori "
              "NAM</b> (20 casse), poi <b>Installa</b>.",
              f"{path('Suoni', 'Scarica e installa...')}, category <b>{ui('Amplificatori per chitarra (NAM)')}</b>: "
              f"tick <b>{ui('Profili NAM consigliati')}</b> (34 famous amps and pedals) and "
              f"<b>{ui('Casse IR per gli amplificatori NAM')}</b> (20 cabinets), then <b>{ui('Installa')}</b>."),
            T(f"Nella catena della chitarra: {b('+ Effetto')} → {b('Saturazione')} → {b('Profilo NAM')} e scegli il "
              "profilo. Sulla card compaiono nome, marca, modello e autore.",
              f"In the guitar chain: {b('+ Effetto')} → {b('Saturazione')} → {b('Profilo NAM')} and choose the "
              "profile. The card shows its name, brand, model and author."),
            T(f"Se il profilo è di una testata senza cassa, menu <b>Cassa</b> → {b('File IR…')} e scegli una delle "
              f"casse scaricate; se la cassa è già inclusa (o è un pedale), lascia {b('Nessuna / inclusa')}.",
              f"If the profile is a head without a cabinet, <b>{ui('Cassa')}</b> menu → {b('File IR…')} and pick one "
              f"of the downloaded cabinets; if the cabinet is included (or it's a pedal), leave "
              f"{b('Nessuna / inclusa')}."),
            T("<b>Ingresso</b> regola quanto spingi il profilo, <b>Livello</b> il volume d'uscita. Togli (o spegni) "
              "l'Amplificatore interno: il profilo lo sostituisce.",
              f"<b>{ui('Ingresso')}</b> sets how hard you drive the profile, <b>{ui('Livello')}</b> the output. "
              "Remove (or bypass) the built-in Amplifier: the profile replaces it."),
        ]),
        tip([T("SoundText porta ogni profilo alla stessa sonorità di riferimento, quindi passare da un profilo "
               "all'altro non fa saltare il volume.",
               "SoundText brings every profile to the same reference loudness, so switching profiles doesn't make "
               "the volume jump."),
             T("Su Linux e Windows (x64) la stessa categoria offre il <b>Motore NAM veloce</b> (il plugin LV2 Neural "
               "Amp Modeler): i profili si calcolano 4–6 volte più in fretta.",
               f"On Linux and Windows (x64) the same category offers the "
               f"<b>{ui('Motore NAM veloce (plugin Neural Amp Modeler)')}</b>: profiles are computed 4–6 times "
               "faster."),
             T("Migliaia di altri profili gratuiti sono su <b>Tone3000</b> (tone3000.com): filtra per NAM e per tipo "
               "(<i>amp</i>, <i>full rig</i>, <i>pedal</i>) ed estrai i file .nam nella cartella dei profili.",
               "Thousands more free profiles are on <b>Tone3000</b> (tone3000.com): filter by NAM and type "
               "(<i>amp</i>, <i>full rig</i>, <i>pedal</i>) and extract the .nam files into the profiles folder.")],
            T("Da sapere", "Good to know")),
        tip([T("Il plugin gratuito di Tone3000 (VST3 e LV2, da tone3000.com/plugin/download) porta tutto il "
               "catalogo dentro SoundText: aggiungilo alla catena con "
               f"{b('+ Effetto')} → {b('Plugin')} → {b('Plugin (VST3/LV2)')}, poi sulla card {b('Parametri…')} e "
               f"{b('Interfaccia del plugin…')}: accedi con l'account gratuito, cerca un suono e caricalo.",
               "The free Tone3000 plugin (VST3 and LV2, from tone3000.com/plugin/download) brings the whole "
               f"catalogue into SoundText: add it to the chain with {b('+ Effetto')} → {b('Plugin')} → "
               f"{b('Plugin (VST3/LV2)')}, then on the card {b('Parametri…')} and {b('Interfaccia del plugin…')}: "
               "sign in with the free account, search for a sound and load it."),
             T("Per caricare un suono servono l'account e la rete; il plugin legge solo i profili A2 e gli IR, non "
               "i vecchi A1, che il Profilo NAM di SoundText invece legge.",
               "Loading a sound needs the account and a network connection; the plugin reads only A2 profiles "
               "and IRs, not the older A1 ones, which SoundText's NAM profile does read.")],
            T("Il plugin di Tone3000", "The Tone3000 plugin")),
    ]

    # -------------------------------------------------------------- 11
    story += chapter(T("11. Il mastering", "11. Mastering"))
    story += [
        P(T("Il <b>mastering</b> è l'ultimo ritocco al mix intero: lo rende più compatto, equilibrato e abbastanza "
            "forte da stare accanto ad altri brani. In SoundText si fa con la catena di effetti sul <b>Master</b>.",
            "<b>Mastering</b> is the final touch on the whole mix: it makes it tighter, more balanced and loud "
            "enough to sit next to other songs. In SoundText it's done with the effect chain on the "
            "<b>Master</b>.")),
        img("07_master_riga.png", 7, T("La riga del Master, in fondo alla colonna delle tracce: FX, volume e "
                                       "misuratore di livello.",
                                       "The Master row, at the bottom of the track column: FX, volume and level "
                                       "meter.")),
        steps([
            T("Clicca sul righello all'inizio del <b>ritornello</b> (la parte più forte del brano): il loop di "
              "calibrazione parte dalla testina.",
              "Click the ruler at the start of the <b>chorus</b> (the loudest part of the song): the calibration "
              "loop starts from the playhead."),
            T(f"Premi <b>FX</b> nella riga del <b>Master</b>: il pannello si apre su {b('Master · mix finale')}.",
              f"Press <b>FX</b> in the <b>Master</b> row: the panel opens on {b('Master · mix finale')}."),
            T(f"Premi {b('+ Catena di mastering')}: arrivano {b('EQ a 3 bande')} «{ui('Neutro')}», "
              f"{b('Compressore')} «{ui('Colla del mix')}» e {b('Limiter')} «{ui('Più forte')}».",
              f"Press {b('+ Catena di mastering')}: you get {b('EQ a 3 bande')} “{ui('Neutro')}”, "
              f"{b('Compressore')} “{ui('Colla del mix')}” and {b('Limiter')} “{ui('Più forte')}”."),
            T(f"{b('▶ Ascolta il loop')} e confronta con {b('Prima / Dopo')}.",
              f"{b('▶ Ascolta il loop')} and compare with {b('Prima / Dopo')}."),
            T("Regola il <b>Guadagno</b> del limiter: più alto = brano più forte e più «schiacciato». Fermati quando "
              "la batteria perde colpo. Il <b>Tetto</b> resta a −1 dB.",
              f"Set the limiter's <b>{ui('Guadagno')}</b>: higher = louder, more squashed song. Stop when the drums "
              f"lose their punch. The <b>{ui('Tetto')}</b> stays at −1 dB."),
            T("Se serve, piccoli ritocchi all'EQ (±1–3 dB). Chiudi con ✕.",
              "If needed, small EQ touches (±1–3 dB). Close with ✕."),
        ]),
        img("06_master.png", 17, T("La catena di mastering: EQ, compressore «Colla del mix» (2:1, attacco lento) e "
                                   "limiter «Più forte» (tetto −1 dB).",
                                   "The mastering chain: EQ, “Mix glue” compressor (2:1, slow attack) and “Louder” "
                                   "limiter (ceiling −1 dB).")),
        warn([T(f"Con {b('Prima / Dopo')} il «dopo» è più forte, e l'orecchio crede sempre che più forte sia più "
                "bello. Per un confronto onesto abbassa temporaneamente il Guadagno del limiter finché i due suonano "
                "a volume simile.",
                f"With {b('Prima / Dopo')} the “after” is louder, and ears always think louder is better. For an "
                "honest comparison, lower the limiter gain until both sound about equally loud."),
              T("Il volume del <b>Master</b> agisce <b>prima</b> della catena: con il limiter attivo alzarlo non "
                "rende il brano più forte oltre il tetto, lo schiaccia soltanto.",
                "The <b>Master</b> volume acts <b>before</b> the chain: with the limiter on, raising it doesn't make "
                "the song louder past the ceiling, it only squashes it.")],
             T("Due trappole", "Two traps")),
    ]

    # -------------------------------------------------------------- 12
    story += chapter(T("12. Esportare il WAV", "12. Exporting the WAV"))
    story += [
        steps([
            T("Salva il progetto (<b>Ctrl+S</b>) e ascolta tutto il brano un'ultima volta dall'inizio.",
              "Save the project (<b>Ctrl+S</b>) and listen to the whole song one last time from the start."),
            T(f"{path('Progetto', 'Esporta', 'Mix audio (WAV)...')}",
              f"{path('Progetto', 'Esporta', 'Mix audio (WAV)...')}"),
            T("Scegli nome e cartella (viene proposto il nome del progetto) e conferma.",
              "Choose name and folder (the project name is suggested) and confirm."),
        ]),
        P(T("Il file è un <b>WAV stereo a 48 kHz, 24 bit</b>, qualità da studio. Contiene il brano <b>come lo "
            "senti</b>: solo le tracce udibili (rispetta Mute e Solo), le tracce audio, tutti gli effetti delle "
            "tracce, l'amplificatore e la catena del master.",
            "The file is a <b>stereo WAV at 48 kHz, 24 bit</b>, studio quality. It contains the song <b>as you "
            "hear it</b>: only the audible tracks (it follows Mute and Solo), the audio tracks, every track effect, "
            "the amplifier and the master chain.")),
        table([[T("Esportazione", "Export"), T("Dove", "Where"), T("Effetti", "Effects"), "Master"],
               [T("Mix del brano (WAV)", "Song mix (WAV)"), path("Progetto", "Esporta", "Mix audio (WAV)..."),
                T("sì", "yes"), T("sì", "yes")],
               [T("Tutte le tracce, un WAV ciascuna (stem)", "All tracks, one WAV each (stems)"),
                path("Progetto", "Esporta", "Tutte le tracce, una per file (stem)..."), T("sì", "yes"),
                T("no", "no")],
               [T("Una sola traccia (WAV)", "A single track (WAV)"),
                path("Traccia", "Esporta questa traccia", "WAV..."), T("sì", "yes"), T("no", "no")],
               ["MIDI", path("Progetto", "Esporta", "MIDI..."), T("solo riverbero e chorus del synth",
                                                                  "synth reverb and chorus only"), T("no", "no")],
               [T("Partitura", "Score"), f"{path('Progetto', 'Esporta', 'Partitura PDF...')}, "
                                         f"{b('Partitura MusicXML...')}", "—", "—"]],
              [0.22, 0.48, 0.18, 0.12]),
        warn(T("Prima di esportare controlla che nessuna traccia sia rimasta in <b>Solo</b> o in <b>Mute</b> per "
               "sbaglio: il WAV le rispetta.",
               "Before exporting, check that no track was left in <b>Solo</b> or <b>Mute</b> by mistake: the WAV "
               "follows them.")),
        tip([T("Per pubblicare in MP3 o AAC converti il WAV con un programma apposito (Audacity, ffmpeg...): "
               "partire dal WAV a 24 bit dà la qualità migliore.",
               "To publish as MP3 or AAC, convert the WAV with a dedicated program (Audacity, ffmpeg...): "
               "starting from the 24-bit WAV gives the best quality."),
             T("Gli stem (una traccia per file, senza master) servono a chi mixerà il brano in un altro programma. "
               "MusicXML porta la partitura in MuseScore e negli altri programmi di notazione (episodio 13).",
               "Stems (one track per file, no master) are for whoever will mix the song in another program. "
               "MusicXML takes the score into MuseScore and other notation programs (episode 13).")],
            T("Dopo l'export", "After the export")),
    ]

    # -------------------------------------------------------------- 13
    story += chapter(T("13. Suoni da studio con programmi esterni", "13. Studio sounds with other programs"))
    story += [
        P(T("Per un suono da studio la via più semplice è il <b>Profilo NAM</b> (capitolo 10). In alternativa si "
            "può far passare la traccia in un simulatore di amplificatore esterno e poi riportarla nel brano. Si "
            "chiama <b>re-amping</b>: si registra una volta la chitarra pulita e si può cambiare amplificatore "
            "quando si vuole, senza risuonare la parte.",
            "For a studio sound the easiest route is the <b>NAM profile</b> (chapter 10). Alternatively you can "
            "run the track through an external amp simulator and bring it back into the song. This is "
            "<b>re-amping</b>: you record the clean guitar once and can change amp whenever you like, without "
            "playing the part again.")),
        *section(T("Il flusso, su qualunque sistema", "The workflow, on any system")),
        steps([
            T("Registra la chitarra <b>pulita</b> in una traccia audio (ingresso <b>INST/Hi-Z</b>, senza "
              "amplificatore) oppure scrivila a note (capitolo 6).",
              "Record the <b>clean</b> guitar on an audio track (<b>INST/Hi-Z</b> input, no amp) or write it as "
              "notes (chapter 6)."),
            T(f"Seleziona la traccia e scegli {path('Traccia', 'Esporta questa traccia', 'WAV asciutto (per il re-amping)...')}"
              ". Il file esce senza effetti, con il pan al centro e senza master; parte dall'inizio del brano, così "
              "resta a tempo.",
              f"Select the track and choose "
              f"{path('Traccia', 'Esporta questa traccia', 'WAV asciutto (per il re-amping)...')}. The file comes "
              "out without effects, panned center and without the master; it starts at the beginning of the "
              "song, so it stays in time."),
            T("Nel programma esterno applica il simulatore al file e salva il risultato come nuovo WAV.",
              "In the external program apply the simulator to the file and save the result as a new WAV."),
            T(f"In SoundText crea una traccia audio (es. «Chitarra ampli») e scegli "
              f"{path('Traccia', 'Importa in questa traccia', 'File audio come clip (traccia audio)...')}: su una "
              "traccia vuota la clip va all'inizio, a tempo col brano.",
              f"In SoundText create an audio track (e.g. “Amped guitar”) and choose "
              f"{path('Traccia', 'Importa in questa traccia', 'File audio come clip (traccia audio)...')}: on an "
              "empty track the clip goes to the start, in time with the song."),
            T("Metti in <b>Mute</b> la traccia originale, oppure tienile entrambe e dosa pulito e amplificato con i "
              "volumi.",
              "<b>Mute</b> the original track, or keep both and blend clean and amped with the volumes."),
        ]),
        *section(T("Programmi gratuiti per il re-amping", "Free programs for re-amping"), 7),
        table([[T("Programma", "Program"), T("Cos'è", "What it is"), T("Sistemi", "Systems")],
               ["<b>Guitarix</b>", T("Amplificatori e pedali a valvole simulati, con casse e IR. Anche come plugin "
                                     f"LV2 ({mono('guitarix-lv2')}), da usare direttamente in SoundText.",
                                     "Simulated tube amps and pedals, with cabinets and IRs. Also as LV2 plugins "
                                     f"({mono('guitarix-lv2')}), usable directly inside SoundText."), "Linux"],
               ["<b>Neural Amp Modeler</b>", T("Il plugin e il programma dei profili .nam: serve per suonare in "
                                               "diretta (in SoundText i profili funzionano già).",
                                               "The plugin and app for .nam profiles: useful for playing live "
                                               "(profiles already work inside SoundText)."), "Windows, macOS"],
               ["<b>AIDA-X</b>", T("Simile a NAM e più leggero. Plugin e programma a sé.",
                                   "Similar to NAM and lighter. Plugin and standalone app."),
                "Windows, macOS, Linux"],
               ["<b>Audacity</b>", T("Apre il WAV asciutto, gli applica un plugin (VST3, LV2, AU) ed esporta.",
                                     "Opens the dry WAV, applies a plugin (VST3, LV2, AU) and exports."),
                "Windows, macOS, Linux"]], [0.27, 0.53, 0.2]),
        P(T("Nomi dei pacchetti e voci dei menu dei programmi esterni possono cambiare da una versione all'altra: in "
            "caso di dubbio fai riferimento alla loro documentazione.",
            "Package names and menu items of external programs can change between versions: when in doubt, check "
            "their documentation."), small),
    ]

    # -------------------------------------------------------------- 14
    story += chapter(T("14. Plugin VST3 e LV2, strumenti SFZ", "14. VST3 and LV2 plugins, SFZ instruments"))
    story += [
        P(T("Oltre agli effetti interni e ai SoundFont, SoundText usa i <b>plugin audio installati sul computer</b>: "
            "strumenti virtuali che suonano le note di una traccia al posto del SoundFont, ed effetti da mettere "
            "nella catena di una traccia o del master. Funzionano i plugin <b>VST3</b> (Linux, Windows, macOS), su macOS "
            "gli <b>Audio Unit</b> (AU) e su Linux gli <b>LV2</b>, ciascuno in un processo separato. CLAP e VST2 non sono supportati.",
            "Besides the built-in effects and SoundFonts, SoundText uses the <b>audio plugins installed on your "
            "computer</b>: virtual instruments that play a track's notes instead of the SoundFont, and effects for "
            "a track's or the master's chain. <b>VST3</b> plugins work (Linux, Windows, macOS), on macOS "
            "<b>Audio Units</b> (AU) and on Linux <b>LV2</b>, each in its own process. CLAP and VST2 are not supported.")),
        P(T(f"Per cominciare, {path('Suoni', 'Scarica e installa...')} → <b>Plugin e programmi gratuiti</b> installa "
            "una scelta di plugin gratuiti nella cartella dell'utente: Surge XT, Dexed, Dragonfly Reverb, "
            "Airwindows Consolidated, OB-Xf e altri, secondo il sistema.",
            f"To get started, {path('Suoni', 'Scarica e installa...')} → <b>{ui('Plugin e programmi gratuiti')}</b> "
            "installs a selection of free plugins in your user folder: Surge XT, Dexed, Dragonfly Reverb, "
            "Airwindows Consolidated, OB-Xf and more, depending on the system.")),
        *section(T("Uno strumento virtuale su una traccia", "A virtual instrument on a track"), 7),
        steps([
            T(f"SoundText cerca i VST3 nelle cartelle standard; altre si aggiungono da "
              f"{path('Suoni', 'Cartelle dei plugin VST3...')}",
              f"SoundText looks for VST3 plugins in the standard folders; add others in "
              f"{path('Suoni', 'Cartelle dei plugin VST3...')}"),
            T(f"Seleziona la traccia (per esempio «{N['chords']}») e scegli "
              f"{path('Traccia', 'Strumento plugin', 'Scegli (VST3/LV2)...')}, oppure tasto destro sul nome della "
              "traccia.",
              f"Select the track (for example “{N['chords']}”) and choose "
              f"{path('Traccia', 'Strumento plugin', 'Scegli (VST3/LV2)...')}, or right-click the track name."),
            T("Scegli lo strumento dall'elenco. La prima volta SoundText carica ogni plugin per capire cos'è: può "
              "volerci un po', poi l'elenco si ricorda.",
              "Pick the instrument from the list. The first time, SoundText loads each plugin to find out what it "
              "is: it may take a while, then the list is remembered."),
            T(f"Si apre la finestra dei <b>parametri</b> (con tanti parametri usa {b('Cerca un parametro')}), oppure "
              f"apri {b('Interfaccia del plugin...')} per usare la sua finestra e i suoi preset. Premi <b>OK</b>.",
              f"The <b>parameters</b> window opens (with many parameters use {b('Cerca un parametro')}), or open "
              f"{b('Interfaccia del plugin...')} to use its own window and presets. Press <b>OK</b>."),
            T("Premi <b>Play</b>: la traccia suona con il plugin. Volume, pan ed effetti della traccia valgono come "
              "sempre.",
              "Press <b>Play</b>: the track plays through the plugin. The track's volume, pan and effects apply as "
              "usual."),
        ]),
        tip([T(f"Per tornare al SoundFont: nello stesso elenco {b('Nessuno: usa il SoundFont')}.",
               f"To go back to the SoundFont: {b('Nessuno: usa il SoundFont')} in the same list."),
             T("Un plugin grande impiega qualche secondo a caricarsi la prima volta che suona: dopo, l'ascolto "
               "riparte subito.",
               "A large plugin takes a few seconds to load the first time it plays: after that, playback starts "
               "right away.")]),
        *section(T("Gli strumenti campionati SFZ", "SFZ sampled instruments"), 7),
        P(T("Gli strumenti <b>SFZ</b> sono pianoforti, chitarre, bassi, archi e batterie campionati da strumenti "
            "veri: suonano molto più realistici del SoundFont General MIDI.",
            "<b>SFZ</b> instruments are pianos, guitars, basses, strings and drums sampled from real instruments: "
            "they sound far more realistic than the General MIDI SoundFont.")),
        steps([
            T(f"In {path('Suoni', 'Scarica e installa...')} spunta gli strumenti che ti servono (<b>Strumenti "
              "campionati (SFZ)</b>) e, sotto <b>Motori</b>, il motore SFZ interno: si compila sul computer in "
              "qualche minuto (servono git, cmake e un compilatore; la finestra si offre di installarli).",
              f"In {path('Suoni', 'Scarica e installa...')} tick the instruments you need "
              f"(<b>{ui('Strumenti campionati (SFZ)')}</b>) and, under <b>{ui('Motori')}</b>, the built-in SFZ "
              "engine: it is compiled on your computer in a few minutes (it needs git, cmake and a compiler; the "
              "window offers to install them)."),
            T(f"{path('Traccia', 'Strumento plugin', 'Scegli (VST3/LV2)...')} → {b('Strumento SFZ (interno)…')} e "
              "scegli il file .sfz dello strumento.",
              f"{path('Traccia', 'Strumento plugin', 'Scegli (VST3/LV2)...')} → {b('Strumento SFZ (interno)…')} "
              "and choose the instrument's .sfz file."),
        ]),
        *section(T("Un plugin come effetto", "A plugin as an effect")),
        P(T(f"Nel pannello Effetti della traccia (capitolo 9): {b('+ Effetto')} → {b('Plugin')} → "
            f"{b('Plugin (VST3/LV2)')} e scegli l'effetto. La card ha le manopole <b>Mix</b> e <b>Livello</b>: i "
            "ritocchi si sentono subito nel loop di ascolto, come per gli effetti interni.",
            f"In the track's Effects panel (chapter 9): {b('+ Effetto')} → {b('Plugin')} → {b('Plugin (VST3/LV2)')} "
            f"and choose the effect. The card has <b>{ui('Mix')}</b> and <b>{ui('Livello')}</b> knobs: tweaks are "
            "heard right away in the listening loop, as with the built-in effects.")),
        tip(T("Se un plugin si blocca o si chiude, SoundText resta aperto: il plugin viene segnato come «non "
              "risponde» fino al prossimo avvio. Un effetto che non funziona lascia passare il suono com'è; una "
              "traccia il cui strumento plugin non funziona suona con il SoundFont.",
              "If a plugin hangs or crashes, SoundText stays open: the plugin is marked as “not responding” until "
              "the next start. A failing effect lets the sound through unchanged; a track whose plugin instrument "
              "fails plays with the SoundFont."), T("Se qualcosa non va", "If something goes wrong")),
    ]

    # -------------------------------------------------------------- 15
    story += chapter(T(f"15. La mappa dei menu (SoundText {VERSION})", f"15. The menu map (SoundText {VERSION})"))
    story += [
        P(T("Dove trovare quello che abbiamo usato, e qualcosa in più.",
            "Where to find what we used, and a few more things.")),
        table([[T("Menu", "Menu"), T("Che cosa ci trovi", "What you'll find")],
               [b("Progetto"), T(f"Nuovo, Apri, {ui('Apri esempio...')}, Salva; Importa (MIDI, MusicXML, ABC, "
                                 "MTXT); Esporta (mix WAV, stem, MIDI, partitura PDF, MusicXML, ABC, MTXT).",
                                 f"New, Open, {ui('Apri esempio...')}, Save; Import (MIDI, MusicXML, ABC, MTXT); "
                                 "Export (WAV mix, stems, MIDI, PDF score, MusicXML, ABC, MTXT).")],
               [b("Modifica"), T("Annulla e Ripeti; elimina e duplica il box; dividi la clip audio alla testina.",
                                 "Undo and Redo; delete and duplicate the box; split the audio clip at the "
                                 "playhead.")],
               [b("Vista"), T(f"{ui('Struttura brano (a box)')}, {ui('Partitura...')} (Ctrl+Shift+P), zoom, altezza "
                              "delle tracce, dimensione del testo.",
                              f"{ui('Struttura brano (a box)')}, {ui('Partitura...')} (Ctrl+Shift+P), zoom, track "
                              "height, text size.")],
               [b("Traccia"), T("Aggiungi (anche con strumento virtuale o audio), strumento plugin, importa ed "
                                "esporta la traccia, registra, suona con la tastiera.",
                                "Add (also with a virtual instrument or audio), plugin instrument, import and "
                                "export the track, record, play with the keyboard.")],
               [b("Componi"), T(f"Genera batteria, basso, giro armonico, accompagnamento; {ui('Arrangia il brano...')};"
                                " stili personali; librerie di pattern e MIDI; analisi della tonalità.",
                                f"Generate drums, bass, progression, comping; {ui('Arrangia il brano...')}; your own "
                                "styles; pattern and MIDI libraries; key analysis.")],
               [b("Riproduzione"), T(f"Play, Stop, loop A-B, velocità d'ascolto, umanizza, "
                                     f"{ui('Analizza livelli...')}.",
                                     f"Play, Stop, A-B loop, listening speed, humanize, "
                                     f"{ui('Analizza livelli...')}.")],
               [b("Suoni"), T(f"{ui('Gestisci strumenti...')}, SoundFont, volume di sintesi, cartelle dei plugin "
                              f"VST3, {ui('Scarica e installa...')}",
                              f"{ui('Gestisci strumenti...')}, SoundFont, synth volume, VST3 plugin folders, "
                              f"{ui('Scarica e installa...')}")],
               [b("Opzioni"), T("Metronomo, umanizza, sorgenti dei download, import MIDI e audio, tema, lingua.",
                                "Metronome, humanize, download sources, MIDI and audio import, theme, language.")],
               [b("Aiuto"), T(f"{ui('Cerca un comando...')} (Ctrl+K), {ui('Guida utente...')} (F1), il file di "
                              "log, informazioni.",
                              f"{ui('Cerca un comando...')} (Ctrl+K), {ui('Guida utente...')} (F1), the log file, "
                              "about.")]],
              [0.2, 0.8]),
        *section(T("I video tutorial", "The video tutorials"), 8),
        P(T("Ogni capitolo di questa guida ha un episodio corrispondente nella serie su YouTube (in inglese, "
            "sottotitoli in italiano, francese e spagnolo): youtube.com/playlist?list=PLbVfXEqrD3P4",
            "Each chapter of this guide has a matching episode in the YouTube series (English, with subtitles in "
            "Italian, French and Spanish): youtube.com/playlist?list=PLbVfXEqrD3P4")),
        table([[T("Episodio", "Episode"), T("Argomento", "Topic"), T("Capitoli", "Chapters")],
               ["1", T("Installare SoundText", "Installing SoundText"), "2"],
               ["2", T("Scaricare suoni e plugin", "Getting the sounds"), "2, 14"],
               ["3", T("Scrivere la musica come testo", "Writing music as text"), "7"],
               ["4", T("Dagli accordi all'arrangiamento", "From chords to an arrangement"), "4, 5"],
               ["5", T("La struttura del brano", "The song structure"), "3, 8"],
               ["6", T("Suonare con la tastiera del computer", "Playing with the computer keyboard"), "7"],
               ["7", T("Accordi, voicing e armonia", "Chords, voicings and harmony"), "4"],
               ["8", T("Tracce audio", "Audio tracks"), "7, 13"],
               ["9", T("Dal suono alla notazione", "From sound to notation"), "7"],
               ["10", T("Strumenti campionati (SFZ)", "Sampled instruments (SFZ)"), "14"],
               ["11", T("Effetti e plugin", "Effects and plugins"), "9, 11, 14"],
               ["12", T("Chitarre con i profili NAM", "Guitars with NAM profiles"), "10"],
               ["13", T("Esportare", "Exporting"), "12"]], [0.15, 0.6, 0.25]),
    ]

    # -------------------------------------------------------------- 16
    story += chapter(T("16. Lista di controllo e problemi comuni", "16. Checklist and common problems"))
    story += [
        *section(T("Prima dell'export", "Before exporting")),
        table([["", T("Controllo", "Check")],
               ["☐", T("Il brano ha inizio e fine puliti (finale della batteria, ultimo accordo lungo)",
                       "The song starts and ends cleanly (drum ending, long last chord)")],
               ["☐", T("Nessuna traccia in Solo o Mute per sbaglio", "No track left in Solo or Mute by mistake")],
               ["☐", T("Volumi bilanciati: la voce/melodia si capisce, il basso si sente anche a volume basso",
                       "Levels balanced: the vocal/melody is clear, the bass is audible even at low volume")],
               ["☐", T("Effetti confrontati con Prima / Dopo: ognuno migliora davvero qualcosa",
                       "Effects checked with Before / After: each one really improves something")],
               ["☐", T("Master: limiter con tetto −1 dB, senza schiacciare la batteria; la spia CLIP resta spenta",
                       "Master: limiter with a −1 dB ceiling, drums not squashed; the CLIP light stays off")],
               ["☐", T("Progetto salvato (Ctrl+S)", "Project saved (Ctrl+S)")]], [0.06, 0.94]),
        *section(T("Problemi comuni", "Common problems"), 8),
        table([[T("Problema", "Problem"), T("Soluzione", "Solution")],
               [T("Non si sente nulla", "No sound at all"),
                T(f"Manca il SoundFont: {path('Suoni', 'SoundFont', 'Mostra SoundFont in uso')} dice quale usa, e se "
                  f"non c'è propone di scaricarlo. Controlla anche che le tracce non siano in Mute.",
                  f"The SoundFont is missing: {path('Suoni', 'SoundFont', 'Mostra SoundFont in uso')} shows which "
                  "one is used and, if none, offers to download one. Also check the tracks aren't muted.")],
               [T(f"«{ui('Basso dagli accordi...')}» è grigio", f"“{ui('Basso dagli accordi...')}” is greyed out"),
                T("Il brano non ha ancora una traccia di accordi: generane una (capitolo 4).",
                  "The song has no chord track yet: generate one (chapter 4).")],
               [T("La chitarra suona impastata", "The guitar sounds muddy"),
                T("Guadagno troppo alto o suono GM già distorto: usa Electric Guitar (clean) e meno guadagno.",
                  "Too much gain or an already distorted GM sound: use Electric Guitar (clean) and less gain.")],
               [T("Il WAV esportato è distorto", "The exported WAV is distorted"),
                T(f"Troppo volume: {path('Riproduzione', 'Analizza livelli...')} indica le tracce che saturano; "
                  "abbassale o metti il limiter sul master.",
                  f"Too loud: {path('Riproduzione', 'Analizza livelli...')} points out the clipping tracks; lower "
                  "them or put the limiter on the master.")],
               [T("La registrazione è fuori tempo", "The recording is out of time"),
                T("Nel dialogo di registrazione usa Calibra... una volta per scheda audio.",
                  "In the recording dialog use Calibrate... once per audio interface.")],
               [T("Qualcosa non funziona", "Something doesn't work"),
                T(f"{path('Aiuto', 'Apri il file di log')} mostra gli errori registrati dal programma: spesso "
                  "spiegano subito il motivo.",
                  f"{path('Aiuto', 'Apri il file di log')} shows the errors the program logged: they often explain "
                  "the cause right away.")],
               [T("Ho sbagliato qualcosa", "I made a mistake"),
                T("Ctrl+Z annulla qualunque modifica, anche agli effetti.",
                  "Ctrl+Z undoes any change, effects included.")]],
              [0.36, 0.64]),
        *section(T("Scorciatoie da ricordare", "Shortcuts to remember"), 8),
        table([[T("Tasto", "Key"), T("Azione", "Action"), T("Tasto", "Key"), T("Azione", "Action")],
               [T("Spazio / F5", "Space / F5"), "Play / " + T("Pausa", "Pause"), "Ctrl+N / Ctrl+S",
                T("Nuovo / Salva", "New / Save")],
               [T("Shift+Spazio", "Shift+Space"), T("Ascolta il box selezionato", "Play the selected box"), "Ctrl+T",
                T("Aggiungi traccia", "Add track")],
               ["F6", "Stop", "Ctrl+R", T("Registra", "Record")],
               ["Ctrl+[ / Ctrl+]", T("Inizio / fine loop", "Loop start / end"), "Ctrl+Z / Ctrl+Y",
                T("Annulla / Ripeti", "Undo / Redo")],
               ["Ctrl+L", T("Loop on/off", "Loop on/off"), "Ctrl+K", T("Cerca un comando", "Find a command")],
               ["Ctrl+D", T("Duplica il box", "Duplicate the box"), "Ctrl+Shift+B",
                T("Vista Struttura / Testo", "Structure / Text view")],
               [T("Canc", "Del"), T("Elimina il box", "Delete the box"), "Ctrl+Shift+P", T("Partitura", "Score")],
               ["S", T("Dividi la clip alla testina", "Split the clip at the playhead"), "F1",
                T("Guida utente", "User guide")]], [0.2, 0.3, 0.2, 0.3]),
        Spacer(1, 10),
        P(T(f"Per tutti i dettagli c'è la guida completa: {path('Aiuto', 'Guida utente...')} (F1). Buona musica!",
            f"For every detail there's the full user guide: {path('Aiuto', 'Guida utente...')} (F1). Enjoy making "
            "music!"), ParagraphStyle("end", parent=base, textColor=GREY)),
    ]
    return story


def build(lang):
    set_language(lang)
    out = os.path.join(ROOT, OUTPUT[lang])
    doc = Doc(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2.2 * cm,
              title=title(), author="SoundText",
              subject=T("Guida pratica alla costruzione di un brano", "A hands-on guide to building a song"))
    doc.multiBuild(build_story(), onFirstPage=page_decor, onLaterPages=page_decor)
    print(out)


if __name__ == "__main__":
    for language in (sys.argv[1:] or ["it", "en"]):
        build(language)
    if missing:
        print("Testi dell'interfaccia senza traduzione:", *sorted(missing), sep="\n  ")
