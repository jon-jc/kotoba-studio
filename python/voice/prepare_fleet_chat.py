"""Promote the pinned runtime's supported conversation transports in Kotoba."""
from pathlib import Path
import shutil


def prepare_chat(root, patch):
    for before, after in (
        ("command-code --trust '--yolo' 'fix the spinner'", "command-code --trust 'fix the spinner'"),
        ('command: "command-code --trust \'--yolo\'"', 'command: "command-code --trust"'),
        ('command: "claude \'--dangerously-skip-permissions\'"', 'command: "claude"'),
    ):
        patch(root, 'src/renderer/src/lib/launch-agent-in-new-tab.test.ts', before, after)
    patch(root, 'src/renderer/src/lib/launch-agent-in-new-tab.ts',
          'export type LaunchAgentInNewTabArgs = {',
          "export type LaunchAgentInNewTabArgs = {\n  viewMode?: 'chat' | 'terminal'")
    patch(root, 'src/renderer/src/lib/launch-agent-in-new-tab.ts',
          '  const store = useAppStore.getState()',
          '  const currentStore = useAppStore.getState()\n'
          '  // A per-launch view choice never changes other chats or saved preferences.\n'
          '  const store = args.viewMode && currentStore.settings ? { ...currentStore, settings: {\n'
          '    ...currentStore.settings,\n'
          "    experimentalNativeChat: args.viewMode === 'chat',\n"
          "    experimentalStructuredNativeChat: args.viewMode === 'chat',\n"
          "    openAgentTabsInChatByDefault: args.viewMode === 'chat'\n"
          '  } } : currentStore')
    patch(root, 'src/renderer/src/lib/launch-agent-in-new-tab.test.ts',
          "  it('stamps the launched agent on the new tab for immediate provider icon bootstrap',",
          """  it.each(['chat', 'terminal'] as const)('honors a per-launch %s choice without changing other sessions', async (viewMode) => {
    const preferChat = viewMode !== 'chat'
    store.settings.experimentalNativeChat = preferChat
    store.settings.experimentalStructuredNativeChat = preferChat
    store.settings.openAgentTabsInChatByDefault = preferChat
    store.settings.agentDefaultArgs = { codex: '--sandbox workspace-write' }
    const original = structuredClone(store.settings)
    const { launchAgentInNewTab } = await import('./launch-agent-in-new-tab')
    launchAgentInNewTab({ agent: 'codex', worktreeId: 'wt-1', viewMode })
    expect(mockCreateTab.mock.calls[0]?.[3]?.viewMode ?? 'terminal').toBe(viewMode)
    expect(store.settings).toEqual(original)
  })

  it('stamps the launched agent on the new tab for immediate provider icon bootstrap',""")
    patch(root, 'src/main/windows/windows-process-table.ts',
          "import { createRequire } from 'node:module'",
          "import { createRequire } from 'node:module'\nimport { join } from 'node:path'")
    patch(root, 'src/main/windows/windows-process-table.ts',
          'const requireFromMain = createRequire(__filename)',
          '// The validated native dependency closure lives in resources/node_modules.\n'
          '// Do not select the collector\'s incomplete JS-only copy inside app.asar.\n'
          'const requireFromMain = createRequire(\n'
          '  process.env.KOTOBA_FLEET_HOME && process.resourcesPath\n'
          "    ? join(process.resourcesPath, 'package.json') : __filename\n)")
    # Kotoba deliberately removed upstream's global approval-bypass defaults.
    patch(root, 'src/renderer/src/lib/agent-launch-routing.test.ts',
          "hasExplicitTuiAgentArgs('codex', '--dangerously-bypass-approvals-and-sandbox')",
          "hasExplicitTuiAgentArgs('codex', '')")
    for key in ('openAgentTabsInChatByDefault', 'experimentalNativeChat', 'experimentalStructuredNativeChat'):
        patch(root, 'src/shared/default-global-settings.ts', f'    {key}: false,', f'    {key}: true,')
    patch(root, 'src/shared/global-settings-types.ts', 'export type GlobalSettings = {',
          'export type GlobalSettings = {\n  kotobaChatDefaultsMigrated?: boolean')
    patch(root, 'src/shared/default-global-settings.ts', '    openAgentTabsInChatByDefault: true,',
          '    kotobaChatDefaultsMigrated: true,\n    openAgentTabsInChatByDefault: true,')
    patch(root, 'src/main/persistence/loading-store/normalize-loaded-global-settings.ts',
          "import { getDefaultVoiceSettings }", "import { migrateKotobaChatDefaults } from '../../../shared/kotoba-chat-defaults'\nimport { getDefaultVoiceSettings }")
    patch(root, 'src/main/persistence/loading-store/normalize-loaded-global-settings.ts',
          '    ...stripRetiredGlobalSettings(parsed.settings),',
          '    ...stripRetiredGlobalSettings(parsed.settings),\n    ...migrateKotobaChatDefaults(parsed.settings),')
    patch(root, 'src/main/persistence/loading-store/prepare-loaded-profile-settings.ts',
          '  const migratedDisabledTuiAgents =',
          '  if (parsed.settings?.kotobaChatDefaultsMigrated !== true) markNeedsSave()\n  const migratedDisabledTuiAgents =')
    patch(root, 'src/renderer/src/components/settings/AgentsPane.tsx',
          "import { KotobaAgentAccess }", "import { KotobaAgentChat } from './KotobaAgentChat'\nimport { KotobaAgentAccess }")
    patch(root, 'src/renderer/src/components/settings/AgentsPane.tsx',
          '      <KotobaAgentAccess settings={settings} updateSettings={updateSettings} />',
          '      <KotobaAgentChat settings={settings} updateSettings={updateSettings} />\n      <KotobaAgentAccess settings={settings} updateSettings={updateSettings} />')
    for source, target in (
        ('fleet_chat_defaults.ts', 'src/shared/kotoba-chat-defaults.ts'),
        ('fleet_chat_defaults.test.ts', 'src/shared/kotoba-chat-defaults.test.ts'),
        ('fleet_chat_panel.tsx', 'src/renderer/src/components/settings/KotobaAgentChat.tsx'),
        ('fleet_window_host.test.ts', 'src/main/window/kotoba-window-host.test.ts'),
        ('fleet_new_chat.tsx', 'src/renderer/src/components/tab-bar/KotobaNewChat.tsx'),
        ('fleet_new_chat.test.tsx', 'src/renderer/src/components/tab-bar/KotobaNewChat.test.tsx'),
    ):
        shutil.copyfile(Path(__file__).with_name(source), root / target)


