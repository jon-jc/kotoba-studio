import { MessageSquare, Terminal, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useAppStore } from '@/store'
import { useDetectedAgents } from '@/hooks/useDetectedAgents'
import { useAgentDetectionTargetForWorktree } from '@/hooks/useAgentDetectionTarget'
import { launchAgentInNewTab } from '@/lib/launch-agent-in-new-tab'
import { useStructuredAgentLaunchStatus } from '@/lib/structured-agent-session-launch'
import { getAgentCatalog } from '@/lib/agent-catalog'
import { isNativeChatSupportedAgent, nativeChatRequiresLocalTranscript } from '../../../../shared/native-chat-agent-support'
import type { TuiAgent } from '../../../../shared/tui-agent'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

export function KotobaNewChat({ worktreeId, groupId, onFocusTerminal, onMenuClose }: {
  worktreeId: string; groupId: string; onFocusTerminal: (id: string) => void; onMenuClose: () => void
}): React.JSX.Element {
  const { i18n } = useTranslation()
  const text = (en: string, ja: string) => i18n.language.startsWith('ja') ? ja : en
  const target = useAgentDetectionTargetForWorktree(worktreeId)
  const { detectedIds } = useDetectedAgents(target)
  const disabled = useAppStore(state => state.settings?.disabledTuiAgents)
  const defaultAgent = useAppStore(state => state.settings?.defaultTuiAgent)
  const pending = { codex: useStructuredAgentLaunchStatus(worktreeId, 'codex'),
    claude: useStructuredAgentLaunchStatus(worktreeId, 'claude') }
  const agents = getAgentCatalog().filter(agent => detectedIds?.includes(agent.id) && !disabled?.includes(agent.id))
    .sort((a, b) => Number(b.id === defaultAgent) - Number(a.id === defaultAgent))
  const chats = agents.filter(agent => isNativeChatSupportedAgent(agent.id) &&
    (!nativeChatRequiresLocalTranscript(agent.id) || target?.kind === 'local'))
  const label = (agent: { id: TuiAgent; label: string }) => agent.id === 'claude' ? 'Claude Code' : agent.label
  const launch = (agent: TuiAgent, viewMode: 'chat' | 'terminal') => {
    const result = launchAgentInNewTab({ agent, worktreeId, groupId, viewMode })
    if (!result) { toast.error(text('Could not open this agent. Check Agent accounts.', 'エージェントを開けません。アカウント設定を確認してください。')); return }
    if (result.tabId) onFocusTerminal(result.tabId)
  }
  return <DropdownMenu modal={false}>
    <DropdownMenuTrigger asChild>
      <button className="ml-2 my-auto inline-flex h-7 shrink-0 items-center gap-1.5 rounded-md border border-border/70 px-2.5 text-xs text-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        <MessageSquare className="size-3.5" aria-hidden="true" />{text('New chat', '新しいチャット')}
      </button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" className="w-64 max-h-[70vh] overflow-y-auto" onCloseAutoFocus={event => { event.preventDefault(); onMenuClose() }}>
      <DropdownMenuLabel>{text('Conversation', '会話')}</DropdownMenuLabel>
      {chats.map(agent => <DropdownMenuItem key={agent.id} disabled={(agent.id === 'codex' || agent.id === 'claude') && pending[agent.id] === 'pending'} onSelect={() => launch(agent.id, 'chat')}>
        <MessageSquare className="size-4" />{label(agent)}{text(' chat', ' チャット')}
      </DropdownMenuItem>)}
      {!chats.length && <DropdownMenuItem disabled>{text('No chat-capable agents enabled here', 'ここで利用できるチャット対応エージェントがありません')}</DropdownMenuItem>}
      <DropdownMenuSeparator />
      <DropdownMenuLabel>{text('Interactive terminal', '対話型ターミナル')}</DropdownMenuLabel>
      {agents.map(agent => <DropdownMenuItem key={agent.id} onSelect={() => launch(agent.id, 'terminal')}>
        <Terminal className="size-4" />{label(agent)}{text(' terminal', ' ターミナル')}
      </DropdownMenuItem>)}
      <DropdownMenuSeparator />
      <DropdownMenuItem onSelect={() => { const state = useAppStore.getState(); state.openSettingsPage(); state.openSettingsTarget({ pane: 'accounts', repoId: null }) }}>
        <Settings className="size-4" />{text('Agent accounts', 'エージェントのアカウント')}
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
}
