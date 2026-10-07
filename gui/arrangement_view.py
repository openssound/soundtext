"""
Vista "Struttura brano": arrangiamento a box (core.model.Clip) su un unico
canvas multi-traccia, alternativo all'editor di testo lineare (gui.main_window)
per lavorare sulla struttura del brano (intro/verse/chorus/...) invece che
nota per nota. Vedi il piano di implementazione per il disegno complessivo:
un box e' un rettangolo largo quanto la durata della sua partitura
st-language, trascinabile solo in orizzontale (il riposizionamento verticale
tra tracce avviene con copia/incolla, non trascinando), con menu tasto-destro
per Play/Trasponi/altro. Il contenuto effettivo (Track.text) resta sempre
quello che playback/export/validazione leggono: ogni modifica ai box
ricalcola Track.text da core.arrangement.flatten_clips_to_text.
"""

import dataclasses
import itertools
import os
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.arrangement import (
    anchored_preview_text,
    clip_duration_beats,
    flatten_clips_to_text,
    load_box_file,
    save_box_file,
)
from core import audio_tracks
from core.instruments import gm_family_for_program
from core.model import AudioClip, Clip, Project
from core.notation import bar_starts, validate_track_text
from core.playback import PlaybackEngine
from core.project_io import ensure_songs_dir
from core.rhythm_generate import project_has_chords, tracks_duration_beats
from core.tempo_map import build_tempo_beat_map

from .audio_import_dialog import AudioImportDialog
from .box_edit_dialog import BoxEditDialog
from .box_transpose_dialog import BoxTransposeDialog
from .keyboard_play_dialog import KeyboardPlayDialog
from .main_window_playback import TEXT_DIM_INVERT_BG
from .rhythm_generate_dialog import (
    BassGenerateDialog, ChordProgressionDialog, DrumGenerateDialog, MelodyGenerateDialog, last_box_key,
    project_bar_beats,
)
from .theme import ACCENT, BORDER, TEXT_DIM, get_active_theme
from .track_header import TrackHeaderWidget, make_add_track_button, refresh_add_track_icon
from .track_widget import AUDIO_TRACK_COLOR, _family_color
from core.i18n import tr

PX_PER_BEAT = 24   # scala orizzontale corrente: cambia con lo zoom (vedi ArrangementView.set_zoom)
DEFAULT_PX_PER_BEAT = 24
MIN_PX_PER_BEAT = 6
MAX_PX_PER_BEAT = 96
ZOOM_STEP = 1.25
ROW_HEIGHT = 64
ROW_GAP = 6
HEADER_WIDTH = 230   # colonna delle testate traccia (mixer dentro le righe, vedi gui.track_header)
RULER_HEIGHT = 26
SNAP_BEATS = 1.0
MIN_SCENE_BARS = 32
BOX_CORNER_RADIUS = 6
PLAYHEAD_EDGE_MARGIN = 60  # px dal bordo del viewport oltre cui l'auto-scroll insegue la testina
PREVIEW_PLAY_TEXT = tr("Ascolta il box selezionato")
PREVIEW_PAUSE_TEXT = tr("Pausa ascolto del box")
CLICK_DRAG_THRESHOLD_PX = 3  # sotto questa soglia un press+release non conta come trascinamento
HELP_TEXT = (
    tr("• Doppio click su una riga vuota: nuovo box (sulle tracce audio: importa un file).\n"
    "• Trascina un box per spostarlo nel tempo; i bordi di una clip audio per tagliarla.\n"
    "• Doppio click su un box: modificalo. Tasto destro: trasponi, duplica, dividi e altro.\n"
    "• Shift+Spazio: ascolta il box selezionato. Play/Stop in alto: tutto il brano.\n"
    "• Clic sul righello: salta in quel punto.\n"
    "• Testata della traccia: M/S/● e volume; ⋯ o tasto destro per tutte le azioni.")
)
EMPTY_ROW_HINT = tr("Doppio click per creare un box · tasto destro per generare, suonare o importare")
EMPTY_AUDIO_ROW_HINT = tr("Doppio click per importare un file audio · ● per registrare")
FREE_TEXT_ROW_HINT = tr("Traccia scritta a testo (vista Testo) · doppio click per aggiungere un box")
NO_TRACKS_HINT = tr("Nessuna traccia: comincia da \"+ Aggiungi traccia\" qui a sinistra")
EDGE_GRAB_PX = 6            # bordo di un box audio che si afferra per tagliarlo
TRIM_SNAP_BEATS = 0.25      # passo del taglio col mouse (Shift = libero)


def _snap(beat: float) -> float:
    return round(round(beat / SNAP_BEATS) * SNAP_BEATS, 6)


def _canvas_colors() -> dict:
    if get_active_theme() == "light":
        return {"bg": "#f0f0f2", "header_bg": "#ffffff", "row_bg": "#f7f7f9", "ruler_bg": "#ffffff",
                "border": "#c4c4c8", "text": TEXT_DIM, "box_text": "#10151a"}
    return {"bg": "#181818", "header_bg": "#232323", "row_bg": "#202020", "ruler_bg": "#232323",
            "border": BORDER, "text": TEXT_DIM, "box_text": "#10151a"}


# ---------------------------------------------------------------------------
# Box (Clip) nel canvas
# ---------------------------------------------------------------------------

class BoxItem(QGraphicsRectItem):
    def __init__(self, view: "ArrangementView", track_name: str, clip: Clip, fixed_y: float):
        super().__init__()
        self.view = view
        self.track_name = track_name
        self.clip = clip
        self._fixed_y = fixed_y
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable |
                       QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self._dragging = False
        self._press_pos = None
        self._layout()

    def _layout(self):
        instrument_name = self.view.host.project.get_track(self.track_name).instrument_name
        duration = self.view.clip_length_beats(self.track_name, self.clip)
        width = max(6.0, duration * PX_PER_BEAT)
        height = ROW_HEIGHT - 10
        self.setRect(0, 0, width, height)
        color = QColor(_family_color(instrument_name))
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(140), 1))
        self.setPos(HEADER_WIDTH + self.clip.start_beat * PX_PER_BEAT, self._fixed_y)
        self.setToolTip(tr("{name}  ({duration:.2f} beat)\nDoppio click per modificare, tasto destro per altre azioni.", name=self.clip.name, duration=duration))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = QPointF(value)
            new_pos.setY(self._fixed_y)
            if new_pos.x() < HEADER_WIDTH:
                new_pos.setX(HEADER_WIDTH)
            if self._dragging:
                # Snap "live" (non solo al rilascio): la formula x = HEADER_WIDTH
                # + start_beat*PX_PER_BEAT e' identica su ogni riga, quindi due
                # box con lo stesso beat cadono sempre sullo stesso pixel -
                # agganciare gia' durante il trascinamento (invece che solo al
                # rilascio) e' cio' che rende possibile allineare a vista un box
                # con uno di un'altra traccia.
                beat = _snap((new_pos.x() - HEADER_WIDTH) / PX_PER_BEAT)
                new_pos.setX(HEADER_WIDTH + beat * PX_PER_BEAT)
                self.view.canvas.set_drag_guide(new_pos.x())
            return new_pos
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self.view.select_box(self.track_name, self.clip)
        self._press_pos = self.pos()
        self._press_scene_pos = event.scenePos()
        self._dragging = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._dragging = False
        self.view.canvas.set_drag_guide(None)
        # Confronta lo spostamento REALE del mouse (press -> release), non
        # quello (gia' agganciato al beat) dell'item: itemChange() sopra
        # aggancia la posizione dell'item al beat piu' vicino ad ogni
        # millimetro di trascinamento, quindi anche un solo pixel di
        # movimento del mouse puo' far saltare l'item di un beat intero se
        # non era gia' su un beat esatto - confrontare le posizioni
        # dell'ITEM (invece che del mouse) sottostimerebbe sistematicamente
        # quanto il mouse si e' davvero mosso.
        moved_px = (event.scenePos() - self._press_scene_pos).manhattanLength()
        if moved_px < CLICK_DRAG_THRESHOLD_PX:
            # Click di sola selezione, senza un trascinamento intenzionale:
            # un micro-spostamento di pochi pixel tra press e release (quasi
            # inevitabile con un mouse vero) non deve comunque spostare il
            # box sul beat piu' vicino - senza questo controllo, il solo
            # selezionare un box posizionato su un beat non intero (es. dopo
            # una tuplet) lo spostava silenziosamente sul quarto piu' vicino.
            # Si ripristina la posizione esatta precedente al click,
            # scartando l'eventuale snap gia' applicato durante il rilascio.
            self.setPos(self._press_pos)
            return
        desired_beat = (self.pos().x() - HEADER_WIDTH) / PX_PER_BEAT
        resolved = _snap(self.view.resolve_free_slot(self.track_name, self.clip, desired_beat))
        if abs(resolved - self.clip.start_beat) < 1e-9:
            # Il trascinamento e' rientrato esattamente nella posizione di
            # partenza: nessuno spostamento da applicare ne' da registrare
            # per l'undo (altrimenti si aggiungerebbe un'azione vuota alla
            # pila, e si segnerebbe il progetto come modificato senza motivo).
            return
        self.clip.start_beat = resolved
        self.view.on_clip_changed(self.track_name)

    def mouseDoubleClickEvent(self, event):
        self.view.edit_box(self)

    def paint(self, painter, option, widget=None):
        # Non super().paint(...): QGraphicsRectItem disegna sempre un
        # rettangolo con angoli vivi, senza modo di arrotondarli - qui si
        # ridisegna a mano con lo stesso pen/brush impostati in _layout(),
        # cosi' inizio/fine di ogni box risaltano meglio nel canvas.
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), BOX_CORNER_RADIUS, BOX_CORNER_RADIUS)
        if self.clip is self.view.selected_clip:
            # Evidenziazione esplicita del box selezionato (invece di
            # affidarsi al solo indicatore tratteggiato predefinito di Qt,
            # poco visibile su uno sfondo gia' colorato): bordo spesso in
            # accento, usato anche da _play_..._into_selected_track/
            # _import_..._into_selected_track (main_window_mixer.py) per
            # sapere se il box selezionato, non la traccia, e' la
            # destinazione di "in questa/o".
            sel_pen = QPen(QColor(ACCENT))
            sel_pen.setWidth(3)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), BOX_CORNER_RADIUS, BOX_CORNER_RADIUS)
        painter.setPen(QPen(QColor(_canvas_colors()["box_text"])))
        painter.setFont(QFont("Sans", 9))
        rect = self.rect().adjusted(4, 2, -4, -2)
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, self.clip.name)


