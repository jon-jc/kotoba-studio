import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget
from kotoba.collaboration import source_token
from kotoba.collaboration_ui import CollaborationDialog


def test_edit_review_invalidation_agent_draft_and_reopen(tmp_path):
    app = QApplication.instance() or QApplication([])
    clipboard = app.clipboard().text()
    voice = QWidget()
    voice.home, voice.locale = tmp_path, "en"
    voice.draft = QPlainTextEdit(voice)
    dialog = CollaborationDialog(voice)
    try:
        dialog.create()
        identity = dialog.identity
        dialog.source.setPlainText("x" * 100001)
        assert dialog.failed
        dialog.source.setPlainText("Release timing is undecided. リリース日は未定です。")
        assert not dialog.failed
        dialog.english.setPlainText("Release timing is undecided.")
        dialog.japanese.setPlainText("リリース日は未定です。")
        dialog.reviewed.setChecked(True)
        dialog.add_item()
        dialog.table.item(0, 1).setText("Confirm release timing")
        dialog.table.item(0, 7).setCheckState(Qt.Checked)
        assert dialog.store.read(identity)[1]["items"][0]["reviewed"]
        dialog.table.item(0, 3).setText("Tanaka")
        assert not dialog.store.read(identity)[1]["items"][0]["reviewed"]
        dialog.glossary.setPlainText("release = リリース")
        assert not dialog.store.read(identity)[1]["reviewed"]
        dialog.prepare()
        assert source_token(dialog.document) in voice.draft.toPlainText()
        assert "Do not use tools" in voice.draft.toPlainText()
        dialog.load(identity)
        assert dialog.table.item(0, 3).text() == "Tanaka"
        dialog.copy()
        assert "## 日本語" in app.clipboard().text()
        assert "Needs review" in app.clipboard().text()
    finally:
        app.clipboard().setText(clipboard)
        dialog.close()
        voice.close()
        dialog.deleteLater()
        voice.deleteLater()
        app.processEvents()


def test_ai_import_is_unreviewed_and_rejects_stale_reply(tmp_path):
    app = QApplication.instance() or QApplication([])
    clipboard = app.clipboard().text()
    voice = QWidget()
    voice.home, voice.locale = tmp_path, "ja"
    voice.draft = QPlainTextEdit(voice)
    dialog = CollaborationDialog(voice)
    try:
        dialog.create()
        dialog.source.setPlainText("リリース日は未定")
        reply = json.dumps({"source_token": source_token(dialog.document), "english": "Timing undecided", "japanese": "時期は未定", "items": []})
        dialog.response.setPlainText(reply)
        dialog.import_response()
        assert dialog.tabs.currentIndex() == 1
        assert dialog.english.toPlainText() == "Timing undecided"
        assert not dialog.reviewed.isChecked()
        dialog.source.setPlainText("リリース日は金曜日")
        dialog.response.setPlainText(reply)
        dialog.import_response()
        assert "変更" in dialog.state.text()
        assert dialog.store.read(dialog.identity)[1]["source"] == "リリース日は金曜日"
    finally:
        app.clipboard().setText(clipboard)
        dialog.close()
        voice.close()
        dialog.deleteLater()
        voice.deleteLater()
        app.processEvents()
