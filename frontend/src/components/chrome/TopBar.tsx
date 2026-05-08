import { useState } from 'react'
import type { NewsFilters } from '@/lib/useFilters'

const REGIONS: { label: string; value: string | null }[] = [
  { label: 'All', value: null },
  { label: 'Europe', value: 'europe' },
  { label: 'M. East', value: 'middle_east' },
  { label: 'APAC', value: 'apac' },
  { label: 'SE Asia', value: 'se_asia' },
  { label: 'S. Asia', value: 's_asia' },
  { label: 'Americas', value: 'americas' },
  { label: 'Africa', value: 'africa' },
]

function Pill({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode
  active?: boolean
  onClick?: () => void
}) {
  return (
    <span
      onClick={onClick}
      className={`inline-flex items-center px-3 py-1 rounded-full border font-mono text-xs select-none ${
        onClick ? 'cursor-pointer' : ''
      } ${
        active
          ? 'border-amber-dim text-amber'
          : 'border-line-strong text-ink-dim hover:border-line hover:text-ink'
      }`}
    >
      {children}
    </span>
  )
}

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`font-mono text-[10px] uppercase tracking-widest px-2.5 py-1 rounded-full border transition-colors ${
        active
          ? 'border-amber-dim text-amber bg-amber-dim/10'
          : 'border-line-strong text-ink-dim hover:border-line hover:text-ink'
      }`}
    >
      {label}
    </button>
  )
}

export function TopBar({
  filters,
  setRegion,
  setMilitary,
}: {
  filters: NewsFilters
  setRegion: (r: string | null) => void
  setMilitary: (m: boolean | null) => void
}) {
  const [filtersOpen, setFiltersOpen] = useState(false)

  return (
    <div className="flex flex-col border-b border-line shrink-0">
      <div className="flex items-center gap-4 px-4 py-2.5">
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
        <Pill active={filtersOpen} onClick={() => setFiltersOpen((o) => !o)}>
          Filters
        </Pill>
      </div>

      {filtersOpen && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-line bg-panel-2">
          <span className="font-mono text-[9px] uppercase tracking-widest text-ink-faint mr-1">
            Region
          </span>
          {REGIONS.map((r) => (
            <FilterPill
              key={r.label}
              label={r.label}
              active={filters.region === r.value}
              onClick={() => setRegion(filters.region === r.value ? null : r.value)}
            />
          ))}
          <div className="w-px h-4 bg-line-strong mx-1" />
          <FilterPill
            label="MIL"
            active={filters.military === true}
            onClick={() => setMilitary(filters.military ? null : true)}
          />
        </div>
      )}
    </div>
  )
}
