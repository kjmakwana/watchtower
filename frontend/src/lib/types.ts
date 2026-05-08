export interface Article {
  id: number
  title: string
  url: string
  source: string
  source_name: string
  region: string
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
