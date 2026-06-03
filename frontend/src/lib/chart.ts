import type { KpiEstimate } from '../api/types'

// The main history-vs-QTD series for ONE selected KPI: historical quarters fill `history`,
// the in-progress 2026Q1 row fills `qtd`.
export interface ChartPoint {
  period: string
  history: number | null
  qtd: number | null
}

// TODO(6.3): merge the historical series with the qtd value into ChartPoint[] (parse the
// string `value` to a number here, never in components). 6.3 also adds a SEPARATE trajectory
// type ({ as_of; value }) for the intra-quarter QTD toggle — do not add it now.
export function toChartSeries(_estimates: KpiEstimate[], _kpi: string): ChartPoint[] {
  throw new Error('toChartSeries not implemented (6.3)')
}
