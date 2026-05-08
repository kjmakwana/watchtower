import type { Article } from '@/lib/types'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  return `${Math.floor(h / 24)}d`
}

export function ArticleCard({ article }: { article: Article }) {
  const tickers = article.tickers ?? []

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noreferrer"
      className="block px-3 py-2.5 border-b border-line hover:bg-panel-2 transition-colors"
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-ink-faint">
          {article.source_name}
        </span>
        <span className="font-mono text-[9px] text-ink-faint">·</span>
        <span className="font-mono text-[9px] uppercase tracking-widest text-ink-faint">
          {article.region}
        </span>
        {article.is_military && (
          <>
            <span className="font-mono text-[9px] text-ink-faint">·</span>
            <span className="font-mono text-[9px] uppercase tracking-widest text-amber">MIL</span>
          </>
        )}
        <span className="ml-auto font-mono text-[9px] text-ink-faint">
          {timeAgo(article.published_at)}
        </span>
      </div>

      <p className="text-[12px] text-ink leading-snug">{article.title}</p>

      {tickers.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {tickers.slice(0, 5).map((t) => (
            <span
              key={t.ticker}
              className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-green-dim text-green"
            >
              {t.ticker}
            </span>
          ))}
        </div>
      )}
    </a>
  )
}
