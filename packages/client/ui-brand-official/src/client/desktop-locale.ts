/** Desktop-to-browser language handoff; model prompts and user text are never translated. */
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-locale/client'

/**
 * Follow the native shell's explicit choice, including a choice made before plugin activation.
 * @param ctx - the owning plugin context and existing locale service.
 * @returns event-listener teardown.
 */
export function followDesktopLocale(ctx: Context): () => void {
  const change = (): void => {
    const choice = document.documentElement.dataset.kotobaLocale
    if (choice === 'en' || choice === 'ja') ctx.locale.setLocale(choice)
  }
  document.addEventListener('kotoba:locale', change)
  change()
  return () => { document.removeEventListener('kotoba:locale', change) }
}
