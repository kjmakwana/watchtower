import type { MarketPrice } from '@/lib/types'

export function MarketRow({ price }: { price: MarketPrice }) {
  const up = price.change_pct != null && price.change_pct > 0
  const down = price.change_pct != null && price.change_pct < 0
  const changeColor = up ? 'text-green' : down ? 'text-red' : 'text-ink-faint'
  const changePrefix = up ? '+' : ''

  return (
    <div className="flex items-center px-3 py-1.5 border-b border-line hover:bg-panel-2 transition-colors">
      <span className="font-mono text-[11px] text-amber w-16 shrink-0">{price.symbol}</span>
      <span className="text-[11px] text-ink-dim flex-1 truncate">{price.label}</span>
      <span className="font-mono text-[11px] text-ink ml-2">
        {price.price.toLocaleString(undefined, { maximumFractionDigits: 4 })}
      </span>
      {price.change_pct != null && (
        <span className={`font-mono text-[10px] ml-2 w-14 text-right ${changeColor}`}>
          {changePrefix}{price.change_pct.toFixed(2)}%
        </span>
      )}
    </div>
  )
}
