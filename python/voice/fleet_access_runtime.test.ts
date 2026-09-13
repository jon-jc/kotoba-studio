import { afterEach, describe, expect, it, vi } from 'vitest'
import { OrcaRuntimeService } from './orca-runtime'
import { applyAccessLevel, ACCESS_LEVELS } from '../../shared/kotoba-agent-access'
import { migrateAgentYoloDefaults } from '../persistence/applying-settings/terminal-settings-migrations'

const { installHost } = vi.hoisted(() => ({ installHost: vi.fn(async (_deps: unknown) => ({})) }))
vi.mock('./structured-agent-session-runtime', async (original) => ({ ...await original<object>(), ensureStructuredAgentSessionHost: installHost }))
afterEach(() => vi.unstubAllEnvs())

describe('Kotoba native access wiring', () => {
  for (const agent of ['codex', 'claude'] as const) for (const level of ACCESS_LEVELS) {
    it(`passes ${agent} ${level} into the structured agent launcher`, async () => {
      const settings = applyAccessLevel({}, agent, level)
      installHost.mockClear()
      await new OrcaRuntimeService({ getSettings: () => settings } as never).ensureStructuredAgentSessionHost()
      const deps = installHost.mock.calls[0]![0] as { resolveLaunchArgs: (agent: string) => string[] | Promise<string[]> }
      const args = await deps.resolveLaunchArgs(agent)
      if (agent === 'claude') expect(args).toContain('--permission-mode')
      else expect(args).toContain('--sandbox')
      for (const argument of settings.agentDefaultArgs![agent]!.split(' ')) expect(args).toContain(argument)
    })
  }
  it('retires existing global bypass presets but preserves custom and selected access settings', () => {
    vi.stubEnv('KOTOBA_FLEET_HOME', 'isolated-test-profile')
    const migrated = migrateAgentYoloDefaults({ agentYoloDefaultsMigrated: true, agentDefaultArgs: { codex: '--dangerously-bypass-approvals-and-sandbox', claude: '--model opus', gemini: '--yolo' }, agentDefaultEnv: { goose: { GOOSE_MODE: 'auto' } } } as never)
    expect(migrated.agentDefaultArgs?.codex).toBe('')
    expect(migrated.agentDefaultArgs?.gemini).toBe('')
    expect(migrated.agentDefaultArgs?.claude).toBe('--model opus')
    expect(migrated.agentDefaultEnv?.goose).toEqual({})
    const selected = applyAccessLevel(migrated, 'codex', 'workspace')
    expect(migrateAgentYoloDefaults(selected as never).agentDefaultArgs).toEqual(selected.agentDefaultArgs)
  })
})
