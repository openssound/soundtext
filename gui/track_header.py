"""
Testata di una traccia, uguale nelle due viste: a sinistra di ogni riga
della vista Struttura brano (gui.arrangement_view) e nella colonna delle
tracce della vista Testo (gui.main_window_mixer). E' il mixer della traccia:
nome, strumento, Mute/Solo, ● per le tracce audio, FX (apre il pannello
Effetti, gui.effects_panel), menu ⋯ con tutte le azioni della traccia e, a destra, le
manopole di volume e pan (gui.knob) alte quanto la riga.

Le due testate di una traccia modificano lo stesso oggetto Track: dopo ogni
cambiamento avvisano la finestra principale (host._on_mixer_changed, che
riavvia l'ascolto e segna la modifica) e riallineano l'altra
(host.sync_mixer_widgets). Cosa fanno menu ⋯ e clic dipende dalla vista:
show_menu(nome, pos) e on_select(nome) li passa chi crea la testata.
"""

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QVBoxLayout

from . import theme
from .effects_panel import fx_button_text, fx_summary, has_fx
from .icons import icon
from .knob import Knob
from .track_widget import _family_color, _pan_label
from core.i18n import tr


def make_add_track_button(populate_menu, width: int, parent=None) -> QToolButton:
    """"+ Aggiungi traccia" sotto l'ultima testata, uguale nelle due viste:
    populate_menu(menu) riempie il menu (host.populate_add_track_menu) ogni
    volta che si apre."""
    button = QToolButton(parent)
    button.setText(tr("  Aggiungi traccia"))
    button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setPopupMode(QToolButton.InstantPopup)
    button.setFixedSize(width, 30)
    button.setStyleSheet(
        "QToolButton { padding: 0px 8px; border: 1px dashed palette(mid); border-radius: 6px; text-align: left; }"
        "QToolButton::menu-indicator { subcontrol-position: right center; right: 8px; }")
    button.setToolTip(tr("Aggiungi una traccia con uno strumento, una traccia audio, una traccia generata "
                      "(batteria, giro, basso, accompagnamento) o da un file MIDI"))
    menu = QMenu(button)
    menu.aboutToShow.connect(lambda: populate_menu(menu))
    button.setMenu(menu)
    refresh_add_track_icon(button)
    return button


def refresh_add_track_icon(button: QToolButton):
    """Icona + nel colore del testo del tema attivo."""
    button.setIcon(icon("plus", "#333333" if theme.get_active_theme() == "light" else "#e0e0e0", 24))


