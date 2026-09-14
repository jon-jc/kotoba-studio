import { BrowserWindow, ipcMain } from 'electron'
import { createInterface } from 'node:readline'
import { createConnection } from 'node:net'

/** Host only the main workspace inside Kotoba; account dialogs keep normal behavior. */
export function installKotobaWindowHost(window: BrowserWindow): void {
  const nonce = process.env.KOTOBA_FLEET_NONCE
  if (!process.env.KOTOBA_FLEET_HOME || !nonce || process.platform !== 'win32') return
  window.setMinimumSize(0, 0)
  window.setMenuBarVisibility(false)
  window.setSkipTaskbar(true)
  // Qt owns native visibility. Chromium must keep painting even though Electron's
  // hidden-launch state cannot observe the foreign parent becoming visible.
  window.webContents.setBackgroundThrottling(false)
  const emit = (value: object): void => { process.stdout.write(JSON.stringify({ kotoba: nonce, ...value }) + '\n') }
  // A foreign Qt parent can own native focus while Chromium only has DOM focus.
  // Transfer focus on a user gesture, never on snapshot/presentation polling.
  const focusContent = (): void => {
    if (!window.isDestroyed() && window.isVisible() && !window.webContents.isDestroyed()) {
      // Qt owns the foreground HWND. Let its UI thread hand native focus to
      // the adopted child; webContents.focus() alone changes only DOM focus.
      emit({ kind: 'focus' })
    }
  }
  const focusFromRenderer = (event: Electron.IpcMainEvent): void => {
    if (event.sender === window.webContents && event.senderFrame === window.webContents.mainFrame) focusContent()
  }
  ipcMain.on('kotoba:focusEmbedded', focusFromRenderer)
  window.once('closed', () => ipcMain.removeListener('kotoba:focusEmbedded', focusFromRenderer))
  window.webContents.on('did-finish-load', () => {
    emit({ kind: 'window', handle: window.getNativeWindowHandle().readBigUInt64LE().toString() })
  })
  const pipe = process.env.KOTOBA_FLEET_PIPE
  if (!pipe) return
  const channel = createConnection(pipe)
  channel.on('error', () => channel.destroy())
  const input = createInterface({ input: channel, crlfDelay: Infinity })
  input.on('line', (line) => {
    if (line.length > 131072 || window.isDestroyed()) return
    let request: { id?: unknown; operation?: unknown; value?: unknown }
    try { request = JSON.parse(line) } catch { return }
    if (!request || typeof request !== 'object' || Array.isArray(request)) return
    if (!Number.isSafeInteger(request.id) || !['snapshot', 'draft', 'addProject', 'navigate', 'present'].includes(String(request.operation))) return
    if (typeof request.value !== 'string' || request.value.length > 64000) return
    if (request.operation === 'present') {
      // Called only after Qt has adopted the owned HWND. Native reparenting alone
      // does not notify Chromium that its initially hidden surface is visible.
      if (request.value === 'hidden') {
        window.hide()
        emit({ kind: 'result', id: request.id, value: true })
        return
      }
      window.showInactive()
      // invalidate() is for offscreen rendering. A compositor copy request forces
      // the native surface to submit a fresh frame after foreign-parent visibility
      // changes. Discard the image immediately; no screenshot is saved or sent.
      void window.webContents.capturePage(undefined, { stayHidden: true }).then(
        frame => emit({ kind: 'result', id: request.id, value: !frame.isEmpty() }),
        () => emit({ kind: 'result', id: request.id, value: false })
      )
      return
    }
    const script = `window.kotobaWorkspace?.[${JSON.stringify(request.operation)}](${JSON.stringify(request.value)}) ?? null`
    void window.webContents.executeJavaScript(script).then(
      value => emit({ kind: 'result', id: request.id, value }),
      () => emit({ kind: 'result', id: request.id, value: null })
    )
  })
  window.once('closed', () => { input.close(); channel.destroy() })
}
