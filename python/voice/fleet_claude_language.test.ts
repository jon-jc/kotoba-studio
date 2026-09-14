import { afterEach, expect, it } from 'vitest'
import { claudeLanguageArgs, setKotobaClaudeLanguageSettings } from './kotoba-claude-language'
import { tokenizeStartupCommand } from '../../../shared/tui-agent-startup-shell'
afterEach(() => setKotobaClaudeLanguageSettings(null))
it('quotes the profile file and preserves model and permission flags', () => {
  const path = "C:\\Users\\Jon's workspace\\日本語\\claude-language.json"
  setKotobaClaudeLanguageSettings(path)
  const args = claudeLanguageArgs('claude', '--model sonnet --permission-mode default', 'powershell', true)!
  const result = tokenizeStartupCommand(args, 'powershell')
  expect(result.ok && result.tokens).toEqual(['--model', 'sonnet', '--permission-mode', 'default', '--settings', path])
})
it('does not replace custom settings or send local paths to other agents or hosts', () => {
  setKotobaClaudeLanguageSettings('C:/owned/claude-language.json')
  for (const args of ['--settings custom.json', '--settings=custom.json', '-- hello']) {
    expect(claudeLanguageArgs('claude', args, 'powershell', true)).toBe(args)
  }
  expect(claudeLanguageArgs('codex', '', 'powershell', true)).toBe('')
  expect(claudeLanguageArgs('claude', '', 'posix', false)).toBe('')
})
