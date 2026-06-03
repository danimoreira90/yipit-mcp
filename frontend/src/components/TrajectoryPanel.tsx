import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { TrajectoryPoint } from '../lib/chart'

interface Props {
  trajectory: TrajectoryPoint[]
  unit: string
}

// The intra-quarter QTD snapshots — how the current-quarter estimate moved through the quarter.
export function TrajectoryPanel({ trajectory, unit }: Props) {
  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <h3 className="mb-2 text-sm font-semibold text-slate-600">
        Intra-quarter QTD trajectory
      </h3>
      <div className="h-44 w-full">
        <ResponsiveContainer>
          <LineChart data={trajectory} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="as_of" tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" width={64} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              name={`QTD (${unit})`}
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
