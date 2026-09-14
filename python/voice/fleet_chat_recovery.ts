import { toast } from 'sonner'
import { i18n } from '@/i18n/i18n'
import { useAppStore } from '@/store'

// Only classify the provider's explicit authentication refusal. Other failures
// keep the normal reconciliation and error path; they must not create siblings.
export function showKotobaChatRecovery(agent: string, error: unknown): boolean {
  if (agent !== 'claude' || !(error instanceof Error) ||
      !error.message.startsWith('Claude is not signed in for the selected account.')) return false
  const ja = i18n.language.startsWith('ja')
  toast.error(ja ? 'Claude Code にサインインしてください' : 'Sign in to Claude Code', {
    id: 'kotoba-claude-sign-in', duration: Infinity,
    description: ja
      ? '選択したアカウントにログイン情報がありません。アカウント設定でサインインし、左側の「新しいチャット」から再度開いてください。プロジェクトはそのまま保持されます。'
      : 'The selected account is not signed in. Connect it in Agent accounts, then retry New chat in the sidebar. Your project stays selected.',
    action: { label: ja ? 'アカウントを接続' : 'Connect account', onClick: () => {
      const state = useAppStore.getState()
      state.openSettingsPage()
      state.openSettingsTarget({ pane: 'accounts', repoId: null, sectionId: 'accounts-claude' })
    } }
  })
  return true
}
