"""
Finestre dei plugin esterni (VST3/LV2, vedi core.plugins):
  - PluginPickerDialog: sceglie un plugin (effetto o strumento) fra quelli
    installati, con la ricerca per nome; per gli strumenti anche un file
    .sfz suonato dal motore SFZ interno (core.sfz_engine);
  - PluginParamsDialog: regola i parametri di un plugin con controlli
    generati dalla sua descrizione, che si sentono subito; per i VST3 apre
    anche l'interfaccia grafica del plugin stesso, per gli LV2 sceglie i
    file che il plugin carica (es. l'SFZ di sfizz);
  - PluginDirsDialog: le cartelle in piu' in cui cercare i VST3.

Il lavoro lento (ricerca dei plugin, finestra del plugin) gira in un thread
di Python controllato da un QTimer, cosi' la finestra resta viva.
"""

import math
import os
import sys
import threading
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea, QSlider,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from core import plugins
from core.lv2_host import decode_state as decode_lv2_state, encode_state as encode_lv2_state
from core.plugins import PluginError, PluginInfo

from . import theme
from core.i18n import tr

NO_PLUGIN = "__nessuno__"
SFZ_CHOICE = "__sfz__"
SFZ_LIBRARY_COMMAND = {"win32": "py scarica_strumenti.py libreria",
                       "darwin": "python3 scarica_strumenti.py libreria"}.get(sys.platform,
                                                                             "./scarica_strumenti.sh libreria")


class _Background:
    """Una funzione in un thread; 'done' chiamata sul thread principale con
    (risultato, errore) quando finisce."""

    def __init__(self, parent, work: Callable, done: Callable):
        self._result = None
        self._error = None
        self._finished = False
        self._done = done

        def run():
            try:
                self._result = work()
            except Exception as e:      # mostrato all'utente in done()
                self._error = e
            self._finished = True
        threading.Thread(target=run, daemon=True).start()
        self._timer = QTimer(parent)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    @property
    def running(self) -> bool:
        return not self._finished

    def _poll(self):
        if self._finished:
            self._timer.stop()
            self._done(self._result, self._error)


# ---------------------------------------------------------------------------
# Scelta del plugin
# ---------------------------------------------------------------------------

