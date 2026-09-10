/** Kotoba Studio occupants for the generic browser-brand slots. */
import type { Context as ClientContext } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-ui-renderer/client'
import type {} from '@deepseek-ai/dsh-client-ui-sidebar/client'
import type {} from '@deepseek-ai/dsh-client-ui-conversation/client'
import type {} from '@deepseek-ai/dsh-client-locale/client'
import type {} from '@deepseek-ai/dsh-client-ui-theme/client'
import { OfficialBrandMark, OfficialBrandName } from './Brand.tsx'
import { japanese } from './japanese.ts'
import { followDesktopLocale } from './desktop-locale.ts'
import { palette } from './palette.ts'

/** Required service: the UI slot registry. */
export const inject = ['slots', 'locale', 'theme']

/**
 * Fill sidebar and conversation brand slots, withdrawing each with its declaration.
 * @param ctx - Client root context.
 */
export function apply(ctx: ClientContext): void {
  ctx.effect(() => ctx.theme.overrideTokens('kotoba-studio', palette), 'Kotoba workbench palette')
  ctx.effect(() => ctx.locale.addLanguage({ id: 'ja', label: '日本語', fallback: 'en' }), 'Kotoba Japanese language')
  for (const [namespace, dictionary] of Object.entries(japanese)) {
    ctx.effect(() => ctx.locale.register(namespace, 'ja', dictionary), `Kotoba Japanese: ${namespace}`)
  }
  ctx.effect(() => followDesktopLocale(ctx), 'Kotoba desktop language handoff')
  ctx.slots.inject('sidebar.brand.mark', () =>
    ctx.slots.inject('sidebar.brand.name', function* () {
      yield ctx.slots.register({ name: 'sidebar.brand.mark' }, OfficialBrandMark)
      yield ctx.slots.register({ name: 'sidebar.brand.name' }, OfficialBrandName)
    }))
  ctx.slots.inject('conversation.hero.brand.mark', () =>
    ctx.slots.register({ name: 'conversation.hero.brand.mark' }, OfficialBrandMark))
}
