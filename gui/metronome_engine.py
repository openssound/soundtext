"""
Motore del click del metronomo: schedulazione dei colpi e riproduzione dei
suoni (QSoundEffect), condiviso tra la finestra principale (durante la
riproduzione dell'ensemble, con eventuali cambi di tempo/metrica) e il
dialogo di importazione audio (un click a tempo/metrica costante, utile per
registrare a tempo dal microfono).
"""

import time

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtMultimedia import QSoundEffect

from core import settings as app_settings
from core.tempo_map import beat_at_elapsed_seconds, seconds_for_beats, click_grid_position


class MetronomeEngine(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._fire_click)
        self._effect_accent = QSoundEffect(self)
        self._effect_normal = QSoundEffect(self)
        self._tempo_map = []
        self._metrica_map = []
        self._offset_beats = 0.0
        self._start_wall = None
        self._pending_click = None
        self._running = False
        # Funzione che ritorna il beat che si sta ascoltando (dal clock del
        # driver audio, vedi PlaybackEngine.position_seconds) o None: se c'e',
        # ha la precedenza sul cronometro interno e il click segue l'audio
        # reale anche quando salta indietro (loop A-B).
        self._position_source = None
        self._last_seen_beat = None   # vedi resync
        self.reload_sounds()

    def reload_sounds(self):
        """Ricarica i due QSoundEffect (accento/normale) dal preset e volume
        correnti (core.settings): da chiamare all'avvio e ogni volta che
        l'utente cambia le impostazioni in Opzioni → Metronomo."""
        from core.metronome_sounds import ensure_click_sound_files
        accent_path, normal_path = ensure_click_sound_files(app_settings.get_metronome_sound())
        volume = app_settings.get_metronome_volume() / 100.0
        self._effect_accent.setSource(QUrl.fromLocalFile(accent_path))
        self._effect_normal.setSource(QUrl.fromLocalFile(normal_path))
        self._effect_accent.setVolume(volume)
        self._effect_normal.setVolume(volume)

    def preview(self):
        """Fa sentire un click di accento seguito da uno normale, con le
        impostazioni correnti (pulsante 'Prova' del dialogo Metronomo)."""
        self._effect_accent.play()
        QTimer.singleShot(350, self._effect_normal.play)

    def is_running(self) -> bool:
        return self._running

    def start(self, tempo_beat_map, metrica_beat_map, offset_beats: float = 0.0,
              start_immediately: bool = True):
        """Avvia il metronomo sulla mappa di tempo/metrica data (vedi
        core.tempo_map: puo' essere a valore costante, per un click semplice,
        o con piu' punti se il brano cambia tempo/metrica durante l'esecuzione).

        start_immediately=True (es. registrazione dal microfono, dove il
        click deve iniziare SUBITO) fissa gia' ora il riferimento temporale;
        False (riproduzione ensemble, il cui audio comincia con un ritardo
        dovuto al rendering) lascia che sia mark_started() a farlo quando
        l'audio comincia davvero."""
        self._tempo_map = tempo_beat_map
        self._metrica_map = metrica_beat_map
        self._offset_beats = offset_beats
        self._running = True
        self._start_wall = time.time() if start_immediately else None
        click_beat, accent = click_grid_position(self._metrica_map, offset_beats)
        self._schedule(click_beat, accent)

    def set_position_source(self, source):
        self._position_source = source

    def resync(self):
        """Riallinea il prossimo click alla posizione reale se l'audio e'
        tornato indietro (fine di un loop A-B, o un salto): da chiamare
        periodicamente dal thread Qt (es. dal timer della barra di
        avanzamento). Senza, il click resterebbe programmato sul punto a
        cui l'audio era arrivato prima del salto."""
        if not self._running or self._pending_click is None:
            return
        current = self._current_beat()
        last = self._last_seen_beat
        self._last_seen_beat = current
        if last is not None and current < last - 1e-3:
            self._schedule(*click_grid_position(self._metrica_map, current))

    def mark_started(self):
        """Da chiamare quando l'audio comincia davvero, se start() e' stato
        invocato con start_immediately=False (vedi PlaybackEngine.play_file,
        on_audio_started). Richiamato dal thread di riproduzione (non quello
        Qt/GUI): si limita percio' a un assegnamento di attributo, senza
        toccare il QTimer (avviarlo/fermarlo da un thread diverso da quello
        che lo possiede e' un errore Qt) — il ri-scheduling vero e proprio
        avviene al prossimo tick di retry di _fire_click, sul thread Qt."""
        if self._running and self._start_wall is None:
            self._start_wall = time.time()

    def stop(self):
        self._running = False
        self._click_timer.stop()
        self._pending_click = None
        self._start_wall = None
        self._last_seen_beat = None

    def _current_beat(self) -> float:
        if self._position_source is not None:
            beat = self._position_source()
            if beat is not None:
                return beat
        if self._start_wall is None:
            return self._offset_beats
        elapsed = time.time() - self._start_wall
        return beat_at_elapsed_seconds(self._tempo_map, self._offset_beats, elapsed)

    def _schedule(self, click_beat: float, accent: bool):
        self._pending_click = (click_beat, accent)
        if not self._running:
            return
        if self._start_wall is None:
            # Audio non ancora avviato (rendering in corso): ritenta a breve,
            # cosi' il primo click resta sincronizzato con l'inizio reale
            # del suono (vedi mark_started).
            self._click_timer.start(20)
            return
        current_beat = self._current_beat()
        # Integra i secondi effettivi tra current_beat e click_beat attraverso
        # la mappa di tempo (non un semplice beat*60/bpm col bpm del punto di
        # arrivo): se click_beat cade esattamente su un cambio di tempo, il
        # tratto da percorrere fino a li' e' ancora al tempo PRECEDENTE.
        delay_seconds = max(0.0, seconds_for_beats(self._tempo_map, click_beat)
                             - seconds_for_beats(self._tempo_map, current_beat))
        self._click_timer.start(max(0, int(delay_seconds * 1000)))

    def _fire_click(self):
        if not self._running or self._pending_click is None:
            return
        if self._start_wall is None:
            # Il timer da 20ms di _schedule e' scattato ma l'audio non e'
            # ancora iniziato davvero (mark_started() non ancora richiamato):
            # e' solo un altro giro di attesa, non un click dovuto.
            self._schedule(*self._pending_click)
            return
        click_beat, accent = self._pending_click
        if self._current_beat() < click_beat - 0.05:
            # Timer scaduto prima che l'audio arrivi al click (l'audio e'
            # tornato indietro nel frattempo, o il timer e' impreciso):
            # si riprogramma sulla posizione reale invece di suonare fuori tempo.
            self._schedule(click_beat, accent)
            return
        (self._effect_accent if accent else self._effect_normal).play()
        next_beat, next_accent = click_grid_position(self._metrica_map, click_beat + 1e-6)
        self._schedule(next_beat, next_accent)
