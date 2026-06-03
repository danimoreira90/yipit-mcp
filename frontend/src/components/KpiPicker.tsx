interface Props {
  kpis: string[]
  selected: string
  loading: boolean
  onSelect: (kpi: string) => void
}

export function KpiPicker({ kpis, selected, loading, onSelect }: Props) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        KPI
      </label>
      {loading ? (
        <p className="text-sm text-slate-400">Loading KPIs…</p>
      ) : (
        <div className="flex flex-col gap-1">
          {kpis.map((kpi) => (
            <button
              key={kpi}
              onClick={() => onSelect(kpi)}
              className={`rounded-md px-3 py-1.5 text-left text-sm ${
                selected === kpi
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
              }`}
            >
              {kpi}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