class PluginPickerDialog(QDialog):
    """Elenco dei plugin installati: effetti (instrument=False) o strumenti
    (instrument=True, con in testa "Nessuno: usa il SoundFont"). Dopo exec(),
    selected_ref() e' il riferimento scelto ('' = nessun plugin)."""

    def __init__(self, parent=None, instrument: bool = False, current_ref: str = ""):
        super().__init__(parent)
        self.instrument = instrument
        self.current_ref = current_ref
        self.setWindowTitle(tr("Scegli uno strumento plugin") if instrument else tr("Scegli un effetto plugin"))
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        intro = QLabel(
            tr("Strumenti virtuali installati sul computer (VST3, e LV2 su Linux): suonano le note della "
            "traccia al posto del SoundFont.") if instrument else
            tr("Effetti installati sul computer (VST3, e LV2 su Linux): elaborano il suono della traccia "
            "come gli effetti interni."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Cerca per nome, produttore o categoria…"))
        self.search.textChanged.connect(self._fill)
        layout.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Nome"), tr("Formato"), tr("Produttore"), tr("Categoria")])
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemDoubleClicked.connect(lambda *_: self._accept_if_usable())
        self.tree.currentItemChanged.connect(lambda *_: self._update_ok())
        layout.addWidget(self.tree, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.rescan_btn = QPushButton(tr("Aggiorna elenco"))
        self.rescan_btn.setToolTip(tr("Cerca di nuovo i plugin (per esempio dopo averne installato uno)"))
        self.rescan_btn.clicked.connect(lambda: self._scan(refresh=True))
        self.dirs_btn = QPushButton(tr("Cartelle VST3…"))
        self.dirs_btn.setToolTip(tr("Aggiungi le cartelle in cui hai installato i plugin VST3"))
        self.dirs_btn.clicked.connect(self._edit_dirs)
        row.addWidget(self.rescan_btn)
        row.addWidget(self.dirs_btn)
        row.addStretch(1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept_if_usable)
        self.buttons.rejected.connect(self.reject)
        row.addWidget(self.buttons)
        layout.addLayout(row)
        self.infos = []
        self._job = None
        self._sfz_ref = current_ref if current_ref.startswith("sfz:") else ""
        self._scan(refresh=False)
        if instrument:
            self._fill()        # "Nessuno" e lo strumento SFZ non aspettano la ricerca dei plugin

    def _scan(self, refresh: bool):
        if self._job is not None and self._job.running:
            return
        self.status.setText(tr("Cerco i plugin installati… (la prima volta ogni VST3 va caricato: "
                            "puo' volerci un po')"))
        self.rescan_btn.setEnabled(False)
        self._job = _Background(self, lambda: plugins.scan_plugins(refresh=refresh), self._scanned)

    def _scanned(self, result, error):
        self.rescan_btn.setEnabled(True)
        if error is not None:
            self.status.setText(tr("Ricerca dei plugin non riuscita: {error}", error=error))
            self.infos = []
        else:
            self.infos = [i for i in result if i.instrument == self.instrument]
            usable = sum(1 for i in self.infos if i.usable)
            if self.instrument:
                self.status.setText(
                    tr("{usable} strumenti utilizzabili.", usable=usable) if self.infos else
                    tr("Nessuno strumento plugin trovato. Installa un plugin VST3 (o LV2 su Linux) oppure "
                       "indica la sua cartella con «Cartelle VST3…»."))
            else:
                self.status.setText(
                    tr("{usable} effetti utilizzabili.", usable=usable) if self.infos else
                    tr("Nessun effetto plugin trovato. Installa un plugin VST3 (o LV2 su Linux) oppure "
                       "indica la sua cartella con «Cartelle VST3…»."))
        self._fill()

    def _fill(self):
        query = self.search.text().strip().lower()
        self.tree.clear()
        if self.instrument:
            none = QTreeWidgetItem([tr("Nessuno: usa il SoundFont"), "", "", ""])
            none.setData(0, Qt.UserRole, NO_PLUGIN)
            self.tree.addTopLevelItem(none)
            if not self.current_ref:
                self.tree.setCurrentItem(none)
            sfz = self._sfz_item()
            self.tree.addTopLevelItem(sfz)
            if self._sfz_ref and sfz.flags() & Qt.ItemIsEnabled:
                self.tree.setCurrentItem(sfz)
        for info in self.infos:
            text = f"{info.name} {info.vendor} {info.category}".lower()
            if query and query not in text:
                continue
            item = QTreeWidgetItem([info.name, info.format_label, info.vendor, info.category])
            item.setData(0, Qt.UserRole, info.ref)
            if not info.usable:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setToolTip(0, tr("Non utilizzabile: {problem}", problem=info.problem))
                item.setText(0, tr("{name}  (non utilizzabile)", name=info.name))
            else:
                item.setToolTip(0, info.ref)
            self.tree.addTopLevelItem(item)
            if info.ref == self.current_ref:
                self.tree.setCurrentItem(item)
        for col in range(4):
            self.tree.resizeColumnToContents(col)
        self._update_ok()

    def _sfz_item(self) -> QTreeWidgetItem:
        from core.sfz_engine import library_found
        if self._sfz_ref:
            name = tr("Strumento SFZ (interno): {name}…", name=plugins.display_name(self._sfz_ref))
        else:
            name = tr("Strumento SFZ (interno)…")
        item = QTreeWidgetItem([name, "SFZ", "", tr("Sceglie un file .sfz")])
        item.setData(0, Qt.UserRole, SFZ_CHOICE)
        if library_found():
            item.setToolTip(0, self._sfz_ref[4:] if self._sfz_ref else
                            tr("Suona un file .sfz con il motore SFZ interno, senza plugin"))
        else:
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            item.setToolTip(0, tr("Libreria SFZ (sfizioso o sfizz) non installata: installala con «{command}»",
                                  command=SFZ_LIBRARY_COMMAND))
        return item

    def _choose_sfz(self) -> bool:
        current = self._sfz_ref[4:]
        start = os.path.dirname(current) if current else os.path.expanduser("~/Strumenti")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, tr("Scegli uno strumento SFZ"), start,
                                              tr("Strumenti SFZ (*.sfz)") + ";;" + tr("Tutti i file (*)"))
        if not path:
            return False
        self._sfz_ref = "sfz:" + path
        return True

    def _update_ok(self):
        item = self.tree.currentItem()
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(item is not None and bool(item.flags() & Qt.ItemIsEnabled))

    def _accept_if_usable(self):
        item = self.tree.currentItem()
        if item is None or not item.flags() & Qt.ItemIsEnabled:
            return
        if item.data(0, Qt.UserRole) == SFZ_CHOICE and not self._choose_sfz():
            return
        self.accept()

    def selected_ref(self) -> Optional[str]:
        item = self.tree.currentItem()
        if item is None:
            return None
        ref = item.data(0, Qt.UserRole)
        if ref == SFZ_CHOICE:
            return self._sfz_ref or None
        return "" if ref == NO_PLUGIN else ref

    def _edit_dirs(self):
        if PluginDirsDialog(self).exec() == QDialog.Accepted:
            self._scan(refresh=True)


# ---------------------------------------------------------------------------
# Parametri
# ---------------------------------------------------------------------------

_SLIDER_STEPS = 1000

# filtro della finestra "Sfoglia" secondo il nome della proprieta' LV2
_FILE_FILTERS = {"sfz": "SFZ (*.sfz)", "scala": "Scala (*.scl)"}


class _FileRow:
    """Il file di una proprieta' LV2: percorso, Sfoglia… e Togli."""

    def __init__(self, parent, file_param, path: str, changed: Callable[[str, str], None]):
        self.param = file_param
        self.parent = parent
        self.changed = changed
        self.widget = QWidget()
        row = QHBoxLayout(self.widget)
        row.setContentsMargins(0, 0, 0, 0)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText(tr("nessun file"))
        self.path_edit.setAccessibleName(file_param.label)
        browse = QPushButton(tr("Sfoglia…"))
        browse.clicked.connect(self._browse)
        self.clear_btn = QPushButton(tr("Togli"))
        self.clear_btn.clicked.connect(lambda: self._emit(""))
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        row.addWidget(self.clear_btn)
        self.set_path(path)

    def set_path(self, path: str):
        self.path = path
        self.path_edit.setText(path)
        self.path_edit.setToolTip(path)
        self.clear_btn.setEnabled(bool(path))

    def _browse(self):
        start = os.path.dirname(self.path) if self.path else os.path.expanduser("~/Strumenti")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        label = self.param.label.lower()
        filters = [f for word, f in _FILE_FILTERS.items() if word in label] + [tr("Tutti i file (*)")]
        path, _ = QFileDialog.getOpenFileName(self.parent, self.param.label, start, ";;".join(filters))
        if path:
            self._emit(path)

    def _emit(self, path: str):
        self.set_path(path)
        self.changed(self.param.key, path)


class _ParamRow:
    """Il controllo di un parametro: tendina, casella o cursore."""

    def __init__(self, param, value: float, changed: Callable[[str, float], None]):
        self.param = param
        self.changed = changed
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(100)
        if param.choices:
            self.widget = QComboBox()
            for v, label in param.choices:
                self.widget.addItem(label, v)
            self.widget.currentIndexChanged.connect(lambda _i: self._emit(self.widget.currentData()))
        elif param.toggled:
            self.widget = QCheckBox()
            self.widget.toggled.connect(lambda on: self._emit(param.maximum if on else param.minimum))
        else:
            self.widget = QSlider(Qt.Horizontal)
            self.widget.setRange(0, _SLIDER_STEPS)
            self.widget.setMinimumWidth(160)
            self.widget.valueChanged.connect(lambda pos: self._emit(self._from_pos(pos)))
        self.widget.setAccessibleName(param.label)
        self.set_value(value)

    def _log(self) -> bool:
        return self.param.logarithmic and self.param.minimum > 0

    def _to_pos(self, value: float) -> int:
        lo, hi = self.param.minimum, self.param.maximum
        if hi <= lo:
            return 0
        if self._log():
            frac = math.log(value / lo) / math.log(hi / lo) if value > 0 else 0.0
        else:
            frac = (value - lo) / (hi - lo)
        return int(round(max(0.0, min(1.0, frac)) * _SLIDER_STEPS))

    def _from_pos(self, pos: int) -> float:
        lo, hi = self.param.minimum, self.param.maximum
        frac = pos / _SLIDER_STEPS
        value = lo * (hi / lo) ** frac if self._log() else lo + (hi - lo) * frac
        if self.param.integer:
            value = float(round(value))
        return value

    def set_value(self, value: float):
        self.widget.blockSignals(True)
        if isinstance(self.widget, QComboBox):
            best = min(range(len(self.param.choices)),
                       key=lambda i: abs(self.param.choices[i][0] - value)) if self.param.choices else 0
            self.widget.setCurrentIndex(best)
        elif isinstance(self.widget, QCheckBox):
            self.widget.setChecked(value > (self.param.minimum + self.param.maximum) / 2)
        else:
            self.widget.setValue(self._to_pos(value))
        self.widget.blockSignals(False)
        self.show_value(value)

    def show_value(self, value: float, text: str = ""):
        if isinstance(self.widget, (QComboBox, QCheckBox)):
            self.value_label.setText("")
            return
        if text:
            try:                 # "50.000000" -> "50"
                text = f"{float(text):.4g}"
            except ValueError:
                pass
            units = self.param.units
            self.value_label.setText(text + (f" {units}" if units and not text.endswith(units) else ""))
        elif self.param.raw:
            self.value_label.setText(f"{value * 100:.0f}%")
        else:
            self.value_label.setText(f"{value:.0f}" if self.param.integer or abs(value) >= 100 else f"{value:.3g}")

    def _emit(self, value: float):
        self.show_value(value)
        self.changed(self.param.key, float(value))


class PluginParamsDialog(QDialog):
    """Regola i parametri di un plugin. on_change(parametri, stato) viene
    chiamata a ogni ritocco (con un attimo di ritardo mentre si trascina),
    cosi' chi la usa puo' far sentire subito il risultato; Annulla la
    richiama con i valori di partenza. Dopo exec() i valori scelti sono in
    params/state."""

    def __init__(self, parent, ref: str, params: Dict[str, float], state: str, title: str = "",
                 on_change: Optional[Callable[[Dict[str, float], str], None]] = None):
        super().__init__(parent)
        self.ref = ref
        self.initial = (dict(params or {}), state or "")
        self.params = dict(params or {})
        self.state = state or ""
        self.on_change = on_change
        self.info: Optional[PluginInfo] = None
        self.error = ""
        self.rows: Dict[str, _ParamRow] = {}
        self.file_rows: Dict[str, _FileRow] = {}
        self._labels: Dict[str, QLabel] = {}
        self._job = None
        self.setWindowTitle(title or tr("Parametri di {0}", plugins.display_name(ref)))
        self.resize(640, 560)
        layout = QVBoxLayout(self)
        self.header = QLabel(f"<b>{plugins.display_name(ref)}</b>")
        layout.addWidget(self.header)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr("Cerca un parametro…"))
        self.filter.textChanged.connect(self._apply_filter)
        self.filter.setVisible(False)
        layout.addWidget(self.filter)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.scroll, 1)
        row = QHBoxLayout()
        self.editor_btn = QPushButton(tr("Interfaccia del plugin…"))
        self.editor_btn.setToolTip(tr("Apre la finestra del plugin: le regolazioni fatte li' restano nel progetto"))
        self.editor_btn.clicked.connect(self._open_editor)
        self.editor_btn.setVisible(False)
        self.defaults_btn = QPushButton(tr("Valori predefiniti"))
        self.defaults_btn.clicked.connect(self.reset_defaults)
        self.defaults_btn.setEnabled(False)
        row.addWidget(self.editor_btn)
        row.addWidget(self.defaults_btn)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self._notify_timer = QTimer(self)
        self._notify_timer.setSingleShot(True)
        self._notify_timer.setInterval(200)
        self._notify_timer.timeout.connect(self._notify)
        if plugins.is_described(ref) or ref.startswith("lv2:"):
            # gia' caricato, o LV2 (la descrizione viene da lilv, subito)
            try:
                self._loaded(plugins.describe(ref), None)
            except PluginError as e:
                self._loaded(None, e)
        else:
            # un VST3 grande puo' metterci decine di secondi a caricarsi
            self.message.setText(tr("Carico il plugin… (la prima volta un plugin grande puo' "
                                 "richiedere qualche decina di secondi)"))
            self._job = _Background(self, lambda: plugins.describe(ref), self._loaded)

    @property
    def loading(self) -> bool:
        return self._job is not None and self._job.running and self.info is None and not self.error

    def _loaded(self, info, error):
        if error is not None:
            self.error = str(error)
            self.message.setText(tr("Il plugin non si puo' usare: {error}", error=self.error))
            self.message.setStyleSheet(f"color: {theme.BAD};")
            return
        self.info = info
        self.header.setText(f"<b>{info.name}</b> · {info.format_label}" + (f" · {info.vendor}" if info.vendor else ""))
        self.message.setText("" if info.params or info.files else tr("Questo plugin non ha parametri regolabili."))
        self.filter.setVisible(len(info.params) > 12)
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setColumnStretch(1, 1)
        files = decode_lv2_state(self.state) if info.format == "lv2" else {}
        for r, file_param in enumerate(info.files):
            file_row = _FileRow(self, file_param, files.get(file_param.key, ""), self._on_file)
            self.file_rows[file_param.key] = file_row
            grid.addWidget(QLabel(file_param.label), r, 0)
            grid.addWidget(file_row.widget, r, 1, 1, 2)
        for r, param in enumerate(info.params, start=len(info.files)):
            row = _ParamRow(param, self.params.get(param.key, param.default), self._on_param)
            self.rows[param.key] = row
            label = QLabel(param.label)
            label.setToolTip(param.key)
            self._labels[param.key] = label
            grid.addWidget(label, r, 0)
            grid.addWidget(row.widget, r, 1)
            grid.addWidget(row.value_label, r, 2)
        grid.setRowStretch(len(info.files) + len(info.params), 1)
        self.scroll.setWidget(holder)
        self.editor_btn.setVisible(info.format == "vst3")
        self.defaults_btn.setEnabled(True)
        if info.format == "vst3":
            self._refresh_texts()

    def _apply_filter(self, text: str):
        query = text.strip().lower()
        for key, row in self.rows.items():
            visible = not query or query in row.param.label.lower() or query in key.lower()
            for w in (self._labels[key], row.widget, row.value_label):
                w.setVisible(visible)

    def _defaults(self) -> Dict[str, float]:
        return {p.key: p.default for p in (self.info.params if self.info else [])}

    def _on_param(self, key: str, value: float):
        self.params[key] = value
        self._notify_timer.start()

    def _on_file(self, key: str, path: str):
        files = decode_lv2_state(self.state)
        files[key] = path
        self.state = encode_lv2_state(files)
        self._notify_timer.start()

    def _notify(self):
        # nel progetto restano solo i parametri diversi dal valore predefinito
        defaults = self._defaults()
        self.params = {k: v for k, v in self.params.items() if k not in defaults or abs(v - defaults[k]) > 1e-9}
        if self.on_change:
            self.on_change(dict(self.params), self.state)
        if self.info and self.info.format == "vst3":
            self._refresh_texts()

    def _refresh_texts(self):
        try:
            texts = plugins.parameter_texts(self.ref, self.params, self.state)
        except PluginError:
            return
        defaults = self._defaults()
        for key, row in self.rows.items():
            if key in texts:
                row.show_value(self.params.get(key, defaults.get(key, 0.0)), texts[key])

    def reset_defaults(self):
        self.params = {}
        self.state = self.info.state if self.info else ""
        for key, row in self.rows.items():
            row.set_value(row.param.default)
        for file_row in self.file_rows.values():
            file_row.set_path("")
        self._notify()

    def _open_editor(self):
        if self._job is not None and self._job.running:
            return
        self.setEnabled(False)
        self.hint.setText(tr("La finestra del plugin e' aperta: chiudila per tornare qui."))
        params, state = dict(self.params), self.state
        self._job = _Background(self, lambda: plugins.open_editor(self.ref, params, state), self._editor_closed)

    def _editor_closed(self, result, error):
        self.setEnabled(True)
        self.hint.setText("")
        if error is not None:
            QMessageBox.warning(self, tr("Interfaccia del plugin"), tr("Non si e' potuta aprire: {error}", error=error))
            return
        values, self.state = result
        self.params = dict(values)
        for key, row in self.rows.items():
            if key in values:
                row.set_value(values[key])
        self._notify()

    def accept(self):
        if self._notify_timer.isActive():
            self._notify_timer.stop()
            self._notify()
        super().accept()

    def reject(self):
        self._notify_timer.stop()
        self.params, self.state = dict(self.initial[0]), self.initial[1]
        if self.on_change:
            self.on_change(dict(self.params), self.state)
        super().reject()


