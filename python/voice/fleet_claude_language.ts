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
