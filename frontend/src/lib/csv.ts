type Cell = string | number | null | undefined
type Row = Record<string, Cell>

// RFC-4180-ish: wrap a cell in quotes when it contains a comma, quote, or newline; double
// any inner quotes. null/undefined become empty cells.
function escapeCell(value: Cell): string {
  const text = value == null ? '' : String(value)
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function toCsv(rows: ReadonlyArray<Row>): string {
  if (rows.length === 0) return ''
  const headers = Object.keys(rows[0])
  const lines = [
    headers.map(escapeCell).join(','),
    ...rows.map((row) => headers.map((header) => escapeCell(row[header])).join(',')),
  ]
  return lines.join('\n')
}
