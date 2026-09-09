/** A packaged dialog must select the runtime's worker entry, not the CLI. */
import { afterEach, expect, it, vi } from 'vitest'

const { spawn } = vi.hoisted(() => ({ spawn: vi.fn(() => ({ on: vi.fn() })) }))
vi.mock('node:child_process', () => ({ spawn }))
import { spawnDialogWorker } from '../src/win32-dialog-host.ts'

afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })

it('selects the packaged dialog worker and retains its IPC channel', () => {
  vi.stubGlobal('process', { ...process, pkg: {}, execPath: 'C:\\Kotoba\\runtime.exe' })
  spawnDialogWorker({ title: 'Select Workspace Directory' })
  expect(spawn).toHaveBeenCalledWith('C:\\Kotoba\\runtime.exe', [], expect.objectContaining({
    env: expect.objectContaining({ DSH_DIRECTORY_DIALOG_WORKER: '1', DSH_DIALOG_TITLE: 'Select Workspace Directory' }),
    stdio: ['ignore', 'inherit', 'inherit', 'ipc'], windowsHide: true,
  }))
})

it('retains source-mode TypeScript launch outside a packaged runtime', () => {
  spawnDialogWorker({ title: 'Source dialog' })
  expect(spawn).toHaveBeenCalledWith(process.execPath, expect.arrayContaining(['--import']), expect.objectContaining({
    env: expect.not.objectContaining({ DSH_DIRECTORY_DIALOG_WORKER: '1' }),
  }))
})
