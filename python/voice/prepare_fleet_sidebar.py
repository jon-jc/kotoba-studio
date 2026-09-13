"""Remove upstream community and onboarding links from Kotoba's help menu."""


def prepare_sidebar(root):
    prepare_sidebar_tests(root)
    path = root / 'src/renderer/src/components/sidebar/SidebarSettingsHelpMenu.tsx'
    source = path.read_text(encoding='utf-8')
    if source.startswith('// Kotoba sidebar menu'):
        return

    def cut(start, end):
        nonlocal source
        left = source.index(start)
        right = source.index(end, left)
        source = source[:left] + source[right:]

    cut('            <DropdownMenuSeparator />\n            <DropdownMenuItem onSelect={handleOpenFeedback}',
        '            <DropdownMenuSeparator />\n            <DropdownMenuItem\n              disabled={updateStatus')
    cut('      {feedbackDialogMounted ? (', '    </>')
    cut('// Why lazy:', 'const NO_UPDATE_CHECK_MODIFIERS')
    cut('function openExternalUrl(', 'export function SidebarSettingsHelpMenu')
    cut('  const showMilestones =', '  const handleMenuOpenChange')
    cut('    if (open) {\n      // Warm on the precursor:', '  }\n\n  const handleOpenFeedback')
    cut('  const handleOpenFeedback =', '  const handleRestartOrca =')
    cut('  const openMilestones =', '  return (')
    for name in ['BookOpen', 'ExternalLink', 'Github', 'MessageSquareText', 'School', 'ScrollText']:
        source = source.replace('  ' + name + ',\n', '')
    for line in source.splitlines(keepends=True):
        if any(marker in line for marker in [
            "import logo from", "import { showOnboardingFromRenderer }", "import { SetupGuideProgressRing }",
            "import { useSetupGuideProgress }", "import { lazyWithRetry }", "import type * as SidebarFeedbackDialogModule",
            'const openModal =', 'const setupProgress =', 'const [feedbackOpen,', 'const [feedbackDialogMounted,',
            'const lastShowOnboardingAtRef =', '// Why sticky:'
        ]):
            source = source.replace(line, '')
    path.write_text('// Kotoba sidebar menu: local controls only.\n' + source, encoding='utf-8', newline='\n')


def prepare_sidebar_tests(root):
    path = root / 'src/renderer/src/components/sidebar/SidebarSettingsHelpMenu.test.tsx'
    source = path.read_text(encoding='utf-8')
    for label in ['Send Feedback', 'Milestones', 'Onboarding', 'Docs', 'Changelog', 'GitHub', 'Discord', '>X<',
                  'data-testid="setup-guide-progress-ring"', 'viewBox="0 0 20 20"',
                  'M16.0742 4.45014C14.9244 3.92097 13.7106 3.54556 12.4638 3.3335']:
        source = source.replace(f"expect(html).toContain('{label}')", f"expect(html).not.toContain('{label}')")
    for title in ['Send Feedback menu item', 'Milestones with progress when setup is incomplete',
                  'the Onboarding menu item by default', 'Docs link', 'Changelog link', 'GitHub link', 'Discord link', 'X link']:
        source = source.replace("it('renders " + title, "it('omits " + title)
    start_marker = "  it('opens Discord invite through the shell bridge'"
    if start_marker in source:
        start = source.index(start_marker)
        end = source.index("  it('", start + len(start_marker))
        source = source[:start] + "  it('does not expose community links or open external sites', async () => {\n    const container = await renderMenu()\n    expect(container.textContent).not.toContain('Discord')\n    expect(mocks.shellOpenUrl).not.toHaveBeenCalled()\n  })\n\n" + source[end:]
    source = source.replace('warms the feedback chunk when the menu opens, before Send Feedback is selected', 'does not load the retired feedback dialog on menu open')
    source = source.replace('expect(mocks.feedbackChunkLoads).toBe(1)', 'expect(mocks.feedbackChunkLoads).toBe(0)')
    source = source.replace('  // No other test in this file opens the menu or selects Send Feedback, so the 0 -> 1\n  // transition below is this warm and nothing else, whatever order the tests run in.\n', '')
    path.write_text(source, encoding='utf-8', newline='\n')
