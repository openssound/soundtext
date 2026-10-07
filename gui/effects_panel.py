"""
Pannello Effetti (fase 2 degli effetti): si apre in fondo alla finestra dal
pulsante FX della testata di una traccia (gui.track_header) o della sua
striscia nel mixer (gui.track_widget), per tracce di testo e audio.

Contiene:
- "Invio rapido" (solo tracce di testo): riverbero e chorus del synth
  (CC91/CC93) e l'ambiente del brano, come nel primo passo degli effetti;
- la catena della traccia (core.effects): una card per effetto, con
  accensione, ordine, preset e manopole;
- il loop di calibrazione: aprendo il pannello si sceglie un tratto di 10
  secondi (modificabile, 2-30) che diventa anche il loop A-B del brano; con
  "Ascolta il loop" lo si risente a ogni ritocco senza rifare il resto
  (core.effect_render.CalibrationSession). Chiudendo il pannello si
  ripristina il loop di prima e si applica la catena a tutta la traccia in
  sottofondo, cosi' il prossimo Play e' gia' pronto.

Ogni modifica passa da host._on_mixer_changed (segna il progetto modificato,
entra in Annulla/Ripeti e riavvia l'ascolto del brano se in corso).
"""

import copy
import os
import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDial, QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QPushButton,
    QScrollArea, QSizePolicy, QSlider, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from core.effects import (
    DEFAULT_REVERB_ROOM, EFFECT_FAMILIES, EFFECT_KINDS, MASTERING_CHAIN, REVERB_ROOMS, active_effects,
    clamp_params, default_params, delay_seconds, effect_params, effects_available, format_value, inactive_params,
    ir_file_problem, matching_preset, preset_params, uses_ir_file,
)
from core.model import Effect

from . import theme
from core.i18n import tr

DEFAULT_LOOP_SECONDS = 10
MIN_LOOP_SECONDS = 2
MAX_LOOP_SECONDS = 30
CUSTOM_PRESET = "Personalizzato"


# ---------------------------------------------------------------- pulsante FX

def has_fx(track) -> bool:
    """Il pulsante FX va acceso: invii al synth o effetti accesi."""
    return bool(track.reverb or track.chorus or active_effects(track.effects))


def fx_button_text(track) -> str:
    count = len(active_effects(track.effects))
    return f"FX {count}" if count else "FX"


def fx_summary(track) -> str:
    """Testo per il tooltip del pulsante FX."""
    parts = []
    effects = active_effects(track.effects)
    if effects:
        parts.append(" → ".join(tr(EFFECT_KINDS[e.kind]["label"]) for e in effects))
    if not track.is_audio and (track.reverb or track.chorus):
        parts.append(tr("Riverbero {reverb}% · Chorus {chorus}%", reverb=track.reverb, chorus=track.chorus))
    if not parts:
        return tr("Effetti della traccia (ora: nessuno): apre il pannello Effetti")
    return tr("Effetti: ") + " · ".join(parts)


# ---------------------------------------------------------------- card

class _Knob(QWidget):
    """Manopola con nome sopra e valore sotto; valueChanged(float)."""
    valueChanged = Signal(float)

    def __init__(self, param, value: float, parent=None):
        super().__init__(parent)
        self.param = param
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        name = QLabel(tr(param.label))
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-size: 11px;")
        self.dial = QDial()
        self.dial.setFixedSize(48, 48)
        self.dial.setNotchesVisible(True)
        self.dial.setRange(0, int(round((param.maximum - param.minimum) / param.step)))
        self.dial.setAccessibleName(tr(param.label))
        self.dial.setToolTip(tr("{label}: da {0} a {1} (predefinito {2}). Doppio click sul valore per tornare al predefinito.", format_value(param, param.minimum), format_value(param, param.maximum), format_value(param, param.default), label=tr(param.label)))
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(name)
        layout.addWidget(self.dial, 0, Qt.AlignHCenter)
        layout.addWidget(self.value_label)
        self.set_value(value)
        self.dial.valueChanged.connect(self._on_dial)
        self.value_label.mouseDoubleClickEvent = lambda _e: self.dial.setValue(self._to_steps(param.default))

    def _to_steps(self, value: float) -> int:
        return int(round((value - self.param.minimum) / self.param.step))

    def value(self) -> float:
        v = self.param.minimum + self.dial.value() * self.param.step
        return float(round(v, 4))

    def set_value(self, value: float):
        self.dial.blockSignals(True)
        self.dial.setValue(self._to_steps(value))
        self.dial.blockSignals(False)
        self.value_label.setText(format_value(self.param, value))

    def _on_dial(self, _steps):
        value = self.value()
        self.value_label.setText(format_value(self.param, value))
        self.valueChanged.emit(value)


class _Choice(QWidget):
    """Parametro a elenco (modello, cassa, suddivisione): nome sopra e menu
    a tendina; stessa interfaccia di _Knob."""
    valueChanged = Signal(float)

    def __init__(self, param, value: float, parent=None):
        super().__init__(parent)
        self.param = param
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        name = QLabel(tr(param.label))
        name.setStyleSheet("font-size: 11px;")
        self.combo = QComboBox()
        self.combo.setAccessibleName(tr(param.label))
        for _key, label in param.choices:
            self.combo.addItem(tr(label))
        layout.addWidget(name)
        layout.addWidget(self.combo)
        self.set_value(value)
        self.combo.currentIndexChanged.connect(lambda i: self.valueChanged.emit(float(i)))

    def value(self) -> float:
        return float(self.combo.currentIndex())

    def set_value(self, value: float):
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(int(round(value)))
        self.combo.blockSignals(False)


