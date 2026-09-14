import { EventEmitter } from 'node:events'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ ipc: { on: vi.fn(), removeListener: vi.fn() }, connect: vi.fn(), lines: vi.fn(), quit: vi.fn() }))
vi.mock('electron', () => ({ app: { quit: mocks.quit }, BrowserWindow: class {}, ipcMain: mocks.ipc }))
vi.mock('node:net', () => ({ createConnection: mocks.connect }))
vi.mock('node:readline', () => ({ createInterface: mocks.lines }))
import { installKotobaWindowHost } from './kotoba-window-host'

afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })

function fixture() {
  vi.stubGlobal('process', { ...process, platform: 'win32',
    env: { KOTOBA_FLEET_HOME: '/owned', KOTOBA_FLEET_NONCE: 'nonce', KOTOBA_FLEET_PIPE: 'pipe' },
    stdout: { write: vi.fn() } })
  const socket = Object.assign(new EventEmitter(), { destroy: vi.fn() })
  const input = Object.assign(new EventEmitter(), { close: vi.fn() })
  mocks.connect.mockReturnValue(socket); mocks.lines.mockReturnValue(input)
  const webContents = Object.assign(new EventEmitter(), { mainFrame: {}, focus: vi.fn(),
    isDestroyed: vi.fn(() => false), setBackgroundThrottling: vi.fn(),
    capturePage: vi.fn(async () => ({ isEmpty: () => false })), executeJavaScript: vi.fn(async () => true) })
  const window = Object.assign(new EventEmitter(), { webContents,
    setMinimumSize: vi.fn(), setMenuBarVisibility: vi.fn(), setSkipTaskbar: vi.fn(),
    showInactive: vi.fn(), hide: vi.fn(), isDestroyed: vi.fn(() => false), isVisible: vi.fn(() => true) })
  installKotobaWindowHost(window as never)
  const focus = mocks.ipc.on.mock.calls.find(([name]) => name === 'kotoba:focusEmbedded')![1]
  return { window, input, webContents, focus }
}

describe('embedded keyboard focus', () => {
  it('focuses only the owned main frame and removes its listener on close', () => {
    const { window, webContents, focus } = fixture()
    focus({ sender: {}, senderFrame: webContents.mainFrame })
    focus({ sender: webContents, senderFrame: {} })
    expect(process.stdout.write).not.toHaveBeenCalled()
    focus({ sender: webContents, senderFrame: webContents.mainFrame })
    expect(process.stdout.write).toHaveBeenCalledWith(expect.stringContaining('"kind":"focus"'))
    expect(webContents.focus).toHaveBeenCalledOnce()
    window.emit('closed')
    expect(mocks.ipc.removeListener).toHaveBeenCalledWith('kotoba:focusEmbedded', focus)
  })
  it('does not request focus during polling and delegates native visibility to Qt', () => {
    const { window, input, webContents, focus } = fixture()
    input.emit('line', JSON.stringify({ id: 1, operation: 'present', value: '' }))
    input.emit('line', JSON.stringify({ id: 2, operation: 'snapshot', value: 'en' }))
    expect(process.stdout.write).not.toHaveBeenCalled()
    expect(webContents.focus).not.toHaveBeenCalled()
    window.isVisible.mockReturnValue(false)
    focus({ sender: webContents, senderFrame: webContents.mainFrame })
    expect(process.stdout.write).toHaveBeenCalledWith(expect.stringContaining('"kind":"focus"'))
    vi.mocked(process.stdout.write).mockClear()
    window.isDestroyed.mockReturnValue(true)
    focus({ sender: webContents, senderFrame: webContents.mainFrame })
    expect(process.stdout.write).not.toHaveBeenCalled()
  })
})


describe('embedded shutdown', () => {
  it('uses normal app quit only for a valid parent request', () => {
    const { input, webContents } = fixture()
    input.emit('line', JSON.stringify({ id: 1, operation: 'quit', value: 'invalid' }))
    input.emit('line', JSON.stringify({ id: '1', operation: 'quit', value: '' }))
    expect(mocks.quit).not.toHaveBeenCalled()
    input.emit('line', JSON.stringify({ id: 2, operation: 'quit', value: '' }))
    expect(mocks.quit).toHaveBeenCalledOnce()
    expect(webContents.executeJavaScript).not.toHaveBeenCalled()
  })
})
