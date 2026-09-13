// Optional Windows smoke against an installed Codex CLI. No sign-in or agent turn.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os'), assert = require('node:assert/strict');
const { _electron } = require(path.resolve(process.argv[2], 'node_modules/playwright'));
(async () => {
  const output = path.resolve(process.argv[4]); fs.mkdirSync(output, { recursive: true });
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'kotoba-codex-smoke-'));
  const env = { ...process.env, KOTOBA_FLEET_HOME: home, KOTOBA_FLEET_NONCE: 'owned-smoke', ORCA_BACKGROUND_LAUNCH: '1', DO_NOT_TRACK: '1', ORCA_TELEMETRY_DISABLED: '1' };
  const inherited = env.PATH ?? env.Path ?? '';
  delete env.Path;
  env.PATH = inherited.split(';').filter(entry => !/OpenAI[\\/]Codex/i.test(entry)).join(';');
  const app = await _electron.launch({ executablePath: path.resolve(process.argv[3], 'KotobaAgents.exe'), args: [], env, timeout: 60000 });
  try {
    const page = await app.firstWindow(); page.setDefaultTimeout(15000);
    await app.evaluate(({ BrowserWindow }) => { const win = BrowserWindow.getAllWindows()[0]; win.webContents.setBackgroundThrottling(false); win.showInactive(); });
    await page.waitForFunction(() => typeof window.kotobaWorkspace === 'object');
    const agents = await page.evaluate(() => window.api.preflight.detectAgents());
    assert.ok(agents.includes('codex'), 'Codex must be detected from its desktop installation');
    const refreshed = await page.evaluate(() => window.api.preflight.refreshAgents());
    assert.ok(refreshed.agents.includes('codex'), 'Refresh must retain Codex');
    const launchPath = await app.evaluate(() => process.env.PATH ?? process.env.Path ?? '');
    const executable = require('node:child_process').execFileSync(path.join(process.env.SystemRoot, 'System32', 'where.exe'), ['codex'], {
      env: { SystemRoot: process.env.SystemRoot, PATH: launchPath, PATHEXT: process.env.PATHEXT },
      encoding: 'utf8', timeout: 15000, windowsHide: true
    }).trim();
    assert.ok(executable.toLowerCase().includes('codex'), 'Terminals must resolve the detected CLI');
    await page.evaluate(() => window.kotobaWorkspace.snapshot('en'));
    await page.evaluate(() => window.kotobaWorkspace.navigate('permissions'));
    await page.getByRole('heading', { name: 'Agent access', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Back to app', exact: true }).click();
    const onboarding = page.locator('[data-onboarding-overlay="true"]');
    await onboarding.getByRole('button', { name: /^Codex/ }).click();
    await onboarding.getByText('Skip to project setup', { exact: true }).click();
    await onboarding.waitFor({ state: 'hidden' });
    await page.keyboard.press('Escape');
    await page.evaluate(() => window.kotobaWorkspace.navigate('sidebar'));
    await page.getByRole('button', { name: 'Help', exact: true }).click();
    const menu = page.getByRole('menu'); await menu.waitFor();
    const text = await menu.innerText();
    for (const label of ['Send Feedback', 'Milestones', 'Onboarding', 'Docs', 'Changelog', 'GitHub', 'Discord']) assert.ok(!text.includes(label), label);
    assert.ok(!text.split('\n').includes('X'));
    assert.ok(text.includes('Keyboard Shortcuts'));
    await page.screenshot({ path: path.join(output, 'help-menu.png') });
    console.log(JSON.stringify({ passed: true, detectedCodex: true, refreshedCodex: true, terminalResolvesCodex: true, removedLinks: 8 }));
  } catch (error) {
    const page = await app.firstWindow();
    await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
    console.error(await page.locator('button[aria-label]').evaluateAll(buttons => buttons.map(button => button.getAttribute('aria-label'))));
    throw error;
  } finally { await app.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