class AudioBoxItem(BoxItem):
    """Box di una clip audio (core.model.AudioClip): largo quanto il file
    (meno i tagli) alla posizione in cui si trova, con la forma d'onda.
    Si trascina come un box di notazione; i bordi si trascinano per
    tagliarne inizio e fine (l'audio resta dov'e' nel tempo, vedi
    core.audio_tracks.trim_clip_start_to_beat); doppio click per rinominarlo."""

    _trim_edge = None

    def _edge_at(self, x: float):
        if getattr(self, "_missing", True):
            return None
        width = self.rect().width()
        grab = min(EDGE_GRAB_PX, width / 3)
        if x <= grab:
            return "left"
        if x >= width - grab:
            return "right"
        return None

    def hoverMoveEvent(self, event):
        self.setCursor(Qt.SizeHorCursor if self._edge_at(event.pos().x()) else Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        edge = self._edge_at(event.pos().x()) if event.button() == Qt.LeftButton else None
        if edge is None:
            super().mousePressEvent(event)
            return
        self.view.select_box(self.track_name, self.clip)
        self._trim_edge = edge
        self._trim_before = (self.clip.start_beat, self.clip.trim_start, self.clip.trim_end)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._trim_edge is None:
            super().mouseMoveEvent(event)
            return
        beat = max(0.0, (event.scenePos().x() - HEADER_WIDTH) / PX_PER_BEAT)
        if not event.modifiers() & Qt.ShiftModifier:
            beat = round(beat / TRIM_SNAP_BEATS) * TRIM_SNAP_BEATS
        tempo_map = self.view._tempo_map()
        if self._trim_edge == "left":
            audio_tracks.trim_clip_start_to_beat(self.clip, beat, tempo_map)
        else:
            audio_tracks.trim_clip_end_to_beat(self.clip, beat, tempo_map)
        self.prepareGeometryChange()
        self._layout()
        edge_x = self.pos().x() + (0 if self._trim_edge == "left" else self.rect().width())
        self.view.canvas.set_drag_guide(edge_x)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._trim_edge is None:
            super().mouseReleaseEvent(event)
            return
        self._trim_edge = None
        self.view.canvas.set_drag_guide(None)
        if (self.clip.start_beat, self.clip.trim_start, self.clip.trim_end) != self._trim_before:
            self.view.on_clip_changed(self.track_name)

    def _layout(self):
        duration = self.view.clip_length_beats(self.track_name, self.clip)
        width = max(6.0, duration * PX_PER_BEAT)
        self.setRect(0, 0, width, ROW_HEIGHT - 10)
        self._missing = audio_tracks.clip_is_missing(self.clip)
        color = QColor("#d06060" if self._missing else AUDIO_TRACK_COLOR)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(140), 1))
        self.setPos(HEADER_WIDTH + self.clip.start_beat * PX_PER_BEAT, self._fixed_y)
        if self._missing:
            tip = tr("{name}\nFILE MANCANTE: {file}\nTasto destro → Ritrova file...", name=self.clip.name, file=self.clip.file)
        else:
            seconds = audio_tracks.clip_play_seconds(self.clip)
            gain = tr(", gain {gain_db:+g} dB", gain_db=self.clip.gain_db) if self.clip.gain_db else ""
            tip = (tr("{name}  ({seconds:.1f} s{gain})\n{file}\nTrascina i bordi per tagliare inizio e fine (Shift: senza aggancio), doppio click per rinominare, tasto destro per altre azioni.", name=self.clip.name, seconds=seconds, gain=gain, file=self.clip.file))
        self.setToolTip(tip)

    def mouseDoubleClickEvent(self, event):
        self.view._rename_clip(self.track_name, self.clip)

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), BOX_CORNER_RADIUS, BOX_CORNER_RADIUS)
        rect = self.rect()
        if not self._missing:
            buckets = max(1, min(4000, int(rect.width() / 2)))
            peaks = audio_tracks.waveform_peaks(self.clip, buckets)
            if peaks is not None:
                mid = rect.center().y()
                half = rect.height() / 2 - 4
                step = rect.width() / buckets
                wave_color = QColor(_canvas_colors()["box_text"])
                wave_color.setAlpha(150)
                painter.setPen(QPen(wave_color, 1))
                for i, peak in enumerate(peaks):
                    x = rect.left() + (i + 0.5) * step
                    h = max(0.5, float(peak) * half)
                    painter.drawLine(QPointF(x, mid - h), QPointF(x, mid + h))
        if self.clip is self.view.selected_clip:
            sel_pen = QPen(QColor(ACCENT))
            sel_pen.setWidth(3)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), BOX_CORNER_RADIUS, BOX_CORNER_RADIUS)
        painter.setPen(QPen(QColor(_canvas_colors()["box_text"])))
        painter.setFont(QFont("Sans", 9, QFont.Bold))
        label = tr("{name}  (file mancante)", name=self.clip.name) if self._missing else self.clip.name
        painter.drawText(rect.adjusted(4, 2, -4, -2), Qt.AlignLeft | Qt.AlignTop | Qt.TextSingleLine, label)


# ---------------------------------------------------------------------------
# Canvas (QGraphicsView): righello + colonna nomi traccia disegnati nel
# viewport (non nella scena), cosi' restano "congelati" rispettivamente allo
# scroll verticale e orizzontale, come in un foglio di calcolo/DAW.
# ---------------------------------------------------------------------------

