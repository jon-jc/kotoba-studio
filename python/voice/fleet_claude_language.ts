import { quoteStartupArg, tokenizeStartupCommand, type AgentStartupShell } from '../../../shared/tui-agent-startup-shell'
let settingsPath: string | null = null
export function setKotobaClaudeLanguageSettings(path: unknown): void {
  settingsPath = typeof path === 'string' && path.length > 0 ? path : null
}
export function claudeLanguageArgs(agent: string, args: string | null | undefined, shell: AgentStartupShell, localWindows: boolean): string | null | undefined {
  if (agent !== 'claude' || !localWindows || !settingsPath) return args
  const parsed = tokenizeStartupCommand(args ?? '', shell)
  // Respect custom settings and malformed input; the normal launch validator owns errors.
  if (!parsed.ok || parsed.tokens.some(token => token === '--settings' || token.startsWith('--settings=') || token === '--')) return args
  return `${args?.trim() ? args.trim() + ' ' : ''}--settings ${quoteStartupArg(settingsPath, shell)}`
}

let presentationLocale = ''
const presentedPanes = new Set<string>()

/** A locale change opens Japanese chat once per pane; explicit terminal returns stay open. */
export function setClaudePresentationLocale(locale: string): void {
  if (locale !== presentationLocale) {
    presentationLocale = locale
    presentedPanes.clear()
  }
}

export function claimJapaneseClaudeChat(paneId: string): boolean {
  if (presentationLocale !== 'ja' || presentedPanes.has(paneId)) return false
  presentedPanes.add(paneId)
  return true
}

/** Translate only Claude's exact sign-in status; conversation prose stays verbatim. */
export function localizedClaudeStatus(text: string, locale: string): string {
  return locale.startsWith('ja') && text.trim() === 'Not logged in · Please run /login'
    ? 'Claude Code にサインインしていません。ターミナルで /login を実行してから、チャットに戻ってください。'
    : text
}