class EffectCard(QFrame):
    """Una card della catena. I callback del pannello: changed() dopo ogni
    ritocco, move(card, delta), remove(card)."""

    def __init__(self, effect: Effect, panel, index: int, count: int):
        super().__init__()
        self.effect = effect
        self.panel = panel
        self.setObjectName("fxCard")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(3)
        self.power_btn = QToolButton()
        self.power_btn.setObjectName("fxPower")
        self.power_btn.setText("⏻")
        self.power_btn.setCheckable(True)
        self.power_btn.setChecked(effect.enabled)
        self.power_btn.setToolTip(tr("Accende/spegne questo effetto (resta nella catena con le sue regolazioni)"))
        self.power_btn.setAccessibleName(tr("Accendi effetto"))
        self.power_btn.toggled.connect(self._on_power)
        top.addWidget(self.power_btn)
        title = QLabel(f"<b>{tr(EFFECT_KINDS[effect.kind]['label'])}</b>")
        top.addWidget(title, 1)
        self.left_btn = self._small("◀", tr("Sposta prima nella catena"), lambda: panel.move_effect(self, -1))
        self.right_btn = self._small("▶", tr("Sposta dopo nella catena"), lambda: panel.move_effect(self, 1))
        self.remove_btn = self._small("✕", tr("Toglie l'effetto dalla catena"), lambda: panel.remove_effect(self))
        self.left_btn.setEnabled(index > 0)
        self.right_btn.setEnabled(index < count - 1)
        for b in (self.left_btn, self.right_btn, self.remove_btn):
            top.addWidget(b)
        layout.addLayout(top)

        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip(tr("Regolazioni pronte: poi puoi ritoccarle con le manopole"))
        for name in EFFECT_KINDS[effect.kind]["presets"]:
            self.preset_combo.addItem(tr(name), name)
        self.preset_combo.addItem(tr(CUSTOM_PRESET), CUSTOM_PRESET)
        layout.addWidget(self.preset_combo)

        # Scelte (menu a tendina) in una riga sopra, manopole sotto.
        choices_row = QHBoxLayout()
        choices_row.setSpacing(6)
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(2)
        self.knobs = {}
        params = clamp_params(effect.kind, effect.params)
        column = 0
        for param in effect_params(effect.kind):
            if param.choices:
                widget = _Choice(param, params[param.key])
                choices_row.addWidget(widget, 1)
            else:
                widget = _Knob(param, params[param.key])
                grid.addWidget(widget, 0, column)
                column += 1
            widget.valueChanged.connect(lambda value, key=param.key: self._on_knob(key, value))
            self.knobs[param.key] = widget
        if choices_row.count():
            layout.addLayout(choices_row)
        # Amplificatore con cassa "File IR": il file scelto e il pulsante per cambiarlo.
        # Profilo NAM: il file .nam e il pulsante per cambiarlo.
        self.nam_row = None
        if effect.kind == "nam":
            self.nam_row = QWidget()
            nam_layout = QVBoxLayout(self.nam_row)
            nam_layout.setContentsMargins(0, 0, 0, 0)
            nam_layout.setSpacing(1)
            top_row = QHBoxLayout()
            self.nam_btn = QPushButton(tr("Scegli profilo…"))
            self.nam_btn.setToolTip(tr("File .nam di Neural Amp Modeler (per esempio da Tone3000)"))
            self.nam_btn.clicked.connect(self._choose_nam)
            self.nam_label = QLabel()
            self.nam_label.setStyleSheet("font-size: 11px; font-weight: bold;")
            top_row.addWidget(self.nam_btn)
            top_row.addWidget(self.nam_label, 1)
            nam_layout.addLayout(top_row)
            self.nam_info = QLabel()
            self.nam_info.setStyleSheet(f"color: {theme.track_card_colors()['text_dim']}; font-size: 10px;")
            nam_layout.addWidget(self.nam_info)
            layout.addWidget(self.nam_row)
        self.ir_row = None
        if effect.kind in ("amplificatore", "nam"):
            self.ir_row = QWidget()
            ir_layout = QHBoxLayout(self.ir_row)
            ir_layout.setContentsMargins(0, 0, 0, 0)
            self.ir_btn = QPushButton(tr("Scegli IR…"))
            self.ir_btn.setToolTip(tr("File WAV con la risposta all'impulso (IR) di una cassa vera"))
            self.ir_btn.clicked.connect(self._choose_ir)
            self.ir_label = QLabel()
            self.ir_label.setStyleSheet("font-size: 11px;")
            ir_layout.addWidget(self.ir_btn)
            ir_layout.addWidget(self.ir_label, 1)
            layout.addWidget(self.ir_row)
        # Plugin esterno: il suo nome, i suoi parametri e il pulsante per cambiarlo.
        self.plugin_row = None
        if effect.kind == "plugin":
            self.plugin_row = QWidget()
            plugin_layout = QVBoxLayout(self.plugin_row)
            plugin_layout.setContentsMargins(0, 0, 0, 0)
            plugin_layout.setSpacing(2)
            self.plugin_label = QLabel()
            self.plugin_label.setStyleSheet("font-size: 11px; font-weight: bold;")
            self.plugin_label.setWordWrap(True)
            plugin_layout.addWidget(self.plugin_label)
            buttons_row = QHBoxLayout()
            self.plugin_params_btn = QPushButton(tr("Parametri…"))
            self.plugin_params_btn.setToolTip(tr("Regola i parametri del plugin (si sentono subito)"))
            self.plugin_params_btn.clicked.connect(self._edit_plugin)
            self.plugin_change_btn = QPushButton(tr("Cambia…"))
            self.plugin_change_btn.setToolTip(tr("Sostituisce il plugin con un altro"))
            self.plugin_change_btn.clicked.connect(self._change_plugin)
            buttons_row.addWidget(self.plugin_params_btn)
            buttons_row.addWidget(self.plugin_change_btn)
            plugin_layout.addLayout(buttons_row)
            layout.addWidget(self.plugin_row)
        layout.addLayout(grid)
        layout.addStretch(1)
        self._sync_preset_combo()
        self.preset_combo.currentIndexChanged.connect(lambda _i: self._on_preset(self.preset_combo.currentData()))
        self._refresh_enabled_look()

    def _small(self, text, tooltip, slot) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setToolTip(tooltip)
        b.setAccessibleName(tooltip)
        b.setFixedSize(22, 20)
        b.clicked.connect(slot)
        return b

    def _sync_preset_combo(self):
        name = matching_preset(self.effect.kind, self.effect.params)
        self.effect.preset = name
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(name or CUSTOM_PRESET))
        self.preset_combo.blockSignals(False)

    def _refresh_enabled_look(self):
        inactive = inactive_params(self.effect.kind, self.effect.params)
        for key, knob in self.knobs.items():
            knob.setEnabled(self.effect.enabled and key not in inactive)
            if isinstance(knob, _Knob):
                knob.set_value(clamp_params(self.effect.kind, self.effect.params)[key])
        if "tempo" in inactive:
            # Delay a tempo: la manopola mostra il tempo che ne risulta.
            seconds = delay_seconds(self.effect.params, self.panel.bpm())
            self.knobs["tempo"].value_label.setText(f"{seconds * 1000:.0f} ms")
            self.knobs["tempo"].setToolTip(
                tr("A tempo col brano ({0:g} BPM, tempo iniziale): {1:.0f} ms. Per regolarlo a mano scegli «Libera (ms)».", self.panel.bpm(), seconds * 1000))
        elif "tempo" in self.knobs:
            self.knobs["tempo"].setToolTip("")
        self._refresh_ir_row()
        self._refresh_nam_row()
        self._refresh_plugin_row()
        self.preset_combo.setEnabled(self.effect.enabled)

    def _refresh_ir_row(self):
        if self.ir_row is None:
            return
        self.ir_row.setVisible(uses_ir_file(self.effect))
        self.ir_row.setEnabled(self.effect.enabled)
        problem = ir_file_problem(self.effect.ir)
        if problem:
            fallback = tr("si usa la Combo 1×12") if self.effect.kind == "amplificatore" else tr("nessuna cassa")
            self.ir_label.setText(f"{problem}: {fallback}")
            self.ir_label.setStyleSheet(f"color: {theme.BAD}; font-size: 11px;")
            self.ir_label.setToolTip(self.effect.ir)
        else:
            self.ir_label.setText(os.path.basename(self.effect.ir))
            self.ir_label.setStyleSheet("font-size: 11px;")
            self.ir_label.setToolTip(self.effect.ir)

    def _refresh_nam_row(self):
        if self.nam_row is None:
            return
        from core.nam import NamError, load_nam
        self.nam_row.setEnabled(self.effect.enabled)
        try:
            model = load_nam(self.effect.nam)
        except NamError as e:
            self.nam_label.setText(tr("{e}: il suono passa invariato", e=e) if self.effect.nam else str(e))
            self.nam_label.setStyleSheet(f"color: {theme.BAD}; font-size: 11px; font-weight: bold;")
            self.nam_label.setToolTip(self.effect.nam)
            self.nam_info.setText("")
            return
        self.nam_label.setText(model.name)
        self.nam_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.nam_label.setToolTip(self.effect.nam)
        info = model.description
        if model.generation != "A1":
            info = (info + " · " if info else "") + f"formato {model.generation}"
        if model.sample_rate != 48000:
            info = (info + " · " if info else "") + f"{model.sample_rate / 1000:g} kHz"
        self.nam_info.setText(info)

    def _choose_nam(self) -> bool:
        path = self.panel.choose_nam_file(self.effect.nam)
        if not path:
            return False
        self.effect.nam = path
        self._refresh_nam_row()
        self.panel.effects_changed()
        return True

    def _refresh_plugin_row(self):
        if self.plugin_row is None:
            return
        from core import plugins
        self.plugin_row.setEnabled(self.effect.enabled)
        ref = self.effect.plugin
        fmt = {"vst3": "VST3", "lv2": "LV2"}.get(ref.partition(":")[0], "")
        problem = plugins.broken_reason(ref)
        if problem:
            self.plugin_label.setText(tr("{0}: {problem}, il suono passa invariato", plugins.display_name(ref), problem=problem))
            self.plugin_label.setStyleSheet(f"color: {theme.BAD}; font-size: 11px; font-weight: bold;")
        else:
            self.plugin_label.setText(f"{plugins.display_name(ref)} · {fmt}")
            self.plugin_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.plugin_label.setToolTip(ref)

    def _set_plugin_values(self, params, state):
        self.effect.plugin_params = dict(params)
        self.effect.plugin_state = state
        self.panel.effects_changed()

    def _edit_plugin(self):
        from .plugin_dialogs import PluginParamsDialog
        dialog = PluginParamsDialog(self.panel.host, self.effect.plugin, self.effect.plugin_params,
                                    self.effect.plugin_state, on_change=self._set_plugin_values)
        dialog.exec()
        self._refresh_plugin_row()

    def _change_plugin(self) -> bool:
        ref = self.panel.choose_plugin(self.effect.plugin)
        if not ref or ref == self.effect.plugin:
            return False
        self.effect.plugin = ref
        self.effect.plugin_params = {}
        self.effect.plugin_state = ""
        self._refresh_plugin_row()
        self.panel.effects_changed()
        return True

    def _choose_ir(self) -> bool:
        path = self.panel.choose_ir_file(self.effect.ir)
        if not path:
            return False
        self.effect.ir = path
        self._refresh_ir_row()
        self.panel.effects_changed()
        return True

    def _on_power(self, checked):
        self.effect.enabled = checked
        self._refresh_enabled_look()
        self.panel.effects_changed()

    def _on_preset(self, name):
        if name == CUSTOM_PRESET:
            return
        self.effect.params = preset_params(self.effect.kind, name)
        for key, knob in self.knobs.items():
            knob.set_value(self.effect.params[key])
        self.effect.preset = name
        self._refresh_enabled_look()
        self.panel.effects_changed()

    def _on_knob(self, key, value):
        previous = clamp_params(self.effect.kind, self.effect.params)[key]
        self.effect.params = clamp_params(self.effect.kind, dict(self.effect.params, **{key: value}))
        if key == "cassa" and uses_ir_file(self.effect) and ir_file_problem(self.effect.ir):
            # "File IR…" senza un file valido: lo si chiede subito; annullando
            # si torna alla cassa di prima.
            path = self.panel.choose_ir_file(self.effect.ir)
            if not path:
                self.effect.params = clamp_params(self.effect.kind, dict(self.effect.params, **{key: previous}))
                self.knobs[key].set_value(previous)
                return
            self.effect.ir = path
        self._sync_preset_combo()
        if self.knobs[key].param.choices:
            self._refresh_enabled_look()
        self.panel.effects_changed()


