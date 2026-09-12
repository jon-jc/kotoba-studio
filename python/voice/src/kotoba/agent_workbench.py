"""Independent harness clients with a left-hand task list and one visible chat."""

import json
import uuid

from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QStackedWidget, QInputDialog, QMessageBox, QListWidget, QListWidgetItem, QFrame, QLineEdit)
from .design import outline_icon


STATE_SCRIPT = """(() => {
  const frame = document.querySelector('[data-kotoba-session]');
  const model = document.querySelector('[data-kotoba-provider]');
  let address = null;
  try { address = JSON.parse(localStorage.getItem('dsh.sessions.current') || '{}').subagentAddress || null; }
  catch (error) { if (!(error instanceof SyntaxError)) throw error; }
  return {ready: !!frame, session: frame?.dataset.kotobaSession || '',
    settled: frame?.dataset.kotobaSessionsReady === 'true',
    address,
    running: frame?.dataset.kotobaRunning === 'true',
    provider: model?.dataset.kotobaProvider || '', model: model?.dataset.kotobaModel || '',
    title: document.title.split(' — ')[0]};
})()"""


class AgentWorkbench(QWidget):
    """Own each browser independently; navigation never stops a host agent."""

    active_changed = Signal(object)
    created = Signal(object)
    history_requested = Signal()
    navigation_changed = Signal()

    def __init__(self, preferences, create_view, parent=None):
        super().__init__(parent)
        self.preferences, self.create_view = preferences, create_view
        restore_active = preferences.value('agents/active', '')
        self.locale = 'en'
        self.entries = []
        self.active = None
        self.origin = None
        self.stopped = False
        self.history = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(246)
        self.sidebar.setStyleSheet('QFrame {background:#16171b;border:0;border-right:1px solid #292c33;}')
        sidebar = QVBoxLayout(self.sidebar)
        sidebar.setContentsMargins(12, 18, 12, 12)
        sidebar.setSpacing(12)
        self.heading = QLabel()
        self.heading.setStyleSheet('font-size:11px;font-weight:600;color:#89919e;border:0;letter-spacing:1px;')
        sidebar.addWidget(self.heading)
        self.add_button = QPushButton()
        self.add_button.clicked.connect(lambda: self.add())
        self.add_button.setStyleSheet('text-align:left;padding:10px 12px;background:#24272d;border:1px solid #353a43;border-radius:8px;')
        sidebar.addWidget(self.add_button)
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self.refresh_labels())
        sidebar.addWidget(self.search)
        self.list = QListWidget()
        self.list.setSpacing(4)
        self.list.setIconSize(QSize(24, 24))
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.setStyleSheet('QListWidget {background:transparent;border:0;outline:0;}'
            'QListWidget::item {padding:10px;border:1px solid transparent;border-radius:8px;color:#b7bdc9;}'
            'QListWidget::item:selected {background:#282d33;border-color:#3d4e48;color:#eef5f0;}'
            'QListWidget::item:hover:!selected {background:#202329;}')
        self.list.currentRowChanged.connect(self.select)
        self.list.itemDoubleClicked.connect(lambda item: self.rename(self.list.row(item)))
        sidebar.addWidget(self.list, 1)
        self.history_button = QPushButton()
        self.history_button.setObjectName('ghost')
        self.history_button.clicked.connect(self.history_requested)
        sidebar.addWidget(self.history_button)
        self.close_button = QPushButton()
        self.close_button.setObjectName('ghost')
        self.close_button.clicked.connect(lambda: self.request_close(self.list.currentRow()))
        sidebar.addWidget(self.close_button)
        layout.addWidget(self.sidebar)
        conversation = QVBoxLayout()
        conversation.setContentsMargins(0, 0, 0, 0)
        conversation.setSpacing(0)
        self.back_button = QPushButton()
        self.back_button.setObjectName('ghost')
        self.back_button.clicked.connect(lambda: self.set_history(False))
        conversation.addWidget(self.back_button, 0, Qt.AlignLeft)
        self.back_button.hide()
        self.context = QLabel()
        self.context.setTextFormat(Qt.PlainText)
        self.context.setStyleSheet('color:#a8afbd;background:#1c1e23;padding:8px 16px;font-size:12px;')
        conversation.addWidget(self.context)
        self.pages = QStackedWidget()
        conversation.addWidget(self.pages, 1)
        layout.addLayout(conversation, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(1200)
        self.timer.timeout.connect(self.poll)
        for key, action in [('Ctrl+T', lambda: self.add()),
                            ('Ctrl+Tab', lambda: self.cycle(1)),
                            ('Ctrl+Shift+Tab', lambda: self.cycle(-1))]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(action)
        for position in range(9):
            shortcut = QShortcut(QKeySequence(f'Ctrl+{position + 1}'), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda i=position: self.list.setCurrentRow(i) if i < len(self.entries) else None)
        rename = QShortcut(QKeySequence('F2'), self.list)
        rename.setContext(Qt.WidgetShortcut)
        rename.activated.connect(lambda: self.rename(self.list.currentRow()))
        try:
            saved = json.loads(preferences.value('agents/views', '[]'))
        except (ValueError, TypeError):
            saved = []
        if not isinstance(saved, list):
            saved = []
        for item in saved:
            if isinstance(item, dict) and isinstance(item.get('id'), str):
                try:
                    identity = 'primary' if item['id'] == 'primary' else str(uuid.UUID(item['id']))
                except ValueError:
                    continue
                if not any(e['id'] == identity for e in self.entries):
                    session = item.get('session', '')
                    self.add(identity, str(item.get('label', ''))[:80], session if isinstance(session, str) and len(session) <= 256 else '', item.get('address'))
        if not self.entries:
            self.add('primary')
        self.list.setCurrentRow(next((i for i, e in enumerate(self.entries) if e['id'] == restore_active), 0))
        self.set_locale('en')

    def add(self, identity=None, label='', session='', address=None):
        self.search.clear()
        identity = identity or str(uuid.uuid4())
        view = self.create_view(identity)
        entry = dict(id=identity, label=label, view=view, title='', provider='', model='',
                     running=False, ready=False, unread=False, pending=False, session=session,
                     address=self.child_address(address, session))
        self.install_selection(entry)
        self.entries.append(entry)
        self.pages.addWidget(view)
        item = QListWidgetItem('')
        item.setIcon(outline_icon('chat'))
        item.setSizeHint(QSize(210, 76))
        self.list.addItem(item)
        self.list.setCurrentRow(len(self.entries) - 1)
        self.select(len(self.entries) - 1)
        self.created.emit(view)
        if self.origin is not None:
            view.page().origin = self.origin
            view.load(self.origin)
        self.save()
        return view

    def save(self):
        self.preferences.setValue('agents/views', json.dumps([
            {'id': e['id'], 'label': e['label'], 'session': e['session'], 'address': e['address']} for e in self.entries]))

    @staticmethod
    def child_address(value, session):
        """Keep the parent address required to reopen a child conversation."""
        if not isinstance(value, dict) or value.get('childSessionId') != session:
            return None
        parent = value.get('parentSessionId')
        if not isinstance(parent, str) or not 0 < len(parent) <= 256 or value.get('mode') not in ('one-shot', 'continuable'):
            return None
        return {key: value[key] for key in ('parentSessionId', 'childSessionId', 'mode')}

    def install_selection(self, entry):
        """Restore only selection, across the runtime's changing loopback port."""
        scripts = entry['view'].page().scripts()
        for old in scripts.find('kotoba-selection'):
            scripts.remove(old)
        script = QWebEngineScript()
        script.setName('kotoba-selection')
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setWorldId(QWebEngineScript.MainWorld)
        selection = {'sessionId': entry['session']} if entry['session'] else {}
        if entry['address']:
            selection['subagentAddress'] = entry['address']
        script.setSourceCode("if(location.protocol==='http:' && location.hostname==='127.0.0.1'){localStorage.setItem('dsh.sessions.current'," + json.dumps(json.dumps(selection)) + ");}")
        scripts.insert(script)

    def select(self, index):
        if not 0 <= index < len(self.entries):
            return
        self.active = self.entries[index]
        self.preferences.setValue('agents/active', self.active['id'])
        self.active['unread'] = False
        self.pages.setCurrentWidget(self.active['view'])
        self.set_history(False)
        self.active_changed.emit(self.active['view'])
        self.refresh_labels()

    def cycle(self, direction):
        self.list.setCurrentRow((self.list.currentRow() + direction) % len(self.entries))

    def set_history(self, visible):
        self.history = visible
        self.sidebar.setVisible(not visible)
        self.back_button.setVisible(visible)
        self.navigation_changed.emit()

    def rename(self, index):
        if not 0 <= index < len(self.entries):
            return
        entry = self.entries[index]
        text, ok = QInputDialog.getText(self, self.tr('Name this chat', 'チャット名'),
            self.tr('Name', '名前'), text=entry['label'] or entry['title'])
        if ok:
            entry['label'] = text.strip()[:80]
            self.save()
            self.refresh_labels()

    def request_close(self, index):
        if len(self.entries) < 2:
            return
        result = QMessageBox.question(self, self.tr('Close chat view?', 'チャット表示を閉じますか？'),
            self.tr('Saved conversations remain in the sidebar. Running agents continue. Unsaved drafts in this view may be lost.',
                    '保存済みの会話はサイドバーに残り、実行中のエージェントは継続します。この表示の未送信の下書きは失われる可能性があります。'),
            QMessageBox.Close | QMessageBox.Cancel, QMessageBox.Cancel)
        if result == QMessageBox.Close:
            self.close_view(index)

    def close_view(self, index):
        if len(self.entries) < 2 or not 0 <= index < len(self.entries):
            return
        entry = self.entries.pop(index)
        self.list.blockSignals(True)
        self.list.takeItem(index)
        self.list.setCurrentRow(max(0, min(index, len(self.entries) - 1)))
        self.list.blockSignals(False)
        self.pages.removeWidget(entry['view'])
        entry['view'].deleteLater()
        self.select(max(0, min(index, len(self.entries) - 1)))
        self.save()

    def load(self, origin):
        self.origin = origin
        for entry in self.entries:
            entry['view'].page().origin = origin
            entry['view'].load(origin)
        self.timer.start()

    def poll(self):
        for entry in self.entries:
            if entry['pending']:
                continue
            entry['pending'] = True
            entry['view'].page().runJavaScript('JSON.stringify(' + STATE_SCRIPT + ')', lambda state, e=entry: self.update_state(e, state))

    def update_state(self, entry, state):
        if self.stopped or entry not in self.entries:
            return
        entry['pending'] = False
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except ValueError:
                state = None
        if not isinstance(state, dict):
            entry['ready'] = False
        else:
            session = state.get('session')
            address = self.child_address(state.get('address'), session)
            if state.get('settled') and isinstance(session, str) and len(session) <= 256 and (session != entry['session'] or address != entry['address']):
                entry['session'] = session
                entry['address'] = address
                self.install_selection(entry)
                self.save()
            if entry['running'] and not state.get('running') and state.get('settled') and entry is not self.active:
                entry['unread'] = True
            for key in ('title', 'provider', 'model'):
                entry[key] = str(state.get(key, ''))[:200]
            if not state.get('session'):
                entry['title'] = ''
            entry['ready'] = state.get('ready') is True
            entry['running'] = state.get('running') is True
        self.refresh_labels()

    def tr(self, en, ja):
        return en if self.locale == 'en' else ja

    def set_locale(self, locale):
        self.locale = locale
        self.add_button.setText(self.tr('+ New agent', '＋ 新しいエージェント'))
        self.add_button.setToolTip(self.tr('Independent chat · Ctrl+T', '独立したチャット · Ctrl+T'))
        self.history_button.setText(self.tr('History / workspaces', '履歴とワークスペース'))
        self.back_button.setText(self.tr('‹ Back to agents', '‹ エージェントに戻る'))
        self.heading.setText(self.tr('YOUR AGENTS', 'マイエージェント'))
        self.search.setPlaceholderText(self.tr('Find an agent…', 'エージェントを検索…'))
        self.search.setAccessibleName(self.search.placeholderText())
        self.list.setAccessibleName(self.tr('Agent chats', 'エージェントのチャット'))
        self.close_button.setText(self.tr('Close selected chat', '選択したチャットを閉じる'))
        self.refresh_labels()

    def refresh_labels(self):
        for index, entry in enumerate(self.entries):
            title = entry['label'] or entry['title'] or self.tr('New chat', '新しいチャット')
            status = '● ' if entry['running'] else '✓ ' if entry['unread'] else ''
            route = ' / '.join(filter(None, [entry['provider'], entry['model']]))
            detail = route or self.tr('Choose a model', 'モデルを選択')
            self.list.item(index).setText(status + title[:32] + '\n' + detail[:36])
            self.list.item(index).setToolTip(title + ('\n' + route if route else '') + '\n' +
                self.tr('Double-click to rename', 'ダブルクリックで名前を変更'))
            self.list.item(index).setHidden(self.search.text().casefold() not in (title + ' ' + route).casefold())
        self.close_button.setEnabled(len(self.entries) > 1)
        if self.active:
            entry = self.active
            route = ' / '.join(filter(None, [entry['provider'], entry['model']]))
            status = self.tr('Running', '実行中') if entry['running'] else self.tr('Ready', '準備完了') if entry['ready'] else self.tr('Connecting', '接続中')
            count = sum(e['running'] for e in self.entries)
            self.context.setText(f'{status}  ·  {route}' if route else self.tr('Choose a provider and model in this chat’s composer', 'このチャットの入力欄でプロバイダーとモデルを選択'))
            if count:
                self.context.setText(self.context.text() + self.tr(f'    ·    {count} agents running', f'    ·    {count} 件のエージェントが実行中'))

    def shutdown(self):
        self.stopped = True
        self.timer.stop()
