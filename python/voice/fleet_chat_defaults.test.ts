import { describe, expect, it } from 'vitest'
import { migrateKotobaChatDefaults } from './kotoba-chat-defaults'
import { getDefaultSettings } from './constants'

describe('Kotoba agent conversation defaults', () => {
  it('upgrades persisted terminal-only profiles once', () => {
    expect(migrateKotobaChatDefaults({ experimentalNativeChat: false })).toEqual({
      kotobaChatDefaultsMigrated: true, experimentalNativeChat: true,
      experimentalStructuredNativeChat: true, openAgentTabsInChatByDefault: true
    })
  })
  it('preserves a later user preference for terminal view or disabling chat', () => {
    expect(migrateKotobaChatDefaults({ kotobaChatDefaultsMigrated: true,
      experimentalNativeChat: false, openAgentTabsInChatByDefault: false })).toEqual({})
  })
  it('starts new profiles with chat enabled', () => {
    const settings = getDefaultSettings('/tmp/kotoba-test')
    expect(settings.experimentalNativeChat).toBe(true)
    expect(settings.experimentalStructuredNativeChat).toBe(true)
    expect(settings.openAgentTabsInChatByDefault).toBe(true)
    expect(settings.kotobaChatDefaultsMigrated).toBe(true)
  })
})
