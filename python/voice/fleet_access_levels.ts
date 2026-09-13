import type { GlobalSettings } from './global-settings-types'
import { tokenizeStartupCommand, type AgentStartupShell } from './tui-agent-startup-shell'

export const ACCESS_LEVELS = ['plan', 'ask', 'workspace'] as const
export type AccessLevel = typeof ACCESS_LEVELS[number]
export const ACCESS_AGENTS = ['codex', 'claude', 'opencode'] as const
export type AccessAgent = typeof ACCESS_AGENTS[number]

const ARGS = {
  codex: {
    plan: '--sandbox read-only --ask-for-approval never',
    ask: '--sandbox read-only --ask-for-approval on-request',
    workspace: '--sandbox workspace-write --ask-for-approval on-request'
  },
  claude: {
    plan: '--permission-mode plan',
    ask: '--permission-mode default',
    workspace: '--permission-mode acceptEdits'
  },
  opencode: { plan: '', ask: '', workspace: '' }
} satisfies Record<AccessAgent, Record<AccessLevel, string>>

const valueFlags = new Set(['--sandbox', '-s', '--ask-for-approval', '-a', '--permission-mode'])
const bypassFlags = new Set(['--dangerously-bypass-approvals-and-sandbox', '--dangerously-skip-permissions', '--allow-dangerously-skip-permissions', '--approve-for-me', '--full-auto', '--auto', '--yolo'])
const otherValueFlags = new Set(['--model', '-m', '--effort', '--reasoning-effort', '--profile', '-p', '--add-dir', '--plugin-dir'])

export function accessArguments(agent: AccessAgent, level: AccessLevel, source: string, shell: AgentStartupShell = 'posix'): string {
  if (!ACCESS_AGENTS.includes(agent) || !ACCESS_LEVELS.includes(level)) throw new Error('Unsupported agent access level')
  const parsed = tokenizeStartupCommand(source, shell)
  if (!parsed.ok || parsed.spans.some(span => span.divergesFromShell)) throw new Error('Review custom launch arguments before applying an access level.')
  const removed = new Set<number>()
  for (let i = 0; i < parsed.tokens.length; i++) {
    const token = parsed.tokens[i]!
    const equals = token.indexOf('=')
    const flag = equals < 0 ? token : token.slice(0, equals)
    if (otherValueFlags.has(flag)) { if (equals < 0) i++; continue }
    if (flag === '--config' || flag === '-c') {
      const value = equals < 0 ? parsed.tokens[i + 1] : token.slice(equals + 1)
      if (/^(sandbox_mode|approval_policy|sandbox_workspace_write\.[\w.]+)\s*=/.test(value ?? '')) {
        removed.add(i)
        if (equals < 0) removed.add(++i)
      } else if (equals < 0) i++
      continue
    }
    if (valueFlags.has(flag) || (agent === 'opencode' && flag === '--agent')) {
      removed.add(i)
      if (equals < 0) {
        if (i + 1 >= parsed.tokens.length) throw new Error('A permission argument is missing its value.')
        removed.add(++i)
      }
    } else if (bypassFlags.has(flag)) removed.add(i)
  }
  const retained = parsed.spans.filter((_, i) => !removed.has(i)).map(span => source.slice(span.start, span.end)).join(' ')
  return [retained, ARGS[agent][level]].filter(Boolean).join(' ').trim()
}

function openCodeConfig(level: AccessLevel, raw?: string): Record<string, unknown> {
  let previous: Record<string, unknown> = {}
  if (raw) {
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Review OpenCode inline configuration before applying access.')
    previous = parsed as Record<string, unknown>
  }
  const permissions = level === 'plan'
    ? { '*': 'deny', read: { '*': 'allow', '*.env': 'deny', '*.env.*': 'deny', '*.env.example': 'allow' }, glob: 'allow', grep: 'allow', list: 'allow', lsp: 'allow', question: 'allow', edit: 'deny', bash: 'deny', external_directory: 'deny' }
    : { '*': 'ask', read: { '*': 'allow', '*.env': 'deny', '*.env.*': 'deny', '*.env.example': 'allow' }, glob: 'allow', grep: 'allow', list: 'allow', question: 'allow', edit: level === 'workspace' ? 'allow' : 'ask', bash: 'ask', external_directory: 'ask' }
  const agents = previous.agent && typeof previous.agent === 'object' && !Array.isArray(previous.agent) ? previous.agent as Record<string, object> : {}
  return { ...previous, permission: permissions, default_agent: level === 'plan' ? 'plan' : 'build', agent: { ...agents, build: { ...agents.build, permission: permissions }, plan: { ...agents.plan, permission: permissions } } }
}

export function applyAccessLevel(settings: Pick<GlobalSettings, 'agentDefaultArgs' | 'agentDefaultEnv'>, agent: AccessAgent, level: AccessLevel, shell: AgentStartupShell = 'posix'): Pick<GlobalSettings, 'agentDefaultArgs' | 'agentDefaultEnv'> {
  const args = accessArguments(agent, level, settings.agentDefaultArgs?.[agent] ?? '', shell)
  const environment = { ...settings.agentDefaultEnv?.[agent] }
  if (agent === 'opencode') {
    environment.OPENCODE_CONFIG_CONTENT = JSON.stringify(openCodeConfig(level, environment.OPENCODE_CONFIG_CONTENT))
    delete environment.OPENCODE_PERMISSION
  }
  return { agentDefaultArgs: { ...settings.agentDefaultArgs, [agent]: args }, agentDefaultEnv: { ...settings.agentDefaultEnv, [agent]: environment } }
}

export function currentAccessLevel(settings: Pick<GlobalSettings, 'agentDefaultArgs' | 'agentDefaultEnv'>, agent: AccessAgent): AccessLevel | 'custom' {
  const args = settings.agentDefaultArgs?.[agent]?.trim() ?? ''
  if (agent === 'opencode') {
    try {
      const raw = settings.agentDefaultEnv?.opencode?.OPENCODE_CONFIG_CONTENT
      if (!raw) return 'custom'
      const config = JSON.parse(raw)
      for (const level of ACCESS_LEVELS) {
        const expected = openCodeConfig(level)
        if (config.default_agent === expected.default_agent &&
          JSON.stringify(config.permission) === JSON.stringify(expected.permission) &&
          JSON.stringify(config.agent?.build?.permission) === JSON.stringify(expected.permission) &&
          JSON.stringify(config.agent?.plan?.permission) === JSON.stringify(expected.permission) &&
          !settings.agentDefaultEnv?.opencode?.OPENCODE_PERMISSION &&
          accessArguments(agent, level, args) === args) return level
      }
    } catch { return 'custom' }
    return 'custom'
  }
  for (const level of ACCESS_LEVELS) {
    try { if (accessArguments(agent, level, args) === args) return level } catch { return 'custom' }
  }
  return 'custom'
}
