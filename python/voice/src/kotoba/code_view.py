"""Read-only source tabs with line numbers and in-file navigation."""
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextDocument, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QWidget, QPlainTextEdit, QTabWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QLabel, QPushButton, QSizePolicy, QFileIconProvider)
from .selection_widgets import ClickTabWidget
from .design import outline_icon
from pygments.lexers import get_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound


class SourceHighlight(QSyntaxHighlighter):
    """Precompute read-only token spans, using Qt's UTF-16 character offsets."""
    def __init__(self, document, path, content):
        self.lines = {}
        if len(content) <= 200_000:
            try:
                lexer = get_lexer_for_filename(path.name, stripnl=False, ensurenl=False)
            except ClassNotFound:
                lexer = None
            if lexer is not None:
                colors = ((Token.Comment, "#858d9f"), (Token.Keyword, "#c5a7e7"),
                          (Token.String, "#b2d5bd"), (Token.Number, "#dfb68e"),
                          (Token.Name.Function, "#a9cbe8"), (Token.Name.Class, "#9ad3cb"))
                formats = {}
                for kind, color in colors:
                    style = QTextCharFormat()
                    style.setForeground(QColor(color))
                    formats[kind] = style
                line, column = 0, 0
                for _, token, value in lexer.get_tokens_unprocessed(content):
                    style = next((formats[kind] for kind, _ in colors if token in kind), None)
                    parts = value.split("\n")
                    for index, part in enumerate(parts):
                        length = len(part.encode("utf-16-le")) // 2
                        if style is not None and length:
                            self.lines.setdefault(line, []).append((column, length, style))
                        column += length
                        if index < len(parts) - 1:
                            line, column = line + 1, 0
        super().__init__(document)

    def highlightBlock(self, text):
        for start, length, style in self.lines.get(self.currentBlock().blockNumber(), ()):
            self.setFormat(start, length, style)


class LineNumbers(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.number_width(), 0)

    def paintEvent(self, event):
        editor = self.editor
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#1c1d22"))
        painter.setPen(QColor("#777c8c"))
        painter.setFont(editor.font())
        block = editor.firstVisibleBlock()
        top = round(editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top())
        while block.isValid() and top <= event.rect().bottom():
            height = round(editor.blockBoundingRect(block).height())
            if block.isVisible() and top + height >= event.rect().top():
                painter.drawText(0, top, self.width() - 12, editor.fontMetrics().height(),
                                 Qt.AlignRight, str(block.blockNumber() + 1))
            top += height
            block = block.next()


class SourceEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet('QPlainTextEdit {font-family:"Consolas";font-size:14px;border:0;border-radius:0;background:#1c1d22;padding:8px;}')
        self.numbers = LineNumbers(self)
        self.blockCountChanged.connect(self.update_margin)
        self.updateRequest.connect(self.update_numbers)
        self.update_margin()

    def number_width(self):
        return 24 + self.fontMetrics().horizontalAdvance("9") * len(str(max(1, self.blockCount())))

    def update_margin(self, *_):
        self.setViewportMargins(self.number_width(), 0, 0, 0)

    def update_numbers(self, rect, dy):
        if dy:
            self.numbers.scroll(0, dy)
        else:
            self.numbers.update(0, rect.y(), self.numbers.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        area = self.contentsRect()
        self.numbers.setGeometry(area.left(), area.top(), self.number_width(), area.height())


class SourceIcons(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.folder = outline_icon("folder")
        self.file = outline_icon("file")

    def icon(self, info):
        directory = info.isDir() if hasattr(info, "isDir") else info == QFileIconProvider.Folder
        return self.folder if directory else self.file


class ElidedPath(QLabel):
    """Keep long paths from widening the workbench; expose the full path on hover."""
    def __init__(self, text=""):
        super().__init__(text)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        painter.drawText(self.contentsRect(), Qt.AlignVCenter | Qt.AlignLeft,
                         self.fontMetrics().elidedText(self.text(), Qt.ElideMiddle, self.contentsRect().width()))


class SourceTabs(QWidget):
    choose_folder = Signal()

    def __init__(self):
        super().__init__()
        self.locale = "en"
        self.workspace_root = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tabs = ClickTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)
        self.empty = QWidget()
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.setSpacing(14)
        empty_layout.addStretch()
        icon = QLabel()
        icon.setPixmap(outline_icon("code").pixmap(44, 44))
        empty_layout.addWidget(icon, 0, Qt.AlignHCenter)
        self.empty_title = QLabel()
        self.empty_title.setStyleSheet("font-size:22px;font-weight:600;color:#e8ecea")
        empty_layout.addWidget(self.empty_title, 0, Qt.AlignHCenter)
        self.empty_hint = QLabel()
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setStyleSheet("color:#969da8;font-size:13px")
        empty_layout.addWidget(self.empty_hint)
        self.open_folder = QPushButton()
        self.open_folder.setObjectName("primary")
        self.open_folder.setIcon(outline_icon("folder"))
        self.open_folder.clicked.connect(self.choose_folder.emit)
        empty_layout.addWidget(self.open_folder, 0, Qt.AlignHCenter)
        empty_layout.addStretch()
        layout.addWidget(self.empty, 1)
        self.breadcrumb = ElidedPath()
        self.breadcrumb.setContentsMargins(14, 0, 14, 0)
        self.breadcrumb.setFixedHeight(36)
        self.breadcrumb.setStyleSheet("color:#9ba4ae;background:#202228;font-size:12px")
        layout.addWidget(self.breadcrumb)
        self.find_bar = QWidget()
        row = QHBoxLayout(self.find_bar)
        row.setContentsMargins(12, 8, 12, 8)
        self.query = QLineEdit()
        self.query.textChanged.connect(lambda: self.find_text(restart=True))
        self.query.returnPressed.connect(self.find_text)
        row.addWidget(self.query, 1)
        self.previous = QPushButton("↑")
        self.next = QPushButton("↓")
        self.previous.clicked.connect(lambda: self.find_text(backward=True))
        self.next.clicked.connect(self.find_text)
        row.addWidget(self.previous)
        row.addWidget(self.next)
        self.dismiss_find = QPushButton("×")
        self.dismiss_find.setFixedWidth(32)
        self.dismiss_find.clicked.connect(self.hide_find)
        row.addWidget(self.dismiss_find)
        self.find_bar.hide()
        layout.addWidget(self.find_bar)
        layout.addWidget(self.tabs, 1)
        self.position = QLabel()
        self.position.setContentsMargins(14, 6, 14, 6)
        self.position.setStyleSheet("color:#8e98a5;font-size:11px;background:#202228")
        layout.addWidget(self.position)
        self.set_locale("en")
        self.update_status()

    def set_locale(self, locale):
        self.locale = locale
        self.empty_title.setText("A closer look at your code" if locale == "en" else "コードを、もっと見やすく。")
        self.empty_hint.setText("Choose a file from Explorer, or open a folder to get started.\nYour conversations stay one click away." if locale == "en" else "エクスプローラーでファイルを選ぶか、フォルダーを開いて始めましょう。\n会話にはいつでも戻れます。")
        self.open_folder.setText("Open folder" if locale == "en" else "フォルダーを開く")
        self.query.setPlaceholderText("Find in file…   Ctrl F" if locale == "en" else "ファイル内を検索…   Ctrl F")
        self.previous.setToolTip("Previous match" if locale == "en" else "前の一致")
        self.next.setToolTip("Next match" if locale == "en" else "次の一致")
        self.dismiss_find.setToolTip("Close search · Esc" if locale == "en" else "検索を閉じる · Esc")
        for button in (self.previous, self.next, self.dismiss_find):
            button.setAccessibleName(button.toolTip())
        self.update_status()

    def show_find(self):
        if self.tabs.currentWidget() is not None:
            self.find_bar.show()
            self.query.setFocus()
            self.query.selectAll()

    def set_workspace(self, path):
        self.workspace_root = Path(path).resolve()
        self.update_status()

    def hide_find(self):
        self.find_bar.hide()
        if self.tabs.currentWidget() is not None:
            self.tabs.currentWidget().setFocus()

    def open_file(self, path: Path, content: str):
        identity = str(path.resolve())
        for index in range(self.tabs.count()):
            if self.tabs.widget(index).property("sourcePath") == identity:
                self.tabs.setCurrentIndex(index)
                return
        editor = SourceEditor()
        editor.setProperty("sourcePath", identity)
        editor.setPlainText(content)
        editor.highlighter = SourceHighlight(editor.document(), path, content)
        editor.cursorPositionChanged.connect(self.update_status)
        index = self.tabs.addTab(editor, path.name)
        self.tabs.setTabToolTip(index, identity)
        self.tabs.setCurrentIndex(index)
        self.update_status()

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if editor is None:
            return
        self.tabs.removeTab(index)
        editor.deleteLater()
        self.update_status()

    def find_text(self, *_args, backward=False, restart=False):
        editor = self.tabs.currentWidget()
        if editor is None or not self.query.text():
            self.update_status()
            return
        if restart:
            editor.moveCursor(QTextCursor.Start)
        flags = QTextDocument.FindBackward if backward else QTextDocument.FindFlags()
        found = editor.find(self.query.text(), flags)
        if not found:
            editor.moveCursor(QTextCursor.End if backward else QTextCursor.Start)
            found = editor.find(self.query.text(), flags)
        if not found:
            self.position.setText("No matches" if self.locale == "en" else "一致なし")

    def update_status(self, *_):
        editor = self.tabs.currentWidget()
        self.empty.setVisible(editor is None)
        self.tabs.setVisible(editor is not None)
        self.breadcrumb.setVisible(editor is not None)
        self.position.setVisible(editor is not None)
        if editor is None:
            self.find_bar.hide()
            self.breadcrumb.clear()
            self.position.setText("")
        else:
            path = Path(editor.property("sourcePath"))
            try:
                display = path.relative_to(self.workspace_root) if self.workspace_root else path
            except ValueError:
                display = path
            self.breadcrumb.setText(display.as_posix())
            self.breadcrumb.setToolTip(str(path))
            cursor = editor.textCursor()
            self.position.setText(f"{cursor.blockNumber() + 1}:{cursor.positionInBlock() + 1}  ·  UTF-8  ·  " + ("Read only" if self.locale == "en" else "読み取り専用"))
