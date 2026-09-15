// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
const locale = vi.hoisted(() => ({ language: 'ja' }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ i18n: locale }) }))
import { KotobaClaudeLanguageNotice } from './KotobaClaudeLanguageNotice'
import { setClaudePresentationLocale } from '../../lib/kotoba-claude-language'

beforeEach(() => {
  locale.language = 'ja'
  setClaudePresentationLocale('en')
  setClaudePresentationLocale('ja')
})
afterEach(cleanup)
it('automatically opens Japanese chat once while retaining an explicit terminal return', () => {
  const open = vi.fn()
  const first = render(<KotobaClaudeLanguageNotice paneId="claude-a" isChat={false} onOpenChat={open} />)
  expect(open).toHaveBeenCalledOnce()
  first.unmount()
  render(<KotobaClaudeLanguageNotice paneId="claude-a" isChat={false} onOpenChat={open} />)
  expect(open).toHaveBeenCalledOnce()
  expect(screen.getByText(/提供元のメニューは英語/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '日本語のチャット表示' }))
  expect(open).toHaveBeenCalledTimes(2)
})
it('switches existing and newly selected panes after another Japanese toggle', () => {
  const open = vi.fn()
  const view = render(<KotobaClaudeLanguageNotice paneId="claude-a" isChat={false} onOpenChat={open} />)
  locale.language = 'en'; setClaudePresentationLocale('en')
  view.rerender(<KotobaClaudeLanguageNotice paneId="claude-a" isChat={false} onOpenChat={open} />)
  expect(view.container.childElementCount).toBe(0)
  expect(open).toHaveBeenCalledOnce()
  locale.language = 'ja'; setClaudePresentationLocale('ja')
  view.rerender(<KotobaClaudeLanguageNotice paneId="claude-a" isChat={false} onOpenChat={open} />)
  expect(open).toHaveBeenCalledTimes(2)
  view.rerender(<KotobaClaudeLanguageNotice paneId="claude-b" isChat={false} onOpenChat={open} />)
  expect(open).toHaveBeenCalledTimes(3)
})
it('keeps English terminals unchanged', () => {
  locale.language = 'en'; setClaudePresentationLocale('en')
  const open = vi.fn()
  const { container } = render(<KotobaClaudeLanguageNotice paneId="claude-a" isChat={false} onOpenChat={open} />)
  expect(container.childElementCount).toBe(0)
  expect(open).not.toHaveBeenCalled()
})

it('allows first-run terminal setup when Japanese was selected while chat was already open', () => {
  const open = vi.fn()
  const view = render(<KotobaClaudeLanguageNotice paneId="setup" isChat={true} onOpenChat={open} />)
  view.rerender(<KotobaClaudeLanguageNotice paneId="setup" isChat={false} onOpenChat={open} />)
  expect(open).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: '日本語のチャット表示' })).toBeTruthy()
})
