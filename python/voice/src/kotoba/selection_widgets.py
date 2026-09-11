"""Voice selectors preserve their selection while the user scrolls the panel."""

from PySide6.QtWidgets import QComboBox, QTabBar, QTabWidget


class ClickComboBox(QComboBox):
    """Require an opened popup or keyboard input to change the selection."""

    def wheelEvent(self, event):
        event.ignore()


class ClickTabBar(QTabBar):
    """Leave wheel events to the surrounding scroll area."""

    def wheelEvent(self, event):
        event.ignore()


class ClickTabWidget(QTabWidget):
    """Keep standard tab clicks and keyboard navigation without wheel switching."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(ClickTabBar(self))
