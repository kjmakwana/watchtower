import { useState } from 'react'

export interface NewsFilters {
  region: string | null
  military: boolean | null
}

export interface MarketFilters {
  type: string | null
}

export function useFilters() {
  const [newsFilters, setNewsFilters] = useState<NewsFilters>({ region: null, military: null })
  const [marketFilters, setMarketFilters] = useState<MarketFilters>({ type: null })

  const setRegion = (r: string | null) => setNewsFilters((f) => ({ ...f, region: r }))
  const setMilitary = (m: boolean | null) => setNewsFilters((f) => ({ ...f, military: m }))
  const setMarketType = (t: string | null) => setMarketFilters({ type: t })

  return { newsFilters, marketFilters, setRegion, setMilitary, setMarketType }
}
