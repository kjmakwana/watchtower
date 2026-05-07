function Pill({ children, active }: { children: React.ReactNode; active?: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full border font-mono text-xs cursor-pointer ${
        active
          ? 'border-amber-dim text-amber'
          : 'border-line-strong text-ink-dim hover:border-line hover:text-ink'
      }`}
    >
      {children}
    </span>
  )
}

export function TopBar() {
  return (
    <div className="flex items-center gap-4 px-4 py-2.5 border-b border-line shrink-0">
      <div className="font-sans text-xl font-semibold text-amber tracking-tight">
        <span className="text-amber-dim">◬ </span>WatchTower
      </div>
      <div className="font-mono text-[11px] text-ink-faint uppercase tracking-widest">
        / console
      </div>

      <div className="flex-1" />

      <div className="font-mono text-[12px] text-ink-dim border-b border-dashed border-line-strong px-1.5 py-1 min-w-[240px]">
        <span className="text-ink-faint">⌕ </span>
        <span>search stories, tickers, regions…</span>
      </div>

      <Pill active>Live</Pill>
      <Pill>Filters</Pill>
    </div>
  )
}
