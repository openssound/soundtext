"""
Costruisce il brano d'esempio della guida PDF «Dal primo accordo al WAV» con i
generatori veri di SoundText e fa gli screenshot usati da make_pdf.py, nella
lingua indicata (it o en): docs/guida_brano/<lingua>/*.png e il brano .st.

Esecuzione (dalla radice del repository, serve un SoundFont General MIDI):
    venv/bin/python docs/guida_brano/shots.py it
    venv/bin/python docs/guida_brano/shots.py en
"""
import os
import sys
import time

LANG = sys.argv[1] if len(sys.argv) > 1 else "it"
os.environ["SOUNDTEXT_LANGUAGE"] = LANG
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, LANG)
ROOT = os.path.dirname(os.path.dirname(HERE))
os.makedirs(OUT, exist_ok=True)
# Scarica e installa guarda una cartella vuota: nessuno strumento risulta gia' installato
import tempfile  # noqa: E402
os.environ["STRUMENTI_DIR"] = tempfile.mkdtemp(prefix="guida-strumenti-")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import _config_isolation  # noqa: E402,F401  (configurazione pulita, non quella dell'utente)

from PySide6.QtCore import QPoint, QRect  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from PySide6.QtCore import QLibraryInfo, QTranslator  # noqa: E402

_qt = QTranslator(app)                    # i pulsanti standard di Qt (Annulla, Chiudi) nella lingua della guida
if _qt.load(f"qtbase_{LANG}", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
    app.installTranslator(_qt)
from core import settings  # noqa: E402

SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
if os.path.exists(SOUNDFONT):
    settings.set_soundfont_path(SOUNDFONT)

from core import rhythm_generate as rg  # noqa: E402
from core.arrangement import flatten_clips_to_text  # noqa: E402
from core.effects import preset_params  # noqa: E402
from core.instruments import InstrumentProfile, add_custom_instrument  # noqa: E402
from core.model import Clip, Effect  # noqa: E402
from core.project_io import project_to_text  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402

# I nomi del brano nelle due lingue della guida
NAMES = {
    "it": dict(song="Il mio primo brano", file="Il_mio_primo_brano.st", chords="Accordi", drums="Batteria",
               bass="Basso", guitar="ChitarraElettrica", voice="Voce", verse="Strofa", chorus="Ritornello",
               verse2="Strofa 2", groove="Groove", groove_full="Groove pieno", comping="Accompagnamento"),
    "en": dict(song="My first song", file="My_first_song.st", chords="Chords", drums="Drums",
               bass="Bass", guitar="ElectricGuitar", voice="Vocals", verse="Verse", chorus="Chorus",
               verse2="Verse 2", groove="Groove", groove_full="Full groove", comping="Comping"),
}[LANG]

W, H = 1600, 900
w = MainWindow()
w.resize(W, H)
w._apply_theme("dark")
p = w.project
p.name = NAMES["song"]
p.tempo_bpm = 100
p.time_sig = "4/4"
p.key = "Am"
w._sync_tempo_metrica_fields()


def boxes(track, parts):
    track.clips = [Clip(name=n, text=t, start_beat=b) for n, t, b in parts]
    track.text = flatten_clips_to_text(track.clips, p.patterns, track.instrument.default_octave)


verse = rg.generate_chord_progression("Am", "minor_pop", bars=8, seed=3)
chorus = rg.generate_chord_progression("Am", "minor_epic", bars=8, seed=5)
acc = p.add_track(NAMES["chords"], "Piano")
boxes(acc, [(NAMES["verse"], verse, 0), (NAMES["chorus"], chorus, 32), (NAMES["verse2"], verse, 64)])
chords_v = rg.extract_chords_from_track(verse, p.patterns)
chords_c = rg.extract_chords_from_track(chorus, p.patterns)
dr = p.add_track(NAMES["drums"], "Drums")
boxes(dr, [(NAMES["groove"], rg.generate_drum_pattern("rock", 8, 4, 0.35, 1, "light", True), 0),
           (NAMES["groove_full"], rg.generate_drum_pattern("rock", 8, 4, 0.35, 2, "full", True), 32),
           (NAMES["groove"], rg.generate_drum_pattern("rock", 8, 4, 0.35, 1, "light", True, True), 64)])
bs = p.add_track(NAMES["bass"], "Bass")
boxes(bs, [(NAMES["bass"], rg.generate_bass_from_chords(chords_v, "root_fifth", 2, seed=1), 0),
           (NAMES["bass"], rg.generate_bass_from_chords(chords_c, "octaves", 2, seed=2, intensity="full"), 32),
           (NAMES["bass"], rg.generate_bass_from_chords(chords_v, "root_fifth", 2, seed=1), 64)])
add_custom_instrument(InstrumentProfile(name=NAMES["guitar"], gm_program=27, default_octave=3,
                                        range_low=40, range_high=88, voicing_style="spread"))
gt = p.add_track(NAMES["guitar"], NAMES["guitar"])
gi = gt.instrument
all_chords = rg.extract_chords_from_track(acc.text, p.patterns)
boxes(gt, [(NAMES["comping"], rg.generate_melodic_line(all_chords, "block_chords", gi.default_octave, gi.range_low,
                                                       gi.range_high, True, seed=4), 0)])
p.add_audio_track(NAMES["voice"])

gt.effects = [Effect("noise_gate", preset_params("noise_gate", "Chitarra"), preset="Chitarra"),
              Effect("amplificatore", preset_params("amplificatore", "Rock classico"), preset="Rock classico"),
              Effect("delay", preset_params("delay", "A tempo 1/8 puntato"), preset="A tempo 1/8 puntato"),
              Effect("riverbero", preset_params("riverbero", "Sala"), preset="Sala")]
bs.effects = [Effect("compressore", preset_params("compressore", "Basso"), preset="Basso")]
acc.reverb = 30
p.reverb_room = "sala"
w.history.reset(p)
w.refresh_mixer()
w.refresh_master_fx_button()
w.select_track(NAMES["guitar"])
w.show()
app.processEvents()


def settle():
    for _ in range(4):
        app.processEvents()
        time.sleep(0.1)


def grab(name, widget=None, rect=None):
    settle()
    image = (widget or w).grab().toImage()
    if rect is not None:
        image = image.copy(rect)
    image.save(os.path.join(OUT, name))
    return image


def window_rect(widget, margin=0):
    """Il rettangolo di 'widget' nelle coordinate della finestra."""
    top_left = widget.mapTo(w, QPoint(0, 0))
    return QRect(top_left.x() - margin, top_left.y() - margin, widget.width() + 2 * margin,
                 widget.height() + 2 * margin)


# 01: la vista Struttura del brano finito
w.resize(W, 600)
w.arrangement_view.set_zoom(14)
grab("01_struttura.png")
w.resize(W, H)

# 02-03: i dialoghi del giro armonico e della batteria
from gui.rhythm_generate_dialog import ChordProgressionDialog, DrumGenerateDialog  # noqa: E402

dlg = ChordProgressionDialog(w, project=p, instrument_name="Piano", context_label=NAMES["chords"],
                             default_bars=8, track_name=NAMES["chords"])
dlg.resize(780, 520)
dlg.show()
grab("02_giro.png", dlg)
dlg.close()
dlg = DrumGenerateDialog(w, project=p, instrument_name="Drums", context_label=NAMES["drums"],
                         default_bars=8, track_name=NAMES["drums"])
dlg.resize(780, 520)
dlg.show()
grab("03_batteria.png", dlg)
dlg.close()

# 04-05: il pannello Effetti (chitarra e accordi), ritagliato sul pannello
for name, track in (("04_effetti_chitarra.png", NAMES["guitar"]), ("05_invio_rapido.png", NAMES["chords"])):
    w.open_effects_panel(track)
    w.effects_panel.wait_until_ready(30)
    grab(name, rect=window_rect(w.effects_panel))
    w.effects_panel.close_panel()

# 06: la catena di mastering
w.effects_panel.open_master()
w.effects_panel.wait_until_ready(30)
if w.effects_panel.mastering_btn is not None:
    w.effects_panel.mastering_btn.click()
    w.effects_panel.wait_until_ready(30)
grab("06_master.png", rect=window_rect(w.effects_panel))
w.effects_panel.close_panel()

# 07: la riga del Master in fondo alla colonna delle tracce
grab("07_master_riga.png", w.master_strip)

# 10: Arrangia il brano
from gui.arrange_dialog import ArrangeDialog  # noqa: E402

try:
    dlg = ArrangeDialog(w, p)
    dlg.resize(820, 640)
    dlg.show()
    grab("10_arrangia.png", dlg)
    dlg.close()
except TypeError as e:
    print("ArrangeDialog:", e)

# 11: Scarica e installa
from gui.download_dialog import DownloadDialog  # noqa: E402

try:
    dlg = DownloadDialog(w)
    dlg.resize(900, 560)
    dlg.show()
    from PySide6.QtWidgets import QTreeWidget  # noqa: E402
    for tree in dlg.findChildren(QTreeWidget):     # le categorie chiuse: si vede tutto quello che offre
        tree.collapseAll()
        for i in range(tree.topLevelItemCount()):  # aperte quelle che usa la guida: SoundFont e NAM
            item = tree.topLevelItem(i)
            item.setExpanded("SoundFont" in item.text(0) or "NAM" in item.text(0))
    grab("11_scarica.png", dlg)
    dlg.close()
except TypeError as e:
    print("DownloadDialog:", e)

with open(os.path.join(OUT, NAMES["file"]), "w", encoding="utf-8") as f:
    f.write(project_to_text(p))
print("ok", LANG, [t.name for t in p.tracks])
sys.stdout.flush()
os._exit(0)
