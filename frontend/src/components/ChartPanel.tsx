import type { ChartPoint, TrajectoryPoint } from '../lib/chart'
import { toCsv } from '../lib/csv'
import { downloadCsv } from '../lib/download'
import type { DateRange } from '../state'
import { AsOfBadge } from './AsOfBadge'
import { HistoryQtdChart } from './HistoryQtdChart'
import { TrajectoryPanel } from './TrajectoryPanel'

interface Props {
  ticker: string
  kpi: string
  unit: string
  series: ChartPoint[]
  trajectory: TrajectoryPoint[]
  asOf: string | null
  range: DateRange
  trajectoryOn: boolean
  loading: boolean
  error: boolean
  onRangeChange: (range: DateRange) => void
  onToggleTrajectory: () => void
}

function Message({ children }: { children: string }) {
  return (
    <div className="flex h-96 items-center justify-center text-sm text-slate-400">{children}</div>
  )
}

// ChartPoint is an interface, so flatten to plain records for the (Record-typed) toCsv.
function seriesToRows(series: ChartPoint[]): Record<string, string | number | null>[] {
  return series.map((point) => ({ period: point.period, history: point.history, qtd: point.qtd }))
}

export function ChartPanel(props: Props) {
  const { ticker, kpi, unit, series, trajectory, asOf, range, trajectoryOn } = props

  if (!ticker) return <Message>Search and pick a company to see its KPI estimates.</Message>
  if (props.loading) return <Message>Loading estimates…</Message>
  if (props.error) return <Message>Couldn’t load estimates. Is the API running?</Message>

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">
          {ticker} <span className="text-slate-400">·</span> {kpi}
        </h2>
        {asOf && <AsOfBadge asOf={asOf} />}
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-4 border-b border-slate-100 pb-4">
        <label className="text-xs font-medium text-slate-500">
          From
          <input
            type="date"
            value={range.start}
            onChange={(event) => props.onRangeChange({ ...range, start: event.target.value })}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-slate-500">
          To
          <input
            type="date"
            value={range.end}
            onChange={(event) => props.onRangeChange({ ...range, end: event.target.value })}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
        {(range.start || range.end) && (
          <button
            onClick={() => props.onRangeChange({ start: '', end: '' })}
            className="text-xs text-slate-400 underline hover:text-slate-600"
          >
            clear
          </button>
        )}

        <div className="ml-auto flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={trajectoryOn}
              onChange={props.onToggleTrajectory}
              className="h-4 w-4 rounded border-slate-300 text-indigo-600"
            />
            QTD trajectory
          </label>
          <button
            onClick={() => downloadCsv(`${ticker}_${kpi}.csv`, toCsv(seriesToRows(series)))}
            disabled={series.length === 0}
            className="rounded-md bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-40"
          >
            Export CSV
          </button>
        </div>
      </div>

      <HistoryQtdChart series={series} unit={unit} />
      {trajectoryOn && trajectory.length > 0 && (
        <TrajectoryPanel trajectory={trajectory} unit={unit} />
      )}
    </section>
  )
}
