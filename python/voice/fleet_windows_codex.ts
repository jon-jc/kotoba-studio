import { readdirSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

/** Bounded discovery of the Windows desktop CLI cache; never run a binary to detect it. */
export function windowsCodexDirectories(
  platform: NodeJS.Platform = process.platform,
  home = homedir(),
  localAppData = home === homedir() ? process.env.LOCALAPPDATA : undefined
): string[] {
  if (platform !== 'win32') return []
  const root = join(localAppData || join(home, 'AppData', 'Local'), 'OpenAI', 'Codex', 'bin')
  try {
    const candidates = [root, ...readdirSync(root, { withFileTypes: true })
      .filter(entry => entry.isDirectory() && /^[a-zA-Z0-9._-]+$/.test(entry.name))
      .slice(0, 64).map(entry => join(root, entry.name))]
    return candidates.flatMap(directory => {
      try {
        const binary = statSync(join(directory, 'codex.exe'))
        return binary.isFile() && binary.size > 0 ? [{ directory, modified: binary.mtimeMs }] : []
      } catch { return [] }
    }).sort((a, b) => b.modified - a.modified || a.directory.localeCompare(b.directory))
      .map(entry => entry.directory)
  } catch { return [] }
}
