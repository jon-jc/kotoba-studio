import { useTranslation } from 'react-i18next'
import { Terminal } from 'lucide-react'

/** Keep first-run Claude questions visible; never answer a trust prompt for the user. */
export function KotobaClaudeSetup({ onOpenTerminal }: {
  onOpenTerminal?: () => void
}): React.JSX.Element {
  const { i18n } = useTranslation()
  const ja = i18n.language.startsWith('ja')
  return <section role="status" className="mx-4 mb-4 rounded-xl border border-border bg-muted/40 p-4">
    <div className="mb-2 flex items-center gap-2 text-sm font-medium">
      <Terminal className="size-4" aria-hidden="true" />
      {ja ? 'Claude Code を起動しています' : 'Starting Claude Code'}
    </div>
    <p className="text-sm text-muted-foreground">{ja
      ? '初回はターミナルでワークスペースの信頼確認やサインインが必要な場合があります。設定を完了してチャットに戻ると、メッセージを送信できます。'
      : 'First launch may require workspace trust or sign-in in the terminal. Finish setup, then return to Chat to send your message.'}</p>
    {onOpenTerminal && <button type="button" onClick={onOpenTerminal}
      className="mt-3 rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      {ja ? 'Claude のターミナルを開く' : 'Open Claude terminal'}
    </button>}
  </section>
}
