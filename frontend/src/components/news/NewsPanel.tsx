import { useQuery } from '@tanstack/react-query'
import { fetchNews } from '@/lib/api'
import { ArticleCard } from './ArticleCard'
import type { NewsFilters } from '@/lib/useFilters'

export function NewsPanel({ filters }: { filters: NewsFilters }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['news', filters],
    queryFn: () => fetchNews({ region: filters.region, military: filters.military, limit: 50 }),
    staleTime: 14 * 60_000,
    refetchInterval: 15 * 60_000,
  })

  const activeLabels = [
    filters.region,
    filters.military ? 'MIL' : null,
  ].filter(Boolean).join(' · ')

  if (isLoading) {
    return (
      <div className="flex flex-col gap-px p-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-12 rounded bg-panel-2 animate-pulse" />
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

  return (
    <div className="h-full flex flex-col min-h-0">
      {activeLabels && (
        <div className="px-3 py-1 font-mono text-[9px] uppercase tracking-widest text-ink-faint border-b border-line">
          {activeLabels}
        </div>
      )}
      <div className="flex-1 overflow-y-auto min-h-0">
        {data?.articles.map((a) => <ArticleCard key={a.id} article={a} />)}
      </div>
    </div>
  )
}
