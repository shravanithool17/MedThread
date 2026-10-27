import { describe, expect, it } from 'vitest'
import { formatTemporalComparison } from './temporalEvidence'
import type { TemporalComparison } from '../types'

const baseComparison: TemporalComparison = {
  first_note_id: 'NOTE_A',
  first_context: 'affirmed',
  first_visit_date: '2024-01-08',
  first_event_date: '2024-01-07',
  second_note_id: 'NOTE_B',
  second_context: 'negated',
  second_visit_date: '2024-01-10',
  second_event_date: '2024-01-09',
  event_date_comparison: 'different_event_dates',
  days_between_event_dates: 2,
}

describe('formatTemporalComparison', () => {
  it('shows elapsed time only for two comparable event dates', () => {
    expect(formatTemporalComparison(baseComparison))
      .toBe('2024-01-07 vs 2024-01-09 (2 days apart)')
  })

  it('does not substitute known visit dates when event dates are unavailable', () => {
    expect(formatTemporalComparison({
      ...baseComparison,
      first_event_date: null,
      second_event_date: null,
      event_date_comparison: 'event_date_unavailable',
      days_between_event_dates: null,
    })).toBe('event-date difference unavailable; one or both normalized dates are missing or invalid')
  })

  it('does not display a fabricated zero-day interval when the difference is missing', () => {
    expect(formatTemporalComparison({
      ...baseComparison,
      days_between_event_dates: null,
    })).toBe('event-date difference unavailable; one or both normalized dates are missing or invalid')
  })

  it('reports the same normalized event date without deriving a visit-date interval', () => {
    expect(formatTemporalComparison({
      ...baseComparison,
      second_event_date: '2024-01-07',
      event_date_comparison: 'same_event_date',
      days_between_event_dates: 0,
    })).toBe('same normalized event date (2024-01-07)')
  })
})
