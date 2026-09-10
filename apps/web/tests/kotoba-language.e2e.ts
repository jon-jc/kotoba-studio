import { chromium } from 'playwright'
import { expect, it } from 'vitest'
import { launchWebScaffold, watchConsole } from './scaffold.ts'
import { connectFreshWorkspace } from './support.ts'

it('switches the composed chat between Japanese and English without losing its draft', async () => {
  const scaffold = await launchWebScaffold({ welcomeNoticePending: true })
  const browser = await chromium.launch()
  try {
    const page = await browser.newPage({ locale: 'en-US' })
    const console = watchConsole(page)
    await page.goto(scaffold.authenticatedUrl)
    await connectFreshWorkspace(page, scaffold.workspaceCwd)
    expect(await page.getByRole('dialog', { name: 'Internal Testing Notice' }).count()).toBe(0)
    const composer = page.locator('[data-composer-input][contenteditable="true"]')
    await composer.fill('Deploy は15時です')
    const documentIdentity = await page.evaluate(() => performance.timeOrigin)
    await page.evaluate(() => {
      document.documentElement.dataset.kotobaLocale = 'ja'
      document.dispatchEvent(new Event('kotoba:locale'))
    })
    await page.getByRole('button', { name: '設定', exact: true }).waitFor()
    expect(await page.locator('html').getAttribute('lang')).toBe('ja')
    expect(await composer.getAttribute('data-placeholder')).toContain('作りたいもの')
    expect(await composer.textContent()).toBe('Deploy は15時です')
    await page.getByRole('button', { name: '設定', exact: true }).click()
    await page.getByRole('button', { name: 'モデル', exact: true }).click()
    await page.getByRole('button', { name: 'プロバイダーを追加', exact: true }).waitFor()
    await page.evaluate(() => {
      document.documentElement.dataset.kotobaLocale = 'en'
      document.dispatchEvent(new Event('kotoba:locale'))
    })
    await page.getByRole('button', { name: 'Add provider', exact: true }).waitFor()
    expect(await page.evaluate(() => performance.timeOrigin)).toBe(documentIdentity)
    expect(await composer.textContent()).toBe('Deploy は15時です')
    expect(console.pageErrors).toEqual([])
  } finally {
    await browser.close()
    await scaffold.close()
  }
}, 90_000)
