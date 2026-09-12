/** Shared projection of the live LLM registry into the browser model catalog. */

import type { Context } from '@deepseek-ai/cordis'
import type { CredentialRef } from '@deepseek-ai/dsh-credentials'
import type {} from '@deepseek-ai/dsh-settings'
import type {
  ModelCatalog,
  ModelReasoning,
  ModelSelection,
} from './types.ts'

/**
 * Build the browser model catalog without requiring a Session.
 * @param ctx - Host context carrying the live LLM registry.
 * @param defaultSelection - deployment default used before a Session selects a model.
 * @returns successful non-empty provider groups and isolated provider failures.
 */
export async function buildModelCatalog(
  ctx: Context,
  defaultSelection: ModelSelection = ctx.agentDefaultModel.currentSelection(),
): Promise<ModelCatalog> {
  const providers = ctx.llm.listProviders()
  const directory = ctx.llm.listConfigurableProviders()
  const settings = ctx.get('settings')
  const credentials = ctx.get('credentials')
  const catalog = await Promise.all(providers.map(async (provider) => {
    try {
      let configured: boolean | undefined
      const declared = directory.find(entry => entry.provider === provider.id)
      if (declared !== undefined && settings !== undefined) {
        let profile = settings.get(declared.settingsNs)
        for (const part of declared.settingsPath) {
          profile = typeof profile === 'object' && profile !== null
            ? (profile as Record<string, unknown>)[part] : undefined
        }
        if (typeof profile === 'object' && profile !== null) {
          const ref = (profile as Record<string, unknown>).apiKeyEnv
          if (typeof ref !== 'string' || ref.length === 0) configured = true
          else if (credentials !== undefined) {
            try { configured = (await credentials.describe(ref as CredentialRef)).configured }
            catch { /* Credential availability is unknown; keep the catalog usable. */ }
          }
        } else configured = false
      }
      const models = await ctx.llm.listModels(provider.id)
      const entries = await Promise.all(models.map(async (model) => {
        const resolved = await ctx.llm.resolveModelInfo(provider.id, model.id)
        const reasoning: ModelReasoning | undefined = resolved.reasoning === undefined
          ? undefined
          : {
            efforts: resolved.reasoning.efforts.map(effort => ({
              id: effort.id,
              name: effort.name,
              ...(effort.description === undefined ? {} : { description: effort.description }),
            })),
            ...(resolved.reasoning.defaultEffort === undefined
              ? {}
              : { defaultEffort: resolved.reasoning.defaultEffort }),
          }
        return {
          id: model.id,
          name: model.name,
          ...(model.description === undefined ? {} : { description: model.description }),
          ...(reasoning === undefined ? {} : { reasoning }),
        }
      }))
      return {
        kind: 'group' as const,
        group: { id: provider.id, name: provider.name, models: entries, ...configured === undefined ? {} : { configured } },
      }
    } catch (error) {
      return {
        kind: 'failure' as const,
        failure: {
          id: provider.id,
          name: provider.name,
          message: error instanceof Error ? error.message : String(error),
        },
      }
    }
  }))
  return {
    default: { ...defaultSelection },
    routableProviders: providers.map(provider => provider.id),
    groups: catalog.flatMap(item => item.kind === 'group' ? [item.group] : [])
      .filter(group => group.models.length > 0)
      .sort((a, b) => Number(b.configured === true) - Number(a.configured === true)),
    failures: catalog.flatMap(item => item.kind === 'failure' ? [item.failure] : []),
  }
}
