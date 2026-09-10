"""Short native reveals and web transitions with a persistent reduced-motion option."""
import json
import sys
from PySide6.QtCore import QObject, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect


def system_reduced_motion():
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    enabled = wintypes.BOOL()
    query = ctypes.WinDLL("user32", use_last_error=True).SystemParametersInfoW
    query.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
    query.restype = wintypes.BOOL
    # SPI_GETCLIENTAREAANIMATION is read-only; do not alter OS preferences.
    return bool(query(0x1042, 0, ctypes.byref(enabled), 0)) and not enabled.value


class Reveal(QObject):
    """Own the animation with its native widget; hiding cancels immediately."""
    def __init__(self, widget, enabled):
        super().__init__(widget)
        self.widget = widget
        self.enabled = enabled
        self.animation = None
        widget.installEventFilter(self)

    def stop(self):
        if self.animation is not None:
            self.animation.stop()
            self.animation.deleteLater()
            self.animation = None
            self.widget.setGraphicsEffect(None)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Hide:
            self.stop()
        elif event.type() == QEvent.Show and self.enabled():
            self.stop()
            effect = QGraphicsOpacityEffect(self.widget)
            self.widget.setGraphicsEffect(effect)
            animation = QPropertyAnimation(effect, b"opacity", self)
            animation.setDuration(160)
            animation.setStartValue(0.35)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            self.animation = animation
            animation.finished.connect(self.stop)
            animation.start()
        return False


WEB_CSS = """
@keyframes kotoba-reveal { from { opacity: .35; } to { opacity: 1; } }
button, input, textarea, [role="tab"] {
  transition: background-color 120ms ease-out, border-color 120ms ease-out, color 120ms ease-out;
}
[role="menu"], [role="listbox"], [role="dialog"] { animation: kotoba-reveal 140ms ease-out; }
html[data-kotoba-motion="off"] *, html[data-kotoba-motion="off"] *::before,
html[data-kotoba-motion="off"] *::after {
  animation: none !important; transition: none !important; scroll-behavior: auto !important;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
"""


def web_script(reduced):
    return """(() => {
      let style = document.getElementById('kotoba-motion');
      if (!style) { style = document.createElement('style'); style.id = 'kotoba-motion'; document.head.appendChild(style); }
      style.textContent = %s;
      document.documentElement.dataset.kotobaMotion = %s;
    })();""" % (json.dumps(WEB_CSS), json.dumps("off" if reduced else "on"))
