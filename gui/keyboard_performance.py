"""
Esecuzione dal vivo del dialogo "Suona con la tastiera" (vedi
gui.keyboard_play_dialog): pressione/rilascio dei tasti-nota, accordi,
pizzicato, bending, pedale, arpeggiatore, feedback sonoro immediato e
cattura degli eventi da quantizzare. Mixin di KeyboardPlayDialog, di cui
usa lo stato (come i mixin di gui.main_window).
"""

import time

from PySide6.QtCore import QTimer

from core.audio_quantize import AudioEvent
from core.chords import midi_note, midi_to_token, note_name_to_pc, ParsedChord, voice_chord
from core.instruments import DRUM_MIDI_CHANNEL, PERCUSSION_MAP
from .keyboard_note_map import (
    PERCUSSION_KEYS, QUALITY_ROW_KEYS, BASS_DOUBLE_KEY, SUSTAIN_KEY, STRUM_KEY, BEND_KEY, INVERSION_KEY,
    VELOCITY_TOGGLE_KEY, ARPEGGIATOR_KEY, VELOCITY_LOW, VELOCITY_HIGH,
)
from .keyboard_scancodes import canonical_key

MIN_NOTE_SECONDS = 0.05  # durata minima anche per un tocco brevissimo del tasto
LIVE_MELODIC_CHANNEL = 0  # canale MIDI usato dal LiveSynth per il feedback sonoro dei tasti (traccia melodica)

# --- Strumming (STRUM_KEY) --------------------------------------------------
STRUM_STEP_SECONDS = 0.02  # scarto tra una nota e la successiva dell'accordo "pizzicato"

# --- Bending (BEND_KEY) ------------------------------------------------------
# Alza una nota di un tono intero mentre BEND_KEY e' tenuto premuto, come un
# vero bending chitarristico: sia dal vivo (rampa di pitch bend MIDI reale
# via LiveSynth.pitch_bend, non un salto secco) sia nella traccia registrata,
# dove viene catturato come portamento/slide (core.notation, 'c*4>d*4') -
# che core.midi_export gia' sa rendere come un pitch bend MIDI continuo
# all'esportazione/riproduzione, non solo durante la registrazione dal vivo.
#
# Si applica in questa forma "vera" SOLO a una nota singola (nessun accordo
# della fila qualita' ne' basso profondo attivi, nessun arpeggiatore): la
# grammatica non supporta ancora piu' slide simultanei dentro un accordo/
# blocco, e un arpeggio e' gia' di suo una sequenza di note discrete. In
# quei casi si ricade su uno scarto fisso applicato subito a tutte le note
# (comportamento piu' semplice, non un vero bending, ma meglio di niente).
#
# Limite noto: tutte le note dal vivo condividono lo stesso canale MIDI
# (LIVE_MELODIC_CHANNEL) e il pitch bend e' uno stato PER CANALE, non per
# nota - se si suona un'altra nota mentre un bending e' in corso, quella
# nota puo' sentirsi temporaneamente stonata dal vivo (mai nell'esportazione
# finale, che genera un pitch bend indipendente per ogni nota).
BEND_SEMITONES = 2
BEND_RAMP_UP_MS = 120     # durata della salita del bending dal vivo
BEND_RAMP_DOWN_MS = 80    # durata della discesa al rilascio del tasto-nota
BEND_RAMP_STEP_MS = 15    # intervallo tra un passo e l'altro della rampa

# --- Arpeggiatore (ARPEGGIATOR_KEY) ------------------------------------------
ARPEGGIO_NOTE_FRACTION = 0.85  # frazione del passo effettivamente tenuta nell'evento catturato (resto = respiro)


