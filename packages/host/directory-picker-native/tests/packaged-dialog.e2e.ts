/** Opt-in Windows qualification of the actual single-executable dialog worker. */
import { spawn } from 'node:child_process'
import { expect, it } from 'vitest'
import { pickWin32Directory } from '../src/win32-dialog.ts'

it.skipIf(process.platform !== 'win32' || process.env.KOTOBA_RUNTIME === undefined)(
  'opens and aborts the packaged native dialog through IPC', async () => {
    const controller = new AbortController()
    let shown = false
    let child: ReturnType<typeof spawn> | undefined
    const deadline = setTimeout(() => { controller.abort() }, 10_000)
    try {
      await expect(pickWin32Directory(controller.signal, {
        spawnWorker(data) {
          child = spawn(process.env.KOTOBA_RUNTIME!, [], {
            env: { ...process.env, DSH_DIRECTORY_DIALOG_WORKER: '1', DSH_DIALOG_TITLE: data.title },
            stdio: ['ignore', 'inherit', 'inherit', 'ipc'], windowsHide: true,
          })
          child.on('message', (message: { kind?: string }) => {
            if (message.kind === 'showing') {
              shown = true
              setTimeout(() => { controller.abort() }, 200)
            }
          })
          return child
        },
      })).rejects.toThrow('native directory picker aborted')
      expect(shown).toBe(true)
    } finally {
      clearTimeout(deadline)
      child?.kill()
    }
  }, 20_000,
)
