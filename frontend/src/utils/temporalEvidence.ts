import type { TemporalComparison } from '../types'

export function formatTemporalComparison(comparison: TemporalComparison): string {
  if (
    comparison.event_date_comparison === 'same_event_date'
    && comparison.first_event_date
  ) {
    return `same normalized event date (${comparison.first_event_date})`
  }

  if (
    comparison.event_date_comparison === 'different_event_dates'
    && comparison.first_event_date
    && comparison.second_event_date
    && comparison.days_between_event_dates != null
    && Number.isFinite(comparison.days_between_event_dates)
  ) {
    return `${comparison.first_event_date} vs ${comparison.second_event_date} (${Math.abs(comparison.days_between_event_dates)} days apart)`
  }

  return 'event-date difference unavailable; one or both normalized dates are missing or invalid'
}
