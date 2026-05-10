import { BreakingTicker } from '@/components/chrome/BreakingTicker'
import { TopBar } from '@/components/chrome/TopBar'
import { NewsPanel } from '@/components/news/NewsPanel'
import { MarketsPanel } from '@/components/markets/MarketsPanel'
import { WorldMap } from '@/components/map/WorldMap'
import { useFilters } from '@/lib/useFilters'

function SectionHeader({ title, right }: { title: string; right?: string }) {
  return (
    <div
      className="flex items-center justify-between px-3 py-2 border-b border-line-strong shrink-0"
      style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.015), transparent)' }}
    >
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">{title}</h3>
      {right && <span className="font-mono text-[10px] text-ink-faint">{right}</span>}
    </div>
  )
}

function Panel({
  title,
  right,
  children,
  className = '',
}: {
  title: string
  right?: string
  children?: React.ReactNode
  className?: string
}) {
  return (
    <div className={`flex flex-col rounded-md border border-line bg-panel overflow-hidden ${className}`}>
      <SectionHeader title={title} right={right} />
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  )
}

function Placeholder({ label }: { label: string }) {
  return (
    <div
      className="h-full flex items-center justify-center"
      style={{
        background: 'repeating-linear-gradient(45deg, transparent 0 8px, rgba(138,154,140,0.04) 8px 9px)',
      }}
    >
      <span className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">
        {label}
      </span>
    </div>
  )
}

export default function App() {
  const { newsFilters, marketFilters, setRegion, setMilitary, setMarketType } = useFilters()

  return (
    <div className="h-screen flex flex-col bg-bg overflow-hidden">
      <BreakingTicker />
      <TopBar filters={newsFilters} setRegion={setRegion} setMilitary={setMilitary} />

      <main className="flex-1 grid grid-cols-[1fr_380px] gap-2.5 p-2.5 min-h-0">
        {/* Left column — full-height world map */}
        <Panel title="world activity" right="pin size = story volume">
          <WorldMap activeRegion={newsFilters.region} onRegionClick={setRegion} />
        </Panel>

        {/* Right rail — news top, markets bottom */}
        <div className="flex flex-col gap-2.5 min-h-0">
          <Panel title="stories" className="flex-1">
            <NewsPanel filters={newsFilters} />
          </Panel>
          <Panel title="market pulse" right="2m" className="flex-1">
            <MarketsPanel type={marketFilters.type} setType={setMarketType} />
          </Panel>
        </div>
      </main>
    </div>
  )
}