class ArrangementCanvas(QGraphicsView):
    def __init__(self, view: "ArrangementView"):
        super().__init__()
        self.view = view
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Necessario perche' il righello e la colonna nomi-traccia sono
        # ridisegnati "a mano" nel viewport (vedi paintEvent), fuori dal
        # normale tracciamento dei dirty-rect della scena: con la modalita'
        # di aggiornamento ottimizzata predefinita (che scorre/ricicla i
        # pixel gia' disegnati invece di ridisegnare tutto), lo scroll o lo
        # spostamento di un box trascinano con se' anche quei pixel "fissi"
        # gia' disegnati, lasciando scritte/righe residue ("sporcizia") dove
        # non vengono piu' ridisegnati nel giro successivo.
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        # Scena ancorata in alto a sinistra: con l'allineamento predefinito
        # (centrato) poche tracce finivano a meta' altezza, lontane dal
        # righello, con una fascia vuota sopra.
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.row_ys = {}          # track_name -> y (inizio riga, coordinate scena)
        self.beats_per_bar = 4.0
        self.meter_args = ("4/4", [], 0.0)      # metrica, cambi e levare del brano (righello)
        self._drag_guide_x = None  # x (coordinate scena) della linea guida durante un trascinamento
        self._playhead_beat = None  # beat corrente di riproduzione, None se non in esecuzione
        # Sezione del loop A-B da mostrare sul righello: (a, b) con b che puo'
        # essere None (solo A impostato), o None; e se il loop e' attivo.
        self._loop_region = None
        self._loop_active = False
        # Testate delle tracce: widget veri (pulsanti, volume) sopra la
        # colonna di sinistra del viewport, dentro un pannello che parte
        # sotto il righello (cosi' le righe che scorrono sotto il righello
        # vengono tagliate), riposizionati a ogni scorrimento verticale.
        self.header_panel = QWidget(self.viewport())
        self.header_widgets = {}
        self.add_track_btn = make_add_track_button(lambda menu: self.view.host.populate_add_track_menu(menu),
                                                   HEADER_WIDTH - 20, parent=self.header_panel)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self.layout_headers())

        # Al posto delle istruzioni fisse sopra il canvas: un "?" nell'angolo
        # sopra le testate (suggerimenti al passaggio del mouse, tutto al
        # click) e, nelle righe ancora vuote, un suggerimento in grigio.
        self.help_btn = QToolButton(self.viewport())
        self.help_btn.setText(tr("?  Come si usa"))
        self.help_btn.setGeometry(0, 0, HEADER_WIDTH, RULER_HEIGHT)
        self.help_btn.setStyleSheet("QToolButton { padding: 0px 10px; border: none; text-align: left; }")
        self.help_btn.setToolTip(HELP_TEXT)
        self.help_btn.clicked.connect(
            lambda: QMessageBox.information(self, tr("Struttura brano: come si usa"),
                                            HELP_TEXT + tr("\n\nGuida completa: Aiuto → Guida utente (F1).")))

    def refresh_add_button_icon(self):
        refresh_add_track_icon(self.add_track_btn)

    def _row_hint(self, track_name: str):
        """Suggerimento in grigio per una riga senza box (None se ne ha)."""
        try:
            track = self.view.host.project.get_track(track_name)
        except KeyError:
            return None
        if track.is_audio:
            return None if track.audio_clips else EMPTY_AUDIO_ROW_HINT
        if track.clips:
            return None
        return FREE_TEXT_ROW_HINT if track.text.strip() else EMPTY_ROW_HINT

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_headers()

    def layout_headers(self):
        """Allinea le testate alle righe (dopo scorrimento, ridimensionamento
        o ricostruzione della scena)."""
        vh = self.viewport().height()
        self.header_panel.setGeometry(0, RULER_HEIGHT, HEADER_WIDTH, max(0, vh - RULER_HEIGHT))
        bottom = 0
        for name, widget in self.header_widgets.items():
            y = self.row_ys.get(name)
            if y is None:
                continue
            top = self.mapFromScene(QPointF(0, y)).y() - RULER_HEIGHT
            widget.move(0, top)
            bottom = max(bottom, top + ROW_HEIGHT)
        if not self.header_widgets:
            bottom = self.mapFromScene(QPointF(0, RULER_HEIGHT)).y() - RULER_HEIGHT
        self.add_track_btn.move(10, bottom + 8)

    def set_drag_guide(self, scene_x: float | None):
        self._drag_guide_x = scene_x
        self.viewport().update()

    def set_playhead_beat(self, beat: float | None):
        """Aggiorna la posizione della testina di riproduzione disegnata in
        paintEvent (linea verticale che attraversa tutte le tracce, stesso
        beat per tutte visto che qui si segue la riproduzione dell'intero
        brano, non di un singolo box): None nasconde la linea (riproduzione
        ferma o non ancora avviata)."""
        self._playhead_beat = beat
        if beat is not None:
            self._autoscroll_to_playhead(HEADER_WIDTH + beat * PX_PER_BEAT)
        self.viewport().update()

    def set_loop_region(self, region, active: bool):
        self._loop_region = region
        self._loop_active = active
        self.viewport().update()

    def _autoscroll_to_playhead(self, scene_x: float):
        """Scorre il canvas in orizzontale quanto basta per tenere la
        testina sempre visibile, senza toccare lo scroll verticale (l'utente
        potrebbe star guardando tracce diverse da quella in cima): come nei
        DAW, si scorre solo quando la testina si avvicina al bordo del
        viewport, non ad ogni tick, cosi' il canvas segue la riproduzione
        invece di ricentrarla di continuo."""
        hbar = self.horizontalScrollBar()
        vw = self.viewport().width()
        viewport_x = self.mapFromScene(QPointF(scene_x, 0)).x()
        if viewport_x > vw - PLAYHEAD_EDGE_MARGIN:
            hbar.setValue(hbar.value() + (viewport_x - (vw - PLAYHEAD_EDGE_MARGIN)))
        elif viewport_x < HEADER_WIDTH + PLAYHEAD_EDGE_MARGIN:
            hbar.setValue(hbar.value() + (viewport_x - (HEADER_WIDTH + PLAYHEAD_EDGE_MARGIN)))

    @staticmethod
    def _over_fixed_area(view_pos) -> bool:
        """Vero se view_pos cade sul righello o sulla colonna dei nomi
        traccia: paintEvent li disegna in coordinate della finestra, fermi
        sopra la scena, quindi vanno cercati in quelle (non nella scena, che
        scorre) e hanno la precedenza sui box che scorrono sotto di loro."""
        return view_pos.x() < HEADER_WIDTH or view_pos.y() < RULER_HEIGHT

    def _track_and_beat_at(self, view_pos) -> tuple | None:
        if self._over_fixed_area(view_pos):
            return None
        scene_pos = self.mapToScene(view_pos)
        for name, y in self.row_ys.items():
            if y <= scene_pos.y() < y + ROW_HEIGHT:
                beat = max(0.0, (scene_pos.x() - HEADER_WIDTH) / PX_PER_BEAT)
                return name, beat
        return None

    def _track_at_header(self, view_pos) -> str | None:
        """Traccia il cui nome (l'etichetta 'a pillola' nella colonna a
        sinistra, vedi paintEvent) e' sotto view_pos, o None se il punto non
        cade nella colonna nomi-traccia."""
        if view_pos.x() >= HEADER_WIDTH or view_pos.y() < RULER_HEIGHT:
            return None
        scene_y = self.mapToScene(view_pos).y()
        for name, y in self.row_ys.items():
            if y <= scene_y < y + ROW_HEIGHT:
                return name
        return None

    def _box_at(self, view_pos):
        """Il box sotto view_pos, se visibile (non coperto da righello o
        colonna dei nomi)."""
        if self._over_fixed_area(view_pos):
            return None
        item = self.itemAt(view_pos)
        return item if isinstance(item, BoxItem) else None

    def wheelEvent(self, event):
        """Ctrl+rotellina: zoom orizzontale, tenendo fermo il beat sotto il
        mouse. Senza Ctrl: scorrimento normale."""
        if not event.modifiers() & Qt.ControlModifier:
            super().wheelEvent(event)
            return
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.view.zoom_by(ZOOM_STEP ** steps, anchor_view_x=event.position().x())
        event.accept()

    def mousePressEvent(self, event):
        view_pos = event.position().toPoint()
        if self._over_fixed_area(view_pos):
            if (event.button() == Qt.LeftButton and view_pos.y() < RULER_HEIGHT
                    and view_pos.x() >= HEADER_WIDTH):
                # Click sul righello: salta in quel punto del brano (agganciato al beat).
                scene_x = self.mapToScene(view_pos).x()
                self.view.host.seek_to_beat(float(round((scene_x - HEADER_WIDTH) / PX_PER_BEAT)))
            elif view_pos.y() >= RULER_HEIGHT:
                self.view.select_box(None, None)   # click sulla colonna dei nomi
            # Niente super(): non si afferra il box che scorre sotto.
            return
        if self._box_at(view_pos) is None:
            self.view.select_box(None, None)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        view_pos = event.position().toPoint()
        if self._over_fixed_area(view_pos):
            return
        item = self._box_at(view_pos)
        if item is not None:
            self.view.edit_box(item)
            return
        hit = self._track_and_beat_at(view_pos)
        if hit:
            track = self.view.host.project.get_track(hit[0])
            if track.is_audio:
                self.view.import_audio_clip(hit[0], _snap(hit[1]))
            elif not track.clips and track.text.strip():
                self.view.box_from_free_text(hit[0])
            else:
                self.view.new_box_at(hit[0], _snap(hit[1]))
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        header_track = self._track_at_header(event.pos())
        if header_track:
            self.view.show_track_menu(header_track, event.globalPos())
            return
        item = self._box_at(event.pos())
        if item is not None:
            self.view.show_box_menu(item, event.globalPos())
            return
        hit = self._track_and_beat_at(event.pos())
        if hit:
            self.view.show_empty_menu(hit[0], _snap(hit[1]), event.globalPos())

    def paintEvent(self, event):
        super().paintEvent(event)
        colors = _canvas_colors()
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        vw, vh = self.viewport().width(), self.viewport().height()

        # Righello (battute): congelato in verticale, scorre in orizzontale.
        painter.fillRect(0, 0, vw, RULER_HEIGHT, QColor(colors["ruler_bg"]))
        beat0_x = self.mapFromScene(QPointF(HEADER_WIDTH, 0)).x()
        pen = QPen(QColor(colors["border"]))
        painter.setPen(pen)
        painter.setFont(QFont("Sans", 8))
        # Le stanghette vere del brano: cambi di metrica e levare compresi
        # (con il levare, la battuta 0 comincia all'inizio del brano).
        time_sig, metrica_changes, pickup = self.meter_args
        starts = itertools.chain([(0, 0)] if pickup else [],
                                 zip(itertools.count(1), bar_starts(time_sig, metrica_changes, pickup)))
        for bar, start in starts:      # generatore infinito: si ferma al bordo della vista
            start = float(start)
            x = beat0_x + start * PX_PER_BEAT
            if x >= vw:
                break
            if x >= HEADER_WIDTH:
                painter.setPen(pen)
                painter.drawLine(int(x), 0, int(x), vh)
                painter.setPen(QColor(colors["text"]))
                painter.drawText(int(x) + 3, RULER_HEIGHT - 8, str(bar))

        # Loop A-B: fascia colorata sul righello (piena se attivo, tenue se
        # solo impostato) con i marcatori A e B.
        if self._loop_region is not None:
            a, b = self._loop_region
            ax = self.mapFromScene(QPointF(HEADER_WIDTH + a * PX_PER_BEAT, 0)).x()
            loop_color = QColor(ACCENT)
            if b is not None:
                bx = self.mapFromScene(QPointF(HEADER_WIDTH + b * PX_PER_BEAT, 0)).x()
                band = QColor(loop_color)
                band.setAlpha(110 if self._loop_active else 45)
                left = max(HEADER_WIDTH, ax)
                if bx > left:
                    painter.fillRect(int(left), 0, int(bx - left), RULER_HEIGHT, band)
            painter.setPen(QPen(loop_color, 2))
            for label, beat in (("A", a), ("B", b)):
                if beat is None:
                    continue
                mx = self.mapFromScene(QPointF(HEADER_WIDTH + beat * PX_PER_BEAT, 0)).x()
                if HEADER_WIDTH <= mx <= vw:
                    painter.drawLine(int(mx), 0, int(mx), RULER_HEIGHT)
                    painter.drawText(int(mx) + 3, 11, label)

        # Colonna nomi traccia: congelata in orizzontale, scorre in verticale.
        painter.fillRect(0, 0, HEADER_WIDTH, vh, QColor(colors["header_bg"]))
        for name, y in self.row_ys.items():
            top = self.mapFromScene(QPointF(0, y)).y()
            bottom = self.mapFromScene(QPointF(0, y + ROW_HEIGHT)).y()
            if bottom < RULER_HEIGHT or top > vh:
                continue
            clip_top = max(top, RULER_HEIGHT)
            # Nome, strumento e controlli della traccia sono i widget di
            # gui.track_header sopra questa fascia (vedi layout_headers).
            painter.fillRect(0, clip_top, HEADER_WIDTH, bottom - clip_top, QColor(colors["row_bg"]))
            hint = self._row_hint(name)
            if hint and top >= RULER_HEIGHT:
                painter.setPen(QColor(colors["text"]))
                painter.setFont(QFont("Sans", 9))
                painter.drawText(QRectF(HEADER_WIDTH + 14, top, vw - HEADER_WIDTH - 20, ROW_HEIGHT),
                                 Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, hint)
        if not self.row_ys:
            painter.setPen(QColor(colors["text"]))
            painter.setFont(QFont("Sans", 10))
            painter.drawText(QRectF(HEADER_WIDTH + 14, RULER_HEIGHT, vw - HEADER_WIDTH - 20, ROW_HEIGHT),
                             Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, NO_TRACKS_HINT)

        painter.fillRect(0, 0, HEADER_WIDTH, RULER_HEIGHT, QColor(colors["header_bg"]))
        painter.setPen(pen)
        painter.drawLine(HEADER_WIDTH, 0, HEADER_WIDTH, vh)
        painter.drawLine(0, RULER_HEIGHT, vw, RULER_HEIGHT)

        # Linea guida durante un trascinamento (vedi BoxItem.itemChange/
        # set_drag_guide): attraversa tutte le righe allo stesso beat, cosi'
        # allineare un box con uno di un'altra traccia e' immediato - lo
        # snap e' gia' "live" durante il trascinamento (non solo al
        # rilascio), quindi la linea coincide sempre con un beat esatto.
        if self._drag_guide_x is not None:
            gx = self.mapFromScene(QPointF(self._drag_guide_x, 0)).x()
            guide_pen = QPen(QColor(ACCENT))
            guide_pen.setWidth(2)
            painter.setPen(guide_pen)
            painter.drawLine(int(gx), RULER_HEIGHT, int(gx), vh)

        # Testina di riproduzione: stesso colore dell'evidenziazione del
        # token in esecuzione nell'editor di testo lineare (TEXT_DIM_INVERT_BG,
        # vedi gui.main_window_playback), cosi' le due viste comunicano lo
        # stesso concetto con lo stesso segnale visivo. Attraversa anche il
        # righello (a differenza della linea guida di trascinamento) per
        # restare visibile pure quando lo scroll verticale nasconde tutte le
        # righe delle tracce.
        if self._playhead_beat is not None:
            px = self.mapFromScene(QPointF(HEADER_WIDTH + self._playhead_beat * PX_PER_BEAT, 0)).x()
            if HEADER_WIDTH <= px <= vw:
                playhead_pen = QPen(QColor(TEXT_DIM_INVERT_BG))
                playhead_pen.setWidth(2)
                painter.setPen(playhead_pen)
                painter.drawLine(int(px), 0, int(px), vh)

        painter.end()


# ---------------------------------------------------------------------------
# Widget pubblico, integrato nel QStackedWidget centrale di MainWindow
# ---------------------------------------------------------------------------