# ---------------------------------------------------------------------------
# Cartelle dei VST3
# ---------------------------------------------------------------------------

class PluginDirsDialog(QDialog):
    """Le cartelle in piu' in cui cercare i plugin VST3 (quelle standard del
    sistema si usano sempre)."""

    def __init__(self, parent=None):
        from core.settings import get_plugin_dirs
        super().__init__(parent)
        self.setWindowTitle(tr("Cartelle dei plugin VST3"))
        self.resize(560, 360)
        layout = QVBoxLayout(self)
        standard = "\n".join(plugins.default_vst3_dirs())
        info = QLabel(tr("SoundText cerca sempre i VST3 nelle cartelle standard del sistema:\n{standard}\n\nAggiungi qui le altre cartelle in cui hai installato dei plugin. I plugin LV2 si trovano da soli, nelle cartelle standard di Linux.", standard=standard))
        info.setWordWrap(True)
        layout.addWidget(info)
        self.list = QListWidget()
        self.list.addItems(get_plugin_dirs())
        layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        add = QPushButton(tr("Aggiungi…"))
        add.clicked.connect(self._add)
        remove = QPushButton(tr("Togli"))
        remove.clicked.connect(lambda: self.list.takeItem(self.list.currentRow()))
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)

    def _add(self):
        path = QFileDialog.getExistingDirectory(self, tr("Cartella dei plugin VST3"), os.path.expanduser("~"))
        if path and path not in self.dirs():
            self.list.addItem(path)

    def dirs(self):
        return [self.list.item(i).text() for i in range(self.list.count())]

    def accept(self):
        from core.settings import set_plugin_dirs
        set_plugin_dirs(self.dirs())
        super().accept()
