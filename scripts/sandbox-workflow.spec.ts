import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import * as yaml from 'js-yaml'
import { describe, expect, it } from 'vitest'

const workflow = yaml.load(readFileSync(resolve(import.meta.dirname, '../.github/workflows/sandbox.yml'), 'utf8')) as {
  jobs: { 'sandbox-e2e': { steps: Array<{ name?: string; run?: string }> } }
}
const bash = process.platform === 'win32'
  ? resolve(process.env.ProgramFiles ?? 'C:/Program Files', 'Git/bin/bash.exe')
  : '/bin/bash'

// Windows needs Git Bash to execute the same shell used by the hosted jobs.
describe.skipIf(!existsSync(bash))('sandbox workflow verdict', () => {
  const steps = workflow.jobs['sandbox-e2e'].steps.filter(step => step.run?.includes('status=$?'))

  it('covers both kernel and packed-install commands', () => {
    expect(steps).toHaveLength(2)
  })

  for (const step of steps) {
    it.each([
      { status: 0, summary: true, expected: 0 },
      { status: 7, summary: true, expected: 7 },
      { status: 0, summary: false, expected: 1 },
      { status: 7, summary: false, expected: 7 },
    ])(`${step.name}: $status with summary=$summary returns $expected`, ({ status, summary, expected }) => {
      const count = step.run!.includes('packed-install.e2e.ts') ? 1 : 2
      const output = summary ? `Test Files  ${count} passed (${count})` : 'Test Files  1 skipped (1)'
      const stub = `pnpm() { printf '%s\\n' '${output}'; return ${status}; }\n`
      const script = step.run!.replaceAll('${{ matrix.runner }}', 'seatbelt')
      const result = spawnSync(bash, ['--noprofile', '--norc', '-c', stub + script], {
        encoding: 'utf8', timeout: 10_000,
      })
      expect(result.error).toBeUndefined()
      expect(result.signal).toBeNull()
      expect(result.status, result.stderr).toBe(expected)
    })
  }
})
