import type { KpiEstimate } from '../api/types'

// The main history-vs-QTD series for ONE selected KPI: historical quarters fill `history`,
// the in-progress 2026Q1 row fills `qtd`.
export interface ChartPoint {
  period: string
  history: number | null
  qtd: number | null
}

// The intra-quarter QTD trajectory (one selected KPI), for the QTD toggle.
export interface TrajectoryPoint {
  as_of: string
  value: number
}

interface PlacedPoint {
  periodStart: string
  point: ChartPoint
}

function inRange(periodStart: string, range?: { start?: string; end?: string }): boolean {
  // ISO date strings sort/compare chronologically. Filter on period_start, never the label.
  if (range?.start && periodStart < range.start) return false
  if (range?.end && periodStart > range.end) return false
  return true
}

export function toChartSeries(
  estimates: KpiEstimate[],
  kpi: string,
  range?: { start?: string; end?: string },
): ChartPoint[] {
  const forKpi = estimates.filter((e) => e.kpi === kpi)

  const placed: PlacedPoint[] = forKpi
    .filter((e) => e.estimate_type === 'historical')
    .map((e) => ({
      periodStart: e.period_start,
      point: { period: e.period, history: Number(e.value), qtd: null },
    }))

  // QTD contributes one point: the latest snapshot (max as_of).
  const qtdRows = forKpi.filter((e) => e.estimate_type === 'qtd')
  if (qtdRows.length > 0) {
    const latest = qtdRows.reduce((a, b) => ((a.as_of ?? '') >= (b.as_of ?? '') ? a : b))
    placed.push({
      periodStart: latest.period_start,
      point: { period: latest.period, history: null, qtd: Number(latest.value) },
    })
  }

  return placed
    .filter((row) => inRange(row.periodStart, range))
    .sort((a, b) => a.periodStart.localeCompare(b.periodStart))
    .map((row) => row.point)
}

export function qtdTrajectory(estimates: KpiEstimate[], kpi: string): TrajectoryPoint[] {
  return estimates
    .filter(
      (e): e is KpiEstimate & { as_of: string } =>
        e.kpi === kpi && e.estimate_type === 'qtd' && e.as_of !== null,
    )
    .map((e) => ({ as_of: e.as_of, value: Number(e.value) }))
    .sort((a, b) => a.as_of.localeCompare(b.as_of))
}
