export interface Article {
  id: number
  title: string
  url: string
  source: string
  source_name: string
  regions: string[]
  region: string  // DEPRECATED — use regions
  is_military: boolean
  summary: string
  published_at: string
  tickers: { ticker: string; weight: number }[] | null
}

export interface NewsResponse {
  total: number
  offset: number
  limit: number
  articles: Article[]
}

export interface MarketPrice {
  label: string
  symbol: string
  asset_type: string
  price: number
  prev_close: number | null
  change_pct: number | null
  currency: string | null
  source: string
  fetched_at: string | null
}

export interface MarketsResponse {
  count: number
  type_filter: string | null
  prices: MarketPrice[]
}

export interface GraphNode {
  id: string
  article_count: number
  military_count: number
  total_weight: number
  intensity: number
  source_diversity: number
  sources: string[]
  tickers_display: string[]
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
  military_weight: number
  dominant_ticker: string
  dominant_category: string
  tickers: { ticker: string; weight: number; category: string }[]
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta: { window_hours: number; generated_at: string; article_count: number; sparse_data: boolean }
}

export interface ClusterStory {
  cluster_id: number
  article_count: number
  title: string
  region: string
}

export interface ClustersResponse {
  clusters: ClusterStory[]
}
