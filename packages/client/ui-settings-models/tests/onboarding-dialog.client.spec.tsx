// @vitest-environment jsdom
/** First-run DeepSeek prompt behavior over the shared Models join. */
import type { GlobalStandardProps } from '@deepseek-ai/dsh-client-ui-slots'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Schema from '@deepseek-ai/schemastery'
import type { SettingsNamespaceView, SettingsPathOpView } from '@deepseek-ai/dsh-api-remotes/client'
import type { JsonValue } from '@deepseek-ai/dsh-util-values'
import { bindSnapshotSelector, RemoteError } from '@deepseek-ai/dsh-client-test-runtime'
import { DeepSeekOnboardingDialog } from '../src/client/DeepSeekOnboardingDialog.tsx'
import type { DeepSeekOnboardingDialogProps } from '../src/client/DeepSeekOnboardingDialog.tsx'
import { SettingsDescribeMirror } from '@deepseek-ai/dsh-client-ui-settings/src/client/settings-mirror.ts'
import { ModelsSettingsStore } from '../src/client/store.ts'
import { createModelsOperations } from '../src/client/operations.ts'
import { en } from '../src/client/locales.ts'
import { settingsSchema } from './settings-schema.client.ts'

// Every fixture carries the resource hook the resources plugin merges into GlobalStandardProps.
const useResource = (() => ({ status: 'none' as const, value: undefined, failure: undefined, reload: () => {} })) as GlobalStandardProps['useResource']

afterEach(() => {
  cleanup()
  document.getElementById('root')?.remove()
})

/** Credentials answers over the Remote carrier, which has no envelope. */
function remoteOk<T>(value: T) {
  return { ok: true as const, value }
}
function remoteFail(message: string) {
  return { ok: false as const, error: new RemoteError('gateway/internal', message, {}) }
}

