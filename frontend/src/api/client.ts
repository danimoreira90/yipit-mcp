import type { Company, KpiEstimate } from './types'

// This is the ONLY module that calls fetch. Everything else consumes this typed client.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`)
  }
  return (await response.json()) as T
}

export function getSectors(): Promise<string[]> {
  return getJson<string[]>('/sectors')
}

export function getCompanies(
  params: { sector?: string; q?: string } = {},
): Promise<Company[]> {
  const search = new URLSearchParams()
  if (params.sector) search.set('sector', params.sector)
  if (params.q) search.set('q', params.q)
  const query = search.toString()
  return getJson<Company[]>(`/companies${query ? `?${query}` : ''}`)
}

export function getCompanyEstimates(ticker: string): Promise<KpiEstimate[]> {
  return getJson<KpiEstimate[]>(`/companies/${encodeURIComponent(ticker)}/estimates`)
}
