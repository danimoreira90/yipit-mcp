import { describe, expect, it } from 'vitest'

import type { KpiEstimate } from '../api/types'
import { qtdTrajectory, toChartSeries } from './chart'

const ASP = 'ASP ($)'

function hist(period: string, periodStart: string, value: string, kpi = ASP): KpiEstimate {
  return {
    ticker: 'ACME',
    kpi,
    unit: '$',
    period,
    period_start: periodStart,
    period_end: '2099-12-31',
    estimate_type: 'historical',
    value,
    as_of: null,
  }
}

function qtd(value: string, asOf: string, kpi = ASP): KpiEstimate {
  return {
    ticker: 'ACME',
    kpi,
    unit: '$',
    period: '2026Q1',
    period_start: '2026-01-01',
    period_end: '2026-03-31',
    estimate_type: 'qtd',
    value,
    as_of: asOf,
  }
}

// ACME 'ASP ($)' — historical and qtd rows deliberately out of order, plus a Units Sold row.
const fixture: KpiEstimate[] = [
  hist('2024Q1', '2024-01-01', '150.00'),
  hist('2022Q1', '2022-01-01', '128.67'),
  hist('2022Q2', '2022-04-01', '141.80'),
  qtd('164.22', '2026-03-15'),
  qtd('162.95', '2026-01-31'),
  qtd('169.64', '2026-02-15'),
  qtd('163.41', '2026-02-28'),
  hist('2022Q1', '2022-01-01', '999.00', 'Units Sold'),
]

describe('toChartSeries', () => {
  it('builds history + latest-qtd points sorted by period_start, values as numbers', () => {
    const series = toChartSeries(fixture, ASP)
    expect(series.map((p) => p.period)).toEqual(['2022Q1', '2022Q2', '2024Q1', '2026Q1'])

    const first = series[0]
    expect(first.period).toBe('2022Q1')
    expect(first.history).toBe(128.67) // ground truth
    expect(first.qtd).toBeNull()
    expect(typeof first.history).toBe('number')

    const current = series[series.length - 1]
    expect(current.period).toBe('2026Q1')
    expect(current.qtd).toBe(164.22) // latest as_of (2026-03-15)
    expect(current.history).toBeNull()
    expect(typeof current.qtd).toBe('number')
  })

  it('filters to the chosen kpi (drops the Units Sold rows)', () => {
    const series = toChartSeries(fixture, ASP)
    expect(series).toHaveLength(4) // 3 historical + 1 qtd
    expect(series.every((p) => p.history !== 999)).toBe(true)
  })

  it('applies the date range on period_start (excludes out-of-range quarters)', () => {
    const series = toChartSeries(fixture, ASP, { start: '2022-04-01', end: '2024-12-31' })
    expect(series.map((p) => p.period)).toEqual(['2022Q2', '2024Q1'])
  })
})

describe('qtdTrajectory', () => {
  it('returns the 4 snapshots sorted by as_of, values as numbers', () => {
    const trajectory = qtdTrajectory(fixture, ASP)
    expect(trajectory.map((t) => t.as_of)).toEqual([
      '2026-01-31',
      '2026-02-15',
      '2026-02-28',
      '2026-03-15',
    ])
    expect(trajectory[0].value).toBe(162.95)
    expect(trajectory[trajectory.length - 1].value).toBe(164.22) // ground truth
    expect(typeof trajectory[0].value).toBe('number')
  })
})
