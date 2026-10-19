"""
Genera la guida PDF "Dal primo accordo al WAV" (SoundText_Guida_dal_primo_accordo_al_WAV.pdf,
nella radice del repository) a partire dagli screenshot di questa cartella (vedi shots.py).

Richiede reportlab (solo per rigenerare la guida, non per il programma). Dalla radice
del repository, con il Python del programma (per leggere la versione di ST-language):
    venv/bin/pip install reportlab
    venv/bin/python docs/guida_brano/make_pdf.py
La guida non va negli installer (vedi tests/test_installer_contents.py).
"""
import datetime
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak, Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "SoundText_Guida_dal_primo_accordo_al_WAV.pdf")

# Versioni scritte in copertina: SoundText da core/version.py, ST-language dal
# pacchetto installato (la riga "ST: x.y" dei file .st) o, senza, da requirements.txt.
sys.path.insert(0, ROOT)
from core.version import APP_VERSION  # noqa: E402
try:
    from st_language.stfile import LANGUAGE_VERSION
    ST_VERSION = "%d.%d" % LANGUAGE_VERSION
except ImportError:
    with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as _f:
        ST_VERSION = re.search(r"st-language>=([0-9.]+)", _f.read()).group(1)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-BI", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVM", os.path.join(FONT_DIR, "DejaVuSansMono.ttf")))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

ACCENT = colors.HexColor("#3d7bab")
ACCENT_LIGHT = colors.HexColor("#e8f1f8")
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


class Doc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))


