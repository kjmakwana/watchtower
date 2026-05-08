import { useQuery } from '@tanstack/react-query'
import { fetchMarkets } from '@/lib/api'
import { MarketRow } from './MarketRow'
import type { MarketPrice } from '@/lib/types'

const TYPE_TABS = ['all', 'commodity', 'forex', 'equity'] as const

function TypeTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 rounded transition-colors ${
        active
          ? 'bg-amber-dim text-amber'
          : 'text-ink-faint hover:text-ink-dim'
      }`}
    >
      {label}
    </button>
  )
}

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

export function MarketsPanel({
  type,
  setType,
}: {
  type: string | null
  setType: (t: string | null) => void
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['markets', { type }],
    queryFn: () => fetchMarkets(type ?? undefined),
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
    <div className="h-full flex flex-col min-h-0">
      <div className="flex items-center justify-between px-3 py-1 border-b border-line shrink-0">
        <div className="flex gap-1">
          {TYPE_TABS.map((tab) => (
            <TypeTab
              key={tab}
              label={tab}
              active={(type ?? 'all') === tab}
              onClick={() => setType(tab === 'all' ? null : tab)}
            />
          ))}
        </div>
        <span className="font-mono text-[9px] text-ink-faint">
          updated {lastUpdated(prices)}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0">
        {keys.map((key) => (
          <div key={key}>
            {!type && <GroupLabel label={key} />}
            {grouped[key].map((p) => <MarketRow key={p.symbol} price={p} />)}
          </div>
        ))}
      </div>
    </div>
  )
}
