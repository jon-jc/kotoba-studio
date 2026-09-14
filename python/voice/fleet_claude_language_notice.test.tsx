// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
const locale = vi.hoisted(() => ({ language: 'ja' }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ i18n: locale }) }))
import { KotobaClaudeLanguageNotice } from './KotobaClaudeLanguageNotice'
afterEach(cleanup)
it('offers the translated chat without claiming terminal menus are translated', () => {
  const open = vi.fn()
  render(<KotobaClaudeLanguageNotice onOpenChat={open} />)
  expect(screen.getByText(/提供元のメニューは英語/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '日本語のチャット表示' }))
  expect(open).toHaveBeenCalledOnce()
})
it('removes the Japanese notice when English is selected', () => {
  locale.language = 'en'
  const { container } = render(<KotobaClaudeLanguageNotice onOpenChat={() => {}} />)
  expect(container.childElementCount).toBe(0)
})
