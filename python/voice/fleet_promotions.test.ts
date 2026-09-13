import { describe, expect, it } from 'vitest'
import { getOrderedUnseenFeatureTips } from './feature-tips'
import { getFeatureTipForModal } from '../renderer/src/components/feature-tips/feature-tip-modal-state'

describe('Kotoba promotion removal', () => {
  it('does not offer the Orca CLI promotion on a fresh profile', () => {
    const tips = getOrderedUnseenFeatureTips({ seenTipIds: new Set() })
    expect(tips.some((tip) => tip.id === 'orca-cli')).toBe(false)
    expect(tips.some((tip) => tip.id === 'cmd-j-palette')).toBe(true)
  })

  it('ignores an explicit or restored CLI promotion request', () => {
    expect(getFeatureTipForModal({
      cliInstalled: false, modalData: { tipId: 'orca-cli' },
      seenTipIds: [], featureInteractions: {}, settings: null
    })).toBeNull()
  })
})
