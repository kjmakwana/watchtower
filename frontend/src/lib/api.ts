import type { NewsResponse, MarketsResponse, GraphResponse, ClustersResponse } from './types'

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

export async function fetchGraph(hours?: number): Promise<GraphResponse> {
  const query = new URLSearchParams()
  if (hours != null) query.set('hours', String(hours))
  const res = await fetch(`${BASE}/api/graph?${query}`)
  if (!res.ok) throw new Error(`graph fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchTopClusters(limit = 5): Promise<ClustersResponse> {
  const query = new URLSearchParams({ limit: String(limit) })
  const res = await fetch(`${BASE}/api/clusters/top?${query}`)
  if (!res.ok) throw new Error(`clusters fetch failed: ${res.status}`)
  return res.json()
}
