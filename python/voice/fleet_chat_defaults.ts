import type { GlobalSettings } from './global-settings-types'

/** Old Kotoba builds persisted the upstream terminal-only defaults. Upgrade once. */
export function migrateKotobaChatDefaults(settings: Partial<GlobalSettings> | undefined) {
  if (settings?.kotobaChatDefaultsMigrated === true) return {}
  return {
    kotobaChatDefaultsMigrated: true,
    experimentalNativeChat: true,
    experimentalStructuredNativeChat: true,
    openAgentTabsInChatByDefault: true
  }
}
