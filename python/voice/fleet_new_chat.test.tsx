// @vitest-environment happy-dom
import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ launch: vi.fn(() => ({ tabId: 'new-tab' })),
  state: { settings: { disabledTuiAgents: ['grok'], defaultTuiAgent: 'codex' } },
  target: { kind: 'local' } }))
vi.mock('@/store', () => ({ useAppStore: (selector: (value: unknown) => unknown) => selector(mocks.state) }))
vi.mock('@/hooks/useDetectedAgents', () => ({ useDetectedAgents: () => ({ detectedIds: ['codex', 'claude', 'openclaude', 'grok', 'omp', 'pi', 'opencode'] }) }))
vi.mock('@/hooks/useAgentDetectionTarget', () => ({ useAgentDetectionTargetForWorktree: () => mocks.target }))
vi.mock('@/lib/agent-catalog', () => ({ getAgentCatalog: () => ['codex', 'claude', 'openclaude', 'grok', 'omp', 'pi', 'opencode'].map(id => ({ id, label: id })) }))
vi.mock('@/lib/launch-agent-in-new-tab', () => ({ launchAgentInNewTab: mocks.launch }))
vi.mock('@/lib/structured-agent-session-launch', () => ({ useStructuredAgentLaunchStatus: () => 'idle' }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ i18n: { language: 'en' } }) }))
vi.mock('@/components/ui/dropdown-menu', () => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => <div>{children}</div>
  return { DropdownMenu: Wrapper, DropdownMenuContent: Wrapper, DropdownMenuTrigger: Wrapper,
    DropdownMenuLabel: Wrapper, DropdownMenuSeparator: () => <hr />,
    DropdownMenuItem: ({ children, onSelect, disabled }: { children: React.ReactNode; onSelect?: () => void; disabled?: boolean }) => <button disabled={disabled} onClick={onSelect}>{children}</button> }
})
import { KotobaNewChat } from './KotobaNewChat'
afterEach(() => { cleanup(); mocks.target.kind = 'local'; vi.clearAllMocks() })

describe('available agent conversation choices', () => {
  it('offers every enabled chat adapter and retains terminal-only agents', () => {
    render(<KotobaNewChat worktreeId="workspace" groupId="group" onFocusTerminal={() => {}} onMenuClose={() => {}} />)
    for (const name of ['codex chat', 'Claude Code chat', 'openclaude chat', 'omp chat']) expect(screen.getByRole('button', { name })).toBeTruthy()
    for (const name of ['grok chat', 'pi chat', 'opencode chat']) expect(screen.queryByRole('button', { name })).toBeNull()
    expect(screen.getByRole('button', { name: 'pi terminal' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'openclaude chat' }))
    expect(mocks.launch).toHaveBeenCalledWith({ agent: 'openclaude', worktreeId: 'workspace', groupId: 'group', viewMode: 'chat' })
    fireEvent.click(screen.getByRole('button', { name: 'codex terminal' }))
    expect(mocks.launch).toHaveBeenLastCalledWith({ agent: 'codex', worktreeId: 'workspace', groupId: 'group', viewMode: 'terminal' })
  })
  it('does not advertise a local-file-only transcript adapter on a remote host', () => {
    mocks.target.kind = 'ssh'
    render(<KotobaNewChat worktreeId="remote" groupId="group" onFocusTerminal={() => {}} onMenuClose={() => {}} />)
    expect(screen.queryByRole('button', { name: 'omp chat' })).toBeNull()
    expect(screen.getByRole('button', { name: 'omp terminal' })).toBeTruthy()
  })
})
