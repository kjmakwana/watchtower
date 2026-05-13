import { useQuery } from '@tanstack/react-query'
import { fetchTopClusters } from '@/lib/api'
import type { ClusterStory } from '@/lib/types'

export function TopStoriesTicker() {
  const { data } = useQuery({
    queryKey: ['top-clusters'],
    queryFn: () => fetchTopClusters(5),
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
  })

  const clusters = data?.clusters ?? []

  return (
    <div
      className="flex items-center px-4 py-1.5 border-b border-line-strong font-mono text-xs shrink-0 overflow-hidden"
      style={{ background: 'linear-gradient(90deg, rgba(201,162,74,0.08), transparent 40%)' }}
    >
      <span className="shrink-0 bg-amber text-[#1a1410] px-2 py-0.5 rounded-sm text-[11px] font-semibold tracking-wide mr-4">
        TOP STORIES
      </span>

      <div className="flex-1 overflow-hidden">
        {clusters.length === 0 ? (
          <span className="text-ink-faint">Awaiting cluster data…</span>
        ) : (
          <div className="ticker-track">
            {[...clusters, ...clusters].map((c: ClusterStory, i: number) => (
              <span key={i} className="inline-flex items-center gap-2 mr-10 text-ink-dim">
                <span className="text-amber-dim text-[8px]">◆</span>
                <span className="text-amber font-semibold">{c.article_count} sources</span>
                <span>{c.title.toUpperCase()}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
