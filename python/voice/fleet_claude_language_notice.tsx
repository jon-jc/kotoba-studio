import { useTranslation } from 'react-i18next'
import { MessageSquare } from 'lucide-react'
export function KotobaClaudeLanguageNotice({ onOpenChat }: { onOpenChat: () => void }): React.JSX.Element | null {
  const { i18n } = useTranslation()
  if (!i18n.language.startsWith('ja')) return null
  return <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/30 px-4 py-2 text-xs">
    <div className="min-w-0 text-muted-foreground">
      <span className="font-medium text-foreground">Claude Code のターミナル</span>
      <span className="ml-2">提供元のメニューは英語です。日本語の操作画面はチャット表示をご利用ください。</span>
    </div>
    <button type="button" onClick={onOpenChat} className="inline-flex shrink-0 items-center gap-2 rounded-md border border-input bg-background px-3 py-1.5 font-medium hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <MessageSquare className="size-3.5" aria-hidden="true" />日本語のチャット表示
    </button>
  </div>
}
