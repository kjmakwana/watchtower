import type { NewsResponse, MarketsResponse } from './types'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function fetchNews(params?: {
  region?: string | null
  military?: boolean | null
  source?: string | null
  limit?: number
}): Promise<NewsResponse> {
  const query = new URLSearchParams()
  if (params?.region) query.set('region', params.region)
  if (params?.military != null) query.set('military', String(params.military))
  if (params?.source) query.set('source', params.source)
  if (params?.limit != null) query.set('limit', String(params.limit))
  const res = await fetch(`${BASE}/api/news?${query}`)
  if (!res.ok) throw new Error(`news fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchMarkets(type?: string): Promise<MarketsResponse> {
  const query = new URLSearchParams()
  if (type) query.set('type', type)
  const res = await fetch(`${BASE}/api/markets?${query}`)
  if (!res.ok) throw new Error(`markets fetch failed: ${res.status}`)
  return res.json()
}
