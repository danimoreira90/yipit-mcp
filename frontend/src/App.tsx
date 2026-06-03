import { useEffect, useMemo, useReducer } from 'react'

import { ChartPanel } from './components/ChartPanel'
import { CompanyBrowser } from './components/CompanyBrowser'
import { KpiPicker } from './components/KpiPicker'
import { SectorFilter } from './components/SectorFilter'
import { useCompanyEstimates } from './hooks/queries'
import { qtdTrajectory, toChartSeries } from './lib/chart'
import { initialSelection, selectionReducer } from './state'

export function App() {
  const [selection, dispatch] = useReducer(selectionReducer, initialSelection)
  const { sector, q, ticker, kpi, range, trajectoryOn } = selection

  const estimatesQuery = useCompanyEstimates(ticker)
  const estimates = useMemo(() => estimatesQuery.data ?? [], [estimatesQuery.data])

  const kpis = useMemo(() => [...new Set(estimates.map((e) => e.kpi))].sort(), [estimates])

  // Default to the first KPI once a company's estimates arrive (or when the pick goes stale).
  useEffect(() => {
    if (kpis.length > 0 && !kpis.includes(kpi)) {
      dispatch({ type: 'setKpi', kpi: kpis[0] })
    }
  }, [kpis, kpi])

  const rangeArg = { start: range.start || undefined, end: range.end || undefined }
  const series = kpi ? toChartSeries(estimates, kpi, rangeArg) : []
  const trajectory = kpi ? qtdTrajectory(estimates, kpi) : []
  const asOf = trajectory.length > 0 ? trajectory[trajectory.length - 1].as_of : null
  const unit = estimates.find((e) => e.kpi === kpi)?.unit ?? ''

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <h1 className="text-xl font-semibold text-slate-900">YipitData KPI Portal</h1>
          <p className="text-sm text-slate-500">
            Browse KPI estimates per company — settled history vs the live quarter-to-date.
          </p>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-6 py-6">
        <aside className="w-80 shrink-0 space-y-4">
          <SectorFilter
            sector={sector}
            onChange={(value) => dispatch({ type: 'setSector', sector: value })}
          />
          <CompanyBrowser
            sector={sector}
            q={q}
            selected={ticker}
            onQueryChange={(value) => dispatch({ type: 'setQuery', q: value })}
            onSelect={(value) => dispatch({ type: 'selectCompany', ticker: value })}
          />
          {ticker && (
            <KpiPicker
              kpis={kpis}
              selected={kpi}
              loading={estimatesQuery.isLoading}
              onSelect={(value) => dispatch({ type: 'setKpi', kpi: value })}
            />
          )}
        </aside>

        <main className="min-w-0 flex-1">
          <ChartPanel
            ticker={ticker}
            kpi={kpi}
            unit={unit}
            series={series}
            trajectory={trajectory}
            asOf={asOf}
            range={range}
            trajectoryOn={trajectoryOn}
            loading={estimatesQuery.isLoading}
            error={estimatesQuery.isError}
            onRangeChange={(value) => dispatch({ type: 'setRange', range: value })}
            onToggleTrajectory={() => dispatch({ type: 'toggleTrajectory' })}
          />
        </main>
      </div>
    </div>
  )
}