def prepare_chat_experience(root, patch):
    voice = Path(__file__).resolve().parent
    for name, dest in [('fleet_sidebar_chat.tsx', 'src/renderer/src/components/sidebar/KotobaSidebarChat.tsx'),
                       ('fleet_chat_recovery.ts', 'src/renderer/src/lib/kotoba-chat-recovery.ts'),
                       ('fleet_chat_recovery.test.ts', 'src/renderer/src/lib/kotoba-chat-recovery.test.ts'),
                       ('fleet_sidebar_chat.test.tsx', 'src/renderer/src/components/sidebar/KotobaSidebarChat.test.tsx')]:
        (root / dest).write_text((voice / name).read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    path = root / 'src/renderer/src/components/tab-bar/tab-bar-surface.tsx'
    source = path.read_text(encoding='utf-8')
    source = source.replace("import { KotobaNewChat } from './KotobaNewChat'\n", '')
    source = '\n'.join(line for line in source.split('\n') if '<KotobaNewChat worktreeId=' not in line)
    path.write_text(source, encoding='utf-8', newline='\n')
    patch(root, 'src/renderer/src/components/sidebar/SidebarNav.tsx', "import React from 'react'",
          "import React from 'react'\nimport { KotobaSidebarChat } from './KotobaSidebarChat'")
    patch(root, 'src/renderer/src/components/sidebar/SidebarNav.tsx',
          '      <button\n        type="button"\n        onClick={() => openModal(\'worktree-palette\')}',
          '      <KotobaSidebarChat />\n      <button\n        type="button"\n        onClick={() => openModal(\'worktree-palette\')}')
    patch(root, 'src/renderer/src/lib/structured-agent-session-launch-failure-toast.ts',
          "import { toast } from 'sonner'", "import { toast } from 'sonner'\nimport { showKotobaChatRecovery } from './kotoba-chat-recovery'")
    patch(root, 'src/renderer/src/lib/structured-agent-session-launch-failure-toast.ts',
          '    const agentLabel = structuredAgentLabel(agent)',
          '    if (showKotobaChatRecovery(agent, error)) return\n    const agentLabel = structuredAgentLabel(agent)')


def prepare_claude_chat_compatibility(root, patch):
    # Claude's initialize control response is available before a prompt, but its
    # session-id-bearing init frame is not. Keep the existing terminal-backed
    # conversation adapter rather than sending a hidden prompt or inventing proof.
    patch(root, 'src/shared/structured-native-chat-launch-route.ts',
          'if (!isAgentSessionHandleProvider(input.agent)) {',
          "if (!isAgentSessionHandleProvider(input.agent) || input.agent === 'claude') {")
    for file in ('src/shared/structured-native-chat-launch-route.test.ts',
                 'src/renderer/src/lib/agent-launch-routing.test.ts'):
        path = root / file
        source = path.read_text(encoding='utf-8').replace("it.each(['claude', 'codex'] as const)", "it.each(['codex'] as const)")
        if file.startswith('src/shared/'):
            source = source.replace("    agent: 'claude',", "    agent: 'codex',")
        path.write_text(source, encoding='utf-8', newline='\n')
    shutil.copyfile(Path(__file__).with_name('fleet_claude_chat_route.test.ts'),
                    root / 'src/renderer/src/lib/kotoba-claude-chat-route.test.ts')

    shutil.copyfile(Path(__file__).with_name('fleet_claude_setup.tsx'),
                    root / 'src/renderer/src/components/native-chat/KotobaClaudeSetup.tsx')
    patch(root, 'src/renderer/src/components/native-chat/NativeChatResolvedView.tsx',
          "import { useCallback, useEffect, useMemo, useRef, useState } from 'react'",
          "import { useCallback, useEffect, useMemo, useRef, useState } from 'react'\nimport { KotobaClaudeSetup } from './KotobaClaudeSetup'")
    patch(root, 'src/renderer/src/components/native-chat/NativeChatResolvedView.tsx',
          "  const canSend = useNativeChatCanSend(targetPtyId)",
          "  const canSend = useNativeChatCanSend(targetPtyId)\n  const claudeStarting = agent === 'claude' && !sessionId")
    patch(root, 'src/renderer/src/components/native-chat/NativeChatResolvedView.tsx',
          "      {questionActive ? null : (",
          "      {claudeStarting ? <KotobaClaudeSetup onOpenTerminal={onSwitchToTerminal} /> : questionActive ? null : (")

    shutil.copyfile(Path(__file__).with_name('fleet_claude_setup.test.tsx'),
                    root / 'src/renderer/src/components/native-chat/KotobaClaudeSetup.test.tsx')

    for source, target in (
        ('fleet_claude_language_file.ts', 'src/main/window/kotoba-claude-language-file.ts'),
        ('fleet_claude_language.ts', 'src/renderer/src/lib/kotoba-claude-language.ts'),
        ('fleet_claude_language_notice.tsx', 'src/renderer/src/components/terminal-pane/KotobaClaudeLanguageNotice.tsx'),
    ):
        shutil.copyfile(Path(__file__).with_name(source), root / target)
    patch(root, 'src/renderer/src/lib/launch-agent-in-new-tab.ts',
          "import { useAppStore } from '@/store'",
          "import { useAppStore } from '@/store'\nimport { claudeLanguageArgs } from './kotoba-claude-language'")
    patch(root, 'src/renderer/src/lib/launch-agent-in-new-tab.ts',
          '    agentArgs: effectiveAgentArgs,',
          "    agentArgs: claudeLanguageArgs(agent, effectiveAgentArgs, queuedShell ?? 'powershell', resolvedLaunchPlatform === 'win32' && !isRemote),")
    patch(root, 'src/renderer/src/components/terminal-pane/TerminalPaneSurface.tsx',
          "import { createPortal } from 'react-dom'",
          "import { createPortal } from 'react-dom'\nimport { KotobaClaudeLanguageNotice } from './KotobaClaudeLanguageNotice'")
    patch(root, 'src/renderer/src/components/terminal-pane/TerminalPaneSurface.tsx',
          '  return (\n    <>',
          "  return (\n    <div className=\"absolute inset-0 flex min-h-0 flex-col\">\n      {isActive && activePaneCanToggleChat && activePane && controller.resolveAgentForLeaf(activePane.leafId) === 'claude' && <KotobaClaudeLanguageNotice paneId={activePane.leafId} isChat={activePaneIsChatLeaf} onOpenChat={handleToggleNativeChat} />}\n      <div className=\"relative min-h-0 flex-1\">")
    patch(root, 'src/renderer/src/components/terminal-pane/TerminalPaneSurface.tsx',
          '    </>\n  )', '      </div>\n    </div>\n  )')

    for source, target in (
        ('fleet_claude_language_file.test.ts', 'src/main/window/kotoba-claude-language-file.test.ts'),
        ('fleet_claude_language.test.ts', 'src/renderer/src/lib/kotoba-claude-language.test.ts'),
        ('fleet_claude_language_notice.test.tsx', 'src/renderer/src/components/terminal-pane/KotobaClaudeLanguageNotice.test.tsx'),
    ):
        shutil.copyfile(Path(__file__).with_name(source), root / target)

    patch(root, 'src/renderer/src/components/native-chat/NativeChatMessageRow.tsx',
          "import { translate } from '@/i18n/i18n'",
          "import { translate } from '@/i18n/i18n'\nimport { useTranslation } from 'react-i18next'\nimport { localizedClaudeStatus } from '../../lib/kotoba-claude-language'")
    patch(root, 'src/renderer/src/components/native-chat/NativeChatMessageRow.tsx',
          '  const rowRef = useRef<HTMLDivElement | null>(null)',
          '  const { i18n } = useTranslation()\n  const rowRef = useRef<HTMLDivElement | null>(null)')
    patch(root, 'src/renderer/src/components/native-chat/NativeChatMessageRow.tsx',
          '          content={markdown}\n          variant="document"',
          '          content={localizedClaudeStatus(markdown, i18n.language)}\n          variant="document"')
