"""
Costruisce il brano d'esempio della guida PDF (Il_mio_primo_brano.st) con i
generatori veri di SoundText e fa gli screenshot usati da make_pdf.py.

Esecuzione (dalla radice del repository, serve il SoundFont di prova):
    python3 docs/guida_brano/shots.py
"""
import os, sys, time
OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(OUT))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import _config_isolation  # noqa
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
app = QApplication([])
from core import settings
settings.set_soundfont_path("/usr/share/sounds/sf2/TimGM6mb.sf2")
from core import rhythm_generate as rg
from core.arrangement import flatten_clips_to_text
from core.model import Clip, Effect
from core.effects import preset_params
from core.project_io import project_to_text
from gui.main_window import MainWindow

w = MainWindow(); w.resize(1500, 950); w._apply_theme("dark")
p = w.project
p.name = "Il mio primo brano"; p.tempo_bpm = 100; p.time_sig = "4/4"; p.key = "Am"
w._sync_tempo_metrica_fields()

def boxes(track, parts):
    track.clips = [Clip(name=n, text=t, start_beat=b) for n, t, b in parts]
    track.text = flatten_clips_to_text(track.clips, p.patterns, track.instrument.default_octave)

strofa = rg.generate_chord_progression("Am", "minor_pop", bars=8, seed=3)
rit = rg.generate_chord_progression("Am", "minor_epic", bars=8, seed=5)
acc = p.add_track("Accordi", "Piano")
boxes(acc, [("Strofa", strofa, 0), ("Ritornello", rit, 32), ("Strofa 2", strofa, 64)])
chords_s = rg.extract_chords_from_track(strofa, p.patterns)
chords_r = rg.extract_chords_from_track(rit, p.patterns)
dr = p.add_track("Batteria", "Drums")
boxes(dr, [("Groove", rg.generate_drum_pattern("rock", 8, 4, 0.35, 1, "light", True), 0),
           ("Groove pieno", rg.generate_drum_pattern("rock", 8, 4, 0.35, 2, "full", True), 32),
           ("Groove", rg.generate_drum_pattern("rock", 8, 4, 0.35, 1, "light", True, True), 64)])
bs = p.add_track("Basso", "Bass")
boxes(bs, [("Basso", rg.generate_bass_from_chords(chords_s, "root_fifth", 2, seed=1), 0),
           ("Basso", rg.generate_bass_from_chords(chords_r, "octaves", 2, seed=2, intensity="full"), 32),
           ("Basso", rg.generate_bass_from_chords(chords_s, "root_fifth", 2, seed=1), 64)])
from core.instruments import InstrumentProfile, add_custom_instrument
add_custom_instrument(InstrumentProfile(name="ChitarraElettrica", gm_program=27, default_octave=3,
                                        range_low=40, range_high=88, voicing_style="spread"))
gt = p.add_track("ChitarraElettrica", "ChitarraElettrica")
gi = gt.instrument
all_chords = rg.extract_chords_from_track(acc.text, p.patterns)
boxes(gt, [("Accompagnamento", rg.generate_melodic_line(all_chords, "block_chords", gi.default_octave, gi.range_low,
                                                        gi.range_high, True, seed=4), 0)])
voce = p.add_audio_track("Voce")
w.refresh_mixer(); w._mark_dirty()
w.select_track("ChitarraElettrica")

# effetti
gt.effects = [Effect("noise_gate", preset_params("noise_gate", "Chitarra"), preset="Chitarra"),
              Effect("amplificatore", preset_params("amplificatore", "Rock classico"), preset="Rock classico"),
              Effect("delay", preset_params("delay", "A tempo 1/8 puntato"), preset="A tempo 1/8 puntato"),
              Effect("riverbero", preset_params("riverbero", "Sala"), preset="Sala")]
bs.effects = [Effect("compressore", preset_params("compressore", "Basso"), preset="Basso")]
acc.reverb = 30; p.reverb_room = "sala"
w.refresh_mixer(); w.refresh_master_fx_button()
w.show(); app.processEvents()

def grab(name, widget=None):
    app.processEvents(); time.sleep(0.2); app.processEvents()
    (widget or w).grab().save(os.path.join(OUT, name))

w.arrangement_view.set_zoom(12.5)
grab("01_struttura.png")

# dialogo del giro armonico
from gui.rhythm_generate_dialog import ChordProgressionDialog, DrumGenerateDialog
dlg = ChordProgressionDialog(w, project=p, instrument_name="Piano", context_label="nuova traccia 'Accordi'",
                             default_bars=8, track_name="Accordi")
dlg.resize(760, 640); dlg.show(); grab("02_giro.png", dlg); dlg.close()
dlg = DrumGenerateDialog(w, project=p, instrument_name="Drums", context_label="nuova traccia 'Batteria'",
                         default_bars=8, track_name="Batteria")
dlg.resize(760, 640); dlg.show(); grab("03_batteria.png", dlg); dlg.close()

# pannello effetti sulla chitarra
w.open_effects_panel("ChitarraElettrica")
w.effects_panel.wait_until_ready(30)
grab("04_effetti_chitarra.png")
w.effects_panel.close_panel()
w.open_effects_panel("Accordi")
w.effects_panel.wait_until_ready(30)
grab("05_invio_rapido.png")
w.effects_panel.close_panel()

# master
w.master_fx_btn.click()
w.effects_panel.mastering_btn.click()
w.effects_panel.wait_until_ready(30)
grab("06_master.png")
w.effects_panel.close_panel()

# ritagli usati nella guida
from PySide6.QtGui import QImage
for name in ("06_master", "05_invio_rapido", "04_effetti_chitarra"):
    QImage(os.path.join(OUT, name + ".png")).copy(0, 655, 1500, 270).save(os.path.join(OUT, name + "_crop.png"))
full = QImage(os.path.join(OUT, "01_struttura.png"))
full.copy(0, 0, 1500, 480).save(os.path.join(OUT, "01_struttura_crop.png"))
full.copy(990, 30, 510, 50).save(os.path.join(OUT, "07_master_btn.png"))
for name in ("01_struttura", "04_effetti_chitarra", "05_invio_rapido", "06_master"):
    os.remove(os.path.join(OUT, name + ".png"))

with open(os.path.join(OUT, "Il_mio_primo_brano.st"), "w") as f:
    f.write(project_to_text(p))
print("ok", [t.name for t in p.tracks])
os._exit(0)
