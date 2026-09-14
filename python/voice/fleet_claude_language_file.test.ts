import { mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { expect, it } from 'vitest'
import { writeClaudeLanguageSettings } from './kotoba-claude-language-file'
it('updates only the owned language source without leaving partial files', () => {
  const home = mkdtempSync(join(tmpdir(), 'kotoba-language-'))
  try {
    const path = writeClaudeLanguageSettings(home, 'ja')
    expect(JSON.parse(readFileSync(path, 'utf8'))).toEqual({ language: 'japanese' })
    expect(writeClaudeLanguageSettings(home, 'ja')).toBe(path)
    writeClaudeLanguageSettings(home, 'en')
    expect(JSON.parse(readFileSync(path, 'utf8'))).toEqual({ language: 'english' })
    expect(readdirSync(home)).toEqual(['claude-language.json'])
  } finally { rmSync(home, { recursive: true, force: true }) }
})
