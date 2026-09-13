import { afterEach, describe, expect, it } from 'vitest'
import { mkdtempSync, mkdirSync, rmSync, utimesSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { windowsCodexDirectories } from './kotoba-windows-codex'
import { resolveCliCommand, resolveCliCommands } from './node-cli-command-resolution'

const homes: string[] = []
function fixture() {
  const home = mkdtempSync(join(tmpdir(), 'kotoba-codex-detection-'))
  homes.push(home)
  const root = join(home, 'AppData', 'Local', 'OpenAI', 'Codex', 'bin')
  const install = (version: string, modified: number) => {
    const directory = join(root, version)
    mkdirSync(directory, { recursive: true })
    const file = join(directory, 'codex.exe')
    writeFileSync(file, 'fixture only')
    utimesSync(file, modified, modified)
    return file
  }
  return { home, root, install }
}
afterEach(() => { for (const home of homes.splice(0)) rmSync(home, { recursive: true, force: true }) })

describe('Windows desktop Codex discovery', () => {
  it('resolves both detection and launch with an empty GUI PATH', () => {
    const { home, install } = fixture()
    const file = install('abcdef123456', 100)
    const options = { homePath: home, platform: 'win32' as const, pathEnv: '' }
    expect(resolveCliCommand('codex', options)).toBe(file)
    expect(resolveCliCommands(['codex'], options).get('codex')).toBe(file)
  })
  it('prefers a newer valid executable and ignores incomplete downloads', () => {
    const { home, root, install } = fixture()
    install('old', 100)
    const newest = install('new', 200)
    mkdirSync(join(root, 'incomplete', 'codex.exe'), { recursive: true })
    const empty = install('empty', 300)
    writeFileSync(empty, '')
    expect(resolveCliCommand('codex', { homePath: home, platform: 'win32', pathEnv: '' })).toBe(newest)
    expect(windowsCodexDirectories('win32', home)).toHaveLength(2)
  })
  it('preserves an explicit PATH install over the desktop cache', () => {
    const { home, install } = fixture()
    install('cached', 100)
    const preferred = join(home, 'preferred')
    mkdirSync(preferred)
    const executable = join(preferred, 'codex.exe')
    writeFileSync(executable, 'fixture only')
    expect(resolveCliCommand('codex', { homePath: home, platform: 'win32', pathEnv: preferred })).toBe(executable)
  })
  it('discovers a new install on refresh without caching absence', () => {
    const { home, install } = fixture()
    expect(windowsCodexDirectories('win32', home)).toEqual([])
    install('added-after-startup', 100)
    expect(windowsCodexDirectories('win32', home)).toHaveLength(1)
  })
  it('supports redirected LocalAppData and skips Windows probing on other platforms', () => {
    const { home, root, install } = fixture()
    install('current', 100)
    expect(windowsCodexDirectories('win32', join(home, 'other-home'), join(home, 'AppData', 'Local'))).toEqual([join(root, 'current')])
    expect(windowsCodexDirectories('darwin', home)).toEqual([])
  })
})
