"""
Dialogo "Registra nella traccia audio" (fase 2 delle tracce audio, vedi
core.audio_recording): scelta di scheda audio, tipo di sorgente e ingresso,
misuratore di livello, conteggio/metronomo e compensazione della latenza;
poi Registra/Stop mentre suona il resto del brano, e "Tieni la ripresa" per
aggiungerla alla traccia come clip.
"""

import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from core import audio_recording, settings
from core.audio_recording import (
    build_calibration_backing, measure_latency_ms,
    DEFAULT_PROFILE, INPUT_PROFILES, DuplexRecorder, InputMonitor, build_backing, channel_choices,
    TakePlayer, level_to_db, list_input_devices, output_device_for, parse_channel_spec, pick_input_device,
    loop_clip, loop_pass_count, punch_clip, recorded_clip, save_take, take_preview,
)

from .theme import GOOD, WARN, dim
from .worker import Worker
from core.i18n import tr

METER_FLOOR_DB = -60.0
PUNCH_STOP_AFTER_B = 1.0      # secondi di ripresa dopo il punto B, poi il punch-in si ferma
TICK_MS = 50


class LevelMeter(QWidget):
    """Barra orizzontale del livello d'ingresso (dBFS), con picco trattenuto
    e spia rossa quando il segnale arriva a fondo scala."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 18)
        self._level_db = METER_FLOOR_DB
        self._hold_db = METER_FLOOR_DB
        self._hold_until = 0.0
        self._clip_until = 0.0

    def push_peak(self, peak: float):
        db = max(METER_FLOOR_DB, level_to_db(peak))
        now = time.monotonic()
        # discesa graduale (circa 20 dB al secondo), salita immediata
        self._level_db = max(db, self._level_db - 20.0 * TICK_MS / 1000.0)
        if db >= self._hold_db or now > self._hold_until:
            self._hold_db, self._hold_until = db, now + 1.5
        if peak >= audio_recording.CLIP_THRESHOLD:
            self._clip_until = now + 2.0
        self.update()

    @property
    def clipping(self) -> bool:
        return time.monotonic() < self._clip_until

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        clip_w = 14
        bar_w = w - clip_w - 4
        p.fillRect(0, 0, bar_w, h, QColor("#2a2a2a"))

        def x_for(db):
            return bar_w * (db - METER_FLOOR_DB) / -METER_FLOOR_DB

        level_x = x_for(self._level_db)
        for lo, hi, color in ((METER_FLOOR_DB, -12.0, "#4caf50"), (-12.0, -3.0, "#e8c96d"), (-3.0, 0.0, "#e05555")):
            a, b = x_for(lo), min(x_for(hi), level_x)
            if b > a:
                p.fillRect(QRectF(a, 2, b - a, h - 4), QColor(color))
        hx = x_for(self._hold_db)
        p.fillRect(QRectF(max(0.0, hx - 2), 1, 2, h - 2), QColor("#ffffff"))
        p.fillRect(bar_w + 4, 0, clip_w, h, QColor("#e05555" if self.clipping else "#3a3a3a"))
        p.end()


class AudioRecordDialog(QDialog):
    """start_options: [(etichetta, beat)] fra cui scegliere da dove partire
    (il primo e' quello proposto). stream_factory/monitor_factory e
    backing_builder sostituiscono sounddevice e il rendering (test senza
    scheda audio); run_in_thread=False prepara la base nel thread della GUI."""

    def __init__(self, parent, project, track, start_options, target_dir, stream_factory=None,
                 monitor_factory=None, backing_builder=None, run_in_thread=True, devices=None,
                 player_factory=None, loop_region=None):
        super().__init__(parent)
        self.project = project
        self.track = track
        self.target_dir = target_dir
        # (A, B) in beat: abilita la registrazione in loop e il punch-in
        self.loop_region = loop_region if loop_region and loop_region[1] > loop_region[0] else None
        self._mode_used = "normal"
        self._stream_factory = stream_factory
        self._monitor_factory = monitor_factory
        self._backing_builder = backing_builder or build_backing
        self._run_in_thread = run_in_thread
        self._devices = list_input_devices() if devices is None else devices
        self._monitor = None
        self._recorder = None
        self._player = None
        self._player_factory = player_factory
        self._backing = None
        self._take = None
        self._start_beat = None
        self._worker = None
        self._result_clip = None
        self._calibration = None   # (recorder, istanti dei click, durata) durante la calibrazione

        self.setWindowTitle(tr("Registra — traccia audio '{name}'", name=track.name))
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        form = self._form = QFormLayout()

        self.device_combo = QComboBox()
        for dev in self._devices:
            self.device_combo.addItem(dev.label)
        chosen = pick_input_device(self._devices, settings.get_audio_input_device())
        if chosen is not None:
            self.device_combo.setCurrentIndex(self._devices.index(chosen))
        self.device_combo.setToolTip(tr("Scheda audio (o microfono) da cui registrare."))
        form.addRow(tr("Scheda audio:"), self.device_combo)

        self.profile_combo = QComboBox()
        for key, (label, _chans, _hint) in INPUT_PROFILES.items():
            self.profile_combo.addItem(label, key)
        profile = track.input_profile if track.input_profile in INPUT_PROFILES else DEFAULT_PROFILE
        self.profile_combo.setCurrentIndex(list(INPUT_PROFILES).index(profile))
        form.addRow(tr("Cosa registri:"), self.profile_combo)

        self.channel_combo = QComboBox()
        form.addRow(tr("Ingresso:"), self.channel_combo)

        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        dim(self.hint_label)
        form.addRow("", self.hint_label)
        self.mic_warning = QLabel(tr(
            "Attenzione: questo ingresso e' probabilmente il microfono del computer, che registra anche il "
            "click e la base se escono dalle casse. Ascolta in cuffia, oppure scegli la scheda audio a cui e' "
            "collegato lo strumento."))
        self.mic_warning.setWordWrap(True)
        self.mic_warning.setStyleSheet(f"color: {WARN};")
        self.mic_warning.setVisible(False)
        form.addRow("", self.mic_warning)

        meter_row = QHBoxLayout()
        self.meter = LevelMeter()
        self.meter_db_label = QLabel("—")
        self.meter_db_label.setMinimumWidth(70)
        meter_row.addWidget(self.meter, 1)
        meter_row.addWidget(self.meter_db_label)
        form.addRow(tr("Livello:"), meter_row)

        # Accordatore (core.tuning): nota e scarto in cent dall'ingresso,
        # finche' non si registra
        self.tuner_label = QLabel("—")
        self.tuner_label.setToolTip(tr("La nota che arriva dall'ingresso e di quanti cent e' sopra (+) o "
                                       "sotto (−) quella giusta, con il La a 440 Hz. Suona una nota sola."))
        form.addRow(tr("Accordatore:"), self.tuner_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(tr("Normale"), "normal")
        self.mode_combo.addItem(tr("In loop fra A e B (ogni giro e' una ripresa)"), "loop")
        self.mode_combo.addItem(tr("Punch-in fra A e B"), "punch")
        if self.loop_region is None:
            self.mode_combo.setEnabled(False)
            self.mode_combo.setToolTip(tr("Imposta prima i punti A e B del loop (Riproduzione → Loop)."))
        else:
            self.mode_combo.setToolTip(tr(
                "In loop: il tratto A-B si ripete finche' non premi Stop, e ogni giro diventa una ripresa "
                "della stessa clip.\nPunch-in: il brano suona dal pre-roll, ma della ripresa si tiene "
                "solo il tratto A-B, come nuova ripresa della clip che c'e' li'."))
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow(tr("Modalita':"), self.mode_combo)

        self.start_combo = QComboBox()
        for label, beat in start_options:
            self.start_combo.addItem(label, beat)
        form.addRow(tr("Parti da:"), self.start_combo)

        self.preroll_spin = QSpinBox()
        self.preroll_spin.setRange(0, 8)
        self.preroll_spin.setValue(2)
        self.preroll_spin.setToolTip(tr("Battute che suonano prima del punto A, per entrare a tempo."))
        form.addRow(tr("Pre-roll (battute):"), self.preroll_spin)

        self.count_in_spin = QSpinBox()
        self.count_in_spin.setRange(0, 4)
        self.count_in_spin.setValue(settings.get_record_count_in_bars())
        self.count_in_spin.setToolTip(tr("Battute di click prima che parta il brano (0 = nessun conteggio)."))
        form.addRow(tr("Conteggio (battute):"), self.count_in_spin)

        self.metronome_check = QCheckBox(tr("Metronomo durante la ripresa"))
        self.metronome_check.setChecked(settings.get_record_metronome())
        form.addRow("", self.metronome_check)

        self.hear_track_check = QCheckBox(tr("Ascolta le clip gia' presenti in questa traccia"))
        self.hear_track_check.setChecked(True)
        self.hear_track_check.setToolTip(
            tr("Toglilo per rifare una parte senza sentire la ripresa precedente."))
        form.addRow("", self.hear_track_check)

        self.latency_spin = QDoubleSpinBox()
        self.latency_spin.setRange(-200.0, 500.0)
        self.latency_spin.setDecimals(1)
        self.latency_spin.setSuffix(" ms")
        self.latency_spin.setToolTip(
            tr("La latenza dichiarata dalla scheda audio viene gia' compensata. Se la ripresa risulta "
            "comunque in ritardo rispetto al brano aumenta questo valore (in anticipo: diminuiscilo). "
            "Viene ricordato per ogni scheda audio."))
        latency_row = QHBoxLayout()
        latency_row.addWidget(self.latency_spin, 1)
        self.calibrate_btn = QPushButton(tr("Calibra..."))
        self.calibrate_btn.setToolTip(
            tr("Misura da solo il valore giusto: fa suonare dei click e li registra da un cavo che "
            "collega un'uscita della scheda a un ingresso (o dal microfono vicino alle casse)."))
        self.calibrate_btn.clicked.connect(self.calibrate_latency)
        latency_row.addWidget(self.calibrate_btn)
        form.addRow(tr("Compensazione latenza:"), latency_row)
        layout.addLayout(form)

        monitor_note = QLabel(
            tr("Per sentirti mentre suoni usa il monitoraggio diretto della scheda audio (manopola o "
            "tasto \"direct monitor\"): e' senza ritardo. SoundText manda in cuffia solo il brano."))
        monitor_note.setWordWrap(True)
        dim(monitor_note, "padding-top: 6px;")
        layout.addWidget(monitor_note)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.record_btn = QPushButton(tr("● Registra"))
        self.record_btn.setStyleSheet("QPushButton { color: #e05555; font-weight: bold; }")
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn = QPushButton(tr("■ Stop"))
        self.stop_btn.clicked.connect(self.stop_recording)
        self.play_btn = QPushButton(tr("▶ Ascolta"))
        self.play_btn.setToolTip(tr("Riascolta la ripresa prima di tenerla"))
        self.play_btn.clicked.connect(self.toggle_listen)
        self.with_backing_check = QCheckBox(tr("con la base"))
        self.with_backing_check.setChecked(True)
        self.with_backing_check.setToolTip(tr("Ascolta la ripresa insieme al resto del brano, allineata "
                                              "come sara' nella traccia (senza metronomo)"))
        self.keep_btn = QPushButton(tr("Tieni la ripresa"))
        self.keep_btn.clicked.connect(self.keep_take)
        close_btn = QPushButton(tr("Annulla"))
        close_btn.clicked.connect(self.reject)
        for b in (self.record_btn, self.stop_btn, self.play_btn, self.with_backing_check, self.keep_btn):
            buttons.addWidget(b)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.metronome_check.toggled.connect(self._update_hint)
        self.count_in_spin.valueChanged.connect(self._update_hint)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self.channel_combo.currentIndexChanged.connect(self._restart_monitor)

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._on_device_changed(initial_channels=track.input_channels)
        self._on_mode_changed()
        self._update_buttons()
        if not self._devices:
            self._set_status(tr("Nessun ingresso audio trovato"), error=True)
            self.hint_label.setText(
                tr("Collega la scheda audio (o un microfono) e riapri questo dialogo. Serve la libreria "
                "di sistema PortAudio (libportaudio2) con il pacchetto sounddevice."))
        elif not self._take:
            self._set_status(tr("Pronto: prova il livello, poi premi Registra"))

    # ------------------------------------------------------------ scelte

    def mode(self) -> str:
        """"normal", "loop" o "punch" (vedi core.audio_recording)."""
        return self.mode_combo.currentData() if self.loop_region is not None else "normal"

    def result_mode(self) -> str:
        """La modalita' con cui e' stata fatta la ripresa tenuta."""
        return self._mode_used

    def _bar_beats(self) -> float:
        try:
            num, den = (int(x) for x in self.project.time_sig.split("/"))
            return 4.0 * num / den
        except (ValueError, ZeroDivisionError):
            return 4.0

    def _record_start_beat(self) -> float:
        mode = self.mode()
        if mode == "loop":
            return self.loop_region[0]
        if mode == "punch":
            return max(0.0, self.loop_region[0] - self.preroll_spin.value() * self._bar_beats())
        return float(self.start_combo.currentData() or 0.0)

    def _on_mode_changed(self, *_args):
        mode = self.mode()
        self._form.setRowVisible(self.start_combo, mode == "normal")
        self._form.setRowVisible(self.preroll_spin, mode == "punch")
        if mode == "loop":
            self.hear_track_check.setChecked(False)   # i giri di prima non si sentono comunque
        self._update_buttons()

    def selected_device(self):
        i = self.device_combo.currentIndex()
        return self._devices[i] if 0 <= i < len(self._devices) else None

    def input_profile(self) -> str:
        return self.profile_combo.currentData()

    def input_channels_spec(self) -> str:
        return self.channel_combo.currentData() or "1"

    def _selected_channels(self):
        dev = self.selected_device()
        return parse_channel_spec(self.input_channels_spec(), dev.max_channels if dev else 1)

    def _on_device_changed(self, *_args, initial_channels: str = ""):
        dev = self.selected_device()
        current = initial_channels or self.channel_combo.currentData() or INPUT_PROFILES[self.input_profile()][1]
        self.channel_combo.blockSignals(True)
        self.channel_combo.clear()
        for label, spec in channel_choices(dev.max_channels if dev else 1):
            self.channel_combo.addItem(label, spec)
        idx = self.channel_combo.findData(current)
        self.channel_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.channel_combo.blockSignals(False)
        self.latency_spin.setValue(settings.get_input_latency_ms(dev.label) if dev else 0.0)
        self._update_hint()
        self._restart_monitor()

    def _on_profile_changed(self, *_args):
        idx = self.channel_combo.findData(INPUT_PROFILES[self.input_profile()][1])
        if idx >= 0:
            self.channel_combo.setCurrentIndex(idx)   # fa ripartire il monitor
        self._update_hint()

    def _update_hint(self):
        if not self._devices:
            return
        self.hint_label.setText(INPUT_PROFILES[self.input_profile()][2])
        dev = self.selected_device()
        warn = dev is not None and not dev.external and bool(self.metronome_check.isChecked()
                                                              or self.count_in_spin.value())
        if warn != self.mic_warning.isVisibleTo(self):
            self.mic_warning.setVisible(warn)
            if warn and self.isVisible():        # la finestra si allunga invece di sovrapporre il testo
                self.resize(self.width(), max(self.height(), self.sizeHint().height()))

    # ------------------------------------------------------------ misuratore

    def _restart_monitor(self, *_args):
        self._stop_monitor()
        dev = self.selected_device()
        if dev is None or self._recorder is not None:
            return
        monitor = InputMonitor(dev.index, self._selected_channels(), stream_factory=self._monitor_factory,
                               fallback_rate=dev.default_samplerate)
        try:
            monitor.start()
        except Exception as e:
            self._set_status(tr("Ingresso non apribile"), error=True)
            self.hint_label.setText(tr("Impossibile leggere da '{label}': {e}", label=dev.label, e=e))
            return
        self._monitor = monitor

    def _stop_monitor(self):
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor = None

    def _tick(self):
        if self._player is not None:
            if not self._player.playing:
                self.stop_listening()
            else:
                self._set_status(tr("▶ Ascolto  {0}", self._mmss(self._player.seconds)))
        if self._calibration is not None:
            recorder, _times, duration = self._calibration
            self.meter.push_peak(recorder.read_peak())
            if recorder.elapsed_seconds >= duration:
                self._finish_calibration()
            return
        source = self._recorder or self._monitor
        if source is not None:
            peak = source.read_peak()
            self.meter.push_peak(peak)
            self.meter_db_label.setText(
                "CLIP!" if self.meter.clipping else f"{max(-60.0, level_to_db(peak)):.0f} dB")
        self._update_tuner()
        if self._recorder is not None:
            elapsed = self._recorder.elapsed_seconds
            count_in = self._backing.count_in_seconds
            if getattr(self, "_punch_stop_at", None) is not None and elapsed >= self._punch_stop_at:
                self.stop_recording()
                return
            if elapsed < count_in:
                self._set_status(f"Conteggio… {count_in - elapsed:.1f}")
            elif self._backing.loop:
                loop = self._backing.loop_seconds
                self._set_status(tr("● REC  giro {n}  {0}", self._mmss((elapsed - count_in) % loop),
                                    n=int((elapsed - count_in) // loop) + 1), recording=True)
            else:
                self._set_status(tr("● REC  {0}", self._mmss(elapsed - count_in)), recording=True)

    def _update_tuner(self):
        monitor = self._monitor if self._recorder is None else None
        if monitor is None or not hasattr(monitor, "read_recent"):
            self.tuner_label.setText("—")
            dim(self.tuner_label)
            return
        from core import tuning
        freq = tuning.block_pitch(monitor.read_recent(tuning.TUNER_BLOCK_SECONDS), monitor.samplerate)
        if freq is None:
            return                     # resta l'ultima nota letta (le note che si spengono)
        name, cents = tuning.note_and_cents(freq)
        sign = "+" if cents > 0 else "−" if cents < 0 else "±"
        self.tuner_label.setText(tr("{note}  {sign}{cents} cent  ({hz:.1f} Hz)",
                                    note=name, sign=sign, cents=abs(cents), hz=freq))
        self.tuner_label.setStyleSheet(f"color: {GOOD if abs(cents) <= 5 else WARN};")

    # ------------------------------------------------------------ registrazione

    def start_recording(self):
        dev = self.selected_device()
        if dev is None or self._recorder is not None or self._worker is not None:
            return
        self.stop_listening()
        if self._take is not None:
            reply = QMessageBox.question(self, tr("Nuova ripresa"),
                                         tr("Scartare la ripresa appena fatta e registrarne un'altra?"))
            if reply != QMessageBox.Yes:
                return
            self._take = None
        settings.set_audio_input_device(dev.label)
        settings.set_input_latency_ms(dev.label, self.latency_spin.value())
        settings.set_record_count_in_bars(self.count_in_spin.value())
        settings.set_record_metronome(self.metronome_check.isChecked())
        self._stop_monitor()
        self._start_beat = self._record_start_beat()
        self._recording_mode = self.mode()
        args = (self.project, self._start_beat, self.count_in_spin.value(), self.metronome_check.isChecked())
        kwargs = {"mute_track": None if self.hear_track_check.isChecked() else self.track.name}
        if self._recording_mode == "loop":
            kwargs.update(end_beat=self.loop_region[1], loop=True)
        self._set_status(tr("Preparazione della base…"))
        self._update_buttons(preparing=True)
        if not self._run_in_thread:
            try:
                backing = self._backing_builder(*args, **kwargs)
            except Exception as e:
                self._on_backing_error(str(e))
                return
            self._on_backing_ready(backing)
            return
        worker = Worker(self._backing_builder, *args, pass_progress=False, **kwargs)
        self._worker = worker
        worker.finished_ok.connect(self._on_backing_ready)
        worker.finished_error.connect(self._on_backing_error)
        worker.start()

    def _finish_worker(self):
        if self._worker is not None:
            self._worker.wait()
            self._worker = None

    def _on_backing_error(self, message: str):
        self._finish_worker()
        self._update_buttons()
        self._set_status(tr("Base non pronta"), error=True)
        QMessageBox.critical(self, tr("Registrazione non avviata"), message)
        self._restart_monitor()

    def _on_backing_ready(self, backing):
        self._finish_worker()
        if not self.isVisible() and self._run_in_thread:
            return   # dialogo chiuso mentre si preparava la base
        dev = self.selected_device()
        self._backing = backing
        recorder = DuplexRecorder(backing, dev.index, self._selected_channels(),
                                  output_device=output_device_for(dev), stream_factory=self._stream_factory,
                                  fallback_rate=dev.default_samplerate)
        try:
            recorder.start()
        except Exception as e:
            self._update_buttons()
            self._set_status(tr("Registrazione non avviata"), error=True)
            QMessageBox.critical(self, tr("Registrazione non avviata"),
                                 tr("Impossibile aprire la scheda audio '{label}':\n{e}", label=dev.label, e=e))
            self._restart_monitor()
            return
        self._recorder = recorder
        self._punch_stop_at = None
        if getattr(self, "_recording_mode", "normal") == "punch":
            # il punch-in si ferma da solo poco dopo B: oltre non serve niente
            from core.tempo_map import build_tempo_beat_map, seconds_for_beats
            tempo_map = build_tempo_beat_map(self.project)
            self._punch_stop_at = (backing.count_in_seconds + PUNCH_STOP_AFTER_B
                                   + seconds_for_beats(tempo_map, self.loop_region[1])
                                   - seconds_for_beats(tempo_map, self._start_beat))
        if backing.midi_skipped:
            self.hint_label.setText(
                tr("Nessun SoundFont: le tracce con note non si sentono in questa ripresa "
                "(solo tracce audio e metronomo)."))
        self._update_buttons()

    def stop_recording(self):
        if self._recorder is None:
            return
        take = self._recorder.stop()
        self._recorder = None
        played = take.seconds - self._backing.count_in_seconds
        if played <= 0.05:
            self._take = None
            self._set_status(tr("Ripresa troppo corta (fermata durante il conteggio)"), error=True)
        else:
            self._take = take
            peak = tr("picco {0:.0f} dB", level_to_db(take.peak))
            if take.clipped:
                self._set_status(tr("Ripresa di {0} — {peak}: SATURA, abbassa il gain sulla scheda e riprova", self._mmss(played), peak=peak), error=True)
            else:
                self._set_status(tr("Ripresa di {0} — {peak}", self._mmss(played), peak=peak))
        self._update_buttons()
        self._restart_monitor()

    # ------------------------------------------------------------ riascolto

    @property
    def listening(self) -> bool:
        return self._player is not None and self._player.playing

    def toggle_listen(self):
        if self._player is not None:
            self.stop_listening()
            return
        if self._take is None:
            return
        dev = self.selected_device()
        audio = take_preview(self._take, self._backing, self.latency_spin.value(),
                             with_backing=self.with_backing_check.isChecked())
        player = TakePlayer(audio, self._backing.rate, output_device=output_device_for(dev) if dev else None,
                            stream_factory=self._player_factory)
        try:
            player.start()
        except Exception as e:
            QMessageBox.warning(self, tr("Ascolto non riuscito"), str(e))
            return
        self._status_before_listen = (self.status_label.text(), self.status_label.styleSheet())
        self._player = player
        self._update_buttons()

    def stop_listening(self):
        if self._player is not None:
            self._player.stop()
            self._player = None
            text, style = self._status_before_listen      # di nuovo la durata e il picco della ripresa
            self.status_label.setText(text)
            self.status_label.setStyleSheet(style)
            self._update_buttons()

    def keep_take(self):
        if self._take is None:
            return
        self.stop_listening()
        n = len(self.track.audio_clips) + 1
        mode = getattr(self, "_recording_mode", "normal")
        latency = self.latency_spin.value()
        if mode == "loop" and loop_pass_count(self._take, self._backing, latency) <= 0:
            QMessageBox.information(self, tr("Nessun giro completo"),
                                    tr("La ripresa e' stata fermata prima della fine del primo giro: "
                                       "non c'e' niente da tenere."))
            return
        try:
            path = save_take(self._take, self.target_dir, f"{self.track.name} ripresa {n}")
        except OSError as e:
            QMessageBox.critical(self, tr("Salvataggio non riuscito"), str(e))
            return
        name = tr("Ripresa {n}", n=n)
        if mode == "loop":
            clip = loop_clip(name, path, self._start_beat, self._take, self._backing, latency)
        elif mode == "punch":
            from core.tempo_map import build_tempo_beat_map
            a, b = self.loop_region
            clip = punch_clip(name, path, self._start_beat, a, b, self._take, self._backing, latency,
                              build_tempo_beat_map(self.project))
            if clip is None:
                QMessageBox.information(self, tr("Punch-in non raggiunto"),
                                        tr("La ripresa e' stata fermata prima del punto A: non c'e' "
                                           "niente da tenere."))
                return
        else:
            clip = recorded_clip(name, path, self._start_beat, self._backing.count_in_seconds,
                                 self._take.alignment_seconds, latency)
        if mode != "punch":
            # la ripresa va a tempo con il brano: lo segue se il tempo cambia
            from core.tempo_map import build_tempo_beat_map, value_at_beat
            clip.source_bpm = float(value_at_beat(build_tempo_beat_map(self.project), clip.start_beat)
                                    or self.project.tempo_bpm)
        self._result_clip = clip
        self._mode_used = mode
        self.accept()

    def result_clip(self):
        return self._result_clip

    # ------------------------------------------------------------ calibrazione

    def calibrate_latency(self):
        dev = self.selected_device()
        if dev is None or self._recorder is not None or self._calibration is not None:
            return
        reply = QMessageBox.information(
            self, tr("Calibra la latenza"),
            tr("SoundText fara' suonare 8 click e li registrera' dall'ingresso scelto qui sopra, per "
            "misurare il ritardo che la scheda audio non dichiara.\n\n"
            "Collega con un cavo un'uscita della scheda audio a quell'ingresso (il modo piu' "
            "preciso), oppure avvicina il microfono alle casse. Tieni il volume moderato e il "
            "monitoraggio diretto spento."),
            QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
        if reply != QMessageBox.Ok:
            return
        self._stop_monitor()
        backing, times = build_calibration_backing()
        recorder = DuplexRecorder(backing, dev.index, self._selected_channels(),
                                  output_device=output_device_for(dev), stream_factory=self._stream_factory,
                                  fallback_rate=dev.default_samplerate)
        try:
            recorder.start()
        except Exception as e:
            QMessageBox.critical(self, tr("Calibrazione non avviata"),
                                 tr("Impossibile aprire la scheda audio '{label}':\n{e}", label=dev.label, e=e))
            self._restart_monitor()
            return
        self._calibration = (recorder, times, len(backing.samples) / float(backing.rate) + 0.3)
        self._update_buttons(preparing=True)
        self._set_status(tr("Calibrazione in corso…"))

    def _finish_calibration(self):
        recorder, times, _duration = self._calibration
        self._calibration = None
        take = recorder.stop()
        dev = self.selected_device()
        try:
            ms = measure_latency_ms(take, times)
        except RuntimeError as e:
            self._set_status(tr("Calibrazione non riuscita"), error=True)
            QMessageBox.warning(self, tr("Calibrazione non riuscita"), str(e))
        else:
            self.latency_spin.setValue(ms)
            if dev is not None:
                settings.set_input_latency_ms(dev.label, ms)
            self._set_status(tr("Latenza misurata: {ms:+.1f} ms (salvata per questa scheda)", ms=ms))
        self._update_buttons()
        self._restart_monitor()

    # ------------------------------------------------------------ varie

    def _update_buttons(self, preparing: bool = False):
        recording = self._recorder is not None
        has_device = self.selected_device() is not None
        self.record_btn.setEnabled(has_device and not recording and not preparing)
        self.stop_btn.setEnabled(recording)
        self.keep_btn.setEnabled(self._take is not None and not recording and not preparing)
        self.play_btn.setEnabled(self._take is not None and not recording and not preparing)
        self.play_btn.setText(tr("■ Ferma") if self._player is not None else tr("▶ Ascolta"))
        self.with_backing_check.setEnabled(self._take is not None and self._player is None
                                           and not recording and not preparing)
        for w in (self.device_combo, self.profile_combo, self.channel_combo, self.start_combo,
                  self.count_in_spin, self.metronome_check, self.hear_track_check, self.latency_spin,
                  self.calibrate_btn, self.preroll_spin):
            w.setEnabled(not recording and not preparing)
        self.mode_combo.setEnabled(self.loop_region is not None and not recording and not preparing)
        self.calibrate_btn.setEnabled(has_device and not recording and not preparing)

    def _set_status(self, text: str, error: bool = False, recording: bool = False):
        color = "#e05555" if (error or recording) else ""
        self.status_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px;" + (f" color: {color};" if color else ""))
        self.status_label.setText(text)

    @staticmethod
    def _mmss(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def done(self, result):
        self.stop_listening()
        if self._recorder is not None:
            self._recorder.stop()
            self._recorder = None
        if self._calibration is not None:
            self._calibration[0].stop()
            self._calibration = None
        self._stop_monitor()
        self._timer.stop()
        if self._worker is not None:
            self._worker.wait()
            self._worker = None
        super().done(result)
