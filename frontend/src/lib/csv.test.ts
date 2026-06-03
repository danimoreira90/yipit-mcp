import { describe, expect, it } from 'vitest'

import { toCsv } from './csv'

describe('toCsv', () => {
  it('writes a header from the first row, then rows, escaping commas and quotes', () => {
    const rows = [
      { ticker: 'ACME', name: 'Acme, Inc', note: 'say "hi"' },
      { ticker: 'CLD9', name: 'Cloud9', note: '' },
    ]
    expect(toCsv(rows)).toBe(
      'ticker,name,note\n' + 'ACME,"Acme, Inc","say ""hi"""\n' + 'CLD9,Cloud9,',
    )
  })
})