class TrackHeaderWidget(QFrame):
    def __init__(self, host, track, width: int, height: int, show_menu, on_select=None, parent=None):
        super().__init__(parent)
        self.host = host
        self.show_menu = show_menu
        self.on_select = on_select if on_select is not None else getattr(host, "select_track", None)
        self.track = track
        self.track_name = track.name
        self._active = False
        self.setFixedSize(width, height)
        self.setObjectName("trackHeader")

        # A sinistra nome/strumento sopra e pulsanti sotto; a destra le due
        # manopole, alte quanto tutta la riga.
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 6, 4, 6)
        outer.setSpacing(4)
        left = QVBoxLayout()
        left.setSpacing(4)
        outer.addLayout(left, 1)

        # Nome e strumento, ciascuno sulla sua riga, accorciati con "…" se
        # non ci stanno (vedi _set_elided): la colonna e' piu' stretta
        # della testata intera.
        self.name_label = QLabel()
        self.name_label.setFont(QFont(self.font().family(), 9, QFont.Bold))
        self.instr_label = QLabel()
        for label in (self.name_label, self.instr_label):
            label.setMinimumWidth(1)
        top = QVBoxLayout()
        top.setSpacing(0)
        top.addWidget(self.name_label)
        top.addWidget(self.instr_label)
        left.addLayout(top)

        # Pulsanti un po' stretti: con ●, FX e ⋯ (tracce audio) devono
        # stare a sinistra delle manopole senza allargare la testata.
        row = QHBoxLayout()
        row.setSpacing(2)
        self.mute_btn = self._small_button("M", tr("Muta questa traccia"))
        self.mute_btn.setObjectName("muteBtn")
        self.solo_btn = self._small_button("S", tr("Solo: se almeno una traccia e' in Solo suonano solo quelle"))
        self.solo_btn.setObjectName("soloBtn")
        self.mute_btn.toggled.connect(self._on_mute)
        self.solo_btn.toggled.connect(self._on_solo)
        row.addWidget(self.mute_btn)
        row.addWidget(self.solo_btn)
        self.record_btn = None
        if track.is_audio:
            self.record_btn = QToolButton()
            self.record_btn.setFixedSize(22, 20)
            self.record_btn.setIconSize(QSize(12, 12))
            self.record_btn.setIcon(icon("record", theme.BAD, 24))
            self.record_btn.setToolTip(tr("Registra in questa traccia (voce, chitarra, tastiera...)"))
            self.record_btn.setAccessibleName(tr("Registra in questa traccia"))
            self.record_btn.clicked.connect(lambda: self.host.record_into_audio_track(self.track_name))
            row.addWidget(self.record_btn)
        self.fx_btn = QToolButton()
        self.fx_btn.setText("FX")
        self.fx_btn.setFixedSize(32, 20)
        self.fx_btn.setAccessibleName(tr("Effetti della traccia"))
        self.fx_btn.clicked.connect(self._open_fx)
        row.addWidget(self.fx_btn)

        row.addStretch(1)

        self.menu_btn = QToolButton()
        self.menu_btn.setObjectName("menuBtn")
        self.menu_btn.setFixedSize(20, 20)
        self.menu_btn.setIconSize(QSize(16, 16))
        self.menu_btn.setToolTip(tr("Tutte le azioni su questa traccia"))
        self.menu_btn.setAccessibleName(tr("Altre azioni sulla traccia"))
        self.menu_btn.clicked.connect(self._open_menu)
        row.addWidget(self.menu_btn)
        left.addLayout(row)

        self.vol_knob = Knob("Vol", 0, 200, 100)
        self.vol_knob.setAccessibleName(tr("Volume"))
        self.vol_knob.valueChanged.connect(self._on_volume)
        self.pan_knob = Knob("Pan", 0, 127, 64, format_value=_pan_label, bipolar=True)
        self.pan_knob.setAccessibleName(tr("Pan"))
        self.pan_knob.valueChanged.connect(self._on_pan)
        outer.addWidget(self.vol_knob, 0, Qt.AlignVCenter)
        outer.addWidget(self.pan_knob, 0, Qt.AlignVCenter)

        self.sync_from_track()

    def _small_button(self, text: str, tooltip: str) -> QToolButton:
        b = QToolButton()
        b.setText(text)
        b.setCheckable(True)
        b.setFixedSize(22, 20)
        b.setToolTip(tooltip)
        return b

    # ------------------------------------------------------------ stato

    def sync_from_track(self):
        """Riallinea i controlli al Track (cambiato altrove, es. dal mixer a
        colonna o da Annulla) senza generare altre modifiche."""
        t = self.track
        subtitle = "Audio" if t.is_audio else t.instrument_name
        if t.synth and not t.is_audio:
            from core.plugins import display_name
            subtitle = f"{display_name(t.synth)} ({'SFZ' if t.synth.startswith('sfz:') else 'plugin'})"
        self._set_elided(self.name_label, t.name)
        self._set_elided(self.instr_label, subtitle)
        for widget, value in ((self.mute_btn, t.mute), (self.solo_btn, t.solo)):
            widget.blockSignals(True)
            widget.setChecked(value)
            widget.blockSignals(False)
        for knob, value in ((self.vol_knob, t.volume), (self.pan_knob, t.pan)):
            knob.blockSignals(True)
            knob.setValue(value)
            knob.blockSignals(False)
            knob.update()
        self._update_knob_tooltips()
        self.fx_btn.setText(fx_button_text(t))
        self.fx_btn.setToolTip(fx_summary(t))
        self.fx_btn.setObjectName("fxBtnOn" if has_fx(t) else "fxBtn")
        self._refresh_style()

    def _set_elided(self, label: QLabel, text: str):
        """Testo accorciato con "…" alla larghezza che la colonna di sinistra
        lascia (la testata ha dimensione fissa); il testo intero nel tooltip."""
        width = self.width() - 10 - 4 - 4 - 2 * self.vol_knob.width() - 4 - 4
        label.setText(label.fontMetrics().elidedText(text, Qt.ElideRight, max(20, width)))
        label.setToolTip(text)

    def _update_knob_tooltips(self):
        t = self.track
        self.vol_knob.setToolTip(tr("Volume: {volume}%\nTrascina su/giu' o usa la rotellina; doppio clic: 100%", volume=t.volume))
        self.pan_knob.setToolTip(tr("Pan: {0} (sinistra L - centro C - destra R)\nTrascina su/giu' o usa la rotellina; doppio clic: centro", _pan_label(t.pan)))

    def set_active(self, active: bool):
        self._active = active
        self._refresh_style()

    def _refresh_style(self):
        colors = theme.track_card_colors()
        stripe = _family_color(self.track.instrument_name)
        bg = colors["bg"]
        border = theme.ACCENT if self._active else colors["border"]
        light = theme.get_active_theme() == "light"
        text_color = "#333333" if light else "#e0e0e0"
        field = "#f0f0f2" if light else "#2d2d30"
        # Il foglio di stile globale da' ai QToolButton un padding pensato
        # per la barra dei comandi: in questi pulsanti da 24x20 non
        # resterebbe spazio per la lettera o l'icona.
        self.setStyleSheet(
            f"QFrame#trackHeader {{ background-color: {bg}; border: none; border-left: 4px solid {stripe}; "
            f"border-bottom: 1px solid {colors['border']}; "
            f"{'border-top: 2px solid ' + border + ';' if self._active else ''} }}"
            f"QFrame#trackHeader QToolButton {{ padding: 0px; border: 1px solid {colors['border']}; "
            f"border-radius: 4px; background: {field}; color: {text_color}; font-size: 11px; font-weight: bold; }}"
            "QFrame#trackHeader QToolButton#muteBtn:checked { background: #e05555; color: white; border-color: #e05555; }"
            "QFrame#trackHeader QToolButton#soloBtn:checked { background: #e8c96d; color: #222; border-color: #e8c96d; }"
            f"QFrame#trackHeader QToolButton#fxBtnOn {{ background: {theme.ACCENT_DIM}; color: white; "
            f"border-color: {theme.ACCENT}; }}"
            "QFrame#trackHeader QToolButton#menuBtn { border: none; background: transparent; }"
            f"QFrame#trackHeader QToolButton#menuBtn:hover {{ background: {field}; }}"
        )
        self.instr_label.setStyleSheet(f"color: {colors['text_dim']};")
        self.menu_btn.setIcon(icon("more", text_color, 24))

    # ------------------------------------------------------------ modifiche

    def _changed(self):
        host = self.host
        host._on_mixer_changed(self.track_name)
        if hasattr(host, "sync_mixer_widgets"):
            host.sync_mixer_widgets(self.track_name, source=self)

    def _on_mute(self, checked):
        self.track.mute = checked
        self._changed()

    def _on_solo(self, checked):
        self.track.solo = checked
        self._changed()

    def _on_volume(self, value):
        self.track.volume = value
        self._update_knob_tooltips()
        self._changed()

    def _on_pan(self, value):
        self.track.pan = value
        self._update_knob_tooltips()
        self._changed()

    def _open_fx(self):
        if hasattr(self.host, "open_effects_panel"):
            self.host.open_effects_panel(self.track_name)

    # ------------------------------------------------------------ mouse e menu

    def _open_menu(self):
        self.show_menu(self.track_name, self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height())))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_select is not None:
            self.on_select(self.track_name)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.host._open_edit_dialog_for(self.track_name)

    def contextMenuEvent(self, event):
        self.show_menu(self.track_name, event.globalPos())
