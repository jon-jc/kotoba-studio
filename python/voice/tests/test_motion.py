"""Motion lifetime checks use the animation clock directly, not elapsed sleeps."""
from PySide6.QtWidgets import QApplication, QWidget
from kotoba.motion import Reveal


def test_reveal_cancels_on_hide_and_reduced_motion(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    widget = QWidget()
    enabled = True
    reveal = Reveal(widget, lambda: enabled)
    try:
        widget.show()
        assert reveal.animation is not None
        widget.hide()
        assert reveal.animation is None and widget.graphicsEffect() is None
        widget.show()
        reveal.animation.setCurrentTime(reveal.animation.duration())
        assert reveal.animation is None and widget.graphicsEffect() is None
        widget.hide()
        enabled = False
        widget.show()
        assert reveal.animation is None and widget.graphicsEffect() is None
    finally:
        widget.close()
        widget.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