class SendsCard(QFrame):
    """Invio rapido al riverbero e al chorus del synth (tracce di testo),
    con l'ambiente del brano: gli effetti del primo passo."""

    def __init__(self, track, project, panel):
        super().__init__()
        self.track = track
        self.project = project
        self.panel = panel
        self.setObjectName("fxCard")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        layout.addWidget(QLabel(tr("<b>Invio rapido</b>")))
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        self.reverb_slider, self.reverb_label = self._row(
            grid, 0, tr("Riverbero"), track.reverb,
            tr("Quanta parte della traccia va al riverbero del synth: da 0% (asciutta) a 100%."))
        self.chorus_slider, self.chorus_label = self._row(
            grid, 1, tr("Chorus"), track.chorus,
            tr("Quanta parte della traccia va al chorus del synth: allarga e \"raddoppia\" il suono."))
        grid.addWidget(QLabel(tr("Ambiente")), 2, 0)
        self.room_combo = QComboBox()
        for key, (label, *_params) in REVERB_ROOMS.items():
            self.room_combo.addItem(tr(label) + (tr(" (predefinito)") if key == DEFAULT_REVERB_ROOM else ""), key)
        self.room_combo.setCurrentIndex(max(0, self.room_combo.findData(project.reverb_room)))
        self.room_combo.setToolTip(
            tr("Lo spazio del riverbero del synth, uno per tutto il brano: tutte le tracce\n"
            "mandano la loro parte di suono nella stessa stanza o sala."))
        grid.addWidget(self.room_combo, 2, 1, 1, 2)
        layout.addLayout(grid)
        self.room_hint = QLabel(tr("Nella stanza piccola il riverbero\nsi sente appena: prova Sala."))
        self.room_hint.setStyleSheet("color: #e8c96d; font-size: 11px;")
        layout.addWidget(self.room_hint)
        dim = QLabel(tr("Effetti del synth: valgono anche\nnell'export MIDI (l'ambiente no)."))
        dim.setStyleSheet(f"color: {theme.track_card_colors()['text_dim']}; font-size: 11px;")
        layout.addWidget(dim)
        layout.addStretch(1)
        self._update_room_hint()
        self.reverb_slider.valueChanged.connect(self._on_reverb)
        self.chorus_slider.valueChanged.connect(self._on_chorus)
        self.room_combo.currentIndexChanged.connect(self._on_room)

    def _row(self, grid, row, label, value, tooltip):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(value)
        slider.setMinimumWidth(110)
        slider.setToolTip(tooltip)
        slider.setAccessibleName(label)
        value_label = QLabel(f"{value}%")
        value_label.setMinimumWidth(36)
        grid.addWidget(QLabel(label), row, 0)
        grid.addWidget(slider, row, 1)
        grid.addWidget(value_label, row, 2)
        return slider, value_label

    def _update_room_hint(self):
        self.room_hint.setVisible(self.project.reverb_room == DEFAULT_REVERB_ROOM and self.track.reverb > 0)

    def _on_reverb(self, value):
        self.track.reverb = value
        self.reverb_label.setText(f"{value}%")
        self._update_room_hint()
        self.panel.sends_changed()

    def _on_chorus(self, value):
        self.track.chorus = value
        self.chorus_label.setText(f"{value}%")
        self.panel.sends_changed()

    def _on_room(self):
        self.project.reverb_room = self.room_combo.currentData()
        self._update_room_hint()
        self.panel.sends_changed()


