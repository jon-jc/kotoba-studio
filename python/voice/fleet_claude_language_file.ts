import { mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

/** A session-only settings source owned by Kotoba, never ~/.claude/settings.json. */
export function writeClaudeLanguageSettings(home: string, locale: string): string {
  const path = join(home, 'claude-language.json')
  const contents = JSON.stringify({ language: locale === 'ja' ? 'japanese' : 'english' }) + '\n'
  try { if (readFileSync(path, 'utf8') === contents) return path } catch { /* First launch. */ }
  mkdirSync(home, { recursive: true })
  const temporary = `${path}.${process.pid}.tmp`
  writeFileSync(temporary, contents, { mode: 0o600 })
  renameSync(temporary, path)
  return path
}
