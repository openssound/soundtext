import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core import settings as app_settings
from gui.text_zoom import text_size


def _app():
    return QApplication.instance() or QApplication([])


def _window():
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "c d e f")
    w.refresh_mixer()
    w.select_track("Piano")
    w.arrangement_action.setChecked(False)      # vista testo della traccia
    w.show()
    w.activateWindow()
    QTest.qWaitForWindowActive(w, 2000)
    w.editor.setFocus()
    QApplication.processEvents()
    return w


def _close(w):
    w._dirty = False
    w.close()


def test_ctrl_plus_and_minus_resize_the_editor_text_and_remember_it():
    _app()
    from gui.text_zoom import DEFAULT_TEXT_SIZE, text_size
    app_settings.set_editor_text_size(DEFAULT_TEXT_SIZE)
    w = _window()
    start = w.editor.fontMetrics().height()
    QTest.keyClick(w.editor, Qt.Key_Plus, Qt.ControlModifier)
    QTest.keyClick(w.editor, Qt.Key_Plus, Qt.ControlModifier)
    assert text_size() > DEFAULT_TEXT_SIZE
    assert w.editor.fontMetrics().height() > start            # il tema non lo blocca a 13px
    assert app_settings.get_editor_text_size() == text_size()
    QTest.keyClick(w.editor, Qt.Key_Minus, Qt.ControlModifier)
    QTest.keyClick(w.editor, Qt.Key_Minus, Qt.ControlModifier)
    QTest.keyClick(w.editor, Qt.Key_Minus, Qt.ControlModifier)
    assert text_size() < DEFAULT_TEXT_SIZE
    assert w.editor.toPlainText() == "c d e f"                 # niente '-' o '♭' scritti
    _close(w)
    w2 = _window()                                              # riaperto: stessa dimensione
    assert text_size() == app_settings.get_editor_text_size() < DEFAULT_TEXT_SIZE
    QTest.keyClick(w2.editor, Qt.Key_0, Qt.ControlModifier)
    assert text_size() == DEFAULT_TEXT_SIZE
    _close(w2)


def test_ctrl_wheel_resizes_the_editor_text():
    _app()
    from gui.text_zoom import text_size
    from gui.voicing_picker import NotationEditor
    editor = NotationEditor()
    size = text_size()
    for delta in (120, -120, -120):
        event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, delta),
                            Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(editor.viewport(), event)
    assert text_size() < size


def test_dialogs_with_notation_share_the_text_size():
    """Ctrl+ in un dialogo (anche un'anteprima in sola lettura) cambia la
    dimensione anche dell'editor della traccia, e viceversa."""
    _app()
    from gui.box_transpose_dialog import BoxTransposeDialog
    from gui.text_zoom import DEFAULT_TEXT_SIZE, text_size
    app_settings.set_editor_text_size(DEFAULT_TEXT_SIZE)
    w = _window()
    dialog = BoxTransposeDialog(w, "4: c d e f", {}, 4)
    dialog.show()
    dialog.activateWindow()
    QTest.qWaitForWindowActive(dialog, 2000)
    dialog.preview_edit.setFocus()
    QApplication.processEvents()
    editor_height = w.editor.fontMetrics().height()
    QTest.keyClick(dialog.preview_edit, Qt.Key_Plus, Qt.ControlModifier)
    assert text_size() > DEFAULT_TEXT_SIZE
    assert dialog.preview_edit.fontMetrics().height() > 0
    assert w.editor.fontMetrics().height() > editor_height
    dialog.close()
    _close(w)


def test_arrangement_view_keeps_ctrl_plus_for_its_zoom():
    _app()
    import gui.arrangement_view as av
    w = _window()
    size = text_size()
    zoom = av.PX_PER_BEAT
    w.arrangement_action.setChecked(True)
    w.arrangement_view.setFocus()
    QApplication.processEvents()
    try:
        QTest.keyClick(w.arrangement_view, Qt.Key_Plus, Qt.ControlModifier)
        assert av.PX_PER_BEAT > zoom
        assert text_size() == size
    finally:
        w.arrangement_view.zoom_reset()
        _close(w)
