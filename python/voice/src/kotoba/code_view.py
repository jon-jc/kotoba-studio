"""Read-only source tabs with line numbers and in-file navigation."""
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextDocument, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QWidget, QPlainTextEdit, QTabWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QLabel, QPushButton)
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


class SourceTabs(QWidget):
    def __init__(self):
        super().__init__()
        self.locale = "en"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)
        self.empty = QLabel()
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setStyleSheet("color:#999daa;padding:60px;font-size:15px")
        layout.addWidget(self.empty)
        layout.addWidget(self.tabs, 1)
        row = QHBoxLayout()
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
        self.position = QLabel()
        row.addWidget(self.position)
        layout.addLayout(row)
        self.set_locale("en")
        self.update_status()

    def set_locale(self, locale):
        self.locale = locale
        self.empty.setText("Open a file to explore your workspace\n\nRead · Search · Compare tabs" if locale == "en" else "ファイルを開いて作業内容を確認\n\n読む · 検索 · タブを比較")
        self.query.setPlaceholderText("Find in file…   Ctrl F" if locale == "en" else "ファイル内を検索…   Ctrl F")
        self.previous.setToolTip("Previous match" if locale == "en" else "前の一致")
        self.next.setToolTip("Next match" if locale == "en" else "次の一致")
        self.update_status()

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
        if editor is None:
            self.position.setText("")
        else:
            cursor = editor.textCursor()
            self.position.setText(f"{cursor.blockNumber() + 1}:{cursor.positionInBlock() + 1}  ·  UTF-8  ·  " + ("Read only" if self.locale == "en" else "読み取り専用"))
