#!/usr/bin/env node
/** Private entry owned by the Python single-file runtime packaging. */

const selectorName = 'DSH_SUBPROCESS_RUNNER'
const selection = process.env[selectorName]
const dialog = process.env.DSH_DIRECTORY_DIALOG_WORKER

if (dialog !== undefined) {
  Reflect.deleteProperty(process.env, 'DSH_DIRECTORY_DIALOG_WORKER')
  if (dialog !== '1' || process.platform !== 'win32' || process.send === undefined) {
    throw new Error('The directory dialog worker requires Windows and an IPC parent.')
  }
  await import('@deepseek-ai/dsh-host-directory-picker-native/worker')
} else if (selection === undefined) {
  const { runCli } = await import('@deepseek-ai/dsh/lib/bin.js')
  await runCli()
} else {
  Reflect.deleteProperty(process.env, selectorName)
  const { runSelectedSubprocessRunner } = await import('@deepseek-ai/dsh-subprocess-local/runner')
  await runSelectedSubprocessRunner(selection)
}