class KeyboardPerformanceMixin:
    def _current_sounding_pitches(self) -> set:
        """Tutte le note MIDI udibili in questo momento: dai tasti-nota
        tenuti (escludendo quelli in attesa nel pool dell'arpeggiatore, che
        non suonano nulla finche' non e' il loro turno - vedi
        _on_arpeggio_tick), dalle eventuali note in sustain, e dalla nota
        corrente dell'arpeggiatore se attivo. Usata sia per evidenziare la
        tastiera visuale sia per il testo in formato ST (vedi
        _update_piano_display)."""
        pitches = set()
        for info in self._active_notes.values():
            if "perc_name" in info or info.get("via_arpeggiator"):
                continue
            pitches.update(info.get("midi_notes", []))
        for info in self._sustained_notes:
            pitches.update(info.get("midi_notes", []))
        if self._arpeggio_current_live_note is not None:
            pitches.add(self._arpeggio_current_live_note)
        return pitches

    def _current_sounding_percussion(self) -> list:
        """Nomi (core.instruments.PERCUSSION_MAP) dei tasti-percussione
        tenuti in questo momento - le percussioni ignorano sempre il
        sustain (vedi _release_note), quindi self._active_notes basta,
        niente arpeggiatore/pool da considerare qui. Usata da
        _update_piano_display per mostrare a quale suono corrisponde il
        tasto appena premuto."""
        return sorted({
            info["perc_name"] for info in self._active_notes.values() if "perc_name" in info
        })

    def _update_piano_display(self):
        """Aggiorna l'etichetta col nome del suono/nota/accordo correnti: per
        una traccia percussiva, il/i nome/i (core.instruments.PERCUSSION_MAP)
        dei tasti premuti in questo momento; altrimenti la tastiera visuale e
        il testo in formato ST Language (es. 'c*4' per una nota singola,
        '[c*4 e*4 g*4]' per un accordo - stessa sintassi a blocco usata da
        core.audio_quantize per le note simultanee)."""
        if self.instr.is_percussion:
            names = self._current_sounding_percussion()
            self.now_playing_label.setText(
                " " if not names else names[0] if len(names) == 1 else "[" + " ".join(names) + "]"
            )
            return
        if self.piano_widget is None:
            return
        pitches = self._current_sounding_pitches()
        self.piano_widget.set_active(pitches)
        if not pitches:
            self.now_playing_label.setText(" ")
            return
        tokens = [midi_to_token(p) for p in sorted(pitches)]
        self.now_playing_label.setText(tokens[0] if len(tokens) == 1 else "[" + " ".join(tokens) + "]")

    def _on_surface_key_press(self, event):
        if not self._instrument_active():
            return
        key = canonical_key(event)

        # Tasti esecutivi/fila qualita' (vedi gui.keyboard_note_map): non
        # suonano nulla da soli, impostano solo lo stato letto qui sotto al
        # momento in cui si preme un tasto-nota.
        if key in QUALITY_ROW_KEYS or key == BASS_DOUBLE_KEY:
            self._held_quality_key = key
            return
        if key == SUSTAIN_KEY:
            self._sustain_active = True
            return
        if key == STRUM_KEY:
            self._strum_active = True
            return
        if key == BEND_KEY:
            self._bend_active = True
            return
        if key == INVERSION_KEY:
            self._inversion_active = True
            return
        if key == VELOCITY_TOGGLE_KEY:
            self._velocity_low = not self._velocity_low
            return
        if key == ARPEGGIATOR_KEY:
            self._start_arpeggiator()
            return

        if key in self._active_notes:
            return
        now = time.time()

        if self.instr.is_percussion:
            if key not in PERCUSSION_KEYS:
                return
            idx = PERCUSSION_KEYS.index(key)
            names = list(PERCUSSION_MAP.keys())
            if idx >= len(names):
                return
            perc_name = names[idx]
            self._active_notes[key] = {"start": now, "perc_name": perc_name}
            if self._live_synth:
                self._live_synth.note_on(DRUM_MIDI_CHANNEL, PERCUSSION_MAP[perc_name], velocity=100)
            self._update_piano_display()
            return

        if key not in self._note_key_map:
            return
        letter, octave = self._note_key_map[key]
        pc = note_name_to_pc(letter)
        velocity = VELOCITY_LOW if self._velocity_low else VELOCITY_HIGH

        if self._held_quality_key == BASS_DOUBLE_KEY:
            # "Basso profondo": raddoppia la fondamentale un'ottava sotto -
            # non e' una qualita' d'accordo, si costruisce a mano invece di
            # passare per voice_chord (il cui trattamento per intervalli
            # negativi dipende dallo stile di voicing dello strumento,
            # imprevedibile qui: vogliamo sempre esattamente questo).
            base = midi_note(pc, octave)
            midi_notes = self._clamp_to_instrument_range([base, base - 12])
        elif self._held_quality_key in QUALITY_ROW_KEYS:
            _, intervals = QUALITY_ROW_KEYS[self._held_quality_key]
            parsed = ParsedChord(root_pc=pc, quality="", intervals=intervals, symbol=letter.upper())
            midi_notes = voice_chord(parsed, octave, self.instr)
            if self._inversion_active:
                midi_notes = self._apply_inversion(midi_notes)
        else:
            midi_notes = [midi_note(pc, octave)]

        # Bending "vero" (slide + rampa dal vivo): solo nota singola, non
        # arpeggiata (vedi la nota su BEND_SEMITONES per il perche').
        bend_as_slide = (
            self._bend_active and not self._arpeggiator_active and len(midi_notes) == 1
        )

        if self._bend_active and not bend_as_slide:
            # Bending "semplice" di ripiego (accordo/basso profondo/arpeggiatore):
            # scarto fisso applicato subito a tutte le note, non un vero glide.
            midi_notes = self._clamp_to_instrument_range([n + BEND_SEMITONES for n in midi_notes])

        if self._arpeggiator_active:
            # Non suona nulla subito: entra nel pool ciclico dell'arpeggiatore
            # (vedi _current_arpeggio_pool/_on_arpeggio_tick), che se ne
            # occupa lui - sia del suono live sia dell'evento catturato.
            self._active_notes[key] = {
                "start": now, "midi_notes": midi_notes, "velocity": velocity, "via_arpeggiator": True,
            }
            return

        if bend_as_slide:
            base_pitch = midi_notes[0]
            bent_pitch = self._clamp_to_instrument_range([base_pitch + BEND_SEMITONES])[0]
            self._active_notes[key] = {
                "start": now, "midi_notes": [base_pitch], "velocity": velocity, "key": key,
                "note_offsets": {base_pitch: 0.0}, "live_bend": True, "slide_to_pitch": bent_pitch,
            }
            if self._live_synth:
                self._live_bend_key = key
                self._live_synth.note_on(LIVE_MELODIC_CHANNEL, base_pitch, velocity=velocity)
                self._pitch_bend_ramp(key, 0.0, float(bent_pitch - base_pitch), BEND_RAMP_UP_MS)
            self._update_piano_display()
            return

        if self._strum_active and len(midi_notes) > 1:
            ordered = sorted(midi_notes)
            offsets = {pitch: i * STRUM_STEP_SECONDS for i, pitch in enumerate(ordered)}
        else:
            offsets = {pitch: 0.0 for pitch in midi_notes}

        self._active_notes[key] = {
            "start": now, "midi_notes": midi_notes, "velocity": velocity, "note_offsets": offsets,
            "key": key,
        }
        if self._live_synth:
            for midi_pitch in midi_notes:
                if offsets[midi_pitch] <= 0:
                    self._live_synth.note_on(LIVE_MELODIC_CHANNEL, midi_pitch, velocity=velocity)
                else:
                    QTimer.singleShot(
                        int(offsets[midi_pitch] * 1000),
                        lambda p=midi_pitch, v=velocity: self._delayed_note_on(p, v))
        self._update_piano_display()

    def _pitch_bend_ramp(self, key, start_val, end_val, total_ms, on_complete=None, step_index=0):
        """Anima il pitch bend del canale live da start_val a end_val (in
        semitoni) in passi di BEND_RAMP_STEP_MS, per un bending dal vivo che
        e' un vero glide invece di un salto secco. Se nel frattempo un
        bending piu' recente ha preso il controllo del canale (self._live_bend_key
        e' cambiato), si ferma senza piu' toccare il pitch bend (che non e'
        piu' suo da modificare) ma chiama comunque on_complete, cosi' la
        pulizia (note-off) avviene sempre anche in quel caso."""
        if self._live_bend_key != key or self._live_synth is None:
            if on_complete:
                on_complete()
            return
        total_steps = max(1, total_ms // BEND_RAMP_STEP_MS)
        frac = min(1.0, step_index / total_steps)
        value = start_val + (end_val - start_val) * frac
        self._live_synth.pitch_bend(LIVE_MELODIC_CHANNEL, value)
        if step_index >= total_steps:
            if on_complete:
                on_complete()
            return
        QTimer.singleShot(
            BEND_RAMP_STEP_MS,
            lambda: self._pitch_bend_ramp(key, start_val, end_val, total_ms, on_complete, step_index + 1))

    def _release_bend_ramp(self, info):
        """Fa scendere il bending dal vivo verso zero (rilascio del tasto,
        con la nota che continua a suonare mentre la rampa scende, come una
        corda di chitarra che smette di essere piegata) e solo alla fine
        ferma davvero la nota - non subito, a differenza del percorso
        normale (vedi _finish_note)."""
        key = info["key"]
        midi_pitch = info["midi_notes"][0]
        bent_offset = info.get("slide_to_pitch", midi_pitch) - midi_pitch

        def _finish_release():
            if self._live_synth:
                self._live_synth.note_off(LIVE_MELODIC_CHANNEL, midi_pitch)
                # Non ripristinare il pitch bend a zero se un bending piu'
                # recente possiede gia' il canale: lo azzererebbe sotto i piedi.
                if self._live_bend_key is None:
                    self._live_synth.pitch_bend(LIVE_MELODIC_CHANNEL, 0)
            if self._live_bend_key == key:
                self._live_bend_key = None

        self._pitch_bend_ramp(key, float(bent_offset), 0.0, BEND_RAMP_DOWN_MS, on_complete=_finish_release)

    def _reset_live_bend(self):
        """Azzera lo stato del bending dal vivo: usato ovunque le note attive
        vengano chiuse in blocco (ferma registrazione/prova, Ok, Annulla),
        cosi' un bending a meta' rampa non lascia il pitch bend del canale
        condiviso bloccato su un valore non nullo tra una sessione e l'altra."""
        self._live_bend_key = None
        self._midi_bend = 0.0          # leva della tastiera MIDI (vedi gui.midi_keyboard)
        if self._live_synth:
            self._live_synth.pitch_bend(LIVE_MELODIC_CHANNEL, 0)

    def _delayed_note_on(self, midi_pitch, velocity):
        """Note-on differito per lo strumming (vedi STRUM_KEY): puo' scattare
        dopo che il tasto e' gia' stato rilasciato in un pizzico molto
        rapido - innocuo, l'evento catturato (vedi _finish_note) e' comunque
        calcolato da note_offsets, indipendente da quando arriva davvero il
        suono live."""
        if self._live_synth:
            self._live_synth.note_on(LIVE_MELODIC_CHANNEL, midi_pitch, velocity=velocity)

    def _clamp_to_instrument_range(self, notes):
        """Riporta ogni nota nel registro (range_low..range_high) dello
        strumento corrente spostandola di ottave, come fa internamente
        core.chords.voice_chord: duplicato qui (poche righe) per i casi che
        costruiscono le note a mano invece di passare da voice_chord (basso
        profondo, inversione)."""
        adjusted = []
        for n in notes:
            while n < self.instr.range_low:
                n += 12
            while n > self.instr.range_high:
                n -= 12
            adjusted.append(n)
        return sorted(set(adjusted))

    def _apply_inversion(self, notes):
        """1a inversione: sposta la nota piu' grave (la fondamentale, in un
        voicing appena generato da voice_chord) un'ottava sopra."""
        if not notes:
            return notes
        notes = sorted(notes)
        root = notes[0]
        return self._clamp_to_instrument_range(notes[1:] + [root + 12])

    def _on_surface_key_release(self, event):
        if not self._instrument_active():
            return
        key = canonical_key(event)

        if key in QUALITY_ROW_KEYS or key == BASS_DOUBLE_KEY:
            if self._held_quality_key == key:
                self._held_quality_key = None
            return
        if key == INVERSION_KEY:
            self._inversion_active = False
            return
        if key == STRUM_KEY:
            self._strum_active = False
            return
        if key == BEND_KEY:
            self._bend_active = False
            return
        if key == SUSTAIN_KEY:
            self._sustain_active = False
            self._flush_sustained_notes(time.time())
            return
        if key == VELOCITY_TOGGLE_KEY:
            return  # commutato gia' al press, niente da fare al release
        if key == ARPEGGIATOR_KEY:
            self._stop_arpeggiator()
            return

        self._release_note(key, time.time())

    def _release_note(self, key, end_time):
        """Chiude il tasto-nota rilasciato: se il sustain e' attivo (vedi
        SUSTAIN_KEY) la nota melodica NON viene fermata subito, resta 'in
        sostegno' (vedi _sustained_notes) finche' il sustain stesso non
        viene rilasciato. Le percussioni ignorano sempre il sustain: un
        colpo e' un singolo suono che decade da solo, non ha un note-off da
        prolungare. Un tasto entrato nel pool dell'arpeggiatore (vedi
        ARPEGGIATOR_KEY) non ha mai avuto un suono/evento proprio: se ne
        occupa gia' del tutto _on_arpeggio_tick, qui si scarta soltanto."""
        info = self._active_notes.pop(key, None)
        if info is None:
            return
        if info.get("via_arpeggiator"):
            return
        if self._sustain_active and "perc_name" not in info:
            self._sustained_notes.append(info)
        else:
            self._finish_note(info, end_time)
        self._update_piano_display()

    def _finish_note(self, info, end_time):
        """Ferma il suono live (se in corso) e, solo se si sta registrando,
        chiude l'evento catturato per la quantizzazione (vedi
        _generate_preview_from_events). Usata sia per una nota rilasciata
        normalmente sia, con ritardo, per una nota tenuta in sustain.
        note_offsets (vedi STRUM_KEY) fa partire ogni nota dell'accordo in un
        istante leggermente diverso invece che tutte insieme, pur chiudendole
        tutte alla stessa fine (quella del tasto fisico). Una nota in
        bending "vero" (vedi BEND_SEMITONES/live_bend) non ferma il suono
        live subito: lo delega a _release_bend_ramp, che lo fa scendere
        gradualmente prima di fermarlo - la durata REGISTRATA invece si
        chiude comunque adesso, al momento vero del rilascio del tasto."""
        if "perc_name" not in info and self._live_synth:
            if info.get("live_bend"):
                self._release_bend_ramp(info)
            else:
                for midi_pitch in info["midi_notes"]:
                    self._live_synth.note_off(LIVE_MELODIC_CHANNEL, midi_pitch)
        if not self._recording:
            return
        start = info["start"]
        end = max(end_time, start + MIN_NOTE_SECONDS)
        end_sec = end - self._record_start_wall
        velocity = info.get("velocity", 100)
        if "perc_name" in info:
            start_sec = start - self._record_start_wall
            self._captured_events.append(
                AudioEvent(start_sec=start_sec, end_sec=end_sec, velocity=velocity, perc_name=info["perc_name"]))
            return
        offsets = info.get("note_offsets", {})
        slide_to_pitch = info.get("slide_to_pitch")
        for midi_pitch in info["midi_notes"]:
            note_start = min(start + offsets.get(midi_pitch, 0.0), end - MIN_NOTE_SECONDS)
            start_sec = note_start - self._record_start_wall
            self._captured_events.append(AudioEvent(
                start_sec=start_sec, end_sec=end_sec, velocity=velocity, midi_pitch=midi_pitch,
                slide_to_pitch=slide_to_pitch))

    def _flush_sustained_notes(self, end_time):
        """Chiude tutte le note in sustain (vedi _release_note), usata sia al
        rilascio di SUSTAIN_KEY sia ovunque le note attive vengano chiuse in
        blocco (ferma registrazione/prova, Ok, Annulla) per non lasciarne
        orfane se il sustain era ancora tenuto premuto in quel momento."""
        if not self._sustained_notes:
            return
        pending = self._sustained_notes
        self._sustained_notes = []
        for info in pending:
            self._finish_note(info, end_time)
        self._update_piano_display()

    # ------------------------------------------------------------ arpeggiatore

    def _seconds_per_arpeggio_step(self):
        bpm = max(1, self.project.tempo_bpm)
        return 60.0 / bpm / 4.0  # un sedicesimo, stessa unita' minima della griglia di quantizzazione

    def _current_arpeggio_pool(self):
        """Altezze (ordinate, senza duplicati) di tutti i tasti-nota premuti
        DOPO ARPEGGIATOR_KEY e ancora tenuti (vedi 'via_arpeggiator' in
        _on_surface_key_press): l'insieme si aggiorna dinamicamente a ogni
        passo, cosi' aggiungere/togliere un tasto mentre lo spazio e' gia'
        tenuto cambia il pool dal passo successivo, senza doverlo riavviare."""
        pool = set()
        for info in self._active_notes.values():
            if info.get("via_arpeggiator") and "perc_name" not in info:
                pool.update(info["midi_notes"])
        return sorted(pool)

    def _start_arpeggiator(self):
        if self._arpeggiator_active:
            return
        self._arpeggiator_active = True
        self._arpeggio_index = 0
        self._arpeggio_timer.start(max(20, int(self._seconds_per_arpeggio_step() * 1000)))
        self._on_arpeggio_tick()  # primo passo subito, senza aspettare il primo intervallo

    def _stop_arpeggiator(self):
        if not self._arpeggiator_active:
            return
        self._arpeggiator_active = False
        self._arpeggio_timer.stop()
        if self._arpeggio_current_live_note is not None and self._live_synth:
            self._live_synth.note_off(LIVE_MELODIC_CHANNEL, self._arpeggio_current_live_note)
        self._arpeggio_current_live_note = None
        self._update_piano_display()

    def _on_arpeggio_tick(self):
        """Un passo dell'arpeggio: ferma (dal vivo) la nota del passo
        precedente, avanza ciclicamente nel pool corrente e ne suona la
        prossima, catturando un evento gia' completo (durata =
        ARPEGGIO_NOTE_FRACTION del passo, per lasciare un piccolo respiro
        articolato tra una nota e l'altra nella notazione risultante) invece
        di aspettare il prossimo giro per chiuderlo."""
        if self._arpeggio_current_live_note is not None and self._live_synth:
            self._live_synth.note_off(LIVE_MELODIC_CHANNEL, self._arpeggio_current_live_note)
            self._arpeggio_current_live_note = None

        pool = self._current_arpeggio_pool()
        if not pool:
            self._update_piano_display()
            return
        pitch = pool[self._arpeggio_index % len(pool)]
        self._arpeggio_index += 1

        velocity = VELOCITY_LOW if self._velocity_low else VELOCITY_HIGH
        if self._live_synth:
            self._live_synth.note_on(LIVE_MELODIC_CHANNEL, pitch, velocity=velocity)
            self._arpeggio_current_live_note = pitch
        self._update_piano_display()

        if self._recording:
            now = time.time()
            step = self._seconds_per_arpeggio_step()
            start_sec = now - self._record_start_wall
            end_sec = start_sec + step * ARPEGGIO_NOTE_FRACTION
            self._captured_events.append(
                AudioEvent(start_sec=start_sec, end_sec=end_sec, velocity=velocity, midi_pitch=pitch))
