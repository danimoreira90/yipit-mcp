export function AsOfBadge({ asOf }: { asOf: string }) {
  return (
    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
      QTD as of {asOf}
    </span>
  )
}
