import { afterEach, describe, expect, it, vi } from 'vitest'

import { getSectors } from './client'

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('getSectors calls GET {base}/sectors and returns the parsed array', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(['Cloud', 'E-commerce']),
    })
    vi.stubGlobal('fetch', fetchMock)

    const sectors = await getSectors()

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/sectors')
    expect(sectors).toEqual(['Cloud', 'E-commerce'])
  })
})
