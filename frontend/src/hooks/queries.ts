import { useQuery } from '@tanstack/react-query'

import { getCompanies, getCompanyEstimates, getSectors } from '../api/client'

// Thin TanStack Query wrappers over the typed client. Hooks never fetch directly —
// the client is the only module that calls fetch (the frontend spine).

export function useSectors() {
  return useQuery({ queryKey: ['sectors'], queryFn: getSectors })
}

export function useCompanies(params: { sector?: string; q?: string } = {}) {
  const { sector, q } = params
  return useQuery({
    queryKey: ['companies', sector ?? null, q ?? null],
    queryFn: () => getCompanies({ sector, q }),
  })
}

export function useCompanyEstimates(ticker: string) {
  return useQuery({
    queryKey: ['company-estimates', ticker],
    queryFn: () => getCompanyEstimates(ticker),
    enabled: ticker !== '',
  })
}
