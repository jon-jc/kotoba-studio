// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
const locale = vi.hoisted(() => ({ language: 'en' }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ i18n: locale }) }))
import { KotobaClaudeSetup } from './KotobaClaudeSetup'
afterEach(cleanup)
describe('Claude first-run guidance', () => {
  it.each([
    ['en', 'Open Claude terminal'],
    ['ja', 'Claude のターミナルを開く']
  ])('offers setup in %s without answering terminal prompts', (language, label) => {
    locale.language = language
    const open = vi.fn()
    render(<KotobaClaudeSetup onOpenTerminal={open} />)
    expect(open).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: label }))
    expect(open).toHaveBeenCalledOnce()
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})
