import { useRef } from 'react'
import { MessageSquarePlus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAppStore } from '@/store'
import { focusTerminalTabSurface } from '@/lib/focus-terminal-tab-surface'
import { KotobaNewChat } from '../tab-bar/KotobaNewChat'

export function KotobaSidebarChat(): React.JSX.Element {
  const { i18n } = useTranslation()
  const worktreeId = useAppStore(state => state.activeWorktreeId)
  const pendingFocus = useRef<string | null>(null)
  if (!worktreeId) return <button type="button"
    className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-[13px] font-medium text-worktree-sidebar-foreground hover:bg-worktree-sidebar-foreground/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    onClick={() => useAppStore.getState().openModal('add-repo')}>
    <MessageSquarePlus className="size-4" aria-hidden="true" />
    {i18n.language.startsWith('ja') ? 'プロジェクトを追加してチャット' : 'Add a project to chat'}
  </button>
  return <KotobaNewChat sidebar worktreeId={worktreeId}
    onFocusTerminal={id => { pendingFocus.current = id }}
    onMenuClose={() => {
      const id = pendingFocus.current
      pendingFocus.current = null
      if (id) focusTerminalTabSurface(id)
      return Boolean(id)
    }} />
}
