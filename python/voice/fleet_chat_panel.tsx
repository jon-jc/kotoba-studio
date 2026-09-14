import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare } from 'lucide-react'
import type { GlobalSettings } from '../../../../shared/global-settings-types'

export function KotobaAgentChat({ settings, updateSettings }: {
  settings: GlobalSettings
  updateSettings: (updates: Partial<GlobalSettings>) => void | Promise<void>
}): React.JSX.Element {
  const { i18n } = useTranslation()
  const text = (en: string, ja: string) => i18n.language.startsWith('ja') ? ja : en
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  const chat = settings.experimentalNativeChat && settings.openAgentTabsInChatByDefault
  const choose = async (value: string) => {
    setSaving(true); setError(false)
    try {
      await updateSettings({ kotobaChatDefaultsMigrated: true, experimentalNativeChat: true,
        experimentalStructuredNativeChat: true, openAgentTabsInChatByDefault: value === 'chat' })
    } catch { setError(true) } finally { setSaving(false) }
  }
  return <section aria-labelledby="kotoba-chat-title" className="rounded-2xl border border-border/70 bg-card/40 p-5 space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-primary/10 p-2.5 text-primary"><MessageSquare className="size-5" /></div>
        <h2 id="kotoba-chat-title" className="text-base font-semibold">{text('Agent conversations', 'エージェントとの会話')}</h2>
      </div>
      <select aria-label={text('New agent view', '新規エージェントの表示')} disabled={saving}
        value={chat ? 'chat' : 'terminal'} onChange={event => { void choose(event.target.value) }}
        className="h-9 min-w-40 rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <option value="chat">{text('Chat', 'チャット')}</option>
        <option value="terminal">{text('Terminal', 'ターミナル')}</option>
      </select>
    </div>
    <p className="text-sm text-muted-foreground">{text(
      'Start a new Codex or Claude Code task with a conversation, model selector, message composer, and reviewable tool activity. Each task keeps its own context and account.',
      'Codex や Claude Code の新規タスクを、会話・モデル選択・メッセージ入力・ツールの実行履歴を備えたチャットで開始。タスクごとにコンテキストとアカウントを保持します。')}</p>
    <p className="text-xs text-muted-foreground">{text(
      'Existing sessions keep their current view. Agents without chat support, including OpenCode and Pi, use their interactive terminal. API chat remains available for configured models.',
      '既存セッションの表示は維持されます。OpenCode や Pi などチャット非対応のエージェントは対話型ターミナルを使用します。設定済みモデルは API チャットでも利用できます。')}</p>
    {error && <p role="alert" className="text-sm text-destructive">{text('Could not save. Please try again.', '保存できませんでした。もう一度お試しください。')}</p>}
  </section>
}
