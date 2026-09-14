// Browser control navigates the real UI; all tested text arrives via Windows keys.
const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process');
const assert = require('node:assert/strict');
const { chromium, expect } = require(path.resolve(process.argv[2], 'node_modules/playwright/test'));
(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:' + process.argv[3]);
  const page = browser.contexts()[0].pages()[0];
  const output = process.argv[5], project = path.join(process.argv[4], 'keyboard-project');
  page.setDefaultTimeout(20000);
  const type = async (element, text) => {
    await element.click();
    const box = await element.boundingBox(); assert.ok(box);
    console.log('NATIVE_TYPE ' + JSON.stringify({ x: box.x + 35, y: box.y + Math.min(20, box.height / 2), text }));
  };
  try {
    await page.waitForFunction(() => window.kotobaWorkspace);
    const onboarding = page.locator('[data-onboarding-overlay="true"]');
    await onboarding.getByRole('button', { name: /^Codex/ }).click();
    await onboarding.getByText('Skip to project setup', { exact: true }).click();
    await onboarding.waitFor({ state: 'hidden' });
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Close', exact: true }).click();
    fs.mkdirSync(project); fs.writeFileSync(path.join(project, 'README.md'), '# Keyboard verification\n');
    for (const args of [['init', '-b', 'main'], ['add', '.'], ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'Fixture']]) {
      cp.execFileSync('git', ['-C', project, ...args], { windowsHide: true, stdio: 'pipe' });
    }
    assert.equal(await page.evaluate(p => window.kotobaWorkspace.addProject(p), project), true);
    const tour = page.getByRole('button', { name: 'Skip tour', exact: true });
    await tour.waitFor(); await tour.click();
    await page.getByText('Terminal 1', { exact: true }).waitFor();
    const terminal = page.locator('.xterm-screen:visible').first();
    await type(terminal, 'echo kotoba > keyboard-proof.txt\n');
    await expect.poll(() => fs.existsSync(path.join(project, 'keyboard-proof.txt')), { timeout: 15000 }).toBe(true);
    assert.ok(fs.readFileSync(path.join(project, 'keyboard-proof.txt'), 'utf8').includes('kotoba'));
    await page.screenshot({ path: path.join(output, 'terminal-keyboard.png') });

    await page.getByRole('button', { name: 'New chat', exact: true }).click();
    await page.getByRole('menuitem', { name: 'Codex chat', exact: true }).click();
    await page.getByText('Codex Chat', { exact: true }).waitFor();
    const composer = page.locator('[contenteditable="true"]:visible');
    await expect(composer).toHaveCount(1);
    await type(composer, 'review this workspace');
    await expect(composer).toContainText('review this workspace', { timeout: 15000 });
    const model = page.getByRole('button', { name: /^Model / });
    await model.waitFor(); await model.click();
    await page.getByRole('menu').waitFor();
    await page.screenshot({ path: path.join(output, 'codex-models.png') });
    await page.keyboard.press('Escape');
    await page.screenshot({ path: path.join(output, 'codex-chat-draft.png') });
    assert.ok(!(await page.locator('body').innerText()).includes("Structured chat isn't available"));

    await page.getByText('Terminal 1', { exact: true }).click();
    console.log('RESTORE');
    // A native hide/show has no DOM visibility event to await. The following
    // command/result is the assertion; this delay only lets Qt process the request.
    await page.waitForTimeout(800);
    await type(terminal, 'echo restored > restored-proof.txt\n');
    await expect.poll(() => fs.existsSync(path.join(project, 'restored-proof.txt')), { timeout: 15000 }).toBe(true);
    await page.getByText('Codex Chat', { exact: true }).click();
    await expect(composer).toContainText('review this workspace');

    await page.evaluate(() => {
      window.smokePtyOutput = ''; window.smokePtyId = null;
      window.smokeUnsubscribe = window.api.pty.onData(event => {
        window.smokePtyId = event.id;
        window.smokePtyOutput = (window.smokePtyOutput + event.data).slice(-131072);
      });
    });
    await page.getByRole('button', { name: 'New chat', exact: true }).click();
    await page.getByRole('menuitem', { name: 'Codex terminal', exact: true }).click();
    await expect.poll(() => page.evaluate(async () => window.smokePtyId
      ? (await window.api.pty.inspectProcess(window.smokePtyId, { scanChildProcesses: true })).foregroundProcess : null), { timeout: 30000 }).toMatch(/codex/i);
    await page.waitForFunction(() => /codex/i.test(window.smokePtyOutput));
    await page.evaluate(() => { window.smokePtyOutput = ''; });
    await type(page.locator('.xterm-screen:visible').first(), '/help');
    await expect.poll(() => page.evaluate(() => window.smokePtyOutput.includes('help')), { timeout: 15000 }).toBe(true);
    await page.screenshot({ path: path.join(output, 'codex-terminal-keyboard.png') });
    await page.evaluate(() => window.smokeUnsubscribe());
    console.log(JSON.stringify({ passed: true, terminalKeyboard: true, shellExecution: true,
      codexStructuredChat: true, composerKeyboard: true, modelMenu: true, restoredTerminal: true,
      retainedDraft: true, codexTerminalProcess: true, codexTerminalKeyboard: true }));
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
