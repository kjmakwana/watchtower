import { useQuery } from '@tanstack/react-query'
import { fetchNews } from '@/lib/api'
import { ArticleCard } from './ArticleCard'

export function NewsPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['news'],
    queryFn: () => fetchNews({ limit: 50 }),
    staleTime: 60_000,
  })

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
    <div className="h-full overflow-y-auto">
      {data?.articles.map((a) => <ArticleCard key={a.id} article={a} />)}
    </div>
  )
}
