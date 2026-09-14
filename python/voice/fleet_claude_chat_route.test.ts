import { describe, expect, it } from 'vitest'
import { resolveAgentLaunchRoute, structuredAgentLaunchSupported } from './agent-launch-routing'
import { STRUCTURED_AGENT_SESSION_RUNTIME_CAPABILITY } from '../../../shared/protocol-version'

const input = {
  agent: 'claude' as const,
  settings: { experimentalNativeChat: true, experimentalStructuredNativeChat: true, openAgentTabsInChatByDefault: true },
  executionHostId: 'local', hostCapabilities: [STRUCTURED_AGENT_SESSION_RUNTIME_CAPABILITY],
  workspaceKind: 'git-worktree' as const, nativeChatTranscriptIsLocalReadable: true
}
describe('Claude pre-prompt chat compatibility', () => {
  it('opens a real conversation without waiting for a post-prompt init frame', () => {
    expect(resolveAgentLaunchRoute(input)).toBe('legacy-native-chat')
    expect(structuredAgentLaunchSupported(input)).toBe(false)
    expect(resolveAgentLaunchRoute({ ...input, agent: 'codex' })).toBe('structured-native-chat')
  })
  it('preserves explicit terminal launches and remote ownership', () => {
    expect(resolveAgentLaunchRoute({ ...input, settings: { ...input.settings, openAgentTabsInChatByDefault: false } })).toBe('terminal-tui')
    expect(resolveAgentLaunchRoute({ ...input, executionHostId: 'ssh:work' })).toBe('legacy-native-chat')
  })
})
