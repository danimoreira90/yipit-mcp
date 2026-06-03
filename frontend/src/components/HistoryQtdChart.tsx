import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { ChartPoint } from '../lib/chart'

interface Props {
  series: ChartPoint[]
  unit: string
}

// Settled history as a solid line; the current-quarter QTD as a distinct dashed marker.
export function HistoryQtdChart({ series, unit }: Props) {
  if (series.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center text-sm text-slate-400">
        No data for this range.
      </div>
    )
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer>
        <LineChart data={series} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="period" tick={{ fontSize: 12 }} stroke="#94a3b8" />
          <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" width={64} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="history"
            name={`History (${unit})`}
            stroke="#4f46e5"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="qtd"
            name={`QTD (${unit})`}
            stroke="#10b981"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={{ r: 4 }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
