"""
Tastiera MIDI esterna nel dialogo "Suona con la tastiera" (vedi
gui.keyboard_play_dialog e core.midi_input): mixin di KeyboardPlayDialog,
di cui usa lo stato e la stessa pipeline dei tasti del computer
(gui.keyboard_performance): note attive, sustain, arpeggiatore, suono dal
vivo, eventi catturati per la quantizzazione.

Rispetto alla tastiera del computer:
- la velocity e' quella vera del tasto (la dinamica si registra);
- gli accordi si suonano direttamente, un tasto per nota;
- il pedale del sustain (control change 64) tiene le note come il tasto
  del sustain della tastiera del computer: la durata registrata arriva al
  rilascio del pedale;
- la leva del pitch bend si sente dal vivo e, se durante una nota sale o
  scende di almeno un semitono, la nota si registra come slide
  ('c*4>d*4') verso l'altezza raggiunta;
- su una traccia di percussioni le note seguono la mappa General MIDI
  della batteria (36 cassa, 38 rullante, 42 hihat...), come i pad delle
  tastiere e delle batterie elettroniche.

I messaggi arrivano nel thread di rtmidi: _MidiBridge li riporta nel thread
della GUI con un segnale Qt (connessione accodata), conservando l'istante
di arrivo preso nel thread di rtmidi.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from core import settings as app_settings
from core.instruments import DRUM_MIDI_CHANNEL, PERCUSSION_MAP
from core.midi_input import SUSTAIN_CC, list_input_ports, midi_input_problem, open_input, pitchwheel_semitones
from .keyboard_performance import LIVE_MELODIC_CHANNEL
from .theme import BAD, TEXT_DIM
from core.i18n import tr

NO_PORT = ""
MIN_SLIDE_SEMITONES = 1.0     # sotto, la leva e' un'inflessione: la nota resta ferma
_NOTE_TO_PERCUSSION = {}
for _name, _note in PERCUSSION_MAP.items():
    _NOTE_TO_PERCUSSION.setdefault(_note, _name)


class _MidiBridge(QObject):
    message = Signal(float, object)


class MidiKeyboardMixin:
    def _init_midi_keyboard(self):
        self._midi_input = None
        self._midi_bend = 0.0
        self._midi_bridge = _MidiBridge()
        self._midi_bridge.message.connect(self._on_midi_message)

    # ------------------------------------------------------------ UI

    def _build_midi_row(self, layout):
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Tastiera MIDI:")))
        self.midi_combo = QComboBox()
        self.midi_combo.setMinimumWidth(220)
        self.midi_combo.setToolTip(
            tr("Suona con una tastiera MIDI collegata (USB o interfaccia MIDI), insieme o al posto "
            "della tastiera del computer: premi Registra o Suona e suona.\n"
            "La velocity dei tasti diventa la dinamica, gli accordi si suonano direttamente, il "
            "pedale del sustain tiene le note e la leva del pitch bend (almeno un semitono) "
            "diventa uno slide. Sulle percussioni vale la mappa General MIDI della batteria."))
        self.midi_combo.currentIndexChanged.connect(self._on_midi_port_selected)
        row.addWidget(self.midi_combo)
        self.midi_refresh_btn = QPushButton("⟳")
        self.midi_refresh_btn.setFixedWidth(32)
        self.midi_refresh_btn.setToolTip(tr("Aggiorna l'elenco (se hai appena collegato la tastiera)."))
        self.midi_refresh_btn.clicked.connect(self._refresh_midi_ports)
        row.addWidget(self.midi_refresh_btn)
        self.midi_status_label = QLabel("")
        self.midi_status_label.setWordWrap(True)
        row.addWidget(self.midi_status_label, 1)
        layout.addLayout(row)
        self._refresh_midi_ports()

    def _set_midi_status(self, text: str, error: bool = False):
        self.midi_status_label.setText(text)
        self.midi_status_label.setStyleSheet(f"color: {BAD if error else TEXT_DIM};")

    def _refresh_midi_ports(self):
        problem = midi_input_problem()
        ports = [] if problem else list_input_ports()
        current = self._midi_input.port_name if self._midi_input is not None else app_settings.get_midi_input_port()
        self.midi_combo.blockSignals(True)
        self.midi_combo.clear()
        self.midi_combo.addItem(tr("Nessuna"), NO_PORT)
        for name in ports:
            self.midi_combo.addItem(name, name)
        self.midi_combo.blockSignals(False)
        self.midi_combo.setEnabled(bool(ports))
        if problem:
            self._close_midi_input()
            self._set_midi_status(tr("Non disponibile: {problem}.", problem=problem), error=True)
            return
        if not ports:
            self._close_midi_input()
            self._set_midi_status(tr("Nessuna tastiera MIDI collegata."))
            return
        # L'ultima usata se c'e' ancora, altrimenti la prima: con una sola
        # tastiera collegata non c'e' niente da scegliere.
        wanted = current if current in ports else ports[0]
        index = self.midi_combo.findData(wanted)
        if index == self.midi_combo.currentIndex():
            self._on_midi_port_selected(index)
        else:
            self.midi_combo.setCurrentIndex(index)

    def _on_midi_port_selected(self, index):
        name = self.midi_combo.itemData(index) if index >= 0 else NO_PORT
        if self._midi_input is not None and self._midi_input.port_name == name:
            self._set_midi_status(tr("Collegata: premi Registra o Suona e suona."))
            return
        self._close_midi_input()
        if not name:
            app_settings.set_midi_input_port(NO_PORT)
            self._set_midi_status("")
            return
        port, problem = open_input(name, self._midi_bridge.message.emit)
        if port is None:
            self._set_midi_status(tr("Non riesco ad aprirla ({problem}).", problem=problem), error=True)
            return
        self._midi_input = port
        app_settings.set_midi_input_port(name)
        self._set_midi_status(tr("Collegata: premi Registra o Suona e suona."))

    def _close_midi_input(self):
        if self._midi_input is not None:
            self._midi_input.close()
            self._midi_input = None

    # ------------------------------------------------------------ messaggi

    def _on_midi_message(self, when: float, message):
        """Un messaggio dalla tastiera MIDI, nel thread della GUI; when e'
        l'istante di arrivo (time.time())."""
        if not self._instrument_active():
            if message.type == "note_on" and message.velocity > 0:
                self._set_midi_status(tr("Premi Registra (o Suona, per provare) e poi suona."))
            return
        if message.type == "control_change":
            if message.control == SUSTAIN_CC:
                if message.value >= 64:
                    self._sustain_active = True
                elif self._sustain_active:
                    self._sustain_active = False
                    self._flush_sustained_notes(when)
            return
        if message.type == "pitchwheel":
            self._on_midi_pitchwheel(message.pitch)
            return
        key = ("midi", message.note)
        if message.type == "note_on" and message.velocity > 0:
            if key in self._active_notes:                      # ribattuta senza note_off
                self._release_note(key, when)
            self._midi_note_on(key, message.note, message.velocity, when)
        else:
            self._midi_note_off(key, message.note, when)

    def _midi_note_on(self, key, note: int, velocity: int, when: float):
        if self.instr.is_percussion:
            perc_name = _NOTE_TO_PERCUSSION.get(note)
            if perc_name is None:
                return
            self._active_notes[key] = {"start": when, "perc_name": perc_name, "velocity": velocity}
            if self._live_synth:
                self._live_synth.note_on(DRUM_MIDI_CHANNEL, note, velocity=velocity)
            self._update_piano_display()
            return
        if self._arpeggiator_active:
            # Come i tasti del computer: entra nel giro dell'arpeggiatore.
            self._active_notes[key] = {"start": when, "midi_notes": [note], "velocity": velocity,
                                       "via_arpeggiator": True}
            return
        self._active_notes[key] = {"start": when, "midi_notes": [note], "velocity": velocity,
                                   "note_offsets": {note: 0.0}, "key": key, "max_bend": 0.0}
        if self._live_synth:
            self._live_synth.note_on(LIVE_MELODIC_CHANNEL, note, velocity=velocity)
        self._update_piano_display()

    def _midi_note_off(self, key, note: int, when: float):
        info = self._active_notes.get(key)
        if info is None:
            return
        bend = info.get("max_bend", 0.0)
        if abs(bend) >= MIN_SLIDE_SEMITONES:
            info["slide_to_pitch"] = max(0, min(127, note + int(round(bend))))
        self._release_note(key, when)

    def _on_midi_pitchwheel(self, pitch: int):
        if self.instr.is_percussion:
            return
        self._midi_bend = pitchwheel_semitones(pitch)
        if self._live_synth:
            self._live_synth.pitch_bend(LIVE_MELODIC_CHANNEL, self._midi_bend)
        for held_key, info in self._active_notes.items():
            if isinstance(held_key, tuple) and "max_bend" in info and abs(self._midi_bend) > abs(info["max_bend"]):
                info["max_bend"] = self._midi_bend
