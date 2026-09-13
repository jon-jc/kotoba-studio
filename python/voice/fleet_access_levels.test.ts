import { describe, it, expect } from 'vitest'
import { ACCESS_AGENTS, ACCESS_LEVELS, accessArguments, applyAccessLevel, currentAccessLevel } from './kotoba-agent-access'

describe('Kotoba agent access', () => {
  for (const agent of ACCESS_AGENTS) for (const level of ACCESS_LEVELS) {
    it(`round trips ${agent} ${level} without changing other agents`, () => {
      const settings = { agentDefaultArgs: { codex: '--model "my model"', claude: '--model opus' }, agentDefaultEnv: { codex: { CUSTOM: 'value' } } }
      const result = applyAccessLevel(settings, agent, level)
      expect(currentAccessLevel(result, agent)).toBe(level)
      expect(applyAccessLevel(result, agent, level)).toEqual(result)
      if (agent !== 'codex') expect(result.agentDefaultArgs!.codex).toBe(settings.agentDefaultArgs.codex)
      expect(result.agentDefaultEnv!.codex?.CUSTOM).toBe('value')
    })
  }
  it('replaces conflicting Codex permissions and preserves quoted model arguments', () => {
    expect(accessArguments('codex', 'ask', '--model "--yolo" --sandbox=danger-full-access -a never --dangerously-bypass-approvals-and-sandbox -c sandbox_workspace_write.network_access=true')).toBe('--model "--yolo" --sandbox read-only --ask-for-approval on-request')
  })
  it('replaces Claude bypass flags and permission mode', () => {
    expect(accessArguments('claude', 'plan', '--model opus --dangerously-skip-permissions --permission-mode=bypassPermissions')).toBe('--model opus --permission-mode plan')
  })
  it('does not silently discard malformed custom configuration', () => {
    expect(() => accessArguments('codex', 'ask', '--sandbox')).toThrow()
    expect(() => accessArguments('codex', 'ask', '--model "unclosed')).toThrow()
    expect(() => applyAccessLevel({ agentDefaultEnv: { opencode: { OPENCODE_CONFIG_CONTENT: '{bad' } } }, 'opencode', 'ask')).toThrow()
  })
  it('overrides OpenCode auto approval and built-in agent overrides without losing unrelated settings', () => {
    const result = applyAccessLevel({ agentDefaultArgs: { opencode: '--auto --agent custom' }, agentDefaultEnv: { opencode: { OPENCODE_PERMISSION: '{"*":"allow"}', OPENCODE_CONFIG_CONTENT: '{"model":"custom/model","agent":{"build":{"temperature":0.2,"permission":{"*":"allow"}}}}' } } }, 'opencode', 'plan')
    const config = JSON.parse(result.agentDefaultEnv!.opencode!.OPENCODE_CONFIG_CONTENT!)
    expect(config.model).toBe('custom/model')
    expect(config.agent.build.temperature).toBe(0.2)
    expect(config.agent.build.permission.bash).toBe('deny')
    expect(config.permission.read['*.env']).toBe('deny')
    expect(result.agentDefaultArgs!.opencode).toBe('')
    expect(result.agentDefaultEnv!.opencode?.OPENCODE_PERMISSION).toBeUndefined()
    config.agent.build.permission = { '*': 'allow' }
    result.agentDefaultEnv!.opencode!.OPENCODE_CONFIG_CONTENT = JSON.stringify(config)
    expect(currentAccessLevel(result, 'opencode')).toBe('custom')
  })
})
