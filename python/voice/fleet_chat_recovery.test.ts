import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  toast: vi.fn(), i18n: { language: 'en' },
  state: { openSettingsPage: vi.fn(), openSettingsTarget: vi.fn() }
}))
vi.mock('sonner', () => ({ toast: { error: mocks.toast } }))
vi.mock('@/i18n/i18n', () => ({ i18n: mocks.i18n }))
vi.mock('@/store', () => ({ useAppStore: { getState: () => mocks.state } }))
import { showKotobaChatRecovery } from './kotoba-chat-recovery'

beforeEach(() => { vi.clearAllMocks(); mocks.i18n.language = 'en' })
describe('Claude authentication recovery', () => {
  it.each(['en', 'ja'])('offers an actionable sign-in recovery in %s', language => {
    mocks.i18n.language = language
    const error = new Error('Claude is not signed in for the selected account. Sign in with the Claude CLI for this CLAUDE_CONFIG_DIR, then retry.')
    expect(showKotobaChatRecovery('claude', error)).toBe(true)
    const [title, options] = mocks.toast.mock.calls[0]
    expect(title).toBe(language === 'ja' ? 'Claude Code にサインインしてください' : 'Sign in to Claude Code')
    expect(options.description).not.toContain('CLAUDE_CONFIG_DIR')
    expect(options.action.label).toBe(language === 'ja' ? 'アカウントを接続' : 'Connect account')
    options.action.onClick()
    expect(mocks.state.openSettingsPage).toHaveBeenCalledOnce()
    expect(mocks.state.openSettingsTarget).toHaveBeenCalledWith({ pane: 'accounts', repoId: null, sectionId: 'accounts-claude' })
  })
  it('does not reclassify transport errors, other agents, or non-errors', () => {
    expect(showKotobaChatRecovery('claude', new Error('Connection timed out'))).toBe(false)
    expect(showKotobaChatRecovery('codex', new Error('Claude is not signed in for the selected account.'))).toBe(false)
    expect(showKotobaChatRecovery('claude', 'Claude is not signed in for the selected account.')).toBe(false)
    expect(mocks.toast).not.toHaveBeenCalled()
  })
})
