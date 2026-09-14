const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process');
const assert = require('node:assert/strict');
const { chromium, expect } = require(path.resolve(process.argv[2], 'node_modules/playwright/test'));
(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:' + process.argv[3]);
  const page = browser.contexts()[0].pages()[0];
  const output = process.argv[5], project = path.join(process.argv[4], 'chat-project');
  page.setDefaultTimeout(30000);
  try {
    await page.waitForFunction(() => window.kotobaWorkspace);
    const onboarding = page.locator('[data-onboarding-overlay="true"]');
    await onboarding.getByRole('button', { name: /^Codex/ }).click();
    await onboarding.getByText('Skip to project setup', { exact: true }).click();
    await onboarding.waitFor({ state: 'hidden' });
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Close', exact: true }).click();
    await page.getByRole('button', { name: 'Add a project to chat', exact: true }).click();
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Close', exact: true }).click();
    fs.mkdirSync(project); fs.writeFileSync(path.join(project, 'README.md'), '# Chat verification\n');
    for (const args of [['init', '-b', 'main'], ['add', '.'], ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'Fixture']]) {
      cp.execFileSync('git', ['-C', project, ...args], { windowsHide: true, stdio: 'pipe' });
    }
    assert.equal(await page.evaluate(p => window.kotobaWorkspace.addProject(p), project), true);
    await page.getByRole('button', { name: 'Skip tour', exact: true }).click();
    await page.getByText('Terminal 1', { exact: true }).waitFor();
    const sidebar = page.locator('[data-contextual-tour-target="sidebar-navigation"]');
    await expect(page.getByRole('button', { name: 'New chat', exact: true })).toHaveCount(1);
    await sidebar.getByRole('button', { name: 'New chat', exact: true }).click();
    await expect(page.getByRole('menuitem', { name: 'Claude Code chat', exact: true })).toBeVisible();
    await page.screenshot({ animations: 'disabled', path: path.join(output, 'sidebar-chat-en.png') });
    await page.getByRole('menuitem', { name: 'Claude Code chat', exact: true }).click();
    await expect(page.getByText('Starting Claude Code', { exact: true })).toBeVisible();
    await expect(page.locator('[data-native-chat-root] [contenteditable=true]')).toHaveCount(0);
    await expect(page.getByText('Could not open Claude chat', { exact: true })).toHaveCount(0);
    await page.screenshot({ animations: 'disabled', path: path.join(output, 'claude-setup-en.png') });
    const before = await page.evaluate(() => window.kotobaWorkspace.snapshot());
    console.log('LOCALE ja');
    await expect(page.getByText('Claude Code を起動しています', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Claude のターミナルを開く', exact: true })).toBeVisible();
    await page.screenshot({ animations: 'disabled', path: path.join(output, 'claude-setup-ja.png') });
    await page.getByRole('button', { name: 'Claude のターミナルを開く', exact: true }).click();
    await expect(page.locator('[data-native-chat-root]')).toHaveCount(0);
    await expect(page.locator('.xterm-screen').last()).toBeVisible();
    console.log('LOCALE en');
    await expect(sidebar.getByRole('button', { name: 'New chat', exact: true })).toBeVisible();
    assert.equal((await page.evaluate(() => window.kotobaWorkspace.snapshot())).path, before.path);
    console.log(JSON.stringify({ passed: true, sidebar: true, projectSetup: true, claudeSetup: true,
      terminalAccessible: true, japanese: true, english: true, projectPreserved: true, promptsSent: 0 }));
  } catch (error) {
    await page.screenshot({ animations: 'disabled', path: path.join(output, 'failure.png') }).catch(() => {});
    console.log((await page.locator('body').innerText()).slice(-4000));
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
