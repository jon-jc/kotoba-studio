"""Shared desktop typography, surfaces, and compact outline navigation icons."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from .branding import icon_path


STYLE = """
QMainWindow, QDialog { background:#191a1e; }
QWidget { color:#e7e7eb; font-family:"Segoe UI", "Yu Gothic UI"; font-size:13px; }
QLabel#brand {font-size:22px; font-weight:600;}
QLabel#muted {color:#a0a2ad; font-size:12px;}
QLabel#micro {color:#9396a3; font-size:11px;}
QLabel#eyebrow {color:#acaebb; font-size:11px; font-weight:600;}
QLabel#hero {font-size:22px; font-weight:600;}
QLabel#route {color:#b1b4c0; font-size:11px; padding:6px 0;}
QFrame#sidebar, QFrame#activity-rail {background:#15161a; border-right:1px solid #2a2c33;}
QFrame#titlebar {background:#1c1d22; border-bottom:1px solid #2b2d35;}
QFrame#statusbar {background:#15161a; border-top:1px solid #2a2c33;}
QFrame#metric {background:#202127; border:1px solid #30323a; border-radius:8px;}
QLabel#value {font-size:18px; color:#dedfe6; font-weight:600;}
QPushButton {background:#25262d; border:1px solid #383a45; border-radius:7px; padding:7px 12px;}
QPushButton:hover {background:#30323b; border-color:#656976;}
QPushButton:focus {border-color:#a5cbbb;}
QPushButton:checked {background:#30363b; border-color:#596d64;}
QPushButton:disabled {color:#727581; background:#202127; border-color:#2e3038;}
QPushButton#activity {background:transparent; border:0; border-radius:8px; padding:0; color:#a0a3ae;}
QPushButton#activity:hover {background:#282a31;}
QPushButton#activity:checked {background:#30333b; border:1px solid #474c58;}
QPushButton#primary {background:#c3dacd; color:#18281f; font-weight:600; border:0; padding:11px;}
QPushButton#primary:hover {background:#d8e9df;}
QPushButton#record {background:#ece9e2; color:#26272b; font-weight:600; border:0; padding:11px;}
QPushButton#record:hover {background:#ffffff;}
QPushButton#ghost {background:transparent; border:0; color:#b0b3be; padding:6px 8px;}
QPushButton#ghost:hover {background:#2c2e36; color:#f2f2f5;}
QPushButton#command-center {background:#24252c; color:#a3a6b2; border-color:#363842; text-align:left;}
QPlainTextEdit, QTextBrowser, QLineEdit {background:#202127; border:1px solid #383a45; border-radius:8px; padding:12px; selection-background-color:#455951;}
QPlainTextEdit:focus, QLineEdit:focus {border-color:#718a7e;}
QSpinBox {background:#222329; border:1px solid #383a45; border-radius:6px; padding:7px;}
QComboBox {background:#222329; border:1px solid #383a45; border-radius:7px; padding:7px 4px 7px 12px;}
QComboBox::drop-down {subcontrol-origin:padding; subcontrol-position:top right; width:28px; border:0; background:transparent;}
QComboBox:hover {background:#282a31; border-color:#656976;}
QComboBox:focus {border-color:#a5cbbb;}
QComboBox#interface-language {padding:0 4px 0 12px; border-radius:7px;}
QComboBox#interface-language:hover {background:#282a31; border-color:#656976;}
QComboBox#interface-language:focus {border-color:#a5cbbb;}
QComboBox#interface-language::drop-down {subcontrol-origin:padding; subcontrol-position:top right; width:28px; border:0; background:transparent;}
QComboBox QAbstractItemView {background:#25262d; selection-background-color:#3a4540;}
QProgressBar {background:#222329; border:1px solid #383a45; border-radius:6px; text-align:center; color:#eceef0;}
QProgressBar::chunk {background:#466658; border-radius:5px;}
QTabWidget::pane {border:0;}
QTabBar::tab {background:transparent; color:#999daa; padding:9px 12px; border-bottom:2px solid transparent;}
QTabBar::tab:selected {color:#f0f0f2; border-bottom:2px solid #a5cbbb;}
QTabBar::tab:hover {background:#25272e;}
QCheckBox {spacing:8px; color:#b0b3be; font-size:12px;}
QSplitter::handle {background:#2d2f38; width:2px; height:2px;}
QTreeView {background:#191a1e; border:0; outline:none; alternate-background-color:#202127;}
QTreeView::item {padding:6px;}
QTreeView::item:selected {background:#333a3a;}
QFrame#code-explorer {background:#1c1e23;border:1px solid #30343c;border-radius:8px;}
QFrame#code-explorer QTreeView {background:transparent;}
QWidget#code-source {background:#1c1d22;border:1px solid #30343c;border-radius:8px;}
QWidget#code-source QTabBar {background:#202228;}
QWidget#code-source QTabBar::tab {background:#202228;padding:10px 14px;}
QWidget#code-source QTabBar::tab:selected {background:#1c1d22;border-bottom:2px solid #a5cbbb;}
QHeaderView::section {background:#202127; border:0; padding:8px; color:#a3a6b2;}
QListWidget {background:#1c1d22; border:1px solid #343640; border-radius:8px; padding:6px;}
QListWidget::item {padding:12px; border-radius:6px;}
QListWidget::item:selected {background:#333a3a; color:#f1f4f2;}
QScrollArea {background:#191a1e; border:0;}
QScrollBar:vertical {background:transparent; width:7px; margin:0;}
QScrollBar::handle:vertical {background:#454853; min-height:32px; border-radius:3px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
QToolTip {background:#32343e; color:#eeeeef; border:1px solid #4b4e5b; padding:6px;}
QMenu {background:#25262d; border:1px solid #454854; padding:6px;}
QMenu::item {padding:9px 28px 9px 12px;}
QMenu::item:selected {background:#3a3e47;}
QPushButton::menu-indicator {width:0;}
"""

STYLE += 'QComboBox::down-arrow {image:url("' + icon_path().with_name('chevron-down.svg').as_posix() + '");width:12px;height:12px;}'

STYLE += """
QFrame#workspace-rail {background:#131416; border-right:1px solid #2b2d31;}
QFrame#workspace-header {background:#191a1e; border-bottom:1px solid #2b2d31;}
QFrame#connection-card {background:#1e2025; border:1px solid #32363e; border-radius:12px;}
QFrame#rail-divider {background:#2c2e32; border:0;}
QLabel#workspace-title {font-size:14px; font-weight:600; color:#ededef;}
QPushButton#workspace-brand {background:transparent; border:0; border-radius:10px; padding:0;}
QPushButton#workspace-brand:hover {background:#26282d;}
QPushButton#workspace-brand:focus {border:1px solid #8da99a;}
QPushButton#workspace-project {background:transparent; border:0; color:#979ba5; padding:6px 10px; font-size:12px;}
QPushButton#workspace-project:hover {background:#24262b; color:#e5e7eb;}
QToolButton#workspace-tool {background:transparent; color:#959aa5; border:1px solid transparent; border-radius:9px; padding:3px 0; font-size:11px;}
QToolButton#workspace-tool:hover {background:#23252a; color:#f1f2f4;}
QToolButton#workspace-tool:checked {background:#2b2e34; color:#fafafa; border-color:#3a3e45;}
QToolButton#workspace-tool[unread="true"] {border-left:2px solid #a5cbbb; color:#dcebe3;}
QToolButton#workspace-tool:focus {border-color:#91b09f;}
QToolButton#workspace-tool:disabled {color:#606570;}
QToolButton#workspace-tool::menu-indicator {image:none; width:0;}
QPushButton#command-center {background:transparent; border:1px solid #303238; color:#969ba5; border-radius:8px; padding:5px 12px; font-size:12px;}
QPushButton#command-center:hover {background:#23252a; color:#e5e7eb; border-color:#444851;}
QComboBox#interface-language {background:transparent; border:1px solid transparent; color:#b8bdc7; padding:0 6px 0 12px;}
QComboBox#interface-language:hover {background:#23252a; border-color:#373a42;}
QFrame#statusbar {background:#191a1e; border-top:1px solid #292c31;}
"""

PATHS = {
    "agents": '<circle cx="12" cy="5" r="3"/><circle cx="5" cy="18" r="3"/><circle cx="19" cy="18" r="3"/><path d="m10 8-4 7m8-7 4 7M8 18h8"/>',
    "shield": '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    "account": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    "settings": '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>',
    "messages": '<path d="M3 3h14v12H8l-5 4Z"/><path d="M17 7h4v14l-5-3h-5v-3"/>',
    "handoff": '<path d="M3 7h15m-4-4 4 4-4 4M21 17H6m4-4-4 4 4 4"/>',

    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
    "chat": '<path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z"/><path d="M7 9h10M7 13h6"/>',
    "mic": '<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
    "code": '<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/>',
    "terminal": '<path d="m4 6 6 6-6 6m9 0h7"/>',
    "routing": '<circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="19" r="3"/><path d="m7 8 4 8m6-8-4 8M8 6h8"/>',
    "plugins": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 17h7m-3.5-3.5v7"/>',
    "models": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4"/>',
    "folder": '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
}


def outline_icon(name: str) -> QIcon:
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#b9bdc9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + PATHS[name] + '</svg>'
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pixmap)
