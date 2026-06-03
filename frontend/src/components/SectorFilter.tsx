import { useSectors } from '../hooks/queries'

interface Props {
  sector: string
  onChange: (sector: string) => void
}

export function SectorFilter({ sector, onChange }: Props) {
  const { data: sectors, isLoading } = useSectors()

  return (
    <div>
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
        Sector
      </label>
      <select
        value={sector}
        onChange={(event) => onChange(event.target.value)}
        disabled={isLoading}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:opacity-50"
      >
        <option value="">All sectors</option>
        {(sectors ?? []).map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </div>
  )
}
