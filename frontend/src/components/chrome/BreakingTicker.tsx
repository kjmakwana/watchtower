// DEPRECATED — replaced by TopStoriesTicker.tsx (live cluster data)
export function BreakingTicker() {
  const items = [
    'HORMUZ INCIDENT — TANKERS REROUTING',
    '$WTI +2.18%',
    'EU EMERGENCY SESSION 14:00 UTC',
    'TAIWAN STRAIT ACTIVITY ↑ MONTH HIGH',
    '$WHEAT +3.10%',
    'SAHEL — URANIUM MARKETS WATCHING',
  ]

  return (
    <div
      className="flex items-center gap-5 px-4 py-1.5 border-b border-line-strong font-mono text-xs shrink-0"
      style={{ background: 'linear-gradient(90deg, rgba(201,162,74,0.08), transparent 40%)' }}
    >
      <span className="shrink-0 bg-amber text-[#1a1410] px-2 py-0.5 rounded-sm text-[11px] font-semibold tracking-wide">
        BREAKING
      </span>
      <div className="flex items-center gap-5 overflow-hidden whitespace-nowrap text-ink-dim">
        {items.map((item, i) => (
          <span key={i} className="flex items-center gap-1.5">
            <span className="text-amber-dim text-[8px]">◆</span>
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}
