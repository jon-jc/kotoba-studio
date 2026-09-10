import type { SidebarBrandMarkOwnerProps } from '@deepseek-ai/dsh-client-ui-sidebar/client'
import { en } from './locales.ts'

/**
 * Render the Kotoba speech mark at the host's requested size.
 * @param props - Host-supplied mark presentation.
 * @returns the decorative speech mark.
 */
export function OfficialBrandMark({ size, className }: SidebarBrandMarkOwnerProps & { className?: string | undefined }) {
  return <img src="/favicon.svg" width={size} height={size} className={className} alt="" aria-hidden="true" />
}

/**
 * Render the invariant product name without its independently slotted mark.
 * @returns the Kotoba Studio wordmark.
 */
export function OfficialBrandName() {
  return <span>{en.productName}</span>
}
