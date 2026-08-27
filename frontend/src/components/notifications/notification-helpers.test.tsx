import { describe, expect, it } from 'vitest'
import { formatNotificationTime } from '@/components/notifications/notification-helpers'

describe('formatNotificationTime', () => {
  it('formats recent timestamps', () => {
    const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    expect(formatNotificationTime(recent)).toBe('5m ago')
  })

  it('returns dash for missing values', () => {
    expect(formatNotificationTime(null)).toBe('—')
  })
})
