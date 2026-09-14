// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ state: { activeWorktreeId: null as string | null, openModal: vi.fn() },
  language: 'en', focus: vi.fn(), menu: vi.fn() }))
vi.mock('@/store', () => ({ useAppStore: Object.assign((selector: (state: typeof mocks.state) => unknown) => selector(mocks.state), { getState: () => mocks.state }) }))
vi.mock('react-i18next', () => ({ useTranslation: () => ({ i18n: { language: mocks.language } }) }))
vi.mock('@/lib/focus-terminal-tab-surface', () => ({ focusTerminalTabSurface: mocks.focus }))
vi.mock('../tab-bar/KotobaNewChat', () => ({ KotobaNewChat: (props: unknown) => { mocks.menu(props); return <div>Chat menu</div> } }))
import { KotobaSidebarChat } from './KotobaSidebarChat'

afterEach(() => { cleanup(); vi.clearAllMocks(); mocks.state.activeWorktreeId = null; mocks.language = 'en' })
describe('sidebar chat entry', () => {
  it.each(['en', 'ja'])('opens project setup without a selected workspace in %s', language => {
    mocks.language = language
    render(<KotobaSidebarChat />)
    fireEvent.click(screen.getByRole('button', { name: language === 'ja' ? 'プロジェクトを追加してチャット' : 'Add a project to chat' }))
    expect(mocks.state.openModal).toHaveBeenCalledWith('add-repo')
    expect(mocks.menu).not.toHaveBeenCalled()
  })
  it('targets the selected project and returns focus only after a launch', () => {
    mocks.state.activeWorktreeId = 'selected-worktree'
    const view = render(<KotobaSidebarChat />)
    let props = mocks.menu.mock.calls.at(-1)![0]
    expect(props.worktreeId).toBe('selected-worktree')
    expect(props.sidebar).toBe(true)
    expect(props.onMenuClose()).toBe(false)
    props.onFocusTerminal('new-terminal')
    expect(props.onMenuClose()).toBe(true)
    expect(mocks.focus).toHaveBeenCalledWith('new-terminal')
    expect(props.onMenuClose()).toBe(false)
    mocks.state.activeWorktreeId = 'another-worktree'
    view.rerender(<KotobaSidebarChat />)
    props = mocks.menu.mock.calls.at(-1)![0]
    expect(props.worktreeId).toBe('another-worktree')
  })
})