const DeepSeekConfig = Schema.object({
  apiKeyEnv: Schema.string().role('credential-ref'),
  baseURL: Schema.string().pattern(/^https:\/\//),
  reasoningEffort: Schema.union(['off', 'low', 'high', 'max']),
  defaultContextWindow: Schema.number().step(1).min(1),
  models: Schema.array(Schema.object({
    id: Schema.string().required(),
    name: Schema.string(),
    description: Schema.string(),
    contextWindow: Schema.number().step(1).min(1),
  })),
})

type AttentionSnapshot = Parameters<Parameters<DeepSeekOnboardingDialogProps['useSessionPendingInteraction']>[0]>[0]
const noAttention: AttentionSnapshot = new Map()
const useSessionPendingInteraction: DeepSeekOnboardingDialogProps['useSessionPendingInteraction'] = selector => selector(noAttention)

function deepSeekNamespace(apiKeyEnv: string | null): SettingsNamespaceView {
  const value = apiKeyEnv === null ? {} : { apiKeyEnv }
  return {
    ns: 'llm-deepseek',
    schema: JSON.parse(JSON.stringify(DeepSeekConfig.toJSON())) as JsonValue,
    value,
    base: value,
    user: {},
    applies: 'live',
    secrets: [],
    revision: 0,
  }
}

function harness(options: {
  nativeProviders?: string[]
  provider?: boolean
  providerSettingsNs?: string
  providerActive?: boolean
  settingsNamespace?: boolean
  apiKeyEnv?: string | null
  configured?: () => boolean
  credential?: { source?: string; writable: boolean }
  describeFailure?: string
  settingsWritable?: boolean
  providersFailure?: string
  setFailure?: string
} = {}) {
  if (document.getElementById('root') === null) {
    const appRoot = document.createElement('div')
    appRoot.id = 'root'
    document.body.append(appRoot)
  }
  let fileConfigured = false
  const configured = options.configured ?? (() => fileConfigured)
  const apiKeyEnv = options.apiKeyEnv === undefined ? 'DEEPSEEK_API_KEY' : options.apiKeyEnv
  const nativeSchema = Schema.object({ providers: Schema.dict(Schema.object({ apiKeyEnv: Schema.string() })) })
  let nativeNamespace: SettingsNamespaceView = {
    ns: 'llm-pi-ai', schema: JSON.parse(JSON.stringify(nativeSchema.toJSON())) as JsonValue,
    value: {}, base: {}, user: {}, applies: 'live', secrets: [], revision: 0,
  }
  const storedKeys = new Set<string>()
  const mutate = vi.fn((_ns: string, ops: SettingsPathOpView[]) => {
    if (options.nativeProviders === undefined) return Promise.resolve(remoteOk(deepSeekNamespace(apiKeyEnv)))
    let user = nativeNamespace.user as Record<string, unknown>
    for (const op of ops) {
      if (op.op === 'set') user = settingsSchema.setPath(user, op.path, op.value)
    }
    nativeNamespace = { ...nativeNamespace, user: user as JsonValue, value: user as JsonValue, revision: nativeNamespace.revision + 1 }
    return Promise.resolve(remoteOk(nativeNamespace))
  })
  const set = vi.fn((_ref: string, _value: string) => {
    if (options.setFailure !== undefined) return Promise.resolve(remoteFail(options.setFailure))
    fileConfigured = true
    storedKeys.add(_ref)
    return Promise.resolve(remoteOk(undefined))
  })
  const face = {
    llm: {
      listProviders: () => {
        if (options.providersFailure !== undefined) return Promise.resolve(remoteFail(options.providersFailure))
        if (options.nativeProviders !== undefined) {
          return Promise.resolve(remoteOk(options.nativeProviders
            .filter(id => settingsSchema.getPath(nativeNamespace.value, ['providers', id]) !== undefined)
            .map(id => ({ id, name: id }))))
        }
        return Promise.resolve(remoteOk(
          options.provider === false || options.providerActive === false
            ? []
            : [{ id: 'deepseek-official', name: 'DeepSeek' }],
        ))
      },
      listConfigurableProviders: () => Promise.resolve(remoteOk(
        options.nativeProviders !== undefined
          ? options.nativeProviders.map(provider => ({ provider, displayName: provider,
            settingsNs: 'llm-pi-ai', settingsPath: ['providers', provider], declared: false }))
          : options.provider === false
            ? []
            : [{
              provider: 'deepseek-official',
              displayName: 'DeepSeek',
              settingsNs: options.providerSettingsNs ?? 'llm-deepseek',
              settingsPath: [],
            }],
      )),
      discoverModels: () => Promise.resolve(remoteOk([])),
    },
    settings: {
      describe: () => Promise.resolve(remoteOk({
        writable: options.settingsWritable ?? true,
        hasDocument: false,
        namespaces: options.nativeProviders !== undefined ? [nativeNamespace]
          : options.settingsNamespace === false ? [] : [deepSeekNamespace(apiKeyEnv)],
      })),
      mutate,
    },
    credentials: {
      describe: () => options.describeFailure === undefined
        ? Promise.resolve(remoteOk({
          ...Object.fromEntries((options.nativeProviders ?? []).map((id) => {
            const ref = `${id.toUpperCase()}_API_KEY`
            return [ref, { configured: storedKeys.has(ref), writable: true }]
          })),
          DEEPSEEK_API_KEY: {
            configured: configured(),
            ...configured() && options.credential?.source !== undefined
              ? { source: options.credential.source }
              : {},
            writable: options.credential?.writable ?? true,
          },
        }))
        : Promise.resolve(remoteFail(options.describeFailure)),
      set,
    },
  }
  // The page plugin's context, scripted down to the namespaces it reaches.
  const ctx = { remote: face } as never
  const mirror = new SettingsDescribeMirror(ctx)
  const operations = createModelsOperations(ctx, (view) => { mirror.acceptView(view) })
  const controller = new ModelsSettingsStore(ctx, settingsSchema, mirror)
  const openSection = vi.fn()
  const complete = vi.fn()
  const unusedHook = (() => { throw new Error('unused standard hook') }) as never
  const props: DeepSeekOnboardingDialogProps = {
    stepId: 'deepseek-official',
    complete,
    openSection,
    useSessions: unusedHook,
    useSessionPendingInteraction,
    useResource,
    useWorkspaces: unusedHook,
    controller,
    useModels: bindSnapshotSelector(controller.store),
    operations,
    schema: settingsSchema,
    t: key => en[key],
  }
  return {
    controller, complete, openSection, props, mutate, set,
    configure: () => { fileConfigured = true },
  }
}

describe('DeepSeekOnboardingDialog', () => {
  it.each(['openai', 'anthropic', 'moonshotai'])('activates %s and stores its own credential without DeepSeek', async (provider) => {
    const h = harness({ nativeProviders: ['openai', 'anthropic', 'moonshotai'] })
    render(<DeepSeekOnboardingDialog {...h.props} />)
    const selector = await screen.findByRole('combobox', { name: en.provider })
    fireEvent.change(selector, { target: { value: provider } })
    expect(screen.getByLabelText<HTMLInputElement>(en.keyInput).placeholder).toBe(en.keyPlaceholder)
    fireEvent.change(screen.getByLabelText(en.keyInput), { target: { value: 'sk-fixture-only' } })
    fireEvent.click(screen.getByRole('button', { name: en.onboardingSave }))
    await waitFor(() => { expect(h.complete).toHaveBeenCalledOnce() })
    const ref = `${provider.toUpperCase()}_API_KEY`
    expect(h.set).toHaveBeenCalledExactlyOnceWith(ref, 'sk-fixture-only')
    expect(h.mutate).toHaveBeenCalledExactlyOnceWith('llm-pi-ai', [
      { op: 'set', path: ['providers', provider, 'apiKeyEnv'], value: ref },
    ], 0)
    expect(h.controller.store.getSnapshot().rows.find(row => row.entry.provider === provider))
      .toMatchObject({ entry: { active: true }, apiKeyEnv: ref, credential: { configured: true } })
  })

  it('discards an unsaved key when switching providers', async () => {
    const h = harness({ nativeProviders: ['openai', 'anthropic', 'moonshotai'] })
    render(<DeepSeekOnboardingDialog {...h.props} />)
    const selector = await screen.findByRole('combobox', { name: en.provider })
    expect({ title: screen.getByRole('heading').textContent,
      providers: [...selector.querySelectorAll('option')].map(option => option.textContent),
      description: screen.getByText(en.onboardingDescription).textContent }).toMatchSnapshot()
    fireEvent.change(screen.getByLabelText(en.keyInput), { target: { value: 'openai-fixture-key' } })
    fireEvent.change(selector, { target: { value: 'anthropic' } })
    expect(screen.getByLabelText<HTMLInputElement>(en.keyInput).value).toBe('')
    expect(screen.getByRole<HTMLButtonElement>('button', { name: en.onboardingSave }).disabled).toBe(true)
    expect(h.set).not.toHaveBeenCalled()
  })

  it('locks provider selection during a credential write and allows retry after rejection', async () => {
    const h = harness({ nativeProviders: ['openai', 'anthropic'] })
    const pending = Promise.withResolvers<string | undefined>()
    const storeCredential = vi.fn(() => pending.promise)
    h.props.operations.storeCredential = storeCredential
    render(<DeepSeekOnboardingDialog {...h.props} />)
    const selector = await screen.findByRole<HTMLSelectElement>('combobox', { name: en.provider })
    fireEvent.change(screen.getByLabelText(en.keyInput), { target: { value: 'sk-fixture-only' } })
    fireEvent.click(screen.getByRole('button', { name: en.onboardingSave }))
    await waitFor(() => { expect(storeCredential).toHaveBeenCalledOnce() })
    expect(selector.disabled).toBe(true)
    await act(async () => { pending.resolve('Unable to store credential') })
    expect(await screen.findByText('Unable to store credential')).toBeTruthy()
    expect(selector.disabled).toBe(false)
    expect(h.complete).not.toHaveBeenCalled()
  })

  it('renders when the shell root is absent', async () => {
    const h = harness()
    document.getElementById('root')!.remove()
    render(<DeepSeekOnboardingDialog {...h.props} />)
    expect(await screen.findByRole('dialog', { name: en.onboardingTitle })).toBeTruthy()
  })

  it('loads a credential-only modal, inerts the product, and focuses the key', async () => {
    const h = harness()
    render(<DeepSeekOnboardingDialog {...h.props} />)
    expect(await screen.findByRole('dialog', { name: en.onboardingTitle })).toBeTruthy()
    expect(document.getElementById('root')?.inert).toBe(true)
    expect(screen.getByText(en.onboardingDescription)).toBeTruthy()
    const key = screen.getByLabelText<HTMLInputElement>(en.keyInput)
    await waitFor(() => { expect(document.activeElement).toBe(key) })
    expect(screen.queryByText(en.customized)).toBeNull()
  })

  it('cannot be dismissed implicitly and restores the previous inert state', async () => {
    const h = harness()
    const appRoot = document.getElementById('root')!
    appRoot.inert = true
    const view = render(<DeepSeekOnboardingDialog {...h.props} />)
    await screen.findByRole('dialog')

    fireEvent.keyDown(document, { key: 'Escape' })
    fireEvent.click(document.querySelector('[class*="mask"]')!)
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(h.complete).not.toHaveBeenCalled()

    view.unmount()
    expect(appRoot.inert).toBe(true)
  })

  it('requires a non-blank key before Save and continue is available', async () => {
    const h = harness()
    render(<DeepSeekOnboardingDialog {...h.props} />)
    await screen.findByRole('dialog')
    const save = screen.getByRole<HTMLButtonElement>('button', { name: en.onboardingSave })
    expect(save.disabled).toBe(true)
    fireEvent.change(screen.getByLabelText(en.keyInput), { target: { value: '   ' } })
    expect(save.disabled).toBe(true)
    expect(screen.getByText(en.keyRequired)).toBeTruthy()
    expect(h.set).not.toHaveBeenCalled()
  })

  it('keeps the modal open and reports a refused credential write', async () => {
    for (const [options, message] of [
      [{ setFailure: 'credential was rejected' }, 'credential was rejected'],
    ] as const) {
      const h = harness(options)
      const view = render(<DeepSeekOnboardingDialog {...h.props} />)
      await screen.findByRole('dialog')
      fireEvent.change(screen.getByLabelText(en.keyInput), { target: { value: 'sk-live' } })
      fireEvent.click(screen.getByRole('button', { name: en.onboardingSave }))
      expect(await screen.findByText(message)).toBeTruthy()
      expect(screen.getByRole('dialog')).toBeTruthy()
      expect(screen.getByRole<HTMLButtonElement>('button', { name: en.onboardingSave }).disabled).toBe(false)
      expect(h.complete).not.toHaveBeenCalled()
      expect(h.mutate).not.toHaveBeenCalled()
      view.unmount()
    }
  })

  it('allows configure-later dismissal without opening settings', async () => {
    const h = harness()
    render(<DeepSeekOnboardingDialog {...h.props} />)
    await screen.findByRole('dialog')
    fireEvent.click(screen.getByRole('button', { name: en.onboardingLater }))
    expect(h.complete).toHaveBeenCalledOnce()
    expect(h.openSection).not.toHaveBeenCalled()
    expect(h.set).not.toHaveBeenCalled()
    expect(h.mutate).not.toHaveBeenCalled()
  })

  it('does not block the product when DeepSeek setup is unavailable', async () => {
    for (const h of [
      harness({ describeFailure: 'credentials service is absent' }),
      harness({ credential: { writable: false } }),
      harness({ settingsWritable: false }),
      harness({ providersFailure: 'the provider directory is unavailable' }),
      harness({ providerActive: false }),
      harness({ settingsNamespace: false }),
      harness({ apiKeyEnv: null }),
    ]) {
      const view = render(<DeepSeekOnboardingDialog {...h.props} />)
      await act(async () => { await h.controller.load() })
      expect(screen.queryByRole('dialog')).toBeNull()
      await waitFor(() => { expect(h.complete).toHaveBeenCalledOnce() })
      expect(h.openSection).not.toHaveBeenCalled()
      view.unmount()
    }
  })

  it('skips an absent adapter and an already-configured environment credential', async () => {
    for (const h of [
      harness({ provider: false }),
      harness({ providerSettingsNs: '' }),
      harness({ configured: () => true, credential: { source: 'env', writable: false } }),
    ]) {
      const view = render(<DeepSeekOnboardingDialog {...h.props} />)
      await act(async () => { await h.controller.load() })
      expect(screen.queryByRole('dialog')).toBeNull()
      await waitFor(() => { expect(h.complete).toHaveBeenCalledOnce() })
      view.unmount()
    }
  })

  it('closes when an external credential invalidation refreshes the shared join', async () => {
    const h = harness()
    render(<DeepSeekOnboardingDialog {...h.props} />)
    await screen.findByRole('dialog')
    h.configure()
    await act(async () => { await h.controller.load() })
    await waitFor(() => { expect(screen.queryByRole('dialog')).toBeNull() })
    expect(h.complete).toHaveBeenCalledOnce()
  })
})
