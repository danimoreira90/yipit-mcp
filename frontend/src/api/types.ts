// Response shapes from the FastAPI backend (backend/api), typed against schemas.py exactly.
// NOTE: `value` arrives as a STRING (Pydantic Decimal -> JSON string); parse it inside the
// lib/ transforms, never in components.

export type EstimateType = 'historical' | 'qtd'

export interface Company {
  ticker: string
  name: string
  sector: string
}

export interface KpiEstimate {
  ticker: string
  kpi: string
  unit: string
  period: string // 'YYYYQn', e.g. '2026Q1'
  period_start: string // ISO date 'YYYY-MM-DD'
  period_end: string // ISO date
  estimate_type: EstimateType
  value: string // Decimal serialized as a string, e.g. '128.67'
  as_of: string | null // ISO date for qtd; null for historical
}