class MasterTarget:
    """Il master visto dal pannello come una "traccia": la sua catena e'
    Project.master_effects. Niente invio al synth (come le tracce audio)
    ne' box da cui far partire il loop."""
    name = "Master"
    is_audio = True
    reverb = 0
    chorus = 0

    def __init__(self, project):
        self.project = project
        self.clips = []
        self.audio_clips = []

    @property
    def effects(self):
        return self.project.master_effects

    @effects.setter
    def effects(self, value):
        self.project.master_effects = value


def master_fx_summary(project) -> str:
    effects = active_effects(project.master_effects)
    if not effects:
        return tr("Effetti sul master (ora: nessuno): EQ, compressore, limiter... sul mix finale del brano")
    return "Master: " + " → ".join(tr(EFFECT_KINDS[e.kind]["label"]) for e in effects)


# ---------------------------------------------------------------- pannello

class EffectsPanel(QFrame):
    """Il pannello in fondo alla finestra principale ('host')."""

    # Emessi dai thread di sottofondo, gestiti sul thread principale.
    _prepared = Signal(object, int)          # sessione, generazione
    _prepare_failed = Signal(object, int)
    _warmed = Signal(str, bool)              # traccia, riuscito

    def __init__(self, host):
        super().__init__()
        self.host = host
        self.track = None
        self._snapshot = None
        self._saved_loop = None
        self._region = None                  # (inizio, fine) in secondi
        self._session = None
        self._generation = 0
        self._listen_wanted = False
        self._engine = None
        self._threads = []                   # lavori in sottofondo (vedi _start_thread)
        self._closing = False
        self.cards = []
        self.sends_card = None
        self.add_btn = None
        self.setObjectName("effectsPanel")
        self.setMinimumHeight(315)
        self.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(4)

        # --- testata
        head = QHBoxLayout()
        head.setSpacing(6)
        self.title_label = QLabel(f"<b>{tr('Effetti')}</b>")
        head.addWidget(self.title_label)
        self.track_chip = QLabel("")
        self.track_chip.setObjectName("fxTrackChip")
        head.addWidget(self.track_chip)
        self.bypass_btn = QPushButton(tr("Prima / Dopo"))
        self.bypass_btn.setCheckable(True)
        self.bypass_btn.setToolTip(tr("Premuto: il loop si sente SENZA la catena di effetti, per confrontare.\n"
                                   "Vale solo per l'ascolto del loop, non cambia la traccia."))
        self.bypass_btn.toggled.connect(self._on_bypass)
        head.addWidget(self.bypass_btn)
        self.copy_btn = QPushButton(tr("Copia su…"))
        self.copy_btn.setToolTip(tr("Copia la catena di effetti di questa traccia su un'altra traccia"))
        self.copy_menu = QMenu(self.copy_btn)
        self.copy_menu.aboutToShow.connect(self._populate_copy_menu)
        self.copy_btn.setMenu(self.copy_menu)
        head.addWidget(self.copy_btn)
        head.addStretch(1)

        head.addWidget(QLabel(tr("Loop")))
        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(MIN_LOOP_SECONDS, MAX_LOOP_SECONDS)
        self.loop_spin.setValue(DEFAULT_LOOP_SECONDS)
        self.loop_spin.setSuffix(" s")
        self.loop_spin.setToolTip(tr("Durata del tratto da risentire mentre regoli gli effetti (2-30 secondi).\n"
                                  "Parte dal box selezionato o dalla posizione della testina."))
        self.loop_spin.valueChanged.connect(self._on_loop_length)
        head.addWidget(self.loop_spin)
        self.with_others_check = QCheckBox(tr("Con le altre tracce"))
        self.with_others_check.setChecked(True)
        self.with_others_check.setToolTip(tr("Nel loop suonano anche le altre tracce del brano, come nel mix finale.\n"
                                          "Tolto: si sente solo questa traccia."))
        self.with_others_check.toggled.connect(lambda _c: self._restart_session())
        head.addWidget(self.with_others_check)
        self.listen_btn = QPushButton(tr("▶ Ascolta il loop"))
        self.listen_btn.setCheckable(True)
        self.listen_btn.setToolTip(tr("Ripete il tratto scelto: ogni ritocco si sente dal giro successivo"))
        self.listen_btn.toggled.connect(self._on_listen)
        head.addWidget(self.listen_btn)
        self.undo_btn = QPushButton(tr("Annulla modifiche"))
        self.undo_btn.setToolTip(tr("Riporta gli effetti di questa traccia a com'erano quando hai aperto il pannello"))
        self.undo_btn.clicked.connect(self.revert_changes)
        head.addWidget(self.undo_btn)
        self.close_btn = QToolButton()
        self.close_btn.setText("✕")
        self.close_btn.setToolTip(tr("Chiude il pannello e applica gli effetti a tutta la traccia"))
        self.close_btn.setAccessibleName(tr("Chiudi il pannello Effetti"))
        self.close_btn.clicked.connect(self.close_panel)
        head.addWidget(self.close_btn)
        outer.addLayout(head)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {theme.TEXT_DIM}; font-size: 11px;")
        outer.addWidget(self.status_label)

        # --- corpo: card in fila, con scorrimento orizzontale
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cards_host = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.scroll.setWidget(self.cards_host)
        outer.addWidget(self.scroll, 1)

        # Riverbero/chorus del synth trascinati: il loop si riprepara una
        # volta sola, quando l'utente si ferma.
        self._session_restart_timer = QTimer(self)
        self._session_restart_timer.setSingleShot(True)
        self._session_restart_timer.setInterval(400)
        self._session_restart_timer.timeout.connect(self._restart_session)

        self._loop_update_timer = QTimer(self)
        self._loop_update_timer.setSingleShot(True)
        self._loop_update_timer.setInterval(120)
        self._loop_update_timer.timeout.connect(self._update_loop)

        self._prepared.connect(self._on_prepared)
        self._prepare_failed.connect(self._on_prepare_failed)
        self._warmed.connect(self._on_warmed)
        self._apply_style()

    # ------------------------------------------------------------ aspetto

    def _apply_style(self):
        colors = theme.track_card_colors()
        light = theme.get_active_theme() == "light"
        text = "#333333" if light else "#e0e0e0"
        base = "#f5f5f5" if light else theme.BG_BASE
        self.setStyleSheet(
            f"QFrame#effectsPanel {{ background: {base}; border-top: 2px solid {theme.ACCENT}; }}"
            f"QFrame#effectsPanel QLabel, QFrame#effectsPanel QCheckBox {{ color: {text}; }}"
            f"QFrame#fxCard {{ background: {colors['bg']}; border: 1px solid {colors['border']}; "
            f"border-radius: 6px; }}"
            f"QLabel#fxTrackChip {{ background: {theme.ACCENT_DIM}; color: white; border-radius: 8px; "
            f"padding: 1px 8px; }}"
            "QFrame#fxCard QToolButton { padding: 0px; font-size: 11px; }"
            f"QToolButton#fxPower:checked {{ color: {theme.GOOD}; }}"
            f"QToolButton#fxPower {{ color: {colors['text_dim']}; font-weight: bold; }}")

    # ------------------------------------------------------------ apertura/chiusura

    def bpm(self) -> float:
        return float(getattr(self.host.project, "tempo_bpm", 120) or 120)

    def theme_changed(self):
        self._apply_style()
        if self.track is not None:
            self.rebuild_cards()

    def is_open(self) -> bool:
        return self.track is not None

    @property
    def is_master(self) -> bool:
        return isinstance(self.track, MasterTarget)

    def open_master(self):
        """Apre il pannello sulla catena del master (mix finale)."""
        if self.is_master and self.track.project is self.host.project:
            self.show()
            return
        self._open(MasterTarget(self.host.project))

    def open_for(self, track_name: str):
        track = self.host.project.get_track(track_name)
        if self.track is track:
            self.show()
            return
        self._open(track)

    def _open(self, track):
        project = self.host.project
        if self.track is not None:
            self.close_panel()
        self.track = track
        self._snapshot = (copy.deepcopy(track.effects), track.reverb, track.chorus, project.reverb_room)
        self.bypass_btn.setChecked(False)
        self._apply_style()
        self.rebuild_cards()
        self.show()
        self._ensure_height()
        try:
            self._choose_region()
        except Exception as e:      # es. un errore di sintassi in una traccia
            self._region = None
            self.status_label.setText(tr("Loop di calibrazione non disponibile: {e}", e=e))
            return
        self._restart_session()

    def _ensure_height(self):
        """Nel divisore verticale della finestra il pannello parte con
        l'altezza giusta per le card, senza schiacciare la vista sopra."""
        splitter = getattr(self.host, "central_splitter", None)
        if splitter is None:
            return
        sizes = splitter.sizes()
        total = sum(sizes)
        want = min(345, max(self.minimumHeight(), total // 3))
        if len(sizes) == 2 and sizes[1] < want and total > want:
            splitter.setSizes([total - want, want])

    def close_panel(self):
        """Chiude il pannello: ferma il loop, ripristina il loop A-B di prima
        e applica la catena a tutta la traccia in sottofondo."""
        if self.track is None:
            self.hide()
            return
        track = self.track
        self.stop_loop()
        self._session_restart_timer.stop()
        self._drop_session()
        self._restore_main_loop()
        self.track = None
        self._snapshot = None
        self.hide()
        self._warm_full_track(track)

    def _start_thread(self, work):
        """Thread NON daemon: all'uscita il processo lo aspetta invece di
        ucciderlo a meta' di una chiamata a fluidsynth/pedalboard (che fa
        abortire il processo). shutdown() lo fa finire subito."""
        self._threads = [t for t in self._threads if t.is_alive()]
        thread = threading.Thread(target=work, daemon=False)
        self._threads.append(thread)
        thread.start()

    def shutdown(self, timeout: float = 10.0):
        """Chiusura della finestra: ferma il loop e i lavori in sottofondo."""
        self._closing = True
        self.discard()
        for thread in self._threads:
            thread.join(timeout)
        self._threads = []

    def discard(self):
        """Chiude il pannello senza applicare nulla in sottofondo (la
        traccia non c'e' piu', o si passa a un altro brano)."""
        if self.track is None:
            return
        self.stop_loop()
        self._session_restart_timer.stop()
        self._drop_session()
        self._restore_main_loop()
        self.track = None
        self._snapshot = None
        self.hide()

    def _warm_full_track(self, track):
        # Il master si applica al mix a ogni Play (in pochi decimi di secondo).
        if isinstance(track, MasterTarget) or not effects_available() or not active_effects(track.effects):
            return
        from core.effect_render import prepare_stem, render_stem
        from core.tempo_map import build_tempo_beat_map
        try:
            request = prepare_stem(self.host.project, track, build_tempo_beat_map(self.host.project))
        except Exception:
            return
        name = track.name
        self.host.statusBar().showMessage(tr("Applico gli effetti a tutta la traccia «{name}»…", name=name))

        def work():
            try:
                ok = render_stem(request, lambda: self._closing) is not None
            except Exception:
                ok = False
            finally:
                request.cleanup()
            try:
                self._warmed.emit(name, ok)
            except RuntimeError:     # finestra gia' chiusa
                pass
        self._start_thread(work)

    def _on_warmed(self, name, ok):
        if ok:
            self.host.statusBar().showMessage(tr("Effetti applicati a tutta la traccia «{name}».", name=name), 5000)
        else:
            self.host.statusBar().showMessage(
                tr("Effetti di «{name}»: la traccia verra' elaborata al prossimo Play.", name=name), 5000)

    def project_changed(self):
        """Il progetto e' stato sostituito o ricaricato (Annulla/Ripeti,
        apertura di un file, rinomina...): si riaggancia la traccia per nome,
        o si chiude il pannello se non c'e' piu'."""
        if self.track is None:
            return
        project = self.host.project
        if self.is_master:
            if self.track.project is not project:
                self.track = MasterTarget(project)
                self.rebuild_cards()
                self._restart_session()
            return
        same = next((t for t in project.tracks if t is self.track), None)
        if same is not None:
            return
        by_name = next((t for t in project.tracks if t.name == self.track.name), None)
        if by_name is None:
            self.discard()
            return
        self.track = by_name
        self.rebuild_cards()
        self._restart_session()

    # ------------------------------------------------------------ card

    def rebuild_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        track = self.track
        if track is None:
            return
        self.track_chip.setText(tr("Master · mix finale") if self.is_master else track.name)
        self.title_label.setText(f"<b>{tr('Effetti')}</b>")
        # Il loop del master e' sempre il brano intero.
        self.with_others_check.setVisible(not self.is_master)
        self.cards = []
        if not track.is_audio:
            self.sends_card = SendsCard(track, self.host.project, self)
            self.cards_layout.addWidget(self.sends_card)
        else:
            self.sends_card = None
        if effects_available():
            for i, effect in enumerate(track.effects):
                if effect.kind not in EFFECT_KINDS:
                    continue
                card = EffectCard(effect, self, i, len(track.effects))
                self.cards_layout.addWidget(card)
                self.cards.append(card)
            self.add_btn = QPushButton(tr("+ Effetto"))
            self.add_btn.setToolTip(tr("Aggiunge un effetto in fondo alla catena"))
            menu = QMenu(self.add_btn)
            for family in EFFECT_FAMILIES:
                menu.addSection(tr(family))
                for kind, info in EFFECT_KINDS.items():
                    if info["family"] == family:
                        menu.addAction(tr(info["label"]), lambda k=kind: self.add_effect(k))
            self.add_btn.setMenu(menu)
            column = QVBoxLayout()
            column.setSpacing(6)
            column.addWidget(self.add_btn)
            self.mastering_btn = None
            if self.is_master:
                self.mastering_btn = QPushButton(tr("+ Catena di mastering"))
                self.mastering_btn.setToolTip(
                    tr("Aggiunge EQ, compressore «Colla del mix» e limiter «Più forte»:\n"
                    "un punto di partenza per rendere il brano più compatto e più forte."))
                self.mastering_btn.clicked.connect(self.add_mastering_chain)
                column.addWidget(self.mastering_btn)
            column.addStretch(1)
            holder = QWidget()
            holder.setLayout(column)
            self.cards_layout.addWidget(holder)
        else:
            self.add_btn = None
            missing = QLabel(tr("Per la catena di effetti (EQ, compressore, delay, riverbero, chorus,\n"
                             "phaser) serve il pacchetto Python 'pedalboard':\n"
                             "pip install pedalboard"))
            missing.setStyleSheet("color: #e8c96d;")
            self.cards_layout.addWidget(missing, 0, Qt.AlignTop)
        self.cards_layout.addStretch(1)
        has_chain = effects_available()
        for w in (self.bypass_btn, self.listen_btn, self.loop_spin, self.with_others_check):
            w.setEnabled(has_chain or not track.is_audio)
        self.bypass_btn.setEnabled(has_chain)

    def add_effect(self, kind: str):
        params = default_params(kind)
        effect = Effect(kind, params, True, matching_preset(kind, params))
        if kind == "nam":
            # senza un profilo l'effetto non fa nulla: lo si chiede subito
            effect.nam = self.choose_nam_file()
            if not effect.nam:
                return
        if kind == "plugin":
            effect.plugin = self.choose_plugin()
            if not effect.plugin:
                return
        self.track.effects.append(effect)
        self.rebuild_cards()
        self.effects_changed()
        self.scroll.horizontalScrollBar().setValue(self.scroll.horizontalScrollBar().maximum())

    def add_mastering_chain(self):
        for kind, preset in MASTERING_CHAIN:
            self.track.effects.append(Effect(kind, preset_params(kind, preset), True, preset))
        self.rebuild_cards()
        self.effects_changed()

    def move_effect(self, card, delta: int):
        effects = self.track.effects
        i = next(i for i, e in enumerate(effects) if e is card.effect)
        j = i + delta
        if 0 <= j < len(effects):
            effects[i], effects[j] = effects[j], effects[i]
            self.rebuild_cards()
            self.effects_changed()

    def remove_effect(self, card):
        self.track.effects = [e for e in self.track.effects if e is not card.effect]
        self.rebuild_cards()
        self.effects_changed()

    def revert_changes(self):
        if self.track is None or self._snapshot is None:
            return
        effects, reverb, chorus, room = self._snapshot
        self.track.effects = copy.deepcopy(effects)
        self.track.reverb, self.track.chorus = reverb, chorus
        room_changed = self.host.project.reverb_room != room
        self.host.project.reverb_room = room
        self.rebuild_cards()
        self._notify_host()
        if room_changed:
            self._restart_session()
        else:
            self._schedule_loop_update()
        self.host.statusBar().showMessage(tr("Effetti di «{name}» riportati a prima.", name=self.track.name), 4000)

    def _populate_copy_menu(self):
        self.copy_menu.clear()
        if self.track is None:
            return
        others = [t for t in self.host.project.tracks if t is not self.track]
        if not others and self.is_master:
            self.copy_menu.addAction(tr("(nessuna traccia)")).setEnabled(False)
        for t in others:
            self.copy_menu.addAction(t.name, lambda name=t.name: self.copy_to(name))
        if not self.is_master:
            self.copy_menu.addSeparator()
            self.copy_menu.addAction(tr("Master (mix finale)"), lambda: self.copy_to(None))

    def choose_plugin(self, current: str = "") -> str:
        """Chiede quale plugin di effetti usare: il riferimento, o '' se
        annullato (vedi gui.plugin_dialogs)."""
        from .plugin_dialogs import PluginPickerDialog
        dialog = PluginPickerDialog(self.host, instrument=False, current_ref=current)
        if dialog.exec() != PluginPickerDialog.Accepted:
            return ""
        return dialog.selected_ref() or ""

    def choose_nam_file(self, current: str = "") -> str:
        """Chiede il file .nam di un profilo: il percorso, o '' se annullato
        o non utilizzabile (con il motivo)."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from core.nam import nam_problem
        from core.nam_profiles import existing_nam_dir
        start = os.path.dirname(current) if current else existing_nam_dir() or os.path.dirname(
            getattr(self.host, "current_path", None) or "") or os.path.expanduser("~")
        path, _filter = QFileDialog.getOpenFileName(
            self, tr("Scegli un profilo NAM"), start, tr("Profili NAM (*.nam)"))
        if not path:
            return ""
        problem = nam_problem(path)
        if problem:
            QMessageBox.warning(self, tr("Profilo NAM"), tr("Non posso usare questo profilo: {problem}.", problem=problem))
            return ""
        return path

    def choose_ir_file(self, current: str = "") -> str:
        """Chiede il file WAV della risposta all'impulso di una cassa: il
        percorso, o '' se annullato o non valido."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from core.cab_irs import existing_cab_dir
        start = os.path.dirname(current) if current else existing_cab_dir() or os.path.dirname(
            getattr(self.host, "current_path", None) or "") or os.path.expanduser("~")
        path, _filter = QFileDialog.getOpenFileName(
            self, tr("Scegli la risposta all'impulso (IR) della cassa"), start, tr("File WAV (*.wav *.WAV)"))
        if not path:
            return ""
        problem = ir_file_problem(path)
        if problem:
            QMessageBox.warning(self, tr("File IR"), tr("Non posso usare questo file ({problem}).", problem=problem))
            return ""
        return path

    def copy_to(self, track_name):
        """Copia la catena su una traccia, o sul master con track_name None."""
        if track_name is None:
            target = MasterTarget(self.host.project)
        else:
            target = self.host.project.get_track(track_name)
        target.effects = copy.deepcopy(self.track.effects)
        self._notify_host_for(target)
        self.host.statusBar().showMessage(
            tr("Catena di effetti copiata da «{name}» a «{0}».", target.name, name=self.track.name), 4000)

    # ------------------------------------------------------------ modifiche

    def _sync_track_widgets(self, name):
        if hasattr(self.host, "sync_mixer_widgets"):
            self.host.sync_mixer_widgets(name)

    def _notify_host(self):
        self._notify_host_for(self.track)

    def _notify_host_for(self, target):
        if isinstance(target, MasterTarget):
            # merge_key proprio: non si confonde con una traccia di nome "Master".
            self.host._on_mixer_changed("\x00master")
            if hasattr(self.host, "refresh_master_fx_button"):
                self.host.refresh_master_fx_button()
            return
        self.host._on_mixer_changed(target.name)
        self._sync_track_widgets(target.name)

    def effects_changed(self):
        """Un ritocco della catena (manopola, preset, accensione, ordine)."""
        self._notify_host()
        self._schedule_loop_update()

    def sends_changed(self):
        """Riverbero/chorus del synth o ambiente: cambiano la sintesi, quindi
        il loop va ripreparato."""
        self._notify_host()
        self._session_restart_timer.start()

    # ------------------------------------------------------------ loop di calibrazione

    def _choose_region(self):
        """Il tratto del loop: dal box selezionato di questa traccia, o dalla
        testina; se li' la traccia non ha box, dal suo primo box."""
        from core.midi_export import compute_project_duration_beats
        from core.tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats

        track = self.track
        host = self.host
        view = host.arrangement_view
        start_beat = None
        clip = getattr(view, "selected_clip", None)
        if clip is not None and any(c is clip for c in track.clips + track.audio_clips):
            start_beat = clip.start_beat
        if start_beat is None:
            start_beat = host._position_for_markers()
            boxes = sorted(c.start_beat for c in track.clips + track.audio_clips)
            if boxes and start_beat <= 0:
                start_beat = boxes[0]
        tempo_map = build_tempo_beat_map(host.project)
        length = self.loop_spin.value()
        start = seconds_for_beats(tempo_map, start_beat)
        try:
            song_end = seconds_for_beats(tempo_map, compute_project_duration_beats(host.project))
        except Exception:
            song_end = 0.0
        if song_end > 0 and start + length > song_end:
            start = max(0.0, song_end - length)
        self._region = (start, start + length)
        self._set_main_loop(beat_at_elapsed_seconds(tempo_map, 0.0, start),
                            beat_at_elapsed_seconds(tempo_map, 0.0, start + length))

    def _set_main_loop(self, a_beat, b_beat):
        host = self.host
        if self._saved_loop is None:
            self._saved_loop = (host._loop_a_beat, host._loop_b_beat, host.loop_action.isChecked())
        host._loop_a_beat, host._loop_b_beat = a_beat, b_beat
        host.loop_action.setEnabled(True)
        host.loop_action.setChecked(True)
        host._loop_markers_changed()

    def _restore_main_loop(self):
        if self._saved_loop is None:
            return
        host = self.host
        a, b, checked = self._saved_loop
        self._saved_loop = None
        host._loop_a_beat, host._loop_b_beat = a, b
        host.loop_action.setChecked(bool(checked and a is not None and b is not None))
        host._loop_markers_changed()

    def _on_loop_length(self, _value):
        if self.track is None or self._region is None:
            return
        from core.tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map
        start = self._region[0]
        self._region = (start, start + self.loop_spin.value())
        try:
            tempo_map = build_tempo_beat_map(self.host.project)
        except Exception:
            return
        self._set_main_loop(beat_at_elapsed_seconds(tempo_map, 0.0, start),
                            beat_at_elapsed_seconds(tempo_map, 0.0, self._region[1]))
        self._restart_session()

    def _drop_session(self):
        self._generation += 1          # il prepare in corso, se c'e', si ferma
        session, self._session = self._session, None
        if session is not None and session.ready:
            session.cleanup()
        # (una sessione ancora in preparazione si pulisce da sola, vedi _prepare_in_background)

    def _restart_session(self):
        """Nuova sessione di calibrazione per il tratto e le impostazioni
        correnti; la parte lenta gira in sottofondo."""
        if self.track is None or self._region is None:
            return
        from core.effect_render import CalibrationSession
        self._drop_session()
        generation = self._generation
        try:
            session = CalibrationSession(self.host.project, None if self.is_master else self.track,
                                         *self._region,
                                         with_others=self.with_others_check.isChecked())
        except Exception as e:
            self.status_label.setText(tr("Loop non disponibile: {e}", e=e))
            return
        self._session = session
        self.status_label.setText(tr("Preparo il loop ({0:.0f} s da {1})…", self._region[1] - self._region[0], self._format_time(self._region[0])))
        self._prepare_in_background(session, generation)

    def _prepare_in_background(self, session, generation):
        def stop_check():
            return self._closing or generation != self._generation

        def work():
            try:
                session.prepare(stop_check)
            except Exception:
                session.cleanup()
                try:
                    self._prepare_failed.emit(session, generation)
                except RuntimeError:
                    pass
                return
            if stop_check():
                session.cleanup()
                return
            try:
                self._prepared.emit(session, generation)
            except RuntimeError:
                pass
        self._start_thread(work)

    def wait_until_ready(self, timeout: float = 30.0) -> bool:
        """Per i test: aspetta la preparazione del loop elaborando gli eventi."""
        import time
        from PySide6.QtWidgets import QApplication
        deadline = time.time() + timeout
        while time.time() < deadline:
            QApplication.processEvents()
            if self._session is not None and self._session.ready:
                return True
            time.sleep(0.01)
        return False

    @staticmethod
    def _format_time(seconds: float) -> str:
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"

    def _on_prepared(self, session, generation):
        if generation != self._generation or session is not self._session:
            session.cleanup()
            return
        self.status_label.setText(
            tr("Loop pronto: {0}–{1}", self._format_time(self._region[0]), self._format_time(self._region[1]))
            + (tr(", tutto il brano") if self.is_master else
               tr(" con le altre tracce") if self.with_others_check.isChecked() else tr(", solo questa traccia"))
            + tr(". Premi «Ascolta il loop» e regola: ogni ritocco si sente dal giro successivo."))
        if self._listen_wanted:
            self._start_loop()

    def _on_prepare_failed(self, session, generation):
        if generation != self._generation:
            return
        self.status_label.setText(tr("Non riesco a preparare il loop (SoundFont o synth non disponibili?)."))
        self._listen_wanted = False
        self.listen_btn.blockSignals(True)
        self.listen_btn.setChecked(False)
        self.listen_btn.blockSignals(False)

    def current_loop_samples(self):
        """Il loop con la catena attuale (o senza, con Prima/Dopo premuto)."""
        if self._session is None or not self._session.ready:
            return None
        effects = [] if self.bypass_btn.isChecked() else self.track.effects
        return self._session.mix(effects)

    def _on_listen(self, checked):
        if not checked:
            self.stop_loop()
            return
        self._listen_wanted = True
        self.listen_btn.setText(tr("■ Ferma il loop"))
        if self._session is not None and self._session.ready:
            self._start_loop()
        else:
            self.status_label.setText(tr("Il loop partira' appena pronto…"))

    def _start_loop(self):
        from core.audio_tracks import AUDIO_SAMPLE_RATE
        from core.playback import PlaybackEngine
        samples = self.current_loop_samples()
        if samples is None:
            return
        # Un solo ascolto alla volta: il brano e l'anteprima dei box si fermano.
        if self.host.playback.is_playing():
            self.host.stop()
        self.host.arrangement_view._stop_preview()
        if self._engine is None:
            self._engine = PlaybackEngine()
        if not self._engine.play_loop_buffer(samples, AUDIO_SAMPLE_RATE):
            self.status_label.setText(tr("L'ascolto del loop richiede il pacchetto 'sounddevice' "
                                      "(streaming audio): regola gli effetti e usa Play."))
            self._listen_wanted = False
            self.listen_btn.blockSignals(True)
            self.listen_btn.setChecked(False)
            self.listen_btn.setText(tr("▶ Ascolta il loop"))
            self.listen_btn.blockSignals(False)

    def stop_loop(self):
        self._listen_wanted = False
        self._loop_update_timer.stop()
        if self._engine is not None:
            self._engine.stop()
        self.listen_btn.blockSignals(True)
        self.listen_btn.setChecked(False)
        self.listen_btn.setText(tr("▶ Ascolta il loop"))
        self.listen_btn.blockSignals(False)

    def is_listening(self) -> bool:
        return self._engine is not None and self._engine.is_playing()

    def _on_bypass(self, checked):
        self.bypass_btn.setText(tr("Prima (senza effetti)") if checked else tr("Prima / Dopo"))
        self._schedule_loop_update()

    def _schedule_loop_update(self):
        if self.is_listening():
            self._loop_update_timer.start()

    def _update_loop(self):
        samples = self.current_loop_samples()
        if samples is not None and self._engine is not None:
            self._engine.update_loop_buffer(samples)
