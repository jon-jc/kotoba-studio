// @vitest-environment jsdom
import { render, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { WelcomeNotice, type WelcomeNoticeProps } from '../src/client/WelcomeNotice.tsx'

afterEach(cleanup)
it('advances startup without a notice, acknowledgement write, or loading dependency', () => {
  const complete = vi.fn()
  const controller = { load: vi.fn(), acknowledge: vi.fn() }
  const props = { complete, controller } as unknown as WelcomeNoticeProps
  const result = render(<WelcomeNotice {...props} />)
  expect(result.container.textContent).toBe('')
  expect(result.queryByRole('dialog')).toBeNull()
  expect(complete).toHaveBeenCalledOnce()
  expect(controller.load).not.toHaveBeenCalled()
  expect(controller.acknowledge).not.toHaveBeenCalled()
})
