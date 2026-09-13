// Kotoba tools share the selected Orca worktree; drafts never submit a turn.
import { i18n } from '../i18n/i18n'
import { useAppStore } from '../store'

i18n.use({ type: 'postProcessor', name: 'kotobaBrand', process: (value: string) => /Orca (Mobile|account)/i.test(value) ? value : value.replace(/\bOrca\b|\bORCA\b/g, 'Kotoba Studio') })
i18n.options.postProcess = ['kotobaBrand']
let appliedLocale = ''

Object.assign(window, {
  kotobaWorkspace: {
    navigate(target: string) {
      const state = useAppStore.getState()
      if (target === 'sidebar') state.setSidebarOpen(true)
      else if (target === 'permissions' || target === 'accounts') {
        state.openSettingsPage()
        state.openSettingsTarget({ pane: target === 'permissions' ? 'agents' : 'accounts', repoId: null })
      }
      else return false
      return true
    },
    snapshot(language: unknown) {
      const state = useAppStore.getState()
      if ((language === 'en' || language === 'ja') && state.settings && appliedLocale !== language) {
        appliedLocale = language
        void i18n.changeLanguage(language)
        void state.updateSettings({ uiLanguage: language })
      }
      const worktree = Object.values(state.worktreesByRepo).flat().find(row => row.id === state.activeWorktreeId)
      return {
        title: worktree?.displayName ?? '',
        path: worktree?.path ?? '',
        local: worktree?.hostId === 'local' || (worktree !== undefined && !worktree.hostId),
        tasks: Object.values(state.tabsByWorktree).flat().length,
      }
    },
    async addProject(path: string) {
      const repo = await useAppStore.getState().addRepoPath(path, 'git', { runtimeEnvironmentId: null })
      if (!repo) return false
      await useAppStore.getState().fetchWorktrees(repo.id)
      const state = useAppStore.getState()
      const worktree = state.worktreesByRepo[repo.id]?.find(row => row.path.toLowerCase().replaceAll('\\', '/') === path.toLowerCase().replaceAll('\\', '/'))
      if (worktree) state.setActiveWorktree(worktree.id, worktree.hostId)
      state.setSidebarOpen(true)
      return true
    },
    draft(text: string) {
      const state = useAppStore.getState()
      const tab = Object.values(state.tabsByWorktree).flat().find(row => row.id === state.activeTabId)
      const inputs = Array.from(document.querySelectorAll<HTMLElement>('[data-composer-scope-key] [contenteditable="true"]'))
        .filter(input => input.getClientRects().length > 0)
      if (!tab?.launchAgent || inputs.length !== 1 || inputs[0]!.innerText.trim() || !text.trim()) return false
      state.seedNativeChatLaunchDraft({ tabId: tab.id, agent: tab.launchAgent, text, createdAt: Date.now() })
      return true
    },
  },
})