class ArrangementView(QWidget):
    """host e' la MainWindow: si legge sempre host.project (sostituito per
    intero da nuovo/apri/importa) invece di tenerne una copia propria, e si
    usano host._mark_dirty()/host.statusBar() per restare coerenti col resto
    dell'app."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.host = host
        self._clipboard: Clip | None = None
        self._preview_playback = PlaybackEngine()
        # Stato di Play/Pausa dell'anteprima (vedi _toggle_play_selected):
        # _preview_start_wall e' impostato da _mark_preview_audio_started
        # (richiamato dal thread di riproduzione) nel momento in cui l'audio
        # inizia DAVVERO, stesso principio di gui.main_window_playback, per
        # calcolare correttamente il beat raggiunto quando si mette in
        # pausa. _previewing_clip/_preview_paused_clip tengono traccia di
        # QUALE box e' in pausa, cosi' selezionarne un altro e premere Play
        # riparte da capo invece di "riprendere" un box diverso.
        self._previewing_clip: Clip | None = None
        self._preview_start_wall = None
        self._preview_offset_beats = 0.0
        self._preview_paused_beat = None
        self._preview_paused_clip: Clip | None = None
        self._preview_status_timer = QTimer(self)
        self._preview_status_timer.setInterval(200)
        self._preview_status_timer.timeout.connect(self._check_preview_still_playing)
        # Box selezionato (evidenziato in BoxItem.paint): letto da
        # gui.main_window_mixer per far agire "Suona con la tastiera/Importa
        # audio/Importa MIDI (in questa)" sul box invece che sulla traccia,
        # quando un box e' selezionato - stesso Clip che vive in
        # track.clips, quindi resta valido attraverso un refresh() (che
        # ricrea i BoxItem ma non i Clip).
        self.selected_track_name: str | None = None
        self.selected_clip: Clip | None = None
        self._tempo_map_cache = None   # (chiave, mappa): vedi _tempo_map

        # Annulla/Ripeti delle azioni sui box: nessuna pila propria, ogni
        # modifica passa da host._mark_dirty (vedi on_clip_changed) ed entra
        # nella cronologia unica del progetto (core.history), comandata da
        # Ctrl+Z/Ctrl+Y del menu Modifica della finestra principale.

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Un solo trasporto: l'ascolto del box selezionato non ha piu' pulsanti
        # propri. Si avvia con Shift+Spazio (qui, cioe' con la vista
        # Struttura attiva: nell'editor di testo Shift+Spazio resta uno
        # spazio), dal menu Playback o dal menu del box; lo ferma lo Stop
        # della barra dei comandi (vedi gui.main_window_playback.stop).
        self.preview_action = QAction(PREVIEW_PLAY_TEXT, self)
        self.preview_action.setShortcut(QKeySequence("Shift+Space"))
        self.preview_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.preview_action.setToolTip(tr("Ascolta solo il box selezionato; di nuovo per la pausa (Shift+Spazio)."))
        self.preview_action.triggered.connect(self._toggle_play_selected)
        self.addAction(self.preview_action)

        self.canvas = ArrangementCanvas(self)
        layout.addWidget(self.canvas)

    # ------------------------------------------------------------ ciclo di vita

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def select_box(self, track_name: str | None, clip: Clip | None):
        self.selected_track_name = track_name
        self.selected_clip = clip
        self.canvas._scene.update()

    def selected_track(self):
        """Traccia che contiene DAVVERO il box selezionato, cercata per
        identita' del Clip e non per selected_track_name: il nome salvato
        alla selezione non e' affidabile (la traccia puo' essere stata
        rinominata nel frattempo), e un confronto per uguaglianza (Clip e'
        una dataclass) scambierebbe per "ancora presente" un box identico
        di un altro progetto o di uno stato ripristinato da Annulla.
        Aggiorna selected_track_name, o azzera la selezione se il box non
        appartiene piu' a nessuna traccia; None se non c'e' selezione."""
        if self.selected_clip is not None:
            for track in self.host.project.tracks:
                if any(c is self.selected_clip for c in track.clips + track.audio_clips):
                    self.selected_track_name = track.name
                    return track
        self.selected_track_name = None
        self.selected_clip = None
        return None

    def set_playhead_beat(self, beat: float | None):
        """Richiamato da gui.main_window_playback ad ogni tick della
        riproduzione principale (non quella di anteprima dei box), per
        seguire l'esecuzione dell'intero brano con una linea verticale nel
        canvas, indipendentemente da quale traccia sia quella selezionata."""
        self.canvas.set_playhead_beat(beat)

    def set_loop_region(self, region, active: bool = False):
        """Sezione del loop A-B della riproduzione principale da mostrare
        sul righello (vedi gui.main_window_playback): (a, b), (a, None) o None."""
        self.canvas.set_loop_region(region, active)

    def refresh(self):
        project = self.host.project
        scene = self.canvas._scene
        scene.clear()
        self.canvas.row_ys = {}

        # Se il box selezionato non esiste piu' (eliminato, o la sua traccia
        # e' stata rimossa) la selezione va sganciata, altrimenti "in
        # questa/o" (vedi gui.main_window_mixer) punterebbe a un Clip ormai
        # fuori da qualunque track.clips.
        self.selected_track()

        self.canvas.meter_args = (project.time_sig, list(project.metrica_changes), project.pickup)
        try:
            num, den = project.time_sig.split("/")
            self.canvas.beats_per_bar = int(num) * 4.0 / int(den)
        except (ValueError, ZeroDivisionError):
            self.canvas.beats_per_bar = 4.0

        max_beat = 0.0
        for t in project.tracks:
            for c in t.clips + t.audio_clips:
                max_beat = max(max_beat, c.start_beat + self.clip_length_beats(t.name, c))
        min_beats = MIN_SCENE_BARS * self.canvas.beats_per_bar
        scene_beats = max(max_beat + self.canvas.beats_per_bar * 4, min_beats)
        scene_width = HEADER_WIDTH + scene_beats * PX_PER_BEAT

        y = RULER_HEIGHT
        for t in project.tracks:
            self.canvas.row_ys[t.name] = y
            for clip in t.clips:
                item = BoxItem(self, t.name, clip, y + 5)
                scene.addItem(item)
            for clip in t.audio_clips:
                scene.addItem(AudioBoxItem(self, t.name, clip, y + 5))
            y += ROW_HEIGHT + ROW_GAP

        # spazio sotto l'ultima riga per il pulsante "Aggiungi traccia"
        scene_height = max(y + 50, RULER_HEIGHT + ROW_HEIGHT)
        scene.setSceneRect(0, 0, scene_width, scene_height)
        self.canvas.setBackgroundBrush(QColor(_canvas_colors()["bg"]))
        self._rebuild_headers()
        self.canvas.refresh_add_button_icon()

    def _rebuild_headers(self):
        """Ricrea le testate delle tracce. Le vecchie si cancellano con
        deleteLater: refresh() puo' arrivare mentre si sta ancora gestendo
        un evento di una di loro (doppio click -> rinomina, menu ⋯ -> azione)."""
        canvas = self.canvas
        for widget in canvas.header_widgets.values():
            widget.hide()
            widget.deleteLater()
        canvas.header_widgets = {}
        for t in self.host.project.tracks:
            header = TrackHeaderWidget(self.host, t, HEADER_WIDTH, ROW_HEIGHT, self.show_track_menu,
                                       on_select=self._select_track_from_header, parent=canvas.header_panel)
            header.show()
            canvas.header_widgets[t.name] = header
        self.set_active_track(getattr(self.host, "current_track_name", None))
        canvas.layout_headers()

    def set_active_track(self, track_name):
        for name, header in self.canvas.header_widgets.items():
            header.set_active(name == track_name)

    def sync_track_header(self, track_name):
        header = self.canvas.header_widgets.get(track_name)
        if header is not None:
            header.sync_from_track()

    # ------------------------------------------------------------ modifica dei box

    def on_clip_changed(self, track_name: str):
        track = self.host.project.get_track(track_name)
        if not track.is_audio:
            track.text = flatten_clips_to_text(track.clips, self.host.project.patterns,
                                                track.instrument.default_octave,
                                                meter=self.host.project.meter())
        self.host._mark_dirty()
        # Il ricalcolo della scena (self.refresh(), piu' sotto) distrugge e
        # ricrea tutti i BoxItem, incluso l'eventuale item la cui gestione
        # evento (mouseReleaseEvent/doppio click su un box, azione di un menu
        # aperto da un item) e' ancora sullo stack di chiamata qui sopra:
        # rifarlo SUBITO farebbe scomparire da sotto i piedi a Qt l'oggetto
        # C++ dell'item corrente prima che la sua gestione evento sia
        # davvero conclusa - stessa classe di crash gia' incontrata e
        # corretta altrove nel progetto per il mixer (vedi refresh_mixer).
        # Rimandarlo al giro successivo del loop eventi lo rende sicuro.
        QTimer.singleShot(0, lambda: self._finish_clip_change(track_name))

    def _finish_clip_change(self, track_name: str):
        self.refresh()
        if self.host.current_track_name == track_name and hasattr(self.host, "select_track"):
            self.host.select_track(track_name)

    # ------------------------------------------------------------ undo/redo

    def undo(self):
        self.host.undo()

    def redo(self):
        self.host.redo()

    def resolve_free_slot(self, track_name: str, clip: Clip, desired_beat: float) -> float:
        """Trova la posizione libera (nessuna sovrapposizione con altri box
        della stessa traccia) piu' vicina a desired_beat: se desired_beat non
        si sovrappone a nulla resta invariata, altrimenti si prova ad
        agganciare al bordo del vuoto libero piu' vicino."""
        track = self.host.project.get_track(track_name)
        duration = self.clip_length_beats(track_name, clip)
        desired_beat = max(0.0, desired_beat)

        siblings = track.audio_clips if track.is_audio else track.clips
        others = sorted((c for c in siblings if c is not clip), key=lambda c: c.start_beat)
        other_durations = {id(o): self.clip_length_beats(track_name, o) for o in others}

        def overlaps(beat):
            for o in others:
                o_dur = other_durations[id(o)]
                if beat < o.start_beat + o_dur and beat + duration > o.start_beat:
                    return True
            return False

        if not overlaps(desired_beat):
            return desired_beat

        candidates = []
        cursor = 0.0
        for o in others:
            o_dur = other_durations[id(o)]
            gap_start, gap_end = cursor, o.start_beat
            if gap_end - gap_start >= duration - 1e-9:
                candidates.append(min(max(desired_beat, gap_start), gap_end - duration))
            cursor = max(cursor, o.start_beat + o_dur)
        candidates.append(max(desired_beat, cursor))
        return min(candidates, key=lambda b: abs(b - desired_beat))

    def _tempo_map(self):
        """Mappa del tempo del brano (come in riproduzione), ricalcolata
        solo quando cambia qualcosa che la influenza: serve per ogni clip
        audio a ogni ridisegno, e ricavarla riparsa tutte le tracce."""
        project = self.host.project
        key = (project.tempo_bpm, project.time_sig, tuple(project.tempo_changes),
               tuple(project.metrica_changes),
               tuple((t.text, t.mute, t.solo) for t in project.tracks),
               tuple((n, tuple(p.tokens)) for n, p in project.patterns.items()))
        if self._tempo_map_cache is None or self._tempo_map_cache[0] != key:
            self._tempo_map_cache = (key, build_tempo_beat_map(project))
        return self._tempo_map_cache[1]

    def clip_length_beats(self, track_name: str, clip) -> float:
        """Durata in beat di un box: dalla notazione per un Clip, dal file
        (alla posizione della clip, vedi core.audio_tracks) per un AudioClip."""
        project = self.host.project
        if isinstance(clip, AudioClip):
            return audio_tracks.clip_duration_beats(clip, self._tempo_map())
        track = project.get_track(track_name)
        return clip_duration_beats(clip.text, project.patterns, track.instrument.default_octave,
                                   start_beat=clip.start_beat, meter=project.meter())

    def edit_box(self, item: BoxItem):
        if isinstance(item, AudioBoxItem):
            self._rename_clip(item.track_name, item.clip)
            return
        clip = item.clip
        track = self.host.project.get_track(item.track_name)
        dlg = BoxEditDialog(self, self.host.project, track.instrument_name, self.host.project.tempo_bpm,
                             clip_name=clip.name, clip_text=clip.text, title=tr("Modifica box — {name}", name=track.name),
                             start_beat=clip.start_beat, track_name=track.name)
        if dlg.exec() != BoxEditDialog.Accepted:
            return
        clip.name = dlg.result_name()
        clip.text = dlg.result_text()
        self.on_clip_changed(item.track_name)

    def edit_free_text(self, track_name: str):
        """Modifica il testo di una traccia senza box (testo libero) con lo
        stesso editor dei box: evidenziazione, Play, Play della selezione."""
        track = self.host.project.get_track(track_name)
        dlg = BoxEditDialog(self, self.host.project, track.instrument_name, self.host.project.tempo_bpm,
                             clip_text=track.text, title=tr("Testo libero — {name}", name=track.name), with_name=False,
                             track_name=track.name)
        if dlg.exec() != BoxEditDialog.Accepted or dlg.result_text() == track.text.strip():
            return
        track.text = dlg.result_text()
        self.host._mark_dirty()
        QTimer.singleShot(0, lambda: self._finish_clip_change(track_name))

    def box_from_free_text(self, track_name: str):
        """Doppio clic su una traccia con testo ma ancora senza box: il box
        si apre gia' riempito con quel testo e, confermato, lo sostituisce
        partendo da 0 (dove il testo libero suonava gia')."""
        track = self.host.project.get_track(track_name)
        dlg = BoxEditDialog(self, self.host.project, track.instrument_name, self.host.project.tempo_bpm,
                             clip_name=track.name, clip_text=track.text,
                             title=tr("Nuovo box — {name}", name=track.name), track_name=track.name)
        if dlg.exec() != BoxEditDialog.Accepted or not dlg.result_text().strip():
            return
        track.clips = [Clip(name=dlg.result_name(), text=dlg.result_text(), start_beat=0.0)]
        self.on_clip_changed(track_name)

    def new_box_at(self, track_name: str, beat: float):
        track = self.host.project.get_track(track_name)
        dlg = BoxEditDialog(self, self.host.project, track.instrument_name, self.host.project.tempo_bpm,
                             title=tr("Nuovo box — {name}", name=track.name), start_beat=_snap(beat),
                             track_name=track.name)
        if dlg.exec() != BoxEditDialog.Accepted:
            return
        clip = Clip(name=dlg.result_name(), text=dlg.result_text(), start_beat=beat)
        self._wrap_free_text_in_box(track)
        clip.start_beat = _snap(self.resolve_free_slot(track_name, clip, beat))
        track.clips.append(clip)
        self.on_clip_changed(track_name)

    def new_box_from_keyboard_at(self, track_name: str, beat: float):
        track = self.host.project.get_track(track_name)
        dlg = KeyboardPlayDialog(self, project=self.host.project, instrument_name=track.instrument_name,
                                  context_label=tr("nuovo box (traccia '{name}')", name=track.name),
                                  current_track_name=track.name)
        accepted = dlg.exec() == KeyboardPlayDialog.Accepted
        self.host._sync_tempo_metrica_fields()
        if not accepted:
            return
        self._create_box_from_recorded_text(track_name, beat, dlg.result_text())

    def new_box_from_audio_at(self, track_name: str, beat: float):
        track = self.host.project.get_track(track_name)
        dlg = AudioImportDialog(self, project=self.host.project, instrument_name=track.instrument_name,
                                 context_label=tr("nuovo box (traccia '{name}')", name=track.name),
                                 track_name=track.name)
        accepted = dlg.exec() == AudioImportDialog.Accepted
        # Il dialogo puo' aver cambiato Tempo/Metrica del progetto (stesso
        # oggetto condiviso) anche se poi annullato: i campi in toolbar
        # vanno comunque riallineati (stessa convenzione di
        # gui.main_window_mixer.import_audio_into_selected_track).
        self.host._sync_tempo_metrica_fields()
        if not accepted:
            return
        self._create_box_from_recorded_text(track_name, beat, dlg.result_text())

    def new_box_from_midi_at(self, track_name: str, beat: float):
        track = self.host.project.get_track(track_name)
        result = self.host._pick_midi_channel_tokens()
        if result is None:
            return
        tokens_text, guessed_instrument, newly_created = result
        self.host._maybe_update_instrument_from_midi(track, guessed_instrument)
        self.host._notify_new_instruments(newly_created)
        self._create_box_from_recorded_text(track_name, beat, tokens_text)

    def _wrap_free_text_in_box(self, track):
        """Una traccia scritta a testo libero (senza box) che riceve il suo
        primo box: il testo gia' scritto diventa a sua volta un box, invece
        di essere sostituito dal testo ricalcolato dai soli box nuovi."""
        if not track.is_audio and not track.clips and track.text.strip():
            track.clips = [Clip(name=track.name, text=track.text, start_beat=0.0)]

    def _create_box_from_recorded_text(self, track_name: str, beat: float, text: str):
        name, ok = QInputDialog.getText(self, tr("Nome del nuovo box"), tr("Nome:"), text=tr("Box"))
        name = name.strip()
        if not ok or not name:
            return
        self._wrap_free_text_in_box(self.host.project.get_track(track_name))
        clip = Clip(name=name, text=text, start_beat=beat)
        clip.start_beat = _snap(self.resolve_free_slot(track_name, clip, beat))
        self.host.project.get_track(track_name).clips.append(clip)
        self.on_clip_changed(track_name)

    @staticmethod
    def _is_bass_instrument(instrument) -> bool:
        return not instrument.is_percussion and gm_family_for_program(instrument.gm_program) == "Bassi"

    def _offers_chord_progression(self, track_name: str, instrument) -> bool:
        """'Genera giro armonico' solo per uno strumento da accordi e finche'
        nessun'ALTRA traccia ha gia' accordi da seguire (li' servono basso e
        accompagnamento, che quegli accordi li leggono). La traccia che il
        giro ce l'ha gia' continua a offrirlo, per accodarne altri box."""
        return (instrument.polyphonic and not instrument.is_percussion
                and not self._is_bass_instrument(instrument)
                and not project_has_chords(self.host.project, exclude_track_name=track_name))

    def _offers_melody(self, track_name: str, instrument) -> bool:
        """'Genera accompagnamento' / 'Genera riff/melodia' solo quando
        un'altra traccia ha gia' accordi da seguire: senza, il dialogo non
        avrebbe niente da generare."""
        return (not instrument.is_percussion and not self._is_bass_instrument(instrument)
                and project_has_chords(self.host.project, exclude_track_name=track_name))

    def _select_track_from_header(self, track_name: str):
        self.select_box(None, None)
        if hasattr(self.host, "select_track"):
            self.host.select_track(track_name)

    def show_track_menu(self, track_name: str, global_pos):
        track = self.host.project.get_track(track_name)
        if track.is_audio:
            menu = QMenu(self)
            record_action = menu.addAction(tr("● Registra..."))
            import_action = menu.addAction(tr("Importa file audio..."))
            menu.addSeparator()
            rename_action = menu.addAction(tr("Rinomina traccia..."))
            menu.addSeparator()
            export_wav_action = menu.addAction(tr("Esporta WAV (solo questa)..."))
            export_dry_action = menu.addAction(tr("Esporta WAV asciutto (per il re-amping)..."))
            menu.addSeparator()
            remove_action = menu.addAction(tr("Rimuovi traccia"))
            chosen = menu.exec(global_pos)
            if chosen is record_action:
                self.host.record_into_audio_track(track_name)
            elif chosen is import_action:
                self.import_audio_clip(track_name, self.end_of_track_beat(track_name))
            elif chosen is rename_action:
                self.host._open_edit_dialog_for(track_name)
            elif chosen is export_wav_action:
                self.host.export_track_wav(track_name)
            elif chosen is export_dry_action:
                self.host.export_track_wav(track_name, dry=True)
            elif chosen is remove_action:
                self._remove_track(track_name)
            return
        instrument = track.instrument
        is_bass = self._is_bass_instrument(instrument)
        menu = QMenu(self)
        generate_drums_action = menu.addAction(tr("Genera batteria...")) if instrument.is_percussion else None
        generate_bass_action = menu.addAction(tr("Genera basso da accordi...")) if is_bass else None
        generate_progression_action = menu.addAction(tr("Genera giro armonico...")) \
            if self._offers_chord_progression(track_name, instrument) else None
        generate_melody_action = None
        if self._offers_melody(track_name, instrument):
            label = tr("Genera accompagnamento...") if instrument.polyphonic else tr("Genera riff/melodia...")
            generate_melody_action = menu.addAction(label)
        if any(a is not None for a in (generate_drums_action, generate_bass_action,
                                        generate_progression_action, generate_melody_action)):
            menu.addSeparator()
        keyboard_action = menu.addAction(tr("Suona con la tastiera..."))
        import_midi_action = menu.addAction(tr("Importa MIDI..."))
        import_audio_action = menu.addAction(tr("Importa audio → note..."))
        menu.addSeparator()
        edit_action = menu.addAction(tr("Nome e strumento..."))
        synth_action = menu.addAction(tr("Strumento plugin (VST3/LV2)..."))
        synth_params_action = menu.addAction(tr("Parametri dello strumento plugin...")) if track.synth else None
        export_action = menu.addAction(tr("Esporta MIDI (solo questa)..."))
        export_wav_action = menu.addAction(tr("Esporta WAV (solo questa)..."))
        export_dry_action = menu.addAction(tr("Esporta WAV asciutto (per il re-amping)..."))
        menu.addSeparator()
        remove_action = menu.addAction(tr("Rimuovi traccia"))
        menu.addSeparator()
        if track.clips:
            convert_action = menu.addAction(tr("Converti in testo libero..."))
            free_text_action = None
        else:
            # Traccia in testo libero: nella vista a box non si vede, la si
            # modifica da qui senza uscire dalla vista.
            convert_action = None
            free_text_action = menu.addAction(tr("Modifica testo libero..."))

        chosen = menu.exec(global_pos)
        if chosen in (keyboard_action, import_midi_action, import_audio_action):
            # Le azioni "in questa" agiscono sul box selezionato, se c'e':
            # dal menu della traccia devono agire sulla traccia.
            self.select_box(None, None)
            self.host.select_track(track_name)
            {keyboard_action: self.host.play_keyboard_into_selected_track,
             import_midi_action: self.host.import_midi_into_selected_track,
             import_audio_action: self.host.import_audio_into_selected_track}[chosen]()
            return
        if chosen is edit_action:
            self.host._open_edit_dialog_for(track_name)
            return
        if chosen is synth_action:
            self.host.choose_track_synth(track_name)
            return
        if synth_params_action is not None and chosen is synth_params_action:
            self.host.edit_track_synth(track_name)
            return
        if chosen is remove_action:
            self._remove_track(track_name)
            return
        if generate_drums_action is not None and chosen is generate_drums_action:
            self._generate_drums_for_new_box(track_name)
        elif generate_bass_action is not None and chosen is generate_bass_action:
            self._generate_bass_for_new_box(track_name)
        elif generate_progression_action is not None and chosen is generate_progression_action:
            self._generate_progression_for_new_box(track_name)
        elif generate_melody_action is not None and chosen is generate_melody_action:
            self._generate_melody_for_new_box(track_name)
        elif chosen is export_action:
            # Riusa la validazione/il dialogo di salvataggio gia' esistenti
            # (gui.main_window_mixer.export_selected_track_midi), che
            # operano su self.host.current_track_name: selezionare prima la
            # traccia allinea anche l'editor classico a quella su cui si e'
            # fatto tasto destro qui.
            self.host.select_track(track_name)
            self.host.export_selected_track_midi()
        elif chosen is export_wav_action:
            self.host.export_track_wav(track_name)
        elif chosen is export_dry_action:
            self.host.export_track_wav(track_name, dry=True)
        elif convert_action is not None and chosen is convert_action:
            self._convert_to_free_text(track_name)
        elif free_text_action is not None and chosen is free_text_action:
            self.edit_free_text(track_name)

    def _remove_track(self, track_name: str):
        self.select_box(None, None)
        self.host.select_track(track_name)
        self.host.remove_track()

    def end_of_track_beat(self, track_name: str) -> float:
        """Beat subito dopo l'ultimo box della traccia (0.0 se non ne ha
        ancora nessuno): dove viene accodato un box generato da questo
        menu, analogamente a come 'Genera batteria/basso in questa traccia'
        accoda il testo generato alla fine del testo gia' presente
        (gui.main_window_mixer._append_or_replace_track_text)."""
        track = self.host.project.get_track(track_name)
        clips = track.audio_clips if track.is_audio else track.clips
        if not clips:
            return 0.0
        return max(c.start_beat + self.clip_length_beats(track_name, c) for c in clips)

    def _generate_drums_for_new_box(self, track_name: str):
        track = self.host.project.get_track(track_name)
        if not track.instrument.is_percussion:
            QMessageBox.information(
                self, tr("Traccia non percussiva"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', non percussivo.\nSeleziona (o crea) una traccia con uno strumento a percussione (es. Drums).", name=track.name, instrument_name=track.instrument_name)
            )
            return
        dlg = DrumGenerateDialog(self, project=self.host.project, instrument_name=track.instrument_name,
                                  context_label=tr("nuovo box (traccia '{name}')", name=track.name), default_bars=4,
                                  track_name=track.name)
        if dlg.exec() != DrumGenerateDialog.Accepted:
            return
        self._create_box_from_recorded_text(track_name, self.end_of_track_beat(track_name), dlg.result_text())

    def _generate_bass_for_new_box(self, track_name: str):
        track = self.host.project.get_track(track_name)
        other_tracks = [(t.name, t.text) for t in self.host.project.tracks
                        if t.name != track_name and not t.is_audio]
        if not other_tracks:
            QMessageBox.information(
                self, tr("Nessuna traccia sorgente"),
                tr("Serve un'altra traccia con degli accordi scritti da cui far derivare il basso.")
            )
            return
        dlg = BassGenerateDialog(self, project=self.host.project, instrument_name=track.instrument_name,
                                  context_label=tr("nuovo box (traccia '{name}')", name=track.name), other_tracks=other_tracks,
                                  track_name=track.name)
        if dlg.exec() != BassGenerateDialog.Accepted:
            return
        self._create_box_from_recorded_text(track_name, self.end_of_track_beat(track_name), dlg.result_text())

    def _generate_melody_for_new_box(self, track_name: str):
        track = self.host.project.get_track(track_name)
        other_tracks = [(t.name, t.text) for t in self.host.project.tracks
                        if t.name != track_name and not t.is_audio]
        if not other_tracks:
            QMessageBox.information(
                self, tr("Nessuna traccia sorgente"),
                tr("Serve un'altra traccia con degli accordi scritti da cui far derivare "
                "l'accompagnamento o il riff.")
            )
            return
        instrument = track.instrument
        dlg = MelodyGenerateDialog(
            self, project=self.host.project, instrument_name=track.instrument_name,
            context_label=tr("nuovo box (traccia '{name}')", name=track.name), other_tracks=other_tracks,
            polyphonic=instrument.polyphonic, default_octave=instrument.default_octave,
            range_low=instrument.range_low, range_high=instrument.range_high,
            default_bars=4, track_name=track.name,
        )
        if dlg.exec() != MelodyGenerateDialog.Accepted:
            return
        self._create_box_from_recorded_text(track_name, self.end_of_track_beat(track_name), dlg.result_text())

    def _generate_progression_for_new_box(self, track_name: str):
        track = self.host.project.get_track(track_name)
        # Di default copre la musica gia' scritta nelle altre tracce; se non
        # c'e' ancora niente, il giro una volta sola (0 = "Giro intero").
        other_beats = tracks_duration_beats(self.host.project, exclude_track_name=track_name)
        default_bars = round(other_beats / project_bar_beats(self.host.project)) if other_beats > 0 else 0
        dlg = ChordProgressionDialog(
            self, project=self.host.project, instrument_name=track.instrument_name,
            context_label=tr("nuovo box (traccia '{name}')", name=track.name), default_bars=default_bars,
            track_name=track.name, default_key=last_box_key(self.host.project, track),
        )
        if dlg.exec() != ChordProgressionDialog.Accepted:
            return
        self._create_box_from_recorded_text(track_name, self.end_of_track_beat(track_name), dlg.result_text())

    def show_box_menu(self, item: BoxItem, global_pos):
        clip = item.clip
        track_name = item.track_name
        if isinstance(item, AudioBoxItem):
            scene_x = self.canvas.mapToScene(self.canvas.viewport().mapFromGlobal(global_pos)).x()
            at_beat = round(max(0.0, (scene_x - HEADER_WIDTH) / PX_PER_BEAT) / TRIM_SNAP_BEATS) * TRIM_SNAP_BEATS
            self._show_audio_box_menu(track_name, clip, global_pos, at_beat)
            return
        menu = QMenu(self)
        play_action = menu.addAction(tr("▶ Play"))
        stop_action = menu.addAction(tr("■ Stop"))
        transpose_action = menu.addAction(tr("Trasponi..."))
        rename_action = menu.addAction(tr("Rinomina..."))
        duplicate_action = menu.addAction(tr("Duplica"))
        menu.addSeparator()
        cut_action = menu.addAction(tr("Taglia"))
        copy_action = menu.addAction(tr("Copia"))
        paste_action = menu.addAction(tr("Incolla qui")) if isinstance(self._clipboard, Clip) else None
        menu.addSeparator()
        export_action = menu.addAction(tr("Esporta come .box..."))
        save_style_action = menu.addAction(tr("Salva come stile del generatore..."))
        menu.addSeparator()
        delete_action = menu.addAction(tr("Elimina"))

        chosen = menu.exec(global_pos)
        if chosen is play_action:
            self._play_clip(track_name, clip)
        elif chosen is save_style_action:
            self._save_clip_as_style(track_name, clip)
        elif chosen is stop_action:
            self._stop_preview()
        elif chosen is transpose_action:
            self._transpose_clip(track_name, clip)
        elif chosen is rename_action:
            self._rename_clip(track_name, clip)
        elif chosen is duplicate_action:
            self._duplicate_clip(track_name, clip)
        elif chosen is cut_action:
            self._clipboard = dataclasses.replace(clip)
            track = self.host.project.get_track(track_name)
            track.clips.remove(clip)
            self.on_clip_changed(track_name)
        elif chosen is copy_action:
            self._clipboard = dataclasses.replace(clip)
        elif paste_action is not None and chosen is paste_action:
            self.paste_at(track_name, clip.start_beat)
        elif chosen is export_action:
            self._export_clip(clip)
        elif chosen is delete_action:
            track = self.host.project.get_track(track_name)
            track.clips.remove(clip)
            self.on_clip_changed(track_name)

    def _save_clip_as_style(self, track_name: str, clip: Clip):
        """Salva come stile del generatore il contenuto di un box (vedi
        gui.save_style_dialog): gli accordi si leggono dalle altre tracce,
        nel punto del brano in cui si trova il box."""
        from .save_style_dialog import SaveStyleDialog, chord_sources_of, source_for_part
        project = self.host.project
        track = project.get_track(track_name)
        source = source_for_part(tr("box '{name}'", name=clip.name), clip.text, track.instrument, offset_beats=clip.start_beat)
        dlg = SaveStyleDialog(self, [source], chord_sources_of(project, track_name), project.patterns,
                              meter=project.time_sig)
        if dlg.exec() == SaveStyleDialog.Accepted and dlg.saved_style() and hasattr(self.host, "statusBar"):
            self.host.statusBar().showMessage(tr("Stile «{0}» salvato fra gli stili personali.", dlg.saved_style()[1]), 4000)

    def _show_audio_box_menu(self, track_name: str, clip: AudioClip, global_pos, at_beat=None):
        missing = audio_tracks.clip_is_missing(clip)
        menu = QMenu(self)
        play_action = menu.addAction(tr("▶ Play"))
        stop_action = menu.addAction(tr("■ Stop"))
        rename_action = menu.addAction(tr("Rinomina..."))
        gain_action = menu.addAction(tr("Guadagno clip (dB)..."))
        trim_action = menu.addAction(tr("Taglio preciso (secondi)...")) if not missing else None
        split_action = None
        if not missing and at_beat is not None and at_beat > clip.start_beat:
            split_action = menu.addAction(tr("Dividi qui (beat {at_beat:g})", at_beat=at_beat))
        duplicate_action = menu.addAction(tr("Duplica"))
        convert_action = menu.addAction(tr("Converti in notazione...")) if not missing else None
        relink_action = menu.addAction(tr("Ritrova file...")) if missing else None
        menu.addSeparator()
        cut_action = menu.addAction(tr("Taglia"))
        copy_action = menu.addAction(tr("Copia"))
        paste_action = menu.addAction(tr("Incolla qui")) if isinstance(self._clipboard, AudioClip) else None
        menu.addSeparator()
        delete_action = menu.addAction(tr("Elimina"))

        chosen = menu.exec(global_pos)
        track = self.host.project.get_track(track_name)
        if chosen is play_action:
            self._play_clip(track_name, clip)
        elif chosen is stop_action:
            self._stop_preview()
        elif chosen is rename_action:
            self._rename_clip(track_name, clip)
        elif chosen is gain_action:
            self._set_clip_gain(track_name, clip)
        elif trim_action is not None and chosen is trim_action:
            self._edit_clip_trim(track_name, clip)
        elif split_action is not None and chosen is split_action:
            self._split_clip(track_name, clip, at_beat)
        elif chosen is duplicate_action:
            self._duplicate_clip(track_name, clip)
        elif convert_action is not None and chosen is convert_action:
            self._convert_clip_to_notation(track_name, clip)
        elif relink_action is not None and chosen is relink_action:
            self._relink_clip(track_name, clip)
        elif chosen is cut_action:
            self._clipboard = dataclasses.replace(clip)
            track.audio_clips.remove(clip)
            self.on_clip_changed(track_name)
        elif chosen is copy_action:
            self._clipboard = dataclasses.replace(clip)
        elif paste_action is not None and chosen is paste_action:
            self.paste_at(track_name, clip.start_beat)
        elif chosen is delete_action:
            track.audio_clips.remove(clip)
            self.on_clip_changed(track_name)

    def _show_audio_empty_menu(self, track_name: str, beat: float, global_pos):
        menu = QMenu(self)
        record_action = menu.addAction(tr("● Registra da qui..."))
        import_action = menu.addAction(tr("Importa file audio qui..."))
        paste_action = menu.addAction(tr("Incolla qui")) if isinstance(self._clipboard, AudioClip) else None
        chosen = menu.exec(global_pos)
        if chosen is record_action:
            self.host.record_into_audio_track(track_name, start_beat=beat)
        elif chosen is import_action:
            self.import_audio_clip(track_name, beat)
        elif paste_action is not None and chosen is paste_action:
            self.paste_at(track_name, beat)

    def show_empty_menu(self, track_name: str, beat: float, global_pos):
        track = self.host.project.get_track(track_name)
        if track.is_audio:
            self._show_audio_empty_menu(track_name, beat, global_pos)
            return
        instrument = track.instrument
        is_bass = self._is_bass_instrument(instrument)
        menu = QMenu(self)
        new_action = menu.addAction(tr("Nuovo box qui"))
        new_keyboard_action = menu.addAction(tr("Nuovo box da tastiera qui"))
        new_audio_action = menu.addAction(tr("Nuovo box da audio qui"))
        new_midi_action = menu.addAction(tr("Importa MIDI qui"))
        paste_action = menu.addAction(tr("Incolla qui")) if isinstance(self._clipboard, Clip) else None
        # Stesse azioni disponibili dal tasto destro sull'etichetta della
        # traccia (show_track_menu): qui accessibili anche cliccando in un
        # punto vuoto della riga, non solo sulla stretta colonna nomi a
        # sinistra, dove intuitivamente ci si aspetta di trovarle lo stesso.
        generate_drums_action = menu.addAction(tr("Genera batteria in questa traccia...")) \
            if instrument.is_percussion else None
        generate_bass_action = menu.addAction(tr("Genera basso da accordi in questa traccia...")) \
            if is_bass else None
        generate_progression_action = menu.addAction(tr("Genera giro armonico in questa traccia...")) \
            if self._offers_chord_progression(track_name, instrument) else None
        generate_melody_action = None
        if self._offers_melody(track_name, instrument):
            label = tr("Genera accompagnamento in questa traccia...") if instrument.polyphonic \
                else tr("Genera riff/melodia in questa traccia...")
            generate_melody_action = menu.addAction(label)
        import_action = menu.addAction(tr("Importa da .box..."))

        chosen = menu.exec(global_pos)
        if chosen is new_action:
            self.new_box_at(track_name, beat)
        elif chosen is new_keyboard_action:
            self.new_box_from_keyboard_at(track_name, beat)
        elif chosen is new_audio_action:
            self.new_box_from_audio_at(track_name, beat)
        elif chosen is new_midi_action:
            self.new_box_from_midi_at(track_name, beat)
        elif paste_action is not None and chosen is paste_action:
            self.paste_at(track_name, beat)
        elif generate_drums_action is not None and chosen is generate_drums_action:
            self._generate_drums_for_new_box(track_name)
        elif generate_bass_action is not None and chosen is generate_bass_action:
            self._generate_bass_for_new_box(track_name)
        elif generate_progression_action is not None and chosen is generate_progression_action:
            self._generate_progression_for_new_box(track_name)
        elif generate_melody_action is not None and chosen is generate_melody_action:
            self._generate_melody_for_new_box(track_name)
        elif chosen is import_action:
            self._import_clip(track_name, beat)

    # ------------------------------------------------------------ azioni

    # ------------------------------------------------------------ zoom

    def set_zoom(self, px_per_beat: float, anchor_view_x: float | None = None):
        """Scala orizzontale del canvas (pixel per beat). anchor_view_x: il
        punto del viewport che deve restare sullo stesso beat (il mouse, per
        Ctrl+rotellina); None = il bordo sinistro dell'area dei box."""
        global PX_PER_BEAT
        px_per_beat = max(MIN_PX_PER_BEAT, min(MAX_PX_PER_BEAT, px_per_beat))
        if abs(px_per_beat - PX_PER_BEAT) < 1e-9:
            return
        canvas = self.canvas
        if anchor_view_x is None:
            anchor_view_x = HEADER_WIDTH
        anchor_beat = (canvas.mapToScene(int(anchor_view_x), 0).x() - HEADER_WIDTH) / PX_PER_BEAT
        PX_PER_BEAT = px_per_beat
        self.refresh()
        target_x = canvas.mapFromScene(QPointF(HEADER_WIDTH + anchor_beat * PX_PER_BEAT, 0)).x()
        hbar = canvas.horizontalScrollBar()
        hbar.setValue(int(hbar.value() + target_x - anchor_view_x))
        canvas.viewport().update()
        self.host.statusBar().showMessage(tr("Zoom: {0:.0%}", PX_PER_BEAT / DEFAULT_PX_PER_BEAT), 2000)

    def zoom_by(self, factor: float, anchor_view_x: float | None = None):
        self.set_zoom(PX_PER_BEAT * factor, anchor_view_x)

    def zoom_in(self):
        self.zoom_by(ZOOM_STEP)

    def zoom_out(self):
        self.zoom_by(1 / ZOOM_STEP)

    def zoom_reset(self):
        self.set_zoom(DEFAULT_PX_PER_BEAT)

    # ------------------------------------------------------------ azioni da tastiera sul box selezionato

    def _selected_or_explain(self):
        track = self.selected_track()
        if track is None:
            self.host.statusBar().showMessage(tr("Seleziona prima un box (clic sul box)."), 4000)
        return track

    def delete_selected_box(self):
        track = self._selected_or_explain()
        if track is None:
            return
        clip = self.selected_clip
        (track.audio_clips if isinstance(clip, AudioClip) else track.clips).remove(clip)
        self.select_box(None, None)
        self.on_clip_changed(track.name)

    def duplicate_selected_box(self):
        track = self._selected_or_explain()
        if track is not None:
            self._duplicate_clip(track.name, self.selected_clip)

    def split_selected_at_playhead(self):
        """Divide la clip audio selezionata nel punto della testina (quello
        in riproduzione, o il punto di pausa/salto)."""
        track = self._selected_or_explain()
        if track is None:
            return
        clip = self.selected_clip
        if not isinstance(clip, AudioClip):
            self.host.statusBar().showMessage(
                tr("Dividere funziona sulle clip audio: per un box di notazione modificane il testo."), 5000)
            return
        beat = self.host._position_for_markers()
        second = audio_tracks.split_clip(clip, beat, self._tempo_map())
        if second is None:
            self.host.statusBar().showMessage(
                tr("La testina non e' dentro la clip selezionata: spostala (clic sul righello) e riprova."), 5000)
            return
        track.audio_clips.append(second)
        self.on_clip_changed(track.name)

    def _toggle_play_selected(self):
        """Pulsante 'Play anteprima': durante la riproduzione mette in
        pausa (_pause_preview); altrimenti avvia il box selezionato, oppure
        lo riprende dal punto di pausa se e' lo STESSO box gia' messo in
        pausa (selezionarne uno diverso e premere Play riparte invece da
        capo su quello nuovo)."""
        if self._preview_playback.is_playing():
            self._pause_preview()
            return
        track = self.selected_track()
        if track is None:
            QMessageBox.information(self, tr("Nessun box selezionato"),
                                    tr("Fai clic su un box per selezionarlo, poi Shift+Spazio per ascoltarlo."))
            return
        resume_beat = 0.0
        if self._preview_paused_clip is self.selected_clip:
            resume_beat = self._preview_paused_beat
        self._play_clip(track.name, self.selected_clip, resume_offset_beats=resume_beat)

    def _play_clip(self, track_name: str, clip: Clip, resume_offset_beats: float = 0.0):
        track = self.host.project.get_track(track_name)
        host = self.host.project
        preview = Project(name="preview", tempo_bpm=host.tempo_bpm, time_sig=host.time_sig,
                          metrica_changes=list(host.metrica_changes))
        lead = 0.0
        if isinstance(clip, AudioClip):
            if audio_tracks.clip_is_missing(clip):
                QMessageBox.warning(self, tr("File mancante"), tr("Il file della clip non si trova:\n{file}", file=clip.file))
                return
            audio = preview.add_audio_track("Anteprima")
            audio.volume = track.volume
            audio.pan = track.pan
            audio.audio_clips.append(dataclasses.replace(clip, start_beat=0.0))
        else:
            ok, msg = validate_track_text(clip.text, self.host.project.patterns,
                                           default_octave=track.instrument.default_octave)
            if not ok:
                QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile riprodurre il box:\n{msg}", msg=msg))
                return
            preview.patterns = self.host.project.patterns
            # Con le ancore bar=N il box suona dal suo punto del brano (la
            # pausa davanti non si sente: l'ascolto parte da 'lead').
            text, lead = anchored_preview_text(clip.text, clip.start_beat, host.patterns)
            preview_track = preview.add_track("Anteprima", track.instrument_name, text)
            # Se la traccia e' suonata da uno strumento plugin, lo e' anche l'anteprima del box.
            preview_track.synth, preview_track.synth_params, preview_track.synth_state = \
                track.synth, dict(track.synth_params), track.synth_state
        # Un solo ascolto alla volta: il brano intero si ferma.
        if getattr(self.host, "playback", None) is not None and self.host.playback.is_playing():
            self.host.stop()
        self._previewing_clip = clip
        self._preview_offset_beats = resume_offset_beats
        self._preview_start_wall = None
        self._preview_paused_beat = None
        self._preview_paused_clip = None
        self._preview_playback.play(preview, only_audible=False, start_offset_beats=lead + resume_offset_beats,
                                     on_audio_started=self._mark_preview_audio_started)
        self._preview_status_timer.start()
        self._set_preview_button(playing=True)

    def _mark_preview_audio_started(self):
        """Richiamato dal thread di riproduzione (core.playback) nel momento
        esatto in cui l'audio inizia davvero: solo assegnamenti semplici,
        nessuna chiamata a widget Qt, sicuro anche se eseguito da un altro
        thread (stesso principio di gui.main_window_playback)."""
        self._preview_start_wall = time.time()

    def _current_preview_elapsed_beats(self) -> float:
        if self._preview_start_wall is None:
            return self._preview_offset_beats
        tempo = max(1, self.host.project.tempo_bpm)
        elapsed_seconds = time.time() - self._preview_start_wall
        return self._preview_offset_beats + elapsed_seconds * (tempo / 60.0)

    def _pause_preview(self):
        if not self._preview_playback.is_playing():
            return
        self._preview_paused_beat = self._current_preview_elapsed_beats()
        self._preview_paused_clip = self._previewing_clip
        self._preview_playback.stop()
        self._preview_status_timer.stop()
        self._preview_start_wall = None
        self._set_preview_button(playing=False)

    def _stop_preview(self):
        self._preview_playback.stop()
        self._preview_status_timer.stop()
        self._preview_start_wall = None
        self._preview_offset_beats = 0.0
        self._preview_paused_beat = None
        self._preview_paused_clip = None
        self._previewing_clip = None
        self._set_preview_button(playing=False)

    def _check_preview_still_playing(self):
        """Chiamato periodicamente mentre il pulsante mostra 'Pausa': se la
        riproduzione e' arrivata alla fine da sola (non fermata dall'utente
        ne' messa in pausa), riporta bottone e stato a 'pronto per ripartire
        da capo' - un'anteprima terminata non ha un punto di pausa da cui
        riprendere."""
        if not self._preview_playback.is_playing():
            self._stop_preview()

    def _set_preview_button(self, playing: bool):
        self.preview_action.setText(PREVIEW_PAUSE_TEXT if playing else PREVIEW_PLAY_TEXT)
        if playing and self._previewing_clip is not None:
            self.host.statusBar().showMessage(
                tr("Ascolto del box '{name}' — Shift+Spazio per la pausa, Stop per fermare.", name=self._previewing_clip.name),
                5000)

    def _transpose_clip(self, track_name: str, clip: Clip):
        track = self.host.project.get_track(track_name)
        dlg = BoxTransposeDialog(self, clip.text, self.host.project.patterns, track.instrument.default_octave)
        if dlg.exec() != BoxTransposeDialog.Accepted:
            return
        clip.text = dlg.result_text()
        self.on_clip_changed(track_name)

    def _rename_clip(self, track_name: str, clip: Clip):
        name, ok = QInputDialog.getText(self, tr("Rinomina box"), tr("Nome:"), text=clip.name)
        name = name.strip()
        if not ok or not name:
            return
        clip.name = name
        self.on_clip_changed(track_name)

    def _duplicate_clip(self, track_name: str, clip: Clip):
        track = self.host.project.get_track(track_name)
        duration = self.clip_length_beats(track_name, clip)
        new_clip = dataclasses.replace(clip, name=f"{clip.name} (copia)", start_beat=clip.start_beat + duration)
        new_clip.start_beat = _snap(self.resolve_free_slot(track_name, new_clip, new_clip.start_beat))
        (track.audio_clips if track.is_audio else track.clips).append(new_clip)
        self.on_clip_changed(track_name)

    def paste_at(self, track_name: str, beat: float):
        if not self._clipboard:
            return
        track = self.host.project.get_track(track_name)
        # Un box di notazione va solo in una traccia di notazione, una clip
        # audio solo in una traccia audio.
        if isinstance(self._clipboard, AudioClip) != track.is_audio:
            return
        new_clip = dataclasses.replace(self._clipboard, start_beat=beat)
        self._wrap_free_text_in_box(track)
        new_clip.start_beat = _snap(self.resolve_free_slot(track_name, new_clip, beat))
        (track.audio_clips if track.is_audio else track.clips).append(new_clip)
        self.on_clip_changed(track_name)

    # ------------------------------------------------------------ clip audio

    def _pick_audio_file(self, title: str):
        patterns = " ".join(f"*{ext}" for ext in audio_tracks.AUDIO_FILE_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(self, title, "", tr("Audio ({patterns});;Tutti i file (*)", patterns=patterns),
                                              options=QFileDialog.Option.DontUseNativeDialog)
        return path or None

    def _import_audio_file(self, src_path: str):
        """Copia/converte src_path nella cartella audio del progetto (vedi
        core.audio_tracks.import_audio_file); None (dopo averlo detto
        all'utente) se non si riesce."""
        error = None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            dest_dir = audio_tracks.target_audio_dir(getattr(self.host, "current_path", None))
            path = audio_tracks.import_audio_file(src_path, dest_dir)
        except (RuntimeError, OSError, ValueError) as e:
            path, error = None, str(e)
        finally:
            QApplication.restoreOverrideCursor()
        if error:
            QMessageBox.critical(self, tr("Importazione audio non riuscita"), error)
        return path

    def import_audio_clip(self, track_name: str, beat: float):
        """Sceglie un file audio e lo aggiunge come clip alla traccia audio
        track_name, a partire da beat (o dal primo posto libero dopo)."""
        src = self._pick_audio_file(tr("Importa file audio"))
        if not src:
            return
        path = self._import_audio_file(src)
        if not path:
            return
        name = os.path.splitext(os.path.basename(src))[0]
        clip = AudioClip(name=name, file=path, start_beat=beat)
        clip.start_beat = _snap(self.resolve_free_slot(track_name, clip, beat))
        self.host.project.get_track(track_name).audio_clips.append(clip)
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("Clip '{name}' aggiunta alla traccia '{track_name}' (file: {path}).", name=name, track_name=track_name, path=path), 6000)

    def _relink_clip(self, track_name: str, clip: AudioClip):
        src = self._pick_audio_file(tr("Ritrova il file di '{name}'", name=clip.name))
        if not src:
            return
        path = self._import_audio_file(src)
        if not path:
            return
        clip.file = path
        self.on_clip_changed(track_name)

    def _split_clip(self, track_name: str, clip: AudioClip, at_beat: float):
        second = audio_tracks.split_clip(clip, at_beat, self._tempo_map())
        if second is None:
            self.host.statusBar().showMessage(tr("Il punto scelto e' troppo vicino ai bordi della clip."), 4000)
            return
        self.host.project.get_track(track_name).audio_clips.append(second)
        self.on_clip_changed(track_name)

    def _edit_clip_trim(self, track_name: str, clip: AudioClip):
        """Taglio di inizio e fine in secondi, per chi preferisce i numeri al
        mouse: come trascinando i bordi, l'audio resta dov'e' nel tempo."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout
        total = audio_tracks.clip_file_seconds(clip)
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Taglio — {name}", name=clip.name))
        form = QFormLayout(dlg)
        form.addRow(QLabel(tr("Durata del file: {total:.3f} s", total=total)))
        spins = []
        for label, value in ((tr("Salta all'inizio (s):"), clip.trim_start), (tr("Salta alla fine (s):"), clip.trim_end)):
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setSingleStep(0.01)
            spin.setRange(0.0, max(0.0, total - audio_tracks.MIN_CLIP_SECONDS))
            spin.setValue(value)
            form.addRow(label, spin)
            spins.append(spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        self._trim_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        self._apply_clip_trim(track_name, clip, spins[0].value(), spins[1].value())

    def _apply_clip_trim(self, track_name: str, clip: AudioClip, trim_start: float, trim_end: float):
        from core.tempo_map import beat_at_elapsed_seconds, seconds_for_beats
        tempo_map = self._tempo_map()
        before = (clip.start_beat, clip.trim_start, clip.trim_end)
        clip.trim_end = 0.0
        start_s = seconds_for_beats(tempo_map, clip.start_beat) + (trim_start - clip.trim_start)
        if start_s < 0:
            trim_start -= start_s   # la clip non puo' iniziare prima del brano
            start_s = 0.0
        audio_tracks.trim_clip_start_to_beat(clip, beat_at_elapsed_seconds(tempo_map, 0.0, start_s), tempo_map)
        total = audio_tracks.clip_file_seconds(clip)
        clip.trim_end = round(max(0.0, min(trim_end, total - clip.trim_start - audio_tracks.MIN_CLIP_SECONDS)), 6)
        if (clip.start_beat, clip.trim_start, clip.trim_end) != before:
            self.on_clip_changed(track_name)

    def _convert_clip_to_notation(self, track_name: str, clip: AudioClip):
        """Converte la parte riprodotta della clip in notazione (stesso
        motore di 'Importa audio', vedi gui.audio_import_dialog) in una nuova
        traccia, con un box che parte dove parte la clip."""
        import tempfile
        from core.instruments import list_instrument_names
        track = self.host.project.get_track(track_name)
        names = list_instrument_names()
        preferred = {"chitarra": "Guitar", "tastiera": "Piano", "voce": "Trumpet"}.get(track.input_profile, "Piano")
        instrument, ok = QInputDialog.getItem(
            self, tr("Converti in notazione"), tr("Strumento della nuova traccia:"), names,
            names.index(preferred) if preferred in names else 0, False)
        if not ok:
            return
        fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="soundtext_clip_")
        os.close(fd)
        try:
            audio_tracks.extract_clip_audio(clip, tmp)
            dlg = AudioImportDialog(self, project=self.host.project, instrument_name=instrument,
                                     context_label=tr("clip '{name}' (traccia '{track_name}')", name=clip.name, track_name=track_name))
            dlg._set_source(tmp)
            accepted = dlg.exec() == AudioImportDialog.Accepted
            text = dlg.result_text() if accepted else None
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self.host._sync_tempo_metrica_fields()
        if not text:
            return
        project = self.host.project
        existing = {t.name for t in project.tracks}
        name, n = f"{clip.name} (note)", 2
        while name in existing:
            name, n = tr("{name} (note {n})", name=clip.name, n=n), n + 1
        new_track = project.add_track(name, instrument, "")
        new_track.clips = [Clip(name=clip.name, text=text, start_beat=clip.start_beat)]
        new_track.text = flatten_clips_to_text(new_track.clips, project.patterns, new_track.instrument.default_octave,
                                              meter=project.meter())
        self.host._mark_dirty()
        self.host.refresh_mixer()
        self.host.select_track(name)
        self.host.statusBar().showMessage(
            tr("Clip '{name}' convertita in notazione nella nuova traccia '{0}'.", name, name=clip.name), 6000)

    def _set_clip_gain(self, track_name: str, clip: AudioClip):
        value, ok = QInputDialog.getDouble(
            self, tr("Guadagno clip"), tr("Guadagno in dB (0 = originale, negativo = piu' piano):"),
            clip.gain_db, -48.0, 24.0, 1)
        if not ok or value == clip.gain_db:
            return
        clip.gain_db = value
        self.on_clip_changed(track_name)

    def _export_clip(self, clip: Clip):
        suggested = f"{clip.name.replace(' ', '_')}.box"
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta box"), f"{ensure_songs_dir()}/{suggested}",
                                               tr("Box (*.box)"), options=QFileDialog.Option.DontUseNativeDialog)
        if not path:
            return
        try:
            save_box_file(clip, path)
            self.host.statusBar().showMessage(tr("Box esportato: {path}", path=path), 4000)
        except OSError as e:
            QMessageBox.critical(self, tr("Errore salvataggio"), str(e))

    def _import_clip(self, track_name: str, beat: float):
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa box"), ensure_songs_dir(), tr("Box (*.box)"),
                                               options=QFileDialog.Option.DontUseNativeDialog)
        if not path:
            return
        try:
            clip = load_box_file(path)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, tr("Errore lettura"), str(e))
            return
        track = self.host.project.get_track(track_name)
        self._wrap_free_text_in_box(track)
        clip.start_beat = _snap(self.resolve_free_slot(track_name, clip, beat))
        track.clips.append(clip)
        self.on_clip_changed(track_name)

    def _convert_to_free_text(self, track_name: str):
        track = self.host.project.get_track(track_name)
        reply = QMessageBox.question(
            self, tr("Convertire in testo libero?"),
            tr("La traccia '{track_name}' tornera' a un unico editor di testo lineare (il contenuto attuale resta invariato) e uscira' dalla vista Struttura brano. Continuare?", track_name=track_name)
        )
        if reply != QMessageBox.Yes:
            return
        track.clips = []
        self.host._mark_dirty()
        self.refresh()
