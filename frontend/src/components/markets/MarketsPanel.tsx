import { useQuery } from '@tanstack/react-query'
import { fetchMarkets } from '@/lib/api'
import { MarketRow } from './MarketRow'
import type { MarketPrice } from '@/lib/types'

function GroupLabel({ label }: { label: string }) {
  return (
    <div className="px-3 py-1 font-mono text-[9px] uppercase tracking-widest text-ink-faint bg-panel border-b border-line">
      {label}
    </div>
  )
}

function lastUpdated(prices: MarketPrice[]): string {
  const ts = prices.find((p) => p.fetched_at)?.fetched_at
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function MarketsPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['markets'],
    queryFn: () => fetchMarkets(),
    refetchInterval: 120_000,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-px p-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-8 rounded bg-panel-2 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="font-mono text-[11px] uppercase tracking-widest text-red">
          backend unavailable
        </span>
      </div>
    )
  }

  const prices = data?.prices ?? []
  const grouped = prices.reduce<Record<string, MarketPrice[]>>((acc, p) => {
    const key = p.asset_type ?? 'other'
    ;(acc[key] ??= []).push(p)
    return acc
  }, {})

  const order = ['commodity', 'equity', 'forex', 'other']
  const keys = [...new Set([...order, ...Object.keys(grouped)])].filter((k) => grouped[k])

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-3 py-1 font-mono text-[9px] text-ink-faint text-right border-b border-line">
        updated {lastUpdated(prices)}
      </div>
      {keys.map((key) => (
        <div key={key}>
          <GroupLabel label={key} />
          {grouped[key].map((p) => <MarketRow key={p.symbol} price={p} />)}
        </div>
      ))}
    </div>
  )
}
