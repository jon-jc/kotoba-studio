"""Bilingual team handoff editor; all sharing and agent submission stay explicit."""

from pathlib import Path
import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from .collaboration import CollaborationStore, markdown, parse_translation, translation_prompt
from .selection_widgets import ClickComboBox, ClickTabWidget


class CollaborationDialog(QDialog):
    def __init__(self, voice, identity=None):
        super().__init__(voice)
        self.voice = voice
        self.store = CollaborationStore(voice.home / "collaboration.sqlite3")
        self.identity = None
        self.document = None
        self.revision = None
        self.loading = False
        self.failed = False
        self.setWindowTitle(self.tr("Team handoffs · Kotoba Studio", "チームの引き継ぎ · Kotoba Studio"))
        self.resize(1200, 800)
        self.setMinimumSize(920, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)
        hero = QLabel(self.tr("One team. Two languages.", "言葉がつなぐ、ひとつのチーム。"))
        hero.setStyleSheet("font-size:24px; font-weight:600;")
        root.addWidget(hero)
        subtitle = QLabel(self.tr("Turn meeting context into clear, reviewable handoffs. Saved on this device; share only when ready.",
            "会議の内容を、確認できる引き継ぎへ。この端末に保存し、準備ができてから共有します。"))
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)
        library = QWidget()
        left = QVBoxLayout(library)
        left.setContentsMargins(0, 0, 16, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search handoffs…", "引き継ぎを検索…"))
        self.search.textChanged.connect(self.refresh)
        left.addWidget(self.search)
        self.add_button(left, self.tr("＋ New handoff", "＋ 引き継ぎを作成"), self.create)
        self.library = QListWidget()
        self.library.currentItemChanged.connect(self.select)
        left.addWidget(self.library, 1)
        self.add_button(left, self.tr("Delete handoff", "引き継ぎを削除"), self.delete)
        split.addWidget(library)
        self.editor = QWidget()
        content = QVBoxLayout(self.editor)
        content.setContentsMargins(12, 0, 0, 0)
        self.title = QLineEdit()
        self.title.setPlaceholderText(self.tr("Handoff title", "引き継ぎのタイトル"))
        self.title.textEdited.connect(self.save)
        content.addWidget(self.title)
        self.tabs = ClickTabWidget()
        content.addWidget(self.tabs, 1)
        context = QWidget()
        context_layout = QVBoxLayout(context)
        self.source = self.text_field(context_layout, self.tr("Original context · paste a message or import from Meetings", "原文 · メッセージを貼り付けるか、会議から取り込みます"))
        self.glossary = self.text_field(context_layout, self.tr("Team terminology · for example: staging = ステージング環境", "チームの用語 · 例: staging = ステージング環境"))
        self.glossary.setMaximumHeight(110)
        self.tabs.addTab(context, self.tr("1  Context", "1  原文"))
        brief = QWidget()
        brief_layout = QVBoxLayout(brief)
        pair = QHBoxLayout()
        en = QVBoxLayout()
        ja = QVBoxLayout()
        self.english = self.text_field(en, "English")
        self.japanese = self.text_field(ja, "日本語")
        pair.addLayout(en, 1)
        pair.addLayout(ja, 1)
        brief_layout.addLayout(pair, 1)
        self.reviewed = QCheckBox(self.tr("I reviewed both versions against the original", "両言語の内容を原文と照合しました"))
        self.reviewed.toggled.connect(self.save)
        brief_layout.addWidget(self.reviewed)
        self.tabs.addTab(brief, self.tr("2  Bilingual brief", "2  バイリンガル要約"))
        tasks = QWidget()
        tasks_layout = QVBoxLayout(tasks)
        tasks_layout.addWidget(QLabel(self.tr("Confirm owners and dates with your teammates before treating them as commitments.", "担当者と期限は、合意事項として扱う前にチームで確認してください。")))
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([self.tr("Kind", "種類"), "English", "日本語", self.tr("Owner", "担当"), self.tr("Due / timezone", "期限・時間帯"), self.tr("Status", "状態"), self.tr("Source quote", "原文引用"), self.tr("Reviewed", "確認済み")])
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(76)
        self.table.setColumnWidth(1, 210)
        self.table.setColumnWidth(2, 210)
        self.table.setColumnWidth(6, 220)
        self.table.itemChanged.connect(self.item_changed)
        tasks_layout.addWidget(self.table, 1)
        task_buttons = QHBoxLayout()
        self.add_button(task_buttons, self.tr("＋ Work item", "＋ 作業項目"), self.add_item)
        self.add_button(task_buttons, self.tr("Remove selected", "選択項目を削除"), self.remove_item)
        task_buttons.addStretch()
        tasks_layout.addLayout(task_buttons)
        self.tabs.addTab(tasks, self.tr("3  Decisions & actions", "3  決定・対応"))
        ai = QWidget()
        ai_layout = QVBoxLayout(ai)
        help_text = QLabel(self.tr("Prepare a request for your selected voice agent, review and send it there, then paste its JSON reply below. Nothing is sent automatically. Cloud agents receive the included context when you send; choose a local model for offline work. Imports replace the brief and work items after confirmation.",
            "選択中の音声エージェント用に依頼を作成し、確認して送信した後、JSON の応答を下に貼り付けます。自動送信はしません。送信すると原文が選択先に渡ります。オフラインで作業する場合はローカルモデルを選んでください。取り込み時は確認後に要約と作業項目を置き換えます。"))
        help_text.setWordWrap(True)
        ai_layout.addWidget(help_text)
        self.add_button(ai_layout, self.tr("Prepare AI request → Voice agent draft", "AI への依頼を作成 → 音声エージェントの下書き"), self.prepare)
        self.response = QPlainTextEdit()
        self.response.setPlaceholderText(self.tr("Paste the JSON response…", "JSON の応答を貼り付け…"))
        ai_layout.addWidget(self.response, 1)
        self.add_button(ai_layout, self.tr("Import as unreviewed draft", "未確認の下書きとして取り込む"), self.import_response)
        self.tabs.addTab(ai, self.tr("AI assistant", "AI アシスタント"))
        footer = QHBoxLayout()
        self.add_button(footer, self.tr("Copy bilingual handoff", "引き継ぎをコピー"), self.copy)
        self.add_button(footer, self.tr("Export Markdown", "Markdown を書き出す"), self.export)
        footer.addStretch()
        content.addLayout(footer)
        split.addWidget(self.editor)
        split.setSizes([235, 915])
        self.state = QLabel()
        self.state.setWordWrap(True)
        root.addWidget(self.state)
        self.identity = identity
        self.refresh()
        if identity:
            self.load(identity)
        else:
            self.editor.setEnabled(False)
            self.state.setText(self.tr("Create a handoff or open an existing one. Meetings can be copied here from their notes window.", "引き継ぎを作成するか、既存のものを開いてください。会議のメモ画面から取り込むこともできます。"))

    def tr(self, en, ja):
        return ja if self.voice.locale == "ja" else en

    @staticmethod
    def add_button(layout, text, callback):
        button = QPushButton(text)
        button.setMinimumHeight(34)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def text_field(self, layout, label):
        layout.addWidget(QLabel(label))
        field = QPlainTextEdit()
        field.textChanged.connect(self.content_changed)
        layout.addWidget(field, 1)
        return field

    def refresh(self, *_):
        self.library.blockSignals(True)
        self.library.clear()
        for identity, title in self.store.search(self.search.text()):
            item = QListWidgetItem(title or self.tr("Untitled", "無題"))
            item.setData(Qt.UserRole, identity)
            self.library.addItem(item)
            if identity == self.identity:
                self.library.setCurrentItem(item)
        self.library.blockSignals(False)

    def create(self):
        if self.failed:
            return
        identity = self.store.create(self.tr("New team handoff", "新しい引き継ぎ"))
        self.search.clear()
        self.load(identity)
        self.refresh()
        self.title.setFocus()
        self.title.selectAll()

    def select(self, current, previous):
        if current:
            if self.failed and QMessageBox.question(self, self.tr("Discard unsaved edits?", "未保存の編集を破棄しますか？"), self.tr("Saving failed. Switching documents will discard unsaved edits. Continue?", "保存に失敗しました。切り替えると未保存の編集が失われます。続けますか？")) != QMessageBox.Yes:
                self.refresh()
                return
            self.load(current.data(Qt.UserRole))

    def load(self, identity):
        try:
            revision, document = self.store.read(identity)
        except (ValueError, OSError) as error:
            self.state.setText(str(error))
            return
        self.loading = True
        self.identity, self.revision, self.document = identity, revision, document
        self.failed = False
        self.editor.setEnabled(True)
        for key in ("title", "source", "english", "japanese", "glossary"):
            field = getattr(self, key)
            field.setText(document[key]) if key == "title" else field.setPlainText(document[key])
        self.reviewed.setChecked(document["reviewed"])
        self.response.clear()
        self.render_items()
        self.loading = False
        self.status()

    def status(self):
        pending = sum(not item["reviewed"] for item in self.document["items"])
        self.state.setText(self.tr(f"Saved on this device · {pending} work items need review · Sharing is manual", f"この端末に保存済み · 未確認の作業項目 {pending} 件 · 共有は手動で行います"))

    def content_changed(self):
        if self.loading:
            return
        self.reviewed.blockSignals(True)
        self.reviewed.setChecked(False)
        self.reviewed.blockSignals(False)
        if self.sender() in (self.source, self.glossary) and self.document:
            for item in self.document["items"]:
                item["reviewed"] = False
            self.render_items()
        self.save()

    def save(self, *_):
        if self.loading or not self.document:
            return
        candidate = {**self.document, "title": self.title.text(), "reviewed": self.reviewed.isChecked()}
        for key in ("source", "english", "japanese", "glossary"):
            candidate[key] = getattr(self, key).toPlainText()
        try:
            self.revision = self.store.save(self.identity, self.revision, candidate)
        except (ValueError, OSError, sqlite3.Error) as error:
            self.failed = True
            self.state.setText(self.tr("Not saved: ", "保存できません: ") + str(error))
            return
        self.document = candidate
        self.failed = False
        self.refresh()
        self.status()

    def render_items(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for row, item in enumerate(self.document["items"]):
            self.table.insertRow(row)
            for col, key in ((0, "kind"), (5, "status")):
                combo = ClickComboBox()
                labels = [("action", "Action", "対応"), ("decision", "Decision", "決定"), ("question", "Question", "質問")] if key == "kind" else [("open", "Open", "未着手"), ("in_progress", "In progress", "進行中"), ("done", "Done", "完了")]
                for value, en, ja in labels:
                    combo.addItem(self.tr(en, ja), value)
                combo.setCurrentIndex(combo.findData(item[key]))
                combo.currentIndexChanged.connect(lambda _, r=row, k=key, c=combo: self.change_item(r, k, c.currentData()))
                self.table.setCellWidget(row, col, combo)
            for col, key in ((1, "english"), (2, "japanese"), (3, "owner"), (4, "due"), (6, "quote")):
                self.table.setItem(row, col, QTableWidgetItem(item[key]))
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            check.setCheckState(Qt.Checked if item["reviewed"] else Qt.Unchecked)
            self.table.setItem(row, 7, check)
        self.table.blockSignals(False)

    def change_item(self, row, key, value):
        self.document["items"][row][key] = value
        if key != "status":
            self.document["items"][row]["reviewed"] = False
            self.table.blockSignals(True)
            self.table.item(row, 7).setCheckState(Qt.Unchecked)
            self.table.blockSignals(False)
        self.save()

    def item_changed(self, cell):
        if cell.column() == 7:
            self.document["items"][cell.row()]["reviewed"] = cell.checkState() == Qt.Checked
            self.save()
        else:
            key = {1: "english", 2: "japanese", 3: "owner", 4: "due", 6: "quote"}[cell.column()]
            self.change_item(cell.row(), key, cell.text())

    def add_item(self):
        if len(self.document["items"]) >= 200:
            self.state.setText(self.tr("This handoff already has 200 items. Create another handoff for additional work.", "作業項目が 200 件あります。追加の作業は別の引き継ぎに記録してください。"))
            return
        self.document["items"].append(dict(kind="action", english="", japanese="", owner="", due="", quote="", status="open", reviewed=False))
        self.render_items()
        self.save()

    def remove_item(self):
        row = self.table.currentRow()
        if row >= 0:
            del self.document["items"][row]
            self.render_items()
            self.save()

    def prepare(self):
        if self.failed or not self.document["source"].strip():
            self.state.setText(self.tr("Save original context before preparing an AI request.", "原文を入力して保存してから依頼を作成してください。"))
            return
        if self.voice.draft.toPlainText().strip() and QMessageBox.question(self, self.tr("Replace voice draft?", "音声の下書きを置き換えますか？"), self.tr("Replace the existing unsent voice draft with this request?", "未送信の音声の下書きをこの依頼に置き換えますか？")) != QMessageBox.Yes:
            return
        self.voice.draft.setPlainText(translation_prompt(self.document))
        self.state.setText(self.tr("Request prepared in Voice → Agent. Close this window, choose your provider/model and review before sending. Return here to import the reply.", "音声 → エージェントに依頼の下書きを作成しました。この画面を閉じ、モデルを選んで確認・送信した後、応答をここに取り込んでください。"))

    def import_response(self):
        if self.failed:
            return
        try:
            candidate = parse_translation(self.response.toPlainText(), self.document)
        except ValueError as error:
            self.state.setText(str(error))
            return
        if (self.document["english"] or self.document["japanese"] or self.document["items"]) and QMessageBox.question(self, self.tr("Replace draft?", "下書きを置き換えますか？"), self.tr("Replace the current bilingual brief and work items? The original context stays available.", "現在の要約と作業項目を置き換えますか？原文は保持されます。")) != QMessageBox.Yes:
            return
        try:
            self.revision = self.store.save(self.identity, self.revision, candidate)
        except (ValueError, OSError, sqlite3.Error) as error:
            self.state.setText(str(error))
            return
        self.load(self.identity)
        self.tabs.setCurrentIndex(1)
        self.state.setText(self.tr("Imported as unreviewed. Matching quotes establish traceability, not translation accuracy. Review both languages and every commitment.", "未確認の下書きとして取り込みました。引用の一致は翻訳の正確さを保証しません。両言語の内容と合意事項を確認してください。"))

    def copy(self):
        if not self.failed:
            QApplication.clipboard().setText(markdown(self.document))
            self.state.setText(self.tr("Copied with review labels and original context. Ready to paste into your team’s tools.", "確認状態と原文を含めてコピーしました。チームのツールに貼り付けられます。"))

    def export(self):
        if self.failed:
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export handoff", "引き継ぎを書き出す"), "kotoba-handoff.md", "Markdown (*.md)")
        if path:
            try:
                Path(path).write_text(markdown(self.document), encoding="utf-8", newline="\n")
            except OSError as error:
                self.state.setText(str(error))

    def delete(self):
        if self.identity and not self.failed and QMessageBox.question(self, self.tr("Delete handoff?", "引き継ぎを削除しますか？"), self.tr("Delete this local handoff? Exported copies are unaffected.", "この端末の引き継ぎを削除しますか？書き出したコピーは残ります。")) == QMessageBox.Yes:
            try:
                self.store.delete(self.identity, self.revision)
            except ValueError as error:
                self.state.setText(str(error))
                return
            self.identity = self.document = None
            self.editor.setEnabled(False)
            self.refresh()
            self.state.setText(self.tr("Handoff deleted", "引き継ぎを削除しました"))

    def reject(self):
        if self.failed and QMessageBox.question(self, self.tr("Discard unsaved edits?", "未保存の編集を破棄しますか？"), self.tr("Saving failed. Close and discard unsaved edits?", "保存に失敗しました。未保存の編集を破棄して閉じますか？")) != QMessageBox.Yes:
            return
        super().reject()
