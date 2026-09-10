/** Product identity is invariant across the supported interface languages. */
export const en = { productName: 'Kotoba Studio' } satisfies Record<string, string>

/** Chinese product identity shares the same registered name. */
export const zh = { productName: 'Kotoba Studio' } satisfies Record<keyof typeof en, string>
