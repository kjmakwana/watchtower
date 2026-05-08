import type { Article } from '@/lib/types'

function formatTime(iso: string): { label: string; title: string } {
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  const m = Math.floor(diff / 60_000)
  const title = d.toLocaleString()
  if (m < 60) return { label: `${m}m`, title }
  const h = Math.floor(m / 60)
  if (h < 24) return { label: `${h}h`, title }
  const days = Math.floor(h / 24)
  if (days < 365) return { label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), title }
  return { label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }), title }
}

export function ArticleCard({ article }: { article: Article }) {
  const tickers = article.tickers ?? []
  const time = formatTime(article.published_at)

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
        <span className="ml-auto font-mono text-[9px] text-ink-faint" title={time.title}>
          {time.label}
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
