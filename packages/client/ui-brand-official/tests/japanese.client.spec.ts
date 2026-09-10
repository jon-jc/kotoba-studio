// @vitest-environment jsdom
import { Context } from '@deepseek-ai/cordis'
import { LocaleRuntime } from '@deepseek-ai/dsh-client-locale/client'
import { afterEach, expect, it } from 'vitest'
import { japanese } from '../src/client/japanese.ts'
import { followDesktopLocale } from '../src/client/desktop-locale.ts'

afterEach(() => {
  delete document.documentElement.dataset.kotobaLocale
  document.body.replaceChildren()
})

it('adopts the desktop language before boot, switches live, and leaves drafts untouched', () => {
  const ctx = new Context()
  const locale = new LocaleRuntime(ctx)
  ctx.provide('locale', locale)
  locale.addLanguage({ id: 'ja', label: '日本語', fallback: 'en' })
  locale.register('conversation', 'en', { 'input.send': 'Send message', extension: 'Extension fallback' })
  for (const [namespace, dict] of Object.entries(japanese)) locale.register(namespace, 'ja', dict)
  document.documentElement.dataset.kotobaLocale = 'ja'
  const draft = document.createElement('textarea')
  draft.value = 'Deploy は15時です'
  document.body.append(draft)
  const stop = followDesktopLocale(ctx)
  const t = locale.bind('conversation')
  expect(t('input.send')).toBe('メッセージを送信')
  expect(locale.bind('conversation' as string)('extension')).toBe('Extension fallback')
  expect(t('todo.completed', { done: 2, total: 3 })).toBe('2/3 件完了')
  // Simulate a saved Host preference arriving after the native language event.
  locale.setLocale('en')
  expect(locale.getLocale().active).toBe('ja')
  document.documentElement.dataset.kotobaLocale = 'en'
  document.dispatchEvent(new Event('kotoba:locale'))
  expect(t('input.send')).toBe('Send message')
  expect(draft.value).toBe('Deploy は15時です')
  document.documentElement.dataset.kotobaLocale = 'untrusted'
  document.dispatchEvent(new Event('kotoba:locale'))
  expect(locale.getLocale().active).toBe('en')
  stop()
  document.documentElement.dataset.kotobaLocale = 'ja'
  document.dispatchEvent(new Event('kotoba:locale'))
  expect(locale.getLocale().active).toBe('en')
})
