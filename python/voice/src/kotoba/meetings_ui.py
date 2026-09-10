"""Bilingual local meeting library, capture controls, and reviewable highlights."""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QListWidget, QListWidgetItem, QPlainTextEdit,
    QSplitter, QWidget, QFileDialog, QMessageBox)
from .audio_sources import sources
from .meetings import MeetingStore, MeetingCapture, suggested_highlights


class MeetingsDialog(QDialog):
    changed = Signal(str)

    def __init__(self, voice):
        super().__init__(voice)
        self.voice = voice
        self.capture = None
        self.selected = None
        self.store = voice.meeting_store
        self.setWindowTitle(self.tr("Meetings & notes", "会議とメモ"))
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.resize(1080, 760)
        self.setMinimumSize(850, 640)
        layout = QVBoxLayout(self)
        heading = QLabel(self.tr("Meetings worth remembering", "会議の大切なことを、次の仕事へ"))
        heading.setObjectName("hero")
        layout.addWidget(heading)
        privacy = QLabel(self.tr("Saved on this device · Audio is not retained · Processing: ",
                                "この端末に保存 · 音声は保存しません · 処理方法: ") + ("LOCAL / ローカル" if voice.config.processing == "local" else "CLOUD UPLOAD / クラウドへ音声を送信"))
        privacy.setObjectName("muted")
        layout.addWidget(privacy)
        self.title = QLineEdit()
        self.title.setPlaceholderText(self.tr("Meeting title", "会議名"))
        layout.addWidget(self.title)
        controls = QHBoxLayout()
        self.source = QComboBox()
        self.source.setMinimumContentsLength(25)
        self.source.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        controls.addWidget(self.source, 1)
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setAccessibleName(self.tr("Refresh windows", "ウィンドウを更新"))
        self.refresh_button.clicked.connect(self.load_sources)
        controls.addWidget(self.refresh_button)
        self.microphone = QCheckBox(self.tr("Include my microphone", "自分のマイクも録音"))
        controls.addWidget(self.microphone)
        self.start_button = QPushButton(self.tr("● Start meeting", "● 会議を録音"))
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.toggle)
        controls.addWidget(self.start_button)
        layout.addLayout(controls)
        self.mic_source = QComboBox()
        self.mic_source.setAccessibleName(self.tr("Your microphone", "自分のマイク"))
        self.mic_source.hide()
        self.microphone.toggled.connect(self.mic_source.setVisible)
        layout.addWidget(self.mic_source)
        scope = QLabel(self.tr("Window selection captures its application process tree, including other tabs. Use headphones when including your microphone. Capture labels identify sources, not individual speakers.",
                               "選択したウィンドウのアプリ全体（他のタブを含む）を録音します。マイク併用時はヘッドホンを使用してください。ラベルは録音元で、話者識別ではありません。"))
        scope.setWordWrap(True)
        scope.setObjectName("micro")
        layout.addWidget(scope)
        self.state = QLabel(self.tr("Ready · download your selected speech model before recording", "準備完了 · 録音前に選択した音声モデルをダウンロードしてください"))
        layout.addWidget(self.state)
        split = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search titles, transcripts and notes", "会議名・文字起こし・メモを検索"))
        self.search.textChanged.connect(self.refresh)
        left_layout.addWidget(self.search)
        self.library = QListWidget()
        self.library.currentItemChanged.connect(self.select)
        left_layout.addWidget(self.library)
        split.addWidget(left)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel(self.tr("Transcript · select a line to highlight", "文字起こし · 行を選択して重要事項に追加")))
        self.transcript = QListWidget()
        self.transcript.setWordWrap(True)
        right_layout.addWidget(self.transcript, 2)
        actions = QHBoxLayout()
        for en, ja, callback in (("☆ Highlight", "☆ 重要事項", self.highlight),
                                 ("Find key points", "重要事項の候補", self.suggest),
                                 ("Add to agent draft", "エージェントの下書きへ", self.handoff)):
            button = QPushButton(self.tr(en, ja))
            button.clicked.connect(callback)
            actions.addWidget(button)
        right_layout.addLayout(actions)
        right_layout.addWidget(QLabel(self.tr("Development notes · saved automatically", "開発メモ · 自動保存")))
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText(self.tr("Decisions, owners, deadlines, next steps…", "決定事項、担当者、期限、次のステップ…"))
        self.notes.textChanged.connect(self.save_notes)
        right_layout.addWidget(self.notes, 1)
        footer = QHBoxLayout()
        export = QPushButton(self.tr("Export Markdown", "Markdown を書き出す"))
        export.clicked.connect(self.export)
        delete = QPushButton(self.tr("Delete note", "メモを削除"))
        delete.clicked.connect(self.delete)
        footer.addWidget(export)
        footer.addStretch()
        footer.addWidget(delete)
        right_layout.addLayout(footer)
        split.addWidget(right)
        split.setSizes([270, 750])
        layout.addWidget(split, 1)
        self.changed.connect(self.capture_changed)
        self.load_sources()
        self.refresh()

    def tr(self, en, ja):
        return en if self.voice.locale == "en" else ja

    def load_sources(self):
        self.source.clear()
        self.mic_source.clear()
        for source in sources():
            self.source.addItem(source.label, source)
            if source.kind == "microphone":
                self.mic_source.addItem(source.label, source)

    def toggle(self):
        if self.capture:
            self.capture.stop()
            self.start_button.setEnabled(False)
            self.state.setText(self.tr("Finishing and saving queued audio…", "残りの音声を文字起こしして保存中…"))
            return
        if self.voice.job is not None or self.voice.stream is not None:
            self.state.setText(self.tr("Finish the current voice task first", "先に音声処理を終了してください"))
            return
        self.voice.ensure_speech(self.start_capture)

    def start_capture(self):
        selected = self.source.currentData()
        if selected is None:
            self.state.setText(self.tr("Select an available audio source", "利用可能な録音元を選択してください"))
            return
        chosen = [selected]
        if self.microphone.isChecked() and selected.kind != "microphone":
            if self.mic_source.currentData() is None:
                return
            chosen.append(self.mic_source.currentData())
        self.capture = MeetingCapture(self.store, self.voice.engine, self.voice.selected_config(), chosen,
                                      self.title.text(), self.changed.emit)
        self.voice.meeting_active = True
        self.start_button.setText(self.tr("■ Stop & save", "■ 停止して保存"))
        for widget in (self.source, self.microphone, self.mic_source, self.refresh_button, self.title):
            widget.setEnabled(False)
        self.state.setText(self.tr("Starting · local model loading…", "開始中 · ローカルモデルを読み込み中…"))
        self.voice.work(lambda emit: self.capture.run(), self.completed)
        self.voice.job.finished.connect(self.settled)

    def completed(self, identity):
        self.selected = identity
        self.refresh()
        meeting, _ = self.store.read(identity)
        self.state.setText(meeting['error'] or self.tr("Saved locally", "端末に保存しました"))

    def settled(self):
        self.capture = None
        self.voice.meeting_active = False
        for widget in (self.start_button, self.source, self.microphone, self.mic_source, self.refresh_button, self.title):
            widget.setEnabled(True)
        self.start_button.setText(self.tr("● Start meeting", "● 会議を録音"))

    def capture_changed(self, identity):
        self.selected = identity
        self.refresh()
        if self.capture and not self.capture.stop_event.is_set():
            self.state.setText(self.tr("● Recording · completed segments saved locally", "● 録音中 · 完了した文字起こしは端末に保存済み"))

    def refresh(self, *_):
        self.library.blockSignals(True)
        self.library.clear()
        for meeting in self.store.search(self.search.text()):
            status = self.tr(meeting['status'], {"recording":"録音中", "complete":"保存済み", "incomplete":"未完了", "interrupted":"中断"}.get(meeting['status'], meeting['status']))
            item = QListWidgetItem(f"{meeting['title']}\n{meeting['created'][:16]} · {status}")
            item.setData(Qt.UserRole, meeting['id'])
            self.library.addItem(item)
            if meeting['id'] == self.selected:
                self.library.setCurrentItem(item)
        self.library.blockSignals(False)
        self.render()

    def select(self, current, previous):
        self.selected = current.data(Qt.UserRole) if current else None
        self.render()

    def render(self):
        self.transcript.clear()
        self.notes.blockSignals(True)
        if self.selected:
            meeting, segments = self.store.read(self.selected)
            for row in segments:
                prefix = "★ " if row['highlight'] else ""
                item = QListWidgetItem(f"{prefix}{int(row['start'])//60:02d}:{int(row['start'])%60:02d} · {row['source']}\n{row['text']}")
                item.setData(Qt.UserRole, row)
                self.transcript.addItem(item)
            if self.notes.toPlainText() != meeting['notes']:
                self.notes.setPlainText(meeting['notes'])
        else:
            self.notes.clear()
        self.notes.setEnabled(bool(self.selected))
        self.notes.blockSignals(False)

    def save_notes(self):
        if self.selected:
            self.store.notes(self.selected, self.notes.toPlainText())

    def highlight(self):
        item = self.transcript.currentItem()
        if item:
            row = item.data(Qt.UserRole)
            self.store.highlight(row['id'], not row['highlight'])
            self.render()

    def suggest(self):
        if self.selected:
            _, segments = self.store.read(self.selected)
            for row in suggested_highlights(segments):
                self.store.highlight(row['id'])
            self.render()
            self.state.setText(self.tr("Keyword-based suggestions · review before using as decisions or tasks", "キーワードによる候補です · 決定事項やタスクにする前に確認してください"))

    def handoff(self):
        if self.selected:
            text = self.store.markdown(self.selected)
            self.voice.draft.setPlainText(self.tr("Review this meeting record. Propose development follow-ups; do not execute actions.\n\n", "この会議記録を確認し、開発のフォローアップを提案してください。操作は実行しないでください。\n\n") + text)
            self.state.setText(self.tr("Added to Voice Studio draft · review, then send", "音声スタジオの下書きに追加しました · 確認して送信してください"))

    def export(self):
        if self.selected:
            path, _ = QFileDialog.getSaveFileName(self, self.tr("Export note", "メモを書き出す"), "meeting.md", "Markdown (*.md)")
            if path:
                Path(path).write_bytes(self.store.markdown(self.selected).encode("utf-8"))

    def delete(self):
        if self.selected and not self.capture and QMessageBox.question(self, self.tr("Delete note?", "メモを削除しますか？"), self.tr("Delete this meeting and its transcript from this device?", "この端末から会議と文字起こしを削除しますか？")) == QMessageBox.Yes:
            self.store.delete(self.selected)
            self.selected = None
            self.refresh()

    def reject(self):
        if self.capture or self.voice.job is not None:
            self.state.setText(self.tr("Stop and save the meeting before closing", "会議を停止して保存してから閉じてください"))
            return
        super().reject()
