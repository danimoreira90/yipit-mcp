import { useCompanies } from '../hooks/queries'

interface Props {
  sector: string
  q: string
  selected: string
  onQueryChange: (q: string) => void
  onSelect: (ticker: string) => void
}

export function CompanyBrowser({ sector, q, selected, onQueryChange, onSelect }: Props) {
  const { data: companies, isLoading, isError } = useCompanies({
    sector: sector || undefined,
    q: q || undefined,
  })

  return (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        Company
      </label>
      <input
        value={q}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="Search name, ticker, or sector"
        className="mb-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
      />
      <div className="max-h-72 overflow-y-auto rounded-md border border-slate-200 bg-white">
        {isLoading && <p className="px-3 py-2 text-sm text-slate-400">Loading…</p>}
        {isError && <p className="px-3 py-2 text-sm text-rose-500">Couldn’t load companies.</p>}
        {companies?.length === 0 && (
          <p className="px-3 py-2 text-sm text-slate-400">No matches.</p>
        )}
        <ul>
          {(companies ?? []).map((company) => (
            <li key={company.ticker}>
              <button
                onClick={() => onSelect(company.ticker)}
                className={`flex w-full items-baseline justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 ${
                  selected === company.ticker ? 'bg-indigo-50' : ''
                }`}
              >
                <span>
                  <span className="font-semibold text-slate-700">{company.ticker}</span>{' '}
                  <span className="text-slate-500">{company.name}</span>
                </span>
                <span className="shrink-0 text-xs text-slate-400">{company.sector}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
