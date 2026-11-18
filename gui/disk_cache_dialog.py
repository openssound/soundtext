"""
Progetto → Cache su disco...: lo spazio occupato dalle cache dei rendering
(core.disk_cache) del progetto aperto e di tutti i progetti, con i pulsanti
Svuota la cache di questo progetto e Svuota tutte le cache. Svuotarle non
toglie niente del brano: i rendering si rifanno al prossimo ascolto.
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout

from core import disk_cache
from core.i18n import tr


def format_size(size: int) -> str:
    if size >= 1024 ** 3:
        return f"{size / 1024 ** 3:.1f} GB"
    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.0f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} kB"
    return f"{size} B"


class DiskCacheDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Cache su disco"))
        layout = QVBoxLayout(self)
        intro = QLabel(tr("I rendering delle tracce con effetti, degli strumenti plugin e dei time-stretch si "
                          "salvano accanto al progetto, per riascoltarlo senza ricalcolare. Svuotare la cache "
                          "non toglie niente del brano: si ricalcola al prossimo ascolto."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.project_label = QLabel()
        self.total_label = QLabel()
        self.limit_label = QLabel()
        form.addRow(tr("Questo progetto:"), self.project_label)
        form.addRow(tr("Tutti i progetti:"), self.total_label)
        form.addRow(tr("Limite complessivo:"), self.limit_label)
        layout.addLayout(form)
        self.clear_project_button = QPushButton(tr("Svuota la cache di questo progetto"))
        self.clear_project_button.clicked.connect(self._clear_project)
        self.clear_all_button = QPushButton(tr("Svuota tutte le cache"))
        self.clear_all_button.clicked.connect(self._clear_all)
        layout.addWidget(self.clear_project_button)
        layout.addWidget(self.clear_all_button)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self):
        directory = disk_cache.cache_dir()
        if directory:
            self.project_label.setText(format_size(disk_cache.dir_size(directory)))
        else:
            self.project_label.setText(tr("nessuna (progetto non salvato)"))
        self.clear_project_button.setEnabled(bool(directory))
        self.total_label.setText(format_size(disk_cache.total_size()))
        self.limit_label.setText(format_size(disk_cache.global_limit()))

    @staticmethod
    def _release_files():
        """Le cache in memoria tengono mappati i file letti dal disco: su
        Windows un file mappato non si cancella. Si lasciano prima."""
        import gc
        from core.memory import clear_memory_caches
        disk_cache.wait_writes(5.0)
        clear_memory_caches()
        gc.collect()

    def _clear_project(self):
        self._release_files()
        disk_cache.clear()
        self.refresh()

    def _clear_all(self):
        self._release_files()
        disk_cache.clear_all()
        self.refresh()
