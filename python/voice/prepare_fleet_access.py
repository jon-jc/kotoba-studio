"""Kotoba product overlays: scoped agent access and no mobile companion surface."""
from pathlib import Path
import shutil


def prepare_access(root, replace_once):
    def patch(path, before, after):
        replace_once(root, path, before, after)
    patch('src/renderer/src/components/onboarding/AgentStep.tsx',
          '      <YoloPermissionsControl\n        yoloPermissions={yoloPermissions}\n        onYoloPermissionsChange={onYoloPermissionsChange}\n      />',
          '      {/* Access levels are configured in Kotoba Agent settings. */}')
    patch('src/renderer/src/components/onboarding/use-onboarding-flow-persistence.ts',
          "mode: yoloPermissions ? 'yolo' : 'manual',", "mode: 'manual',")
    patch('src/renderer/src/components/sidebar/SidebarNav.tsx',
          '{showMobileButton ? (', '{false && showMobileButton ? (')
    patch('src/renderer/src/hooks/settings-navigation-capability-sections.ts',
          "...(showDesktopOnlySettings\n      ? [\n          {\n            id: 'mobile',",
          "...(false && showDesktopOnlySettings\n      ? [\n          {\n            id: 'mobile',")
    patch('src/renderer/src/components/settings/settings-setup-workflow-section-renderers.tsx',
          "  return model.showDesktopOnlySettings ? (\n    <SettingsSection\n      id=\"mobile\"",
          "  return false && model.showDesktopOnlySettings ? (\n    <SettingsSection\n      id=\"mobile\"")
    patch('src/renderer/src/app-shell/AppWorkspaceShell.tsx',
          "{activeView === 'mobile' ? <MobilePage /> : null}",
          "{activeView === 'mobile' ? <Landing /> : null}")
    patch('src/renderer/src/store/slices/ui/ui-slice-view-actions.ts',
          "        activeView: 'mobile',", "        activeView: 'terminal', // Kotoba has no mobile companion.")
    appearance = root / 'src/renderer/src/components/settings/AppearanceWindowSidebarSection.tsx'
    source = appearance.read_text(encoding='utf-8')
    marker = "'Show Orca Mobile Button'"
    if marker in source:
        index = source.index(marker)
        start = source.rfind('                  <SearchableSetting', 0, index)
        end = source.index('</SearchableSetting>', index) + len('</SearchableSetting>')
        if start < 0:
            raise ValueError('Mobile appearance overlay no longer matches')
        source = source[:start] + '                  {/* Mobile companion removed in Kotoba. */}' + source[end:]
        appearance.write_text(source, encoding='utf-8', newline='\n')
    patch('src/main/ipc/mobile.ts',
          '  const firewallEnvironment = dependencies.firewallEnvironment ?? {',
          "  if (process.env.KOTOBA_FLEET_HOME) return\n  const firewallEnvironment = dependencies.firewallEnvironment ?? {")
    launch = root / 'src/main/startup/main-process-runtime-launch.ts'
    source = launch.read_text(encoding='utf-8')
    source = source.replace('\n  startDesktopPushService(runtimeRpc)', '\n  if (!process.env.KOTOBA_FLEET_HOME) startDesktopPushService(runtimeRpc)')
    launch.write_text(source, encoding='utf-8', newline='\n')
    patch('src/main/startup/main-process-runtime-launch.ts',
          '  if (cloudAuth.configured) {',
          '  if (cloudAuth.configured && !process.env.KOTOBA_FLEET_HOME) {')
    pane = root / 'src/renderer/src/components/settings/AgentsPane.tsx'
    source = pane.read_text(encoding='utf-8')
    start_marker = 'export function AgentPermissionsSetting('
    if start_marker in source:
        start = source.index(start_marker)
        end = source.index('export function AgentsPane(', start)
        source = source[:start] + source[end:]
        block_start = source.index('      <AgentPermissionsSetting')
        block_end = source.index('      />', block_start) + len('      />')
        source = source[:block_start] + source[block_end:]
        source = source.replace('    <div className="space-y-8">', '    <div className="space-y-8">\n      <KotobaAgentAccess settings={settings} updateSettings={updateSettings} />', 1)
        source = source.replace("import { Info } from 'lucide-react'", "import { KotobaAgentAccess } from './KotobaAgentAccess'")
        source = source.replace('  SettingsSegmentedControl,\n', '')
        source = source.replace("import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip'\n", '')
        start = source.index('import {\n  applyAgentPermissionMode,')
        end = source.index("from '../../../../shared/tui-agent-permissions'", start) + len("from '../../../../shared/tui-agent-permissions'")
        source = source[:start] + source[end:]
        pane.write_text(source, encoding='utf-8', newline='\n')
    for local, target in [('fleet_access_levels.ts', 'src/shared/kotoba-agent-access.ts'),
                           ('fleet_access_levels.test.ts', 'src/shared/kotoba-agent-access.test.ts'),
                           ('fleet_access_panel.tsx', 'src/renderer/src/components/settings/KotobaAgentAccess.tsx')]:
        shutil.copyfile(Path(__file__).with_name(local), root / target)

    patch('src/main/persistence/applying-settings/terminal-settings-migrations.ts',
          "import type { GlobalSettings, OrcaWorkspaceLayout }",
          "import { applyAgentPermissionMode } from '../../../shared/tui-agent-permissions'\nimport type { GlobalSettings, OrcaWorkspaceLayout }")
    patch('src/main/persistence/applying-settings/terminal-settings-migrations.ts',
          "  const existingEnv = normalizeTuiAgentEnvRecord(settings?.agentDefaultEnv)",
          "  const existingEnv = normalizeTuiAgentEnvRecord(settings?.agentDefaultEnv)\n  if (process.env.KOTOBA_FLEET_HOME) {\n    // Retire the old global bypass preset; preserve user-owned custom arguments.\n    return { ...applyAgentPermissionMode({ mode: 'manual', agentDefaultArgs: existingArgs, agentDefaultEnv: existingEnv }), agentYoloDefaultsMigrated: true }\n  }")
    # Remove retired component definitions and their now-unused imports as well.
    agent_step = root / 'src/renderer/src/components/onboarding/AgentStep.tsx'
    source = agent_step.read_text(encoding='utf-8')
    if 'function YoloPermissionsControl(' in source:
        start = source.index('function YoloPermissionsControl(')
        end = source.index('function SectionHeader(', start)
        source = source[:start] + source[end:]
        source = source.replace('Check, ExternalLink, Info', 'Check, ExternalLink')
        source = source.replace("import { Checkbox } from '@/components/ui/checkbox'\n", '')
        source = source.replace('  isDetecting,\n  yoloPermissions = true,\n  onYoloPermissionsChange', '  isDetecting')
        agent_step.write_text(source, encoding='utf-8', newline='\n')
    for file, removed in [
        ('src/renderer/src/app-shell/AppWorkspaceShell.tsx', "const MobilePage = lazy(() => import('../components/mobile/MobilePage'))\n"),
        ('src/renderer/src/components/settings/AgentsPane.tsx', '  SettingsSubsectionHeader,\n'),
        ('src/renderer/src/components/settings/AgentsPane.tsx', "import { translate } from '@/i18n/i18n'\n"),
    ]:
        path = root / file
        source = path.read_text(encoding='utf-8').replace(removed, '')
        path.write_text(source, encoding='utf-8', newline='\n')
    # The pinned upstream test for the removed toggle is superseded by Kotoba's access tests.
    path = root / 'src/renderer/src/components/settings/AgentsPane.test.tsx'
    source = path.read_text(encoding='utf-8').replace('  AgentPermissionsSetting,\n', '')
    marker = "  it('applies the selected agent permission mode from settings without a mixed segment'"
    if marker in source:
        start = source.index(marker)
        end = source.index("  it('keeps catalog agent ids", start)
        source = source[:start] + source[end:]
    path.write_text(source, encoding='utf-8', newline='\n')
    path = root / 'src/renderer/src/components/settings/appearance-sidebar-search.ts'
    source = path.read_text(encoding='utf-8')
    marker = "'Show Orca Mobile Button'"
    if marker in source:
        start = source.rfind('  {\n', 0, source.index(marker))
        end = source.index('  getWorkspaceCardLayoutEntry()', start)
        source = source[:start] + source[end:]
    path.write_text(source, encoding='utf-8', newline='\n')
    path = root / 'src/renderer/src/components/onboarding/AgentStep.tsx'
    source = path.read_text(encoding='utf-8').replace("import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'\n", '')
    path.write_text(source, encoding='utf-8', newline='\n')
    shutil.copyfile(Path(__file__).with_name('fleet_access_runtime.test.ts'), root / 'src/main/runtime/kotoba-agent-access.test.ts')
    # Account pages must not advertise the retired relay service.
    for name, component in [('settings/OrcaAccountSettingsPane.tsx', 'AccountBenefit'), ('UnexpectedSignoutCard.tsx', 'FeatureRow')]:
        path = root / ('src/renderer/src/components/' + name)
        source = path.read_text(encoding='utf-8')
        marker = "'Connect Orca Mobile to this desktop across cellular or any Wi-Fi.'"
        if marker in source:
            start = source.rfind('<' + component, 0, source.index(marker))
            end = source.index('/>', source.index(marker)) + 2
            source = source[:start] + '{/* Mobile relay is not part of Kotoba. */}' + source[end:]
            source = source.replace('  Smartphone,\n', '').replace(', Smartphone', '').replace('Smartphone, ', '')
            path.write_text(source, encoding='utf-8', newline='\n')
    patch('src/main/persistence/loading-store/prepare-loaded-profile-settings.ts',
          '    parsed.settings?.agentYoloDefaultsMigrated !== true ||',
          "    (process.env.KOTOBA_FLEET_HOME && (JSON.stringify(parsed.settings?.agentDefaultArgs) !== JSON.stringify(migratedAgentYoloDefaults.agentDefaultArgs) || JSON.stringify(parsed.settings?.agentDefaultEnv) !== JSON.stringify(migratedAgentYoloDefaults.agentDefaultEnv))) ||\n    parsed.settings?.agentYoloDefaultsMigrated !== true ||")
    for relative in ['src/renderer/src/hooks/settings-navigation-capability-sections.ts', 'src/renderer/src/components/settings/settings-setup-workflow-section-renderers.tsx']:
        path = root / relative
        source = path.read_text(encoding='utf-8').replace('auto.components.settings.orcaAccount.description', 'auto.components.settings.orcaAccount.artifactsDescription').replace('Share work instantly and reach your desktop from Orca Mobile wherever you are.', 'Publish HTML and Markdown files, then manage every shared link from Orca.')
        path.write_text(source, encoding='utf-8', newline='\n')
    # Retire upstream promotions without changing coding-agent sign-in or CLI execution.
    patch('src/shared/feature-tips.ts',
          '(tip) => !args.seenTipIds.has(tip.id) && !completedTipIds.has(tip.id)',
          "(tip) => tip.id !== 'orca-cli' && !args.seenTipIds.has(tip.id) && !completedTipIds.has(tip.id)")
    patch('src/renderer/src/components/feature-tips/feature-tip-modal-state.ts',
          '  const modalTipId = isFeatureTipId(args.modalData.tipId)',
          "  if (args.modalData.tipId === 'orca-cli') return null\n  const modalTipId = isFeatureTipId(args.modalData.tipId)")
    patch('src/renderer/src/components/feature-tips/FeatureTipsModal.tsx',
          '  const markCurrentTipSeen = (): void => {',
          "  useEffect(() => {\n    if (isOpen && !currentTip) closeModal()\n  }, [isOpen, currentTip, closeModal])\n\n  const markCurrentTipSeen = (): void => {")
    patch('src/renderer/src/hooks/settings-navigation-capability-sections.ts',
          "...(showDesktopOnlySettings\n      ? [\n          {\n            id: 'orca-account',",
          "...(false && showDesktopOnlySettings\n      ? [\n          {\n            id: 'orca-account',")
    patch('src/renderer/src/components/settings/settings-setup-workflow-section-renderers.tsx',
          '  return model.showDesktopOnlySettings ? (\n    <SettingsSection\n      id="orca-account"',
          '  return false && model.showDesktopOnlySettings ? (\n    <SettingsSection\n      id="orca-account"')
    patch('src/renderer/src/store/slices/ui/ui-slice-settings-actions.ts',
          '      set({ settingsNavigationTarget: target })',
          "      set({ settingsNavigationTarget: target.pane === 'orca-account'\n        ? { pane: 'accounts', repoId: null } : target })")
    path = root / 'src/renderer/src/app-shell/AppRootSurfaces.tsx'
    source = path.read_text(encoding='utf-8')
    start_marker = 'const UnexpectedSignoutCard = lazy(() =>'
    if start_marker in source:
        start = source.index(start_marker)
        end = source.index('\n)', start) + 2
        source = source[:start] + source[end:]
        start = source.rfind('        <Suspense', 0, source.index('<UnexpectedSignoutCard />'))
        end = source.index('</Suspense>', start) + len('</Suspense>')
        source = source[:start] + source[end:]
        path.write_text(source, encoding='utf-8', newline='\n')
    shutil.copyfile(Path(__file__).with_name('fleet_promotions.test.ts'), root / 'src/shared/kotoba-promotions.test.ts')
    # Retain upstream coverage, updating only expectations for the retired promotion.
    for relative in ['src/shared/feature-tips.test.ts', 'src/renderer/src/components/feature-tips/feature-tip-modal-state.test.ts']:
        path = root / relative
        source = path.read_text(encoding='utf-8')
        source = source.replace("expect(tips.map((tip) => tip.id)).toEqual(['orca-cli', 'cmd-j-palette', 'voice-dictation'])",
                                "expect(tips.map((tip) => tip.id)).toEqual(['cmd-j-palette', 'voice-dictation'])")
        source = source.replace("expect(tips.map((tip) => tip.id)).toEqual(['orca-cli', 'cmd-j-palette'])",
                                "expect(tips.map((tip) => tip.id)).toEqual(['cmd-j-palette'])")
        source = source.replace('falls back to the CLI tip', 'falls back to the command palette tip')
        source = source.replace("expect(tip?.id).toBe('orca-cli')", "expect(tip?.id).toBe('cmd-j-palette')")
        path.write_text(source, encoding='utf-8', newline='\n')
    path = root / 'src/renderer/src/hooks/useSettingsNavigationMetadata.test.ts'
    source = path.read_text(encoding='utf-8')
    source = source.replace("      'orca-account',\n", '')
    source = source.replace("      'mobile'\n", "      'automations',\n      'artifacts'\n")
    source = source.replace('places Mobile under Set Up instead of its own sidebar group', 'omits the retired mobile section')
    source = source.replace("expect(sections.find((section) => section.id === 'mobile')?.group).toBe('setup')",
                            "expect(sections.find((section) => section.id === 'mobile')).toBeUndefined()")
    source = source.replace('places the Orca account in Set Up on desktop only', 'omits the Orca cloud account on desktop and web')
    source = source.replace("expect(account?.group).toBe('setup')\n    expect(account?.searchEntries[0]?.title).toBe('Orca account')",
                            "expect(account).toBeUndefined()\n    expect(desktopSections.some((section) => section.id === 'accounts')).toBe(true)")
    path.write_text(source, encoding='utf-8', newline='\n')