def page_decor(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("DV", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(2 * cm, 1.2 * cm, "SoundText — Dal primo accordo al WAV")
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


def box(title, text, bg=TIP_BG, border=TIP_BORDER):
    content = [P(f"<b>{title}</b>", ParagraphStyle("bt", parent=base, spaceAfter=2))]
    for t in (text if isinstance(text, list) else [text]):
        content.append(P(t, ParagraphStyle("bb", parent=base, spaceAfter=2)))
    t = Table([[content]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 8)])


def tip(text, title="Consiglio"):
    return box(title, text)


def warn(text, title="Attenzione"):
    return box(title, text, WARN_BG, WARN_BORDER)


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
    path = os.path.join(HERE, name)
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    w = width_cm * cm
    h = w * ih / iw
    im = Image(path, width=w, height=h)
    frame = Table([[im]], colWidths=[w + 2])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return KeepTogether([Spacer(1, 4), frame, P(text, caption)])


def chapter(title):
    # Pagina nuova solo se nella corrente resta poco spazio.
    return [CondPageBreak(9 * cm), Spacer(1, 8), P(title, h1)]


story = []

# ------------------------------------------------------------------ copertina
story += [
    Spacer(1, 4.5 * cm),
    P("SoundText", ParagraphStyle("c0", fontName="DV-B", fontSize=34, leading=40, textColor=ACCENT,
                                  alignment=TA_CENTER)),
    Spacer(1, 0.6 * cm),
    P("Dal primo accordo al WAV", ParagraphStyle("c1", fontName="DV-B", fontSize=22, leading=28,
                                                   alignment=TA_CENTER)),
    Spacer(1, 0.4 * cm),
    P("Guida pratica per costruire un brano dall'inizio alla fine:<br/>accordi, batteria, basso, chitarra, "
      "voce, effetti, amplificatore, plugin, mastering ed export audio",
      ParagraphStyle("c2", parent=base, fontSize=12, leading=18, alignment=TA_CENTER, textColor=GREY)),
    Spacer(1, 1.2 * cm),
]
cover_img = os.path.join(HERE, "01_struttura_crop.png")
from reportlab.lib.utils import ImageReader  # noqa: E402
iw, ih = ImageReader(cover_img).getSize()
story.append(Image(cover_img, width=W, height=W * ih / iw))
story += [Spacer(1, 1.5 * cm),
          P(f"SoundText {APP_VERSION} · ST-language {ST_VERSION}<br/>"
            f"Edizione del {datetime.date.today().strftime('%d/%m/%Y')}",
            ParagraphStyle("c3", parent=small, alignment=TA_CENTER))]

# ------------------------------------------------------------------ indice
story += [PageBreak(), P("Indice", ParagraphStyle("hi", parent=h1))]
toc = TableOfContents()
toc.levelStyles = [toc1]
toc.dotsMinLevel = 0
story.append(toc)

# ------------------------------------------------------------------ 1
story += [PageBreak(), P("1. Che cosa costruiremo", h1)]
story += [
    P("In questa guida costruiamo, passo dopo passo, un brano completo e lo trasformiamo in un file audio "
      "<b>WAV</b> pronto da ascoltare ovunque, da mandare a un amico o da caricare online. Useremo quasi "
      "tutto quello che SoundText mette a disposizione: i generatori automatici, la scrittura a mano delle "
      "note, la registrazione, il mixer, gli effetti, l'amplificatore per chitarra e il mastering."),
    P("Il brano d'esempio si chiama <b>«Il mio primo brano»</b>:"),
    table([["Elemento", "Scelta"],
           ["Tonalità", "La minore (Am)"],
           ["Tempo e metrica", "100 BPM, 4/4"],
           ["Struttura", "Strofa (8 battute) → Ritornello (8 battute) → Strofa 2 (8 battute)"],
           ["Tracce", "Accordi (pianoforte), Batteria, Basso, Chitarra elettrica con amplificatore, "
                      "Voce (registrata) o melodia scritta"],
           ["Risultato", "Un file WAV a 48 kHz / 24 bit, con effetti e mastering"]], [0.28, 0.72]),
    CondPageBreak(5 * cm), P("Il percorso, in sintesi:", h2),
    table([["Passo", "Che cosa si fa", "Capitolo"],
           ["1", "Preparare il programma (SoundFont, pacchetti)", "2"],
           ["2", "Creare il progetto: tempo, metrica, tonalità, salvataggio", "3"],
           ["3", "Scrivere il giro di accordi (strofa e ritornello)", "4"],
           ["4", "Aggiungere batteria e basso", "5"],
           ["5", "Aggiungere la chitarra elettrica", "6"],
           ["6", "Melodia: scriverla a mano o registrare la voce", "7"],
           ["7", "Ascoltare, sistemare la struttura, bilanciare i volumi", "8"],
           ["8", "Effetti sulle tracce", "9"],
           ["9", "Amplificatore o amplificatore vero (profilo NAM) sulla chitarra", "10"],
           ["10", "Mastering del mix finale", "11"],
           ["11", "Esportare il WAV", "12"],
           ["12", "Facoltativo: suoni da studio con programmi esterni (re-amping)", "13"],
           ["13", "Facoltativo: plugin VST3 e LV2 e strumenti SFZ (motore sfizz interno)", "14"],
           ["14", "Le novità del programma e dei menu", "15"]], [0.1, 0.72, 0.18]),
    tip(["Non serve seguire tutto alla lettera: ogni capitolo sta in piedi da solo. Se hai già un brano, "
         "puoi saltare direttamente agli effetti (capitolo 9) o all'esportazione (capitolo 12).",
         "Qualunque comando si trova anche con <b>Ctrl+K</b> («Cerca un comando»): scrivi cosa vuoi fare "
         "(«esporta», «registra», «genera basso»...) e premi Invio.",
         "Per vedere brani finiti, con effetti, strumenti SFZ, plugin e profili NAM: <b>Progetto → Apri "
         "esempio...</b> L'esempio si apre come copia: <b>Salva</b> chiede dove salvarlo e l'originale resta "
         "intatto."], "Tre cose utili fin da subito"),
]

# ------------------------------------------------------------------ 2
story += chapter("2. Prima di cominciare")
story += [
    P("SoundText suona le tracce scritte (note e accordi) con un <b>SoundFont</b>, un file <b>.sf2</b> che "
      "contiene i suoni degli strumenti. Senza SoundFont si sentono solo le tracce audio registrate."),
    steps([
        "Scegli un SoundFont General MIDI completo (per esempio <b>FluidR3_GM.sf2</b> o "
        "<b>GeneralUser GS</b>) e mettilo nella cartella <b>soundfonts/</b> di SoundText.",
        "Menu <b>Suoni → SoundFont → Scegli SoundFont (.sf2)...</b> e seleziona il file. La scelta viene ricordata.",
        "Premi <b>Play</b> su un progetto qualsiasi per controllare che si senta.",
    ]),
    CondPageBreak(5 * cm), P("Pacchetti Python usati in questa guida", h2),
    table([["Pacchetto", "A cosa serve", "Senza..."],
           ["sounddevice", "Ascolto diretto, loop A-B, loop di calibrazione degli effetti, registrazione, "
                           "click del metronomo",
            "niente loop e niente registrazione"],
           ["pedalboard", "Catena di effetti, amplificatore, mastering",
            "restano solo riverbero e chorus del synth"]],
          [0.24, 0.46, 0.30]),
    P("Sono già nei requisiti del programma (<font name='DVM'>pip install -r requirements.txt</font>); gli "
      "installer per Linux, Windows e macOS li installano da soli."),
    tip("Usa le <b>cuffie</b> o delle casse decenti: gli effetti (soprattutto riverbero, compressore e "
        "limiter) si giudicano male dagli altoparlanti di un portatile."),
    tip(["Oltre al SoundFont, SoundText può suonare gli <b>strumenti campionati SFZ</b> (pianoforti, bassi, "
         "batterie, archi...). Lo script <font name='DVM'>scarica_strumenti.py</font>, uguale su Linux, Windows "
         "e macOS, li scarica e installa per te: <font name='DVM'>python3 scarica_strumenti.py</font>, lanciato "
         "senza altro, mostra un menu numerato dei gruppi disponibili. Su Windows l'installer mette anche "
         "le voci nel menu Start. Se ne parla nel capitolo 14.",
         "Dal menu <b>Suoni → Scarica</b> si prendono anche i profili NAM e le casse IR per l'amplificatore "
         "(capitolo 10)."], "Più suoni, gratis"),
]

# ------------------------------------------------------------------ 3
story += chapter("3. Il progetto e la finestra")
story += [
    steps([
        "<b>Progetto → Nuovo</b> (<b>Ctrl+N</b>).",
        "Nella barra dei comandi, blocco <b>Tempo / Metrica / Tonalità</b>: imposta <b>100 BPM</b>, "
        "<b>4/4</b> e <b>Am</b>. La tonalità viene proposta dai generatori.",
        "Salva subito: <b>Progetto → Salva</b> (<b>Ctrl+S</b>), per esempio come "
        "<b>Il_mio_primo_brano.st</b> nella cartella <b>songs/</b>.",
        "Controlla di essere nella vista <b>Struttura</b> (pulsante in alto a destra; è la vista iniziale).",
    ]),
    tip("Salvare all'inizio non è un vezzo: le registrazioni e i file audio importati finiscono nella "
        "cartella <b>Il_mio_primo_brano_audio/</b> accanto al file .st. Da qui in poi premi <b>Ctrl+S</b> "
        "ogni tanto, e ricorda che <b>Ctrl+Z</b> annulla qualunque modifica."),
    img("01_struttura_crop.png", 17, "La vista Struttura del brano finito: una riga per traccia, i box "
        "(Strofa, Ritornello, Strofa 2) sull'asse del tempo, il mixer (Vol, Pan, M, S, FX) nelle testate a "
        "sinistra."),
    CondPageBreak(5 * cm), P("Le parti della finestra", h2),
    bullets([
        "<b>Barra dei comandi</b>: torna all'inizio, <b>Play</b>/Pausa (<b>Spazio</b> o F5), Stop, "
        "<b>●</b> Registra, loop A-B, metronomo; poi tempo, metrica, levare e tonalità; le viste "
        "<b>Struttura</b>/<b>Testo</b>; il <b>Master</b> con il suo pulsante <b>FX</b>. In alto a destra, "
        "accanto ai menu, la casella <b>Cerca un comando… Ctrl+K</b>.",
        "<b>Barra di avanzamento</b>: tempo trascorso e durata; clic per saltare in un punto. A destra, "
        "l'indicatore di livello del master con la spia <b>CLIP</b> (capitolo 8).",
        "<b>Testate delle tracce</b> (a sinistra): nome e strumento, <b>M</b> (Mute), <b>S</b> (Solo), "
        "<b>FX</b> (effetti), le manopole <b>Vol</b> e <b>Pan</b> e il menu <b>⋯</b> con tutte le azioni "
        "della traccia. Durante l'ascolto un sottile vu-meter sul bordo destro mostra il livello della traccia.",
        "<b>Righe con i box</b>: ogni box è un pezzo di musica con un nome. Si trascina nel tempo, "
        "si apre con un doppio click, il tasto destro dà tutte le azioni (Play, Duplica, Rinomina, "
        "Trasponi, Taglia/Copia/Incolla, Elimina).",
        "<b>Righello</b> in alto: clic per spostare la testina (il prossimo Play parte da lì).",
    ]),
]

# ------------------------------------------------------------------ 4
story += chapter("4. Gli accordi: il giro armonico")
story += [
    P("Gli accordi sono la base su cui si appoggiano basso e chitarra: si parte da qui. SoundText li scrive "
      "per te a partire da uno stile."),
    steps([
        "Clicca <b>+ Aggiungi traccia</b> (sotto l'ultima riga) → <b>Genera una traccia → Giro armonico...</b>",
        "Nel dialogo: <b>Tonalità</b> Am (già proposta), <b>Stile</b> <b>Pop minore (i-VI-III-VII)</b>, "
        "<b>Durata di ogni accordo</b> 1 battuta, <b>Battute</b> 8.",
        "Premi <b>▶ Ascolta</b>. Se non ti convince premi <b>Nuova variazione</b>, oppure cambia stile.",
        "Premi <b>OK</b>: nasce la traccia <b>Accordi</b> (pianoforte) con un box di 8 battute.",
        "Tasto destro sul box → <b>Rinomina...</b> → «Strofa».",
    ]),
    img("02_giro.png", 12.5, "Il dialogo «Genera giro armonico»: stile, durata degli accordi, battute, "
        "variabilità e l'anteprima modificabile. «Ascolta» fa sentire il risultato prima di confermare."),
    CondPageBreak(5 * cm), P("Il ritornello", h2),
    steps([
        "Tasto destro sul nome della traccia <b>Accordi</b> → <b>Genera giro armonico in questa traccia...</b>",
        "Stile <b>Minore epico (i-VI-VII-i)</b>, 8 battute, <b>OK</b>: il nuovo box viene messo subito dopo "
        "la strofa. Rinominalo «Ritornello».",
        "Seleziona il box «Strofa» e premi <b>Ctrl+D</b> (Duplica): la copia va nel primo spazio libero, "
        "cioè dopo il ritornello. Rinominala «Strofa 2».",
    ]),
    CondPageBreak(5 * cm), P("Capire il cursore Variabilità", h2),
    P("A 0% lo stile viene scritto così com'è; alzandolo compaiono accordi più ricchi (settime, sus), "
      "dominanti secondarie e sostituzioni. I preset <b>Fedele</b> (15%), <b>Musicista</b> (35%) e "
      "<b>Creativo</b> (75%) sono buoni punti di partenza. Il testo nell'anteprima si può anche "
      "modificare a mano prima di premere OK."),
    tip("Vuoi vedere cosa c'è dentro un box? Doppio click: si apre l'editor con il testo, per esempio "
        "<font name='DVM'>4: 4Am 4F 4C 4G</font> (griglia a quarti, ogni accordo dura 4 quarti = una "
        "battuta). Nel capitolo 7 vediamo come si legge questa scrittura."),
]

# ------------------------------------------------------------------ 5
story += chapter("5. Batteria e basso")
story += [
    CondPageBreak(5 * cm), P("Batteria: strofe leggere, ritornello pieno", h2),
    steps([
        "<b>+ Aggiungi traccia → Genera una traccia → Batteria...</b>",
        "<b>Stile</b> Rock, <b>Battute</b> 8, <b>Fill ogni N battute</b> 4, <b>Fill a frasi</b> spuntato, "
        "<b>Intensità</b> <b>Leggera (strofa, intro)</b>. Ascolta con <b>Con le altre tracce</b> spuntato "
        "per sentirla insieme agli accordi, poi <b>OK</b>.",
        "Tasto destro sul nome della traccia <b>Batteria</b> → <b>Genera batteria in questa traccia...</b>: "
        "8 battute con <b>Intensità</b> <b>Piena (ritornello)</b> — passa al ride, suona più forte e apre "
        "con un crash. Il box va dopo il primo: rinominalo «Groove pieno».",
        "Per la Strofa 2 duplica il primo box (<b>Ctrl+D</b>), oppure generane uno nuovo con "
        "<b>Finale sull'ultima battuta</b> spuntato per chiudere il brano con un colpo di crash.",
    ]),
    img("03_batteria.png", 12, "Il dialogo della batteria: stile, battute, fill, intensità e variabilità. "
        "L'anteprima è il testo della batteria (kick, snare, hihat...), modificabile."),
    CondPageBreak(5 * cm), P("Basso: segue gli accordi da solo", h2),
    steps([
        "<b>+ Aggiungi traccia → Genera una traccia → Basso dagli accordi...</b> (è attivo solo quando il "
        "brano ha una traccia di accordi).",
        "<b>Accordi da</b>: Accordi. <b>Stile</b>: <b>Fondamentale/quinta</b> (semplice e solido) oppure "
        "<b>Ottave</b> per un ritornello più mosso. <b>OK</b>.",
        "Il basso copre tutto il giro: strofa, ritornello e strofa 2.",
    ]),
    tip(["<b>Rigenera solo alcune battute</b>: se una battuta non ti piace, indica «da N a M» sotto "
         "l'anteprima e premi <b>Rigenera queste</b>: cambiano solo quelle.",
         "<b>Shift+Spazio</b> ascolta solo il box selezionato; <b>Spazio</b> tutto il brano."],
        "Per rifinire"),
]

# ------------------------------------------------------------------ 6
story += chapter("6. La chitarra elettrica")
story += [
    P("Per usare bene l'amplificatore (capitolo 10) serve un suono di chitarra elettrica <b>pulito</b>: "
      "sarà l'amplificatore di SoundText a distorcerlo, come succede con una chitarra vera collegata a un "
      "amplificatore."),
    CondPageBreak(5 * cm), P("Creare lo strumento", h2),
    steps([
        "Menu <b>Strumenti → Gestisci strumenti...</b> → <b>+ Nuovo strumento</b>.",
        "<b>Nome nel programma</b>: ChitarraElettrica (una parola, senza spazi).",
        "<b>Suono General MIDI</b>: digita «clean» e scegli <b>Electric Guitar (clean)</b>. Ottava, "
        "estensione e voicing vengono compilati da soli. <b>OK</b>.",
    ]),
    warn("Non scegliere «Overdriven Guitar» o «Distortion Guitar» se poi userai l'amplificatore: "
         "distorceresti due volte, con un suono impastato e confuso."),
    CondPageBreak(5 * cm), P("Generare l'accompagnamento", h2),
    steps([
        "<b>+ Aggiungi traccia → Genera una traccia → Accompagnamento o riff...</b> e scegli "
        "<b>ChitarraElettrica</b> come strumento (polifonico = accompagnamento).",
        "<b>Accordi da</b>: Accordi. <b>Stile</b>: <b>Accordi battuti (comping)</b>. Lascia spuntato "
        "<b>Rivolti vicini</b>: gli accordi si muovono il meno possibile, come li suonerebbe un chitarrista.",
        "<b>Ascolta</b>, poi <b>OK</b>. Per ora suonerà pulita: l'amplificatore arriva nel capitolo 10.",
    ]),
    tip("Hai una chitarra vera? Crea invece una <b>Traccia audio</b> e registrala collegata all'ingresso "
        "<b>INST/Hi-Z</b> della scheda audio, senza amplificatore: si registra il suono pulito e "
        "l'amplificatore di SoundText lo lavora dopo, e puoi cambiarlo quando vuoi senza rifare la ripresa."),
]

# ------------------------------------------------------------------ 7
story += chapter("7. La melodia: scritta a mano o registrata")
story += [
    CondPageBreak(5 * cm), P("Strada A — Scrivere le note", h2),
    steps([
        "<b>+ Aggiungi traccia → Traccia con strumento...</b> (<b>Ctrl+T</b>): nome «Melodia», strumento "
        "Trumpet (o uno strumento personalizzato: flauto, sax, violino...).",
        "Doppio click sulla riga della traccia, all'inizio della strofa: si apre l'editor di un nuovo box.",
        "Scrivi le note (vedi sotto), premi <b>▶ Play</b> nell'editor per ascoltarle, poi <b>OK</b>.",
    ]),
    CondPageBreak(5 * cm), P("La scrittura di SoundText in cinque minuti", h2),
    table([["Scrivi", "Significa", "Esempio"],
           ["<font name='DVM'>c d e f g a b</font>", "Note (do re mi fa sol la si)", "<font name='DVM'>c e g</font>"],
           ["<font name='DVM'>*n</font>", "Ottava della nota", "<font name='DVM'>a*4 c*5</font>"],
           ["<font name='DVM'>#</font>, <font name='DVM'>b</font> o <font name='DVM'>♭</font>",
            "Diesis e bemolle", "<font name='DVM'>f# eb</font>"],
           ["<font name='DVM'>N:</font>", "Griglia: 4 = quarti, 8 = ottavi, 16 = sedicesimi",
            "<font name='DVM'>8:</font>"],
           ["numero davanti", "Durata in unità di griglia", "<font name='DVM'>2c*5</font> (due ottavi)"],
           ["<font name='DVM'>r</font>, <font name='DVM'>Nr</font>", "Pausa", "<font name='DVM'>2r</font>"],
           ["<font name='DVM'>N@</font>, <font name='DVM'>mf@</font>", "Volume delle note (velocity o dinamica)",
            "<font name='DVM'>90@</font>, <font name='DVM'>p@</font>"],
           ["<font name='DVM'>[...]</font>", "Note insieme", "<font name='DVM'>[c e g]</font>"],
           ["Maiuscola", "Accordo", "<font name='DVM'>Am F C G7</font>"],
           ["<font name='DVM'>N(...)</font>", "Ripete N volte", "<font name='DVM'>2(c d e)</font>"]],
          [0.24, 0.48, 0.28]),
    P("Una frase per la strofa in La minore, a ottavi:"),
    P("8: 90@ a*4 c*5 e*5 d*5 2c*5 a*4 2r<br/>8: 100@ e*5 e*5 d*5 c*5 4a*4 4r", code),
    P("E una frase che cresce di volume (<font name='DVM'>p@ &gt;&gt; ... f@</font> è un crescendo):"),
    P("4: p@ &gt;&gt; a*4 c*5 e*5 f@ 4e*5", code),
    P("I colori dell'editor ti dicono come il programma legge il testo (note azzurre, accordi ambra, pause "
      "grigie...), e un errore viene segnalato prima di confermare. Durante la scrittura un "
      "autocompletamento suggerisce accordi, stili e percussioni."),
    CondPageBreak(5 * cm), P("Strada B — Registrare la voce", h2),
    steps([
        "<b>+ Aggiungi traccia → Traccia audio (voce, chitarra, tastiera)...</b>, nome «Voce».",
        "Clicca sul righello dove vuoi iniziare, poi il pulsante rosso <b>●</b> della traccia "
        "(o <b>Ctrl+R</b>, o semplicemente <b>R</b>).",
        "Nel dialogo: <b>Scheda audio</b>, <b>Cosa registri</b> = Voce / microfono, <b>Ingresso</b>. "
        "Regola il gain sulla scheda perché le parti più forti arrivino tra <b>−12 e −6 dB</b> "
        "senza accendere la spia rossa.",
        "<b>Conteggio</b> 1 o 2 battute, <b>● Registra</b>, canta, <b>■ Stop</b>. Se va bene, "
        "<b>Tieni la ripresa</b>: diventa una clip nella traccia.",
    ]),
    tip(["Per sentirti senza ritardo usa il <b>monitoraggio diretto</b> della scheda audio (tasto o "
         "manopola «direct monitor»): SoundText manda in cuffia solo il brano.",
         "La prima volta usa <b>Calibra...</b> nel dialogo, così la ripresa risulta perfettamente a tempo.",
         "Una clip si accorcia trascinandone i bordi e si divide con <b>S</b> nel punto della testina."],
        "Registrare bene"),
    P("Strada C — Suonare con la tastiera del computer o con una <b>tastiera MIDI</b> collegata: menu ⋯ della "
      "traccia → <b>Suona con la tastiera...</b> (la tastiera MIDI si sceglie nel menu «Tastiera MIDI» del "
      "dialogo, con dinamica, accordi, pedale del sustain e pitch bend), le note suonate diventano testo nella "
      "traccia.", small),
    P("Strada D — Cantare o suonare e far scrivere le note a SoundText: <b>Traccia → Importa in questa traccia → "
      "Audio → notazione (microfono o file)...</b> La finestra procede in tre passi: <b>1. Cosa riconoscere</b> "
      "(Melodia, Percussioni o Accordi), <b>2. Audio</b> (registra o scegli un file) e <b>3. Risultato</b>: "
      "la conversione parte da sola, si ascolta con <b>▶ Ascolta</b> e si conferma con <b>Inserisci nella "
      "traccia</b>.", small),
]

# ------------------------------------------------------------------ 8
story += chapter("8. Ascoltare, sistemare, bilanciare")
story += [
    CondPageBreak(5 * cm), P("Ascolto", h2),
    bullets([
        "<b>Spazio</b> (o F5): Play/Pausa del brano; <b>F6</b>: Stop; clic sul righello per saltare.",
        "<b>Loop A-B</b>: durante l'ascolto <b>Ctrl+[</b> fissa l'inizio e <b>Ctrl+]</b> la fine; "
        "<b>Ctrl+L</b> accende e spegne il loop; con il loop acceso <b>Play</b> parte da A. Ottimo per "
        "lavorare sul ritornello.",
        "<b>Shift+Spazio</b>: solo il box selezionato. Il <b>metronomo</b> è nella barra dei comandi; suono "
        "e volume del click in <b>Opzioni → Metronomo...</b>",
    ]),
    CondPageBreak(5 * cm), P("Struttura", h2),
    bullets([
        "Trascina i box per spostarli nel tempo (si agganciano alla battuta).",
        "<b>Ctrl+D</b> duplica, <b>Canc</b> elimina, tasto destro → <b>Trasponi...</b> per cambiare "
        "tonalità a un box.",
        "Per spostare un box su un'altra traccia: tasto destro → Taglia, poi tasto destro sulla riga di "
        "destinazione → Incolla qui.",
    ]),
    CondPageBreak(5 * cm), P("Il bilanciamento (mix)", h2),
    P("Volume e pan di ogni traccia sono le due manopole della sua testata: <b>Vol</b> (0–200%, 100% = "
      "volume originale) e <b>Pan</b> (C = centro, L/R = sinistra/destra). Si girano trascinando su e giù "
      "o con la rotellina; doppio click = torna a 100% / al centro. Il pan si applica <b>dopo</b> gli "
      "effetti della traccia, quindi una chitarra spostata a destra resta a destra anche con un "
      "amplificatore mono."),
    table([["Traccia", "Volume indicativo", "Pan indicativo"],
           ["Batteria", "90–100%", "centro"],
           ["Basso", "90–110%", "centro"],
           ["Accordi (piano)", "70–85%", "leggermente a sinistra"],
           ["Chitarra elettrica", "75–90%", "leggermente a destra"],
           ["Voce o melodia", "100–120%", "centro"]], [0.36, 0.32, 0.32]),
    tip("Regola i volumi <b>prima</b> degli effetti, e ricontrollali dopo: compressore e amplificatore "
        "cambiano il volume percepito. <b>S</b> (Solo) su una traccia per ascoltarla da sola, "
        "<b>M</b> (Mute) per zittirla."),
    CondPageBreak(5 * cm), P("Tenere d'occhio i livelli", h2),
    bullets([
        "Durante l'ascolto ogni testata ha un <b>vu-meter</b> sul bordo destro: la cima diventa rossa se la "
        "traccia supera il fondo scala.",
        "Accanto alla barra di avanzamento c'è il livello del <b>master</b> in dBFS e la spia <b>CLIP</b>: "
        "si accende quando il mix supera il fondo scala e il suono si rompe, e resta accesa finché non la "
        "clicchi. Il suggerimento della spia dice in quali battute succede.",
        "<b>Riproduzione → Analizza livelli...</b> misura, in sottofondo, il picco di ogni traccia suonata da "
        "sola e del mix: il valore compare nella testata di ogni traccia (CLIP in rosso se clippa già da "
        "sola) e un riepilogo dice dove intervenire.",
    ]),
]

# ------------------------------------------------------------------ 9
story += chapter("9. Gli effetti sulle tracce")
story += [
    P("Ogni traccia, di note o audio, ha un pulsante <b>FX</b> nella testata. Premendolo si apre in fondo "
      "alla finestra il <b>pannello Effetti</b> di quella traccia. Il pulsante si accende quando la "
      "traccia ha effetti e ne mostra il numero (es. <b>FX 3</b>)."),
    img("05_invio_rapido_crop.png", 17, "Il pannello Effetti della traccia Accordi: la card «Invio "
        "rapido» con riverbero, chorus e ambiente. A destra, «+ Effetto» aggiunge la catena."),
    CondPageBreak(5 * cm), P("Invio rapido (solo tracce di note)", h2),
    P("<b>Riverbero</b> e <b>Chorus</b> del synth, da 0 a 100%, e l'<b>Ambiente</b> del riverbero, uno per "
      "tutto il brano. Nella <b>Stanza piccola</b> predefinita il riverbero si sente appena: per il nostro "
      "brano scegli <b>Sala</b> e dai il 20–30% di riverbero agli accordi."),
    CondPageBreak(5 * cm), P("La catena di effetti", h2),
    P("<b>+ Effetto</b> aggiunge un effetto in fondo alla catena; il suono passa da sinistra a destra. "
      "Ogni effetto è una <b>card</b>:"),
    bullets([
        "il pulsante di <b>accensione</b> (in alto a sinistra) lo spegne senza perdere le regolazioni;",
        "<b>◀ ▶</b> lo spostano nella catena, <b>✕</b> lo toglie;",
        "il menu dei <b>preset</b>: scegline uno, poi ritocca le manopole (il menu diventa "
        "«Personalizzato»);",
        "le <b>manopole</b>: trascinale col mouse o usa la rotellina; doppio click sul valore per tornare "
        "al predefinito.",
    ]),
    table([["Famiglia", "Effetti"],
           ["Dinamica", "Compressore, Limiter, Noise gate, Volume (solo guadagno, ±24 dB)"],
           ["Tono", "EQ a 3 bande, Filtro passa-alto, Filtro passa-basso"],
           ["Saturazione", "Amplificatore, Profilo NAM (capitolo 10), Distorsione"],
           ["Spazio", "Delay (anche a tempo col brano), Riverbero, Chorus, Phaser"],
           ["Plugin", "Plugin (VST3/LV2) installati sul computer (capitolo 14)"]], [0.25, 0.75]),
    CondPageBreak(5 * cm), P("Il loop di calibrazione", h2),
    P("Aprendo il pannello, SoundText sceglie un tratto di <b>10 secondi</b> (dal box selezionato o dalla "
      "testina) e lo imposta come loop sul righello. Premi <b>▶ Ascolta il loop</b>: il tratto si ripete e "
      "<b>ogni ritocco si sente dal giro successivo</b>, senza aspettare."),
    bullets([
        "<b>Loop</b>: da 2 a 30 secondi;",
        "<b>Con le altre tracce</b>: senti la traccia nel mix (consigliato) o da sola;",
        "<b>Prima / Dopo</b>: premuto, senti la traccia senza la catena: il modo più onesto per capire se "
        "un effetto migliora davvero;",
        "<b>Annulla modifiche</b>: torna a com'era all'apertura del pannello;",
        "<b>Copia su…</b>: copia la catena su un'altra traccia (o sul master);",
        "<b>✕</b>: chiude; il loop di prima torna com'era e gli effetti vengono applicati a tutta la "
        "traccia in sottofondo (la barra di stato avvisa quando ha finito).",
    ]),
    CondPageBreak(5 * cm), P("Ricette per il nostro brano", h2),
    table([["Traccia", "Catena consigliata (nell'ordine)", "Perché"],
           ["Basso", "Compressore «Basso»", "Livello costante, basso più presente"],
           ["Batteria", "Compressore «Batteria» → EQ «Più presenza»", "Più compatta e incisiva"],
           ["Accordi", "EQ «Più calore» + Invio rapido riverbero 25%, ambiente Sala",
            "Morbidi e dietro alla voce"],
           ["Voce registrata", "Filtro passa-alto «Voce» → Noise gate «Voce» → Compressore «Voce» → "
                               "EQ «Più presenza» → Delay «A tempo 1/4» → Riverbero «Stanza»",
            "Pulita, costante, davanti, con un po' di spazio"],
           ["Melodia scritta", "Riverbero «Sala» (mix 15–20%)", "Meno «finta», più ambiente"]],
          [0.18, 0.52, 0.30]),
    tip(["<b>Delay a tempo</b>: nel delay, menu <b>A tempo</b> → 1/4, 1/8 puntato... Le ripetizioni cadono "
         "a tempo col BPM del brano; la manopola Tempo si spegne e mostra i millisecondi (a 100 BPM, "
         "1/8 puntato = 450 ms).",
         "Pochi effetti, fatti bene: prova sempre con <b>Prima / Dopo</b>."], "Due consigli"),
]

# ------------------------------------------------------------------ 10
story += chapter("10. L'amplificatore per chitarra")
story += [
    P("L'<b>Amplificatore</b> è un amplificatore da chitarra completo: preamplificatore (la distorsione), "
      "controlli di tono e cassa. Lo applichiamo alla traccia ChitarraElettrica."),
    steps([
        "Premi <b>FX</b> sulla traccia <b>ChitarraElettrica</b>.",
        "<b>+ Effetto → Saturazione → Amplificatore</b>. Parte dal preset <b>Blues</b>.",
        "<b>▶ Ascolta il loop</b>, poi scegli il preset <b>Rock classico</b> (modello British, cassa 4×12 "
        "chiusa).",
        "Completa la catena: <b>Noise gate</b> «Chitarra» <b>prima</b> dell'amplificatore (usa ◀ per "
        "spostarlo), poi <b>Delay</b> «A tempo 1/8 puntato» e <b>Riverbero</b> «Sala» <b>dopo</b>.",
        "Confronta con <b>Prima / Dopo</b>, sistema <b>Livello</b> e volume della traccia, chiudi con ✕.",
    ]),
    img("04_effetti_chitarra_crop.png", 17, "La catena della chitarra: Noise gate → Amplificatore "
        "(Rock classico: British, 4×12 chiusa) → Delay a tempo 1/8 puntato → Riverbero Sala."),
    CondPageBreak(5 * cm), P("Modelli e casse", h2),
    table([["Modello", "Carattere", "Toni", "Per"],
           ["Pulito", "Quasi senza saturazione", "Fender", "Funk, pop, arpeggi, jazz"],
           ["Crunch", "Saturazione morbida che risponde al tocco", "Fender", "Blues, rock leggero"],
           ["British", "Medi in evidenza, due stadi di saturazione", "Marshall", "Rock classico, hard rock"],
           ["High gain", "Bassi stretti, molta saturazione", "Marshall", "Metal, rock moderno"]],
          [0.16, 0.42, 0.14, 0.28]),
    table([["Cassa", "Suono"],
           ["Combo 1×12", "Equilibrata, aperta: la scelta più versatile"],
           ["2×12", "Più piena, medi più scolpiti"],
           ["4×12 chiusa", "Più corpo e «botta» sui bassi: rock e metal"],
           ["Vintage 1×10", "Più sottile e nasale, anni '50–'60"],
           ["Nessuna", "Il suono diretto dell'amplificatore, senza cassa (raramente utile)"],
           ["File IR…", "La risposta all'impulso di una cassa vera, da un file WAV scelto da te "
                        "(vedi sotto)"]], [0.25, 0.75]),
    CondPageBreak(5 * cm), P("Una cassa vera: il file IR", h2),
    P("Una <b>IR</b> (risposta all'impulso) è la «fotografia» del suono di una cassa vera ripresa con un "
      "microfono: un piccolo file WAV. Se ne trovano moltissime gratuite in rete, di casse famose e con "
      "microfoni diversi, ed è il modo più semplice per avere un suono da studio. Per cominciare, "
      "<b>Suoni → Scarica → Scarica casse IR per gli amplificatori NAM...</b> scarica 20 casse per chitarra gratuite "
      "(meno di 1 MB) nella cartella <b>profili_nam/casse</b>."),
    steps([
        "Nella card dell'amplificatore, menu <b>Cassa</b> → <b>File IR…</b>: si apre la finestra per scegliere "
        "il file (se annulli, resta la cassa di prima).",
        "Accanto al pulsante <b>Scegli IR…</b> compare il nome del file; il pulsante serve a cambiarlo.",
        "Prova più IR con <b>▶ Ascolta il loop</b>: microfoni e posizioni diverse cambiano molto il suono.",
    ]),
    tip("Copia i file IR in una cartella accanto al progetto (per esempio <b>ir/</b>): nel file .st il "
        "percorso si salva relativo al progetto, così spostando la cartella tutto continua a funzionare. "
        "Se un file non si trova più, la card lo segnala in rosso e si usa la cassa Combo 1×12."),
    CondPageBreak(5 * cm), P("Le manopole", h2),
    bullets([
        "<b>Guadagno</b>: quanto distorce. Poco = crunch, tanto = saturazione piena.",
        "<b>Bassi, Medi, Alti</b> (0–10): il circuito dei toni degli amplificatori veri (Fender o Marshall, "
        "secondo il modello). Come negli originali si influenzano a vicenda e a metà corsa i medi sono già un "
        "po' «scavati». Per far «uscire» la chitarra nel mix alza i <b>Medi</b>, non il volume; per il metal "
        "abbassali (3 o meno).",
        "<b>Presenza</b> (0–10): gli acuti dopo lo stadio finale, per dare «aria» e mordente.",
        "<b>Potenza</b> (0–100%): quanto si spinge lo stadio finale a valvole. Aggiunge calore (armoniche "
        "pari) e un po' di compressione sugli accordi tenuti («sag»): 30–50% è il suono di un amplificatore "
        "suonato a volume.",
        "<b>Livello</b>: il volume d'uscita. Più guadagno significa più volume: abbassa il Livello mentre "
        "sali col Guadagno.",
    ]),
    tip(["<b>L'ordine conta</b>: noise gate → amplificatore → delay → riverbero. Il gate prima toglie il "
         "fruscio che l'amplificatore gonfierebbe; delay e riverbero dopo restano puliti, come nelle "
         "pedaliere vere.",
         "<b>Accordi bassi definiti</b>: come negli amplificatori a valvole veri, i bassi saturano meno dei "
         "medi, quindi i power chord sulle corde gravi restano chiari invece di impastarsi.",
         "<b>Suona con il plettro, non con la manopola</b>: l'amplificatore risponde al tocco. Piano resta "
         "più pulito, attaccando forte si sporca e per un attimo «respira» (le valvole cambiano punto di "
         "lavoro), soprattutto con Crunch e British. Con le tracce a note lo stesso effetto lo danno le "
         "dinamiche (<font name='DVM'>p@</font>, <font name='DVM'>f@</font>).",
         "<b>Meno guadagno di quanto pensi</b>: da solo un suono molto distorto impressiona, nel mix "
         "diventa un impasto. Nel ritornello con batteria e basso spesso basta il Crunch.",
         "La <b>Distorsione</b> (stessa famiglia) è un pedale singolo: utile su basso e synth; per la "
         "chitarra l'Amplificatore è più completo."], "I segreti di un buon suono"),
    CondPageBreak(6 * cm), P("Un amplificatore vero: i profili NAM", h2),
    P("L'Amplificatore interno è comodo, ma è un'<i>imitazione</i>. <b>Neural Amp Modeler</b> (NAM) fa "
      "un'altra cosa: qualcuno ha collegato un amplificatore o un pedale <b>vero</b> a un computer, ne ha "
      "registrato il suono e ha «insegnato» a una rete neurale a comportarsi allo stesso modo. Il risultato è "
      "un piccolo file con estensione <font name='DVM'>.nam</font>, chiamato <b>profilo</b>. Caricarlo in "
      "SoundText equivale ad avere quell'amplificatore in sala prove, senza microfoni né rumore. "
      "Funziona su Linux, Windows e macOS, e non serve installare nient'altro."),
    P("Per capire cosa si scarica, bastano tre parole:", base),
    table([["Parola", "Che cos'è", "Cosa fare"],
           ["<b>Amp</b> (testata)", "Solo l'amplificatore, senza cassa. Da solo suona aspro e «ronzante».",
            "Niente: SoundText gli mette da solo una cassa interna; per un suono più vero, un file IR."],
           ["<b>Full rig</b>", "Amplificatore <b>con</b> la cassa già dentro.",
            "Niente: è pronto."],
           ["<b>Pedal</b>", "Un pedale (Tube Screamer, Klon...): da solo suona «piccolo».",
            "Metterlo <b>prima</b> di un amplificatore."]],
          [0.20, 0.50, 0.30]),

    CondPageBreak(5 * cm), P("Primo passo: scaricare i profili e le casse", h2),
    P("Fai queste due operazioni una volta sola. Servono due clic e circa 12 MB in tutto; non occorre "
      "registrarsi da nessuna parte."),
    steps([
        "Menu <b>Suoni → Scarica → Scarica profili NAM consigliati...</b> Arrivano 34 profili di "
        "amplificatori e pedali famosi (circa 11 MB) nella cartella <b>profili_nam</b> accanto a SoundText.",
        "Menu <b>Suoni → Scarica → Scarica casse IR per gli amplificatori NAM...</b> Arrivano 20 casse nella "
        "cartella <b>profili_nam/casse</b>. Ogni file ha il nome dell'amplificatore di cui riproduce la cassa.",
    ]),
    P("Ecco i profili scaricati, per famiglia, e quando usarli:", base),
    table([["Profili", "Tipo", "Adatti a"],
           ["Fender Twin Reverb (pulito, vibrato), Vox AC15 – Top Boost, Magnatone Super 59 (pulito, spinto), "
            "Marshall JCM2000 (pulito, crunch), Friedman Dirty Shirley Mini (pulito, crunch)",
            "amp", "Funk, pop, arpeggi, jazz, blues, country, rock classico"],
           ["Orange Rockerverb, Sovtek MIG50", "amp", "Stoner e doom"],
           ["Marshall JCM900 – lead, Splawn Pro Mod, Mesa Boogie Mark IV – lead", "amp",
            "Hard rock, metal anni '80, assoli"],
           ["Peavey 5150 e 6505+, Engl Savage, Meshuggah – djent", "amp", "Metal, metal moderno"],
           ["Bugera 333 (pulito, crunch), Marshall JVM (pulito, distorto): «con cassa»", "full rig",
            "Il modo più semplice per cominciare"],
           ["Ibanez TS9 Tube Screamer, Maxon OD808, Boss SD-1, Klon Centaur (clone), EarthQuaker Plumes "
            "(clone), Boss OS-2, Boss DS-1", "pedal", "Overdrive e distorsione davanti a un amplificatore: "
            "blues e rock"],
           ["MXR M77, Horizon Precision Drive, Fortin Grind", "pedal", "Boost per il metal"],
           ["Boss HM-2 – svedese", "pedal", "Death metal"],
           ["Tech 21 dUg DP3X", "pedal", "Per il <b>basso</b>"]], [0.52, 0.12, 0.36]),
    tip("Se vuoi il risultato più veloce possibile, scegli <b>Bugera 333 – crunch con cassa</b> (o "
        "<b>Marshall JVM – distorto con cassa</b> per un rock più spinto): è un amplificatore con la cassa "
        "già inclusa, quindi non devi fare altro che caricarlo.",
        "Il consiglio per cominciare"),

    CondPageBreak(7 * cm), P("Secondo passo: usare il profilo sulla chitarra", h2),
    P("Parti da una traccia di <b>ChitarraElettrica con suono pulito</b> (capitolo 6): sarà il profilo a "
      "distorcerla, proprio come l'amplificatore vero farebbe con una chitarra vera."),
    steps([
        "Premi <b>FX</b> sulla traccia <b>ChitarraElettrica</b>. Se c'è già l'<b>Amplificatore</b> interno, "
        "toglilo con ✕ oppure spegnilo: il profilo lo <b>sostituisce</b> (due amplificatori in fila "
        "distorcono due volte e suonano impastati).",
        "Premi <b>+ Effetto → Saturazione → Profilo NAM</b>. Si apre la finestra <b>Scegli un profilo "
        "NAM</b>: i profili della cartella <b>profili_nam</b> divisi per tipologia (amplificatori senza cassa, "
        "amplificatori con la cassa, pedali), ciascuno con tipo, suono e uso, e una casella per cercarli. "
        "<b>Altro file…</b> apre un <font name='DVM'>.nam</font> qualsiasi. Se annulli, l'effetto non viene "
        "aggiunto.",
        "Sulla card dell'effetto compaiono il nome del profilo, la marca, il modello e il tipo. Il pulsante "
        "<b>Scegli profilo…</b> serve a cambiarlo quando vuoi.",
        "Se il profilo è un <b>amp</b> (senza cassa), SoundText gli mette da solo una <b>cassa interna</b> "
        "adatta (4×12 per Marshall, Mesa, 5150 e simili, Combo 1×12 per Vox e simili, altrimenti 2×12). Per "
        "un suono più vero: menu <b>Cassa → File IR…</b> e scegli un file dalla cartella "
        "<b>profili_nam/casse</b>. Se è un <b>full rig</b> o un pedale la cassa resta su <b>Nessuna / "
        "inclusa</b>.",
        "Premi <b>▶ Ascolta il loop</b> e, mentre suona, regola <b>Ingresso</b> e <b>Livello</b> (vedi sotto). "
        "Confronta con <b>Prima / Dopo</b>.",
        "Completa la catena come per l'Amplificatore: <b>Noise gate</b> «Chitarra» <b>prima</b> del profilo, "
        "<b>Delay</b> e <b>Riverbero</b> <b>dopo</b>. Chiudi con ✕.",
    ]),
    table([["Manopola", "Cosa fa", "Come regolarla"],
           ["<b>Ingresso</b>", "Quanto forte arriva la chitarra al profilo: è il «gain» dell'amplificatore.",
            "Più alto = più distorsione, più basso = più pulito. Se suona troppo sporco, abbassalo prima di "
            "cambiare profilo."],
           ["<b>Cassa</b>", "Quale cassa si sente.",
            "<i>Nessuna / inclusa</i> per full rig e pedali; per gli amp una cassa interna (Combo 1×12, 2×12, "
            "4×12 chiusa, Vintage 1×10, scelta da sola) o <i>File IR…</i>."],
           ["<b>Livello</b>", "Il volume d'uscita del profilo.",
            "Serve a pareggiare il volume con le altre tracce."],
           ["<b>Preset</b>", "Tre partenze rapide.",
            "<i>Neutro</i>, <i>Più spinto</i> (+6 dB di ingresso), <i>Più pulito</i> (−6 dB)."]],
          [0.16, 0.38, 0.46]),
    tip(["<b>Amplificatore e pedale insieme</b>: per un suono rock «vero» metti prima un profilo <b>pedal</b> "
         "(Tube Screamer) e dopo un profilo <b>amp</b> con la sua cassa. Aggiungi i due effetti nello stesso "
         "modo e controlla l'ordine con ◀ ▶: noise gate, pedale, amplificatore, delay, riverbero.",
         "<b>Cambiare profilo non fa saltare il volume</b>: SoundText porta ogni profilo alla stessa "
         "sonorità, quindi puoi provarne molti di seguito e confrontarli a parità di volume.",
         "Se il suono è troppo «aspro» o «ronzante», quasi sempre manca la cassa: scegline una nel menu "
         "<b>Cassa</b> o un IR. Se è troppo «piccolo» e sottile, stai usando un pedale da solo: mettilo "
         "davanti a un amplificatore.",
         "<b>Il synth arriva «secco»</b>: una traccia di note che va in un profilo NAM viene suonata senza il "
         "riverbero e il chorus del synth, come una chitarra collegata direttamente all'amplificatore (un "
         "amplificatore molto spinto farebbe sfrigolare la coda del riverbero). Il riverbero mettilo con "
         "l'effetto <b>Riverbero</b> dopo il profilo."],
        "Trucchi per un buon suono"),

    CondPageBreak(5 * cm), P("Se qualcosa non va", h2),
    table([["Cosa senti o vedi", "Perché", "Rimedio"],
           ["Suono aspro, che «frigge»", "Amp senza cassa (Cassa su Nessuna)",
            "Cassa → una cassa interna, o File IR… e scegli un file"],
           ["Suono sottile e debole", "Hai caricato un pedale da solo", "Mettilo prima di un amplificatore"],
           ["Troppo distorto", "Ingresso alto, oppure il profilo è già high gain",
            "Abbassa Ingresso, o usa un profilo più pulito"],
           ["Doppia distorsione, impastato", "C'è ancora l'Amplificatore interno", "Toglilo o spegnilo"],
           ["Nome del profilo in rosso, suono invariato", "Il file è stato spostato o cancellato",
            "Scegli di nuovo il profilo con Scegli profilo…"],
           ["«Non posso usare questo profilo»", "Formato sperimentale non supportato",
            "Prova un altro profilo (i normali funzionano tutti)"],
           ["Il ritocco è lento", "La rete neurale è pesante",
            "Normale: circa 1 secondo a ritocco, una trentina di secondi (su più core) per una traccia di 3 "
            "minuti. Livello, Cassa ed effetti dopo il profilo non fanno ricalcolare la rete"]],
          [0.30, 0.34, 0.36]),
    tip(["Nel file del brano si salva il <b>percorso</b> del profilo, relativo alla cartella del progetto. "
         "Se sposti o mandi il brano a qualcuno, porta con te anche la cartella <b>profili_nam</b> (o copia i "
         "file accanto al progetto).",
         "Il profilo lavora in <b>mono</b>, come il plugin originale: gli effetti «spaziali» (riverbero, "
         "chorus) vanno <b>dopo</b>. Il pan della traccia si applica dopo la catena, quindi la chitarra resta "
         "dove l'hai messa."], "Salvare e spostare il brano"),

    CondPageBreak(5 * cm), P("Trovare altri profili", h2),
    P("I 34 profili consigliati bastano per cominciare, ma le possibilità sono enormi. Il sito di "
      "riferimento è <b>Tone3000</b> (tone3000.com), con decine di migliaia di profili gratuiti; per scaricare "
      "può chiedere di creare un account gratuito."),
    steps([
        "Cerca l'apparecchio che ti piace («Plexi», «Dumble», «Rectifier», «Tube Screamer»...).",
        "Filtra per piattaforma <b>NAM</b> e per tipo: <i>amp</i> (serve una cassa), <i>full rig</i> (con la cassa, "
        "pronto) o <i>pedal</i>. Ordinando per download trovi i più usati.",
        "Scarica il file: spesso è uno ZIP con più varianti (<i>standard</i>, <i>lite</i>, <i>feather</i>, "
        "<i>nano</i>). La <b>standard</b> è la qualità piena, le altre sono più leggere: SoundText le legge tutte.",
        "Estrai i <font name='DVM'>.nam</font> nella cartella <b>profili_nam</b> e sceglili con "
        "<b>Scegli profilo…</b>. Su Tone3000 trovi anche gli <b>IR</b> (tipo <i>IR</i>) per l'altra manopola, "
        "<b>Cassa → File IR…</b>.",
    ]),
]

# ------------------------------------------------------------------ 11
story += chapter("11. Il mastering")
story += [
    P("Il <b>mastering</b> è l'ultimo ritocco al mix intero: lo rende più compatto, equilibrato e "
      "abbastanza forte da stare accanto ad altri brani. In SoundText si fa con la catena di effetti "
      "sul <b>master</b>."),
    img("07_master_btn.png", 9, "Il pulsante FX accanto allo slider Master, nella barra dei comandi."),
    steps([
        "Clicca sul righello all'inizio del <b>ritornello</b> (la parte più forte del brano): il loop di "
        "calibrazione parte dalla testina.",
        "Premi <b>FX</b> accanto allo slider <b>Master</b>: il pannello si apre su «Master · mix finale».",
        "Premi <b>+ Catena di mastering</b>: arrivano <b>EQ</b> «Neutro», <b>Compressore</b> «Colla del "
        "mix» e <b>Limiter</b> «Più forte».",
        "<b>▶ Ascolta il loop</b> e confronta con <b>Prima / Dopo</b>.",
        "Regola il <b>Guadagno del limiter</b>: più alto = brano più forte e più «schiacciato». Fermati "
        "quando la batteria perde colpo. Il <b>Tetto</b> resta a −1 dB.",
        "Se serve, piccoli ritocchi all'EQ (±1–3 dB). Chiudi con ✕.",
    ]),
    img("06_master_crop.png", 17, "La catena di mastering: EQ, compressore «Colla del mix» (2:1, attacco "
        "lento) e limiter «Più forte» (tetto −1 dB)."),
    warn(["Con <b>Prima / Dopo</b> il «dopo» è più forte, e l'orecchio crede sempre che più forte sia più "
          "bello. Per un confronto onesto abbassa temporaneamente il Guadagno del limiter finché i due "
          "suonano a volume simile.",
          "Lo slider <b>Master</b> agisce <b>prima</b> della catena: con il limiter attivo alzarlo non rende il "
          "brano più forte oltre il tetto, lo schiaccia soltanto."], "Due trappole"),
    tip(["Se la spia <b>CLIP</b> si accende già <b>prima</b> della catena (le tracce sommate superano 0 dB), "
         "metti in testa alla catena del master l'effetto <b>Volume</b> con il preset «Margine per il "
         "master» (−6 dB): compressore e limiter lavorano meno e la batteria non viene schiacciata. A "
         "differenza del volume delle tracce, non cambia il timbro degli strumenti.",
         "<b>Riproduzione → Analizza livelli...</b> dice quali tracce clippano già da sole: lì conviene "
         "abbassare il volume della traccia."], "Il margine prima del master"),
    P("Il master vale per l'ascolto, per l'export WAV del brano e per la base che senti mentre registri. "
      "Dopo un ritocco al solo master il Play successivo è rapido: il mix prima del master resta in "
      "memoria."),
]

# ------------------------------------------------------------------ 12
story += chapter("12. Esportare il WAV")
story += [
    steps([
        "Salva il progetto (<b>Ctrl+S</b>).",
        "Ascolta tutto il brano un'ultima volta dall'inizio.",
        "Menu <b>Progetto → Esporta → Mix audio (WAV)...</b>",
        "Scegli nome e cartella (viene proposto il nome del progetto) e conferma.",
    ]),
    P("Il file è un <b>WAV stereo a 48 kHz, 24 bit</b>, cioè qualità da studio. Contiene il brano "
      "<b>come lo senti</b>: solo le tracce udibili (rispetta Mute e Solo), le tracce audio, tutti gli "
      "effetti delle tracce, l'amplificatore e la catena del master."),
    table([["Esportazione", "Dove", "Effetti", "Master"],
           ["Mix del brano (WAV)", "Progetto → Esporta → Mix audio (WAV)...", "sì", "sì"],
           ["Una sola traccia (WAV)", "Tasto destro sul nome della traccia → Esporta WAV (solo questa)...",
            "sì", "no"],
           ["MIDI", "Progetto → Esporta → MIDI... (o tasto destro sulla traccia → Esporta MIDI (solo questa)...)",
            "solo riverbero e chorus del synth", "no"]], [0.22, 0.48, 0.18, 0.12]),
    warn("Prima di esportare controlla che nessuna traccia sia rimasta in <b>Solo</b> o in <b>Mute</b> per "
         "sbaglio: il WAV le rispetta. Ascoltando, guarda anche la spia <b>CLIP</b>: se si accende, il WAV "
         "sarà distorto in quei punti."),
    tip(["Per pubblicare in MP3 o AAC converti il WAV con un programma apposito (Audacity, ffmpeg...): "
         "partire dal WAV a 24 bit dà la qualità migliore.",
         "Esportare le tracce una per una (WAV «solo questa») è utile per mandarle a qualcuno che mixerà "
         "in un altro programma: senza master, come si usa fare."], "Dopo l'export"),
]

# ------------------------------------------------------------------ 13
story += chapter("13. Suoni da studio con programmi esterni")
story += [
    P("L'amplificatore di SoundText va bene per bozze, basi e demo; per un suono da studio la via più semplice "
      "è il <b>Profilo NAM</b> (capitolo 10), che usa dentro SoundText le catture di amplificatori veri. In "
      "alternativa si può far passare la traccia in un simulatore di amplificatore esterno e poi riportarla "
      "nel brano. Si chiama "
      "<b>re-amping</b>: si registra una volta la chitarra pulita e si può cambiare amplificatore quando si "
      "vuole, senza risuonare la parte."),
    CondPageBreak(5 * cm), P("Il flusso, su qualunque sistema", h2),
    steps([
        "Registra la chitarra <b>pulita</b> in una traccia audio (ingresso <b>INST/Hi-Z</b> della scheda "
        "audio, senza amplificatore) oppure scrivila a note (capitolo 6).",
        "Tasto destro sul nome della traccia → <b>Esporta WAV asciutto (per il re-amping)...</b> Il file esce "
        "senza effetti, senza riverbero e chorus, con il pan al centro e senza master; parte dall'inizio del "
        "brano, così resta a tempo.",
        "Nel programma esterno applica il simulatore al file e salva il risultato come nuovo WAV (vedi sotto).",
        "In SoundText: <b>+ Aggiungi traccia → Traccia audio...</b> (es. «Chitarra ampli»), poi "
        "<b>⋯ → Importa file audio...</b>: su una traccia vuota la clip va all'inizio, a tempo col brano.",
        "Metti in <b>Mute</b> la traccia originale, oppure tienile entrambe e dosa pulito e amplificato con "
        "i volumi.",
    ]),
    tip("Se il suono amplificato risulta un po' in ritardo (succede usando il simulatore in tempo reale, non "
        "nell'elaborazione offline), trascina di poco la clip o accorciane l'inizio trascinandone il bordo."),
    CondPageBreak(6 * cm), P("Linux: Guitarix", h2),
    P("<b>Guitarix</b> è gratuito e simula i circuiti a valvole di molti amplificatori e pedali, con casse e "
      "caricamento di IR. Funziona <b>solo su Linux</b>. Si installa dai repository della distribuzione:"),
    P("sudo apt install guitarix guitarix-lv2     # Debian, Ubuntu, Mint<br/>"
      "sudo dnf install guitarix                  # Fedora<br/>"
      "sudo pacman -S guitarix                    # Arch, Manjaro, CachyOS", code),
    table([["Modo", "Come", "Quando"],
           ["Offline (consigliato)", "Apri il WAV asciutto in <b>Audacity</b> o <b>Ardour</b>, applica i plugin "
            "LV2 di Guitarix come effetto, esporta il risultato.", "Re-amping di tracce già registrate o scritte "
            "a note: nessun collegamento audio da configurare."],
           ["In diretta", "Avvia Guitarix (con PipeWire, se serve: <font name='DVM'>pw-jack guitarix</font>), "
            "collega con <b>qpwgraph</b> o <b>Helvum</b> la chitarra all'ingresso di Guitarix e la sua uscita "
            "al registratore.", "Suonare sentendo già il suono amplificato; per registrare in SoundText scegli "
            "l'ingresso di PipeWire come scheda audio."]], [0.2, 0.5, 0.3]),
    CondPageBreak(6 * cm), P("Windows e macOS", h2),
    table([["Programma", "Cos'è", "Sistemi"],
           ["<b>Neural Amp Modeler (NAM)</b>", "Gratuito. Modelli neurali «catturati» da amplificatori veri: "
            "file <font name='DVM'>.nam</font>, migliaia gratuiti su Tone3000. Carica anche le IR delle casse. "
            "Plugin VST3/AU e programma a sé. I profili (A1, A2 e LSTM) funzionano anche dentro SoundText "
            "(capitolo 10): il plugin serve per suonare in diretta.", "Windows, macOS"],
           ["<b>AIDA-X</b>", "Gratuito, simile a NAM e più leggero. Plugin e programma a sé.",
            "Windows, macOS, Linux"],
           ["<b>GarageBand</b>", "Gratuito, con amplificatori e pedali già inclusi.", "macOS"],
           ["<b>Audacity</b>", "Gratuito: apre il WAV asciutto e gli applica un plugin VST3 (AU su macOS, LV2 su "
            "Linux), poi esporta.", "Windows, macOS, Linux"],
           ["<b>Reaper</b>", "Programma di registrazione completo, economico, prova gratuita.",
            "Windows, macOS, Linux"]], [0.27, 0.53, 0.2]),
    tip(["La strada più semplice su Windows e macOS: <b>Audacity + NAM</b>. Apri il WAV asciutto, "
         "<b>Effetti → NAM</b>, scegli un modello .nam e un'IR di cassa, esporta.",
         "In diretta, NAM e AIDA-X funzionano anche come programmi a sé: la chitarra entra nel simulatore e "
         "registri l'uscita in un altro programma, poi importi il file in SoundText."],
        "Il consiglio"),
    P("Su Linux i plugin LV2 di Guitarix si possono usare anche <b>direttamente in SoundText</b>, come effetti "
      "nella catena della chitarra, senza re-amping: vedi il capitolo 14."),
    P("Nomi dei pacchetti e voci dei menu dei programmi esterni possono cambiare da una versione all'altra: "
      "in caso di dubbio fai riferimento alla loro documentazione.", small),
]

# ------------------------------------------------------------------ 14
story += chapter("14. Plugin VST3 e LV2: strumenti ed effetti in più")
story += [
    P("Oltre agli effetti interni e ai SoundFont, SoundText usa i <b>plugin audio installati sul computer</b>: "
      "strumenti virtuali (synth, pianoforti campionati...) che suonano le note di una traccia al posto del "
      "SoundFont, ed effetti da mettere nella catena di una traccia o del master. Funzionano i plugin "
      "<b>VST3</b> (Linux, Windows, macOS) e, su Linux, <b>LV2</b>. CLAP e VST2 non sono supportati."),
    CondPageBreak(6 * cm), P("Uno strumento virtuale su una traccia", h2),
    steps([
        "Installa il plugin come indicato dal suo autore. SoundText cerca i VST3 nelle cartelle standard "
        "(Linux <font name='DVM'>~/.vst3</font> e <font name='DVM'>/usr/lib/vst3</font>, Windows "
        "<font name='DVM'>C:\\Program Files\\Common Files\\VST3</font>, macOS "
        "<font name='DVM'>/Library/Audio/Plug-Ins/VST3</font>); altre cartelle si aggiungono da "
        "<b>Suoni → Cartelle dei plugin VST3...</b> Alcuni plugin gratuiti li installa per te "
        "<font name='DVM'>scarica_strumenti.py vst3</font> (vedi «Plugin gratuiti utili»).",
        "Seleziona la traccia (per esempio «Accordi») e scegli <b>Traccia → Strumento plugin → Scegli "
        "(VST3/LV2)...</b>, oppure tasto destro sul nome della traccia. Per una traccia nuova c'è "
        "<b>Traccia → Aggiungi → Traccia con strumento virtuale (VST3/LV2)...</b>.",
        "Scegli lo strumento dall'elenco (la casella in alto cerca per nome, produttore o categoria). La "
        "prima volta SoundText deve sapere che cos'è ogni VST3: lo legge dal bundle quando il bundle lo dice, "
        "altrimenti carica il plugin una volta, e può volerci un po'; intanto l'elenco mostra già i plugin "
        "noti. Poi l'elenco si ricorda.",
        "Si apre la finestra dei <b>parametri</b>: regola quello che ti serve (con tanti parametri usa la "
        "casella «Cerca un parametro»), oppure apri <b>Interfaccia del plugin...</b> per usare la sua "
        "finestra e i suoi preset. Premi <b>OK</b>.",
        "Premi <b>Play</b>: la traccia suona con il plugin. Volume, pan ed effetti della traccia valgono come "
        "sempre. Sotto il nome della traccia compare il nome del plugin.",
    ]),
    img("09_plugin_parametri.png", 12.5, "I parametri di Surge XT, filtrati con la parola «volume». "
        "I valori sono quelli scritti dal plugin stesso."),
    tip(["Un plugin grande (Surge XT, per esempio) impiega una decina di secondi a caricarsi la prima volta "
         "che suona: dopo, l'ascolto riparte subito.",
         "Per sicurezza un VST3 si carica solo dalle cartelle dei plugin: se un brano ricevuto da altri indica "
         "un plugin che sta altrove, SoundText lo cerca per nome nelle tue cartelle e, se non lo trova, non lo "
         "carica. Per usare un plugin che sta in un'altra cartella aggiungila da <b>Suoni → Cartelle dei "
         "plugin VST3...</b>",
         "Per tornare al SoundFont: <b>Strumento plugin... → Nessuno: usa il SoundFont</b>.",
         "Per un file <b>.sfz</b> non serve un plugin: vedi più sotto «Strumenti SFZ con il motore interno»."]),
    CondPageBreak(6 * cm), P("Un plugin come effetto", h2),
    P("Nel pannello Effetti della traccia (capitolo 9): <b>+ Effetto → Plugin (VST3/LV2)</b> e scegli "
      "l'effetto. La card ha le manopole <b>Mix</b> (quanto suono elaborato mescolare all'originale) e "
      "<b>Livello</b>, e i pulsanti <b>Parametri...</b> e <b>Cambia...</b>: i ritocchi si sentono subito nel "
      "loop di ascolto, come per gli effetti interni."),
    img("08_plugin_scelta.png", 13, "L'elenco degli effetti installati: VST3 e LV2 insieme, con la ricerca "
        "per nome, produttore o categoria."),
    CondPageBreak(8 * cm), P("Strumenti SFZ con il motore interno (sfizz)", h2),
    P("Un file <b>.sfz</b> è uno strumento campionato: pianoforti, bassi, batterie, archi, sax... Si può suonare "
      "con il plugin sfizz (come sopra), ma c'è una strada più semplice: il <b>motore SFZ interno</b>. È la "
      "libreria di <b>sfizz</b> (nella versione «sfizioso») caricata direttamente dentro SoundText: niente "
      "plugin da installare, niente finestre, niente processi separati."),
    steps([
        "<b>Scarica gli strumenti.</b> Da terminale, nella cartella di SoundText: "
        "<font name='DVM'>python3 scarica_strumenti.py piano basso</font> (su Windows "
        "<font name='DVM'>py</font> al posto di <font name='DVM'>python3</font>). Senza gruppi, lo script "
        "mostra un menu numerato di quelli disponibili: pianoforti, chitarre, bassi, organo, arpa, sax, archi, "
        "batterie, perfino un banco General MIDI completo. Vanno nella cartella <font name='DVM'>~/Strumenti</font>; i download "
        "interrotti si riprendono e i gruppi già presenti si saltano.",
        "<b>Installa la libreria, una volta sola:</b> <font name='DVM'>python3 scarica_strumenti.py "
        "libreria</font>. La compila in circa 5 minuti (su Linux c'è anche <font name='DVM'>./scarica_"
        "strumenti.sh libreria</font>; su Windows servono i Visual Studio Build Tools con il C++).",
        "Seleziona la traccia e scegli <b>Traccia → Strumento plugin → Scegli (VST3/LV2)...</b> (o tasto "
        "destro sul nome della traccia). Nell'elenco c'è la voce <b>Strumento SFZ (interno)...</b>: scegli "
        "questa e poi il file <font name='DVM'>.sfz</font>.",
        "Premi <b>Play</b>. Sotto il nome della traccia compare il nome del file con «(SFZ)».",
    ]),
    table([["", "Strumento SFZ interno", "Plugin sfizz"],
           ["Installazione", "La libreria, una volta, con lo script", "Il plugin VST3/LV2, a mano"],
           ["Parametri", "Nessuno: «Parametri dello strumento plugin...» fa scegliere un altro file",
            "Finestra dei parametri e interfaccia del plugin"],
           ["Se modifichi il file .sfz", "Il brano viene ricalcolato", "—"],
           ["Senza la libreria", "La voce compare in grigio", "—"]], [0.24, 0.46, 0.30]),
    tip("Con una traccia che ha uno strumento SFZ, LV2 o VST3, anche <b>Suona con la tastiera</b> (capitolo 7) "
        "fa sentire i tasti con quello strumento, con il suono che avrà la traccia."),
    CondPageBreak(16 * cm), P("Plugin gratuiti utili", h2),
    P("Qualche punto di partenza, tutti gratuiti (versioni, formati e sistemi possono cambiare: controlla "
      "sul sito di ciascuno):"),
    table([["Plugin", "Che cos'è", "Formati", "Sistemi"],
           ["<b>Surge XT</b>", "Synth completo: bassi, pad, lead, centinaia di preset. Provato con SoundText.",
            "VST3, LV2", "Win, macOS, Linux"],
           ["<b>Dexed</b>", "Synth FM che imita lo Yamaha DX7: piani elettrici, campane, bassi anni '80.",
            "VST3", "Win, macOS, Linux"],
           ["<b>Odin 2</b>", "Synth sottrattivo con un bel suono analogico.", "VST3, LV2", "Win, macOS, Linux"],
           ["<b>OB-Xd</b>", "Ispirato all'Oberheim OB-X: pad e ottoni sintetici.", "VST3", "Win, macOS, Linux"],
           ["<b>sfizz</b>", "Campionatore per le librerie SFZ (pianoforti, archi, batterie campionati). Per i file SFZ c'è anche il motore interno, senza plugin.",
            "VST3, LV2", "Win, macOS, Linux"],
           ["<b>Dragonfly Reverb</b>", "Riverberi di sala, stanza e piastra di ottima qualità.", "VST3, LV2",
            "Win, macOS, Linux"],
           ["<b>Airwindows Consolidated</b>", "Centinaia di effetti in un solo plugin: saturazioni, "
            "compressori, riverberi, nastro.", "VST3, LV2", "Win, macOS, Linux"],
           ["<b>ChowTapeModel</b>", "Simula un registratore a nastro analogico: calore e saturazione.",
            "VST3, LV2", "Win, macOS, Linux"],
           ["<b>LSP Plugins</b>", "Equalizzatori, compressori, limiter e strumenti di analisi professionali.",
            "VST3, LV2", "Linux"],
           ["<b>Guitarix</b>", "Amplificatori e pedali per chitarra (<font name='DVM'>guitarix-lv2</font>).",
            "LV2", "Linux"],
           ["<b>Valhalla Supermassive</b>", "Delay e riverberi enormi, da ambient.", "VST3", "Win, macOS"]],
          [0.24, 0.46, 0.13, 0.17]),
    P("<b>Dexed</b>, <b>Airwindows Consolidated</b>, <b>Dragonfly Reverb</b> e (solo su Linux) <b>LSP "
      "Plugins</b> li scarica dalle pagine ufficiali e li copia nella tua cartella VST3, senza diritti di "
      "amministratore, il comando <font name='DVM'>vst3</font> dello script degli strumenti:"),
    P("python3 scarica_strumenti.py vst3     # Linux e macOS<br/>"
      "scarica_strumenti.bat vst3            # Windows", code),
    P("Su Linux ci sono anche i <b>plugin LV2</b> dei pacchetti della distribuzione: riverberi Dragonfly, "
      "amplificatori e pedali Guitarix, gli effetti Calf (Leslie, riverbero, delay, phaser...), LSP, gli "
      "strumenti x42 (con la batteria AVL Drums) e l'organo Hammond setBfree. Su Debian, Ubuntu e derivate:"),
    P("sudo apt install dragonfly-reverb-lv2 guitarix-lv2 calf-plugins \\<br/>"
      "&nbsp;&nbsp;&nbsp;&nbsp;lsp-plugins-lv2 x42-plugins setbfree", code),
    tip(["Se un plugin si blocca o si chiude, SoundText resta aperto: il plugin viene segnato come «non "
         "risponde» fino al prossimo avvio. Un effetto che non funziona lascia passare il suono com'è; una "
         "traccia il cui strumento plugin non funziona suona con il SoundFont.",
         "Se un brano usa un <b>plugin LV2 che sul tuo computer manca</b> (succede su Windows e macOS con "
         "Guitarix o Calf), al suo posto suona l'effetto interno più vicino (un Tube Screamer diventa la "
         "Distorsione «Overdrive», un riverbero il Riverbero «Sala»...): il pulsante FX dice che cosa suona "
         "al posto del plugin.",
         "Nell'elenco, i plugin che non si possono usare compaiono in grigio, in fondo: passa il mouse sul "
         "nome per leggere il motivo. Un plugin che alla prima ricerca non ha risposto si riprova da solo la "
         "volta dopo; per gli altri errori c'è <b>Aggiorna elenco</b>. Qualche plugin non va d'accordo con il "
         "motore che SoundText usa per i VST3 (per esempio i synth Kars e Nekobi di DISTRHO si bloccano al "
         "caricamento): in quel caso provane un altro."], "Se qualcosa non va"),
    P("Le anteprime veloci (la nota della tastiera, l'ascolto di un pattern) usano ancora il SoundFont; "
      "l'export MIDI e MusicXML contiene le note, non il suono del plugin. Tutti i dettagli nella guida "
      "completa, sezione 8.7.", small),
]

# ------------------------------------------------------------------ 15
# la tabella dei menu sta tutta insieme: meglio iniziare il capitolo su una pagina nuova
story += [CondPageBreak(20 * cm)]
story += chapter("15. Le novità del programma e dei menu")
story += [
    P("Una mappa dei menu com'è oggi, e delle funzioni arrivate dopo le prime edizioni della guida."),
    table([["Menu", "Che cosa ci trovi di nuovo"],
           ["<b>Progetto → Apri esempio...</b>", "I brani d'esempio (blues, hard rock, jazz, sinfonici...), "
            "molti con strumenti SFZ, plugin e profili NAM: si aprono come copia, l'originale resta intatto."],
           ["<b>Progetto → Importa</b>", "MIDI, <b>MusicXML</b> (MuseScore, Finale, Sibelius), <b>ABC</b> e "
            "<b>MTXT</b>: ognuno crea un nuovo progetto."],
           ["<b>Progetto → Esporta</b>", "Mix audio (WAV), MIDI, <b>Partitura PDF</b>, <b>Partitura MusicXML</b>, "
            "<b>Partitura ABC</b>, <b>MTXT</b>."],
           ["<b>Vista → Partitura...</b>", "Le tracce su pentagramma (<b>Ctrl+Shift+P</b>), che si aggiorna "
            "mentre scrivi; da lì esporti il PDF o stampi. Senza programmi esterni."],
           ["<b>Vista → zoom</b>", "<b>Ctrl+=</b>, <b>Ctrl+-</b>, <b>Ctrl+0</b> (anche Ctrl+rotella): nella "
            "vista Struttura allargano la linea del tempo, negli editor di testo cambiano la dimensione della "
            "scrittura."],
           ["<b>Traccia → Aggiungi</b>", "Traccia (<b>Ctrl+T</b>), <b>Traccia con strumento virtuale "
            "(VST3/LV2)...</b>, Traccia audio."],
           ["<b>Traccia → Strumento plugin</b>", "Scegli (VST3/LV2) o <b>Strumento SFZ (interno)</b>; "
            "Parametri... per riaprire quelli dello strumento."],
           ["<b>Traccia → Importa / Esporta questa traccia</b>", "MIDI, audio come clip, <b>audio → "
            "notazione</b> (in tre passi, anche per gli accordi); WAV e <b>WAV asciutto per il re-amping</b>."],
           ["<b>Traccia → Suona con la tastiera in questa traccia...</b>", "Suona con la tastiera del computer "
            "o con una tastiera MIDI; i tasti suonano con lo strumento plugin della traccia."],
           ["<b>Componi</b>", "Genera batteria, basso, giro armonico, accompagnamento; stili personali; "
            "libreria pattern e libreria MIDI; <b>Converti le tracce in box</b>; analisi della tonalità."],
           ["<b>Riproduzione</b>", "<b>Analizza livelli...</b>: il picco di ogni traccia e del mix, e dove "
            "clippano; il menu <b>Loop</b> con A, B e Ripeti la sezione A-B."],
           ["<b>Suoni</b>", "Strumenti, <b>SoundFont</b>, volume di sintesi, <b>Cartelle dei plugin VST3</b> e, "
            "in <b>Scarica</b>, profili NAM e casse IR."],
           ["<b>Opzioni</b>", "Metronomo (suono e volume), Umanizza, import MIDI, parametri avanzati "
            "dell'import audio, tema e lingua."],
           ["<b>Aiuto → Cerca un comando</b>", "<b>Ctrl+K</b>: scrivi cosa vuoi fare e premi Invio."]],
          [0.3, 0.7]),
    CondPageBreak(7 * cm), P("Importare partiture e brani", h2),
    P("<b>MusicXML</b> è il formato di scambio di quasi tutti i programmi di notazione. L'import crea una "
      "traccia per parte, con le note all'altezza reale (anche per sax, clarinetto, tromba), tempo, metrica, "
      "tonalità, dinamiche, ritornelli e finali svolti, le sigle degli accordi in una traccia <b>Accordi</b> "
      "e il testo cantato. L'<b>ABC</b>, notazione in solo testo diffusa nella musica tradizionale, si "
      "importa e si esporta allo stesso modo. Si può anche aprire un file direttamente dal terminale: "
      "<font name='DVM'>soundtext brano.musicxml</font>."),
    CondPageBreak(9 * cm), P("La scrittura delle note: le aggiunte più recenti", h2),
    P(f"La notazione di SoundText (<b>ST-language</b>, oggi alla versione {ST_VERSION}, anche come libreria "
      "Python a sé: <font name='DVM'>pip install st-language</font>) si è arricchita di cose utili anche al "
      "nostro brano:"),
    table([["Scrivi", "Significa"],
           ["<font name='DVM'>C7#5 Cm11 C69 Cmaj7#11 C9sus4</font>", "Altri accordi, per il jazz e il pop"],
           ["<font name='DVM'>d'g c</font>, <font name='DVM'>d'G c</font>",
            "Acciaccatura e appoggiatura (note di abbellimento); <font name='DVM'>snare'g snare</font> è un flam"],
           ["<font name='DVM'>C$arp</font>, <font name='DVM'>c$sfz</font>, <font name='DVM'>c$trem</font>",
            "Accordo arpeggiato, sforzando, tremolo (sulla batteria una rullata)"],
           ["<font name='DVM'>$Am7</font>", "Sigla scritta sopra la melodia, senza suonarla"],
           ["<font name='DVM'>$segno $tocoda $ds $coda</font>, <font name='DVM'>$fine $dc</font>",
            "D.S. al Coda, D.C. al Fine: si suonano come li suona un musicista"],
           ["<font name='DVM'>\"2: altre pa- ro- le\"</font>", "Una seconda strofa sotto la stessa melodia"],
           ["<font name='DVM'>tempo=60'4.</font>", "60 semiminime puntate al minuto (comodo in 6/8)"]],
          [0.42, 0.58]),
    P("Nel file del brano si possono scrivere anche <b>Titolo:</b>, <b>Autore:</b> e <b>Parole:</b>, che vanno "
      "nella partitura, e la tonalità che cambia a una certa battuta (<font name='DVM'>Tonalita: 1: C, 17: "
      "G</font>). La prima riga del file dice con quale versione della notazione è scritto "
      f"(<font name='DVM'>ST: {ST_VERSION}</font>). Con la 2.8 lo spazio fra due box della vista Struttura "
      "diventa una pausa esatta: un box che segue un box in terzina o in quintina non slitta più. Tutto il "
      "resto nella guida completa, sezione 2.23."),
    CondPageBreak(5 * cm), P("Se SoundText si chiude male", h2),
    P("Mentre ci sono modifiche non salvate, SoundText scrive una <b>copia di recupero</b> ogni minuto, senza "
      "toccare il tuo file. Se il programma si chiude male (crash, blocco, corrente), al prossimo avvio chiede "
      "se <b>recuperare</b> il progetto: <b>Recupera</b> lo riapre come modificato, <b>Elimina la copia</b> la "
      "cancella, <b>Decidi dopo</b> la lascia per la volta successiva. Anche il salvataggio normale è «tutto o "
      "niente»: un'interruzione a metà non lascia un file troncato."),
    CondPageBreak(6 * cm), P("Registrare meglio", h2),
    P("Nel dialogo di registrazione (capitolo 7) il pulsante <b>▶ Ascolta</b> fa riascoltare la ripresa, "
      "insieme al resto del brano, prima di <b>Tenerla</b>. Con <b>Compensazione latenza</b> e "
      "<b>Calibra...</b> la ripresa risulta a tempo, e togliendo «Ascolta le clip già presenti in questa "
      "traccia» si rifà una parte senza sentire la precedente."),
    tip("Se qualcosa non funziona, <b>Aiuto → Apri il file di log</b> mostra gli errori registrati dal "
        "programma: spesso spiegano subito il motivo."),
]

# ------------------------------------------------------------------ 16
story += chapter("16. Lista di controllo e problemi comuni")
story += [
    CondPageBreak(5 * cm), P("Prima dell'export", h2),
    table([["", "Controllo"],
           ["☐", "Il brano ha inizio e fine puliti (finale della batteria, ultimo accordo lungo)"],
           ["☐", "Nessuna traccia in Solo o Mute per sbaglio"],
           ["☐", "Volumi bilanciati: la voce/melodia si capisce, il basso si sente anche a volume basso"],
           ["☐", "Effetti confrontati con Prima / Dopo: ognuno migliora davvero qualcosa"],
           ["☐", "Master: limiter con tetto −1 dB, senza schiacciare la batteria"],
           ["☐", "Progetto salvato (Ctrl+S)"]], [0.06, 0.94]),
    CondPageBreak(5 * cm), P("Problemi comuni", h2),
    table([["Problema", "Soluzione"],
           ["Non si sente nulla", "Controlla il SoundFont (Suoni → SoundFont → Scegli SoundFont) e che le tracce "
                                  "non siano in Mute."],
           ["Nel pannello non ci sono effetti, solo «Invio rapido»", "Manca il pacchetto pedalboard: "
            "<font name='DVM'>pip install pedalboard</font>."],
           ["«Ascolta il loop» non parte", "Serve lo streaming audio (pacchetto sounddevice)."],
           ["«Basso dagli accordi» è grigio", "Il brano non ha ancora una traccia di accordi: generane una "
                                              "(capitolo 4)."],
           ["La chitarra suona impastata", "Guadagno troppo alto o suono GM già distorto: usa Electric "
                                           "Guitar (clean) e meno guadagno."],
           ["Il WAV esportato è distorto, la spia CLIP si accende", "Troppo volume: <b>Riproduzione → "
            "Analizza livelli...</b> dice dove; abbassa i volumi delle tracce, metti il Volume «Margine per il "
            "master» e il limiter sul master."],
           ["La registrazione è fuori tempo", "Nel dialogo di registrazione usa Calibra... una volta per "
                                              "scheda audio."],
           ["Ho sbagliato qualcosa", "Ctrl+Z annulla qualunque modifica, anche agli effetti."]],
          [0.36, 0.64]),
    CondPageBreak(8 * cm), P("Scorciatoie da ricordare", h2),
    table([["Tasto", "Azione", "Tasto", "Azione"],
           ["Spazio / F5", "Play / Pausa", "Ctrl+N / Ctrl+S", "Nuovo / Salva"],
           ["Shift+Spazio", "Ascolta il box selezionato", "Ctrl+T", "Aggiungi traccia"],
           ["F6", "Stop", "Ctrl+R / R", "Registra"],
           ["Ctrl+[ / Ctrl+]", "Inizio / fine loop", "Ctrl+Z / Ctrl+Y", "Annulla / Ripeti"],
           ["Ctrl+L", "Loop on/off", "Ctrl+K", "Cerca un comando"],
           ["Ctrl+D", "Duplica il box", "Ctrl+Shift+P", "Partitura"],
           ["Canc", "Elimina il box", "F1", "Guida completa"]], [0.2, 0.3, 0.2, 0.3]),
    Spacer(1, 10),
    P("Per tutti i dettagli c'è la guida completa: <b>Aiuto → Guida utente...</b> (F1), o il file "
      "<b>docs/HELP.md</b>. Buona musica!", ParagraphStyle("end", parent=base,
                                                                            textColor=GREY)),
]

doc = Doc(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2.2 * cm,
          title="SoundText — Dal primo accordo al WAV", author="SoundText",
          subject="Guida pratica alla costruzione di un brano")
doc.multiBuild(story, onFirstPage=page_decor, onLaterPages=page_decor)
print(OUT)
