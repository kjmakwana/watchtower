import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ComposableMap, Geographies, Geography, Graticule, Marker, Sphere } from 'react-simple-maps'
import { fetchGraph } from '@/lib/api'
import type { GraphNode } from '@/lib/types'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

const CENTROIDS: Record<string, [number, number]> = {
  europe:      [15,  52],
  middle_east: [42,  29],
  apac:        [127, 36],
  se_asia:     [108, 13],
  s_asia:      [78,  22],
  americas:    [-85, 15],
  africa:      [20,  5],
}

const REGION_LABELS: Record<string, string> = {
  europe:      'Europe',
  middle_east: 'M. East',
  apac:        'APAC',
  se_asia:     'SE Asia',
  s_asia:      'S. Asia',
  americas:    'Americas',
  africa:      'Africa',
}

const CORE_R   = 6
const RING1_R  = 12
const RING2_R  = 19
const TICK_R   = 23   // tick inner edge
const TICK_LEN = 6    // tick length

const HEAT_GREEN = '#22c55e'
const HEAT_AMBER = '#f59e0b'
const HEAT_RED   = '#ef4444'

function heatColour(intensity: number): string {
  /**
   * Map a 0–10 intensity score to a discrete colour band.
   *
   * Called from RegionMarker and tooltip rendering.
   * intensity — GraphNode.intensity (0.0–10.0)
   * returns   — hex colour string
   */
  if (intensity >= 7.0) return HEAT_RED
  if (intensity >= 4.0) return HEAT_AMBER
  return HEAT_GREEN
}

function RegionMarker({ node, active, label, onClick, onHover, onLeave, onMove }: {
  node: GraphNode
  active: boolean
  label: string
  onClick: () => void
  onHover: (e: React.MouseEvent) => void
  onLeave: () => void
  onMove: (e: React.MouseEvent) => void
}) {
  const accent = active ? '#39ff85' : '#00c8ff'   // neon green if selected, neon blue otherwise
  const dim    = active ? 1 : 0.75

  return (
    <g
      onClick={onClick}
      onMouseEnter={onHover}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ cursor: 'pointer' }}
      filter="url(#neon-glow)"
    >
      {/* Ping rings — SVG-native animation, no CSS dependency */}
      <circle r={RING1_R} fill="none" stroke={accent} strokeWidth={0.8} strokeOpacity={0}>
        <animate attributeName="r"              from={RING1_R} to={42}  dur="2.8s" begin="0s"   repeatCount="indefinite" />
        <animate attributeName="stroke-opacity" from={0.6}     to={0}   dur="2.8s" begin="0s"   repeatCount="indefinite" />
      </circle>
      <circle r={RING1_R} fill="none" stroke={accent} strokeWidth={0.8} strokeOpacity={0}>
        <animate attributeName="r"              from={RING1_R} to={42}  dur="2.8s" begin="1.4s" repeatCount="indefinite" />
        <animate attributeName="stroke-opacity" from={0.6}     to={0}   dur="2.8s" begin="1.4s" repeatCount="indefinite" />
      </circle>

      {/* Static concentric rings */}
      <circle r={RING1_R} fill="none" stroke={accent} strokeWidth={0.8} strokeOpacity={active ? 0.7 : 0.45} />
      <circle r={RING2_R} fill="none" stroke={accent} strokeWidth={0.6} strokeOpacity={active ? 0.45 : 0.25} />

      {/* Crosshair tick marks — N S E W */}
      {([
        [0, -(TICK_R + TICK_LEN), 0, -TICK_R],
        [0,   TICK_R,             0,  TICK_R + TICK_LEN],
        [-(TICK_R + TICK_LEN), 0, -TICK_R, 0],
        [TICK_R, 0, TICK_R + TICK_LEN, 0],
      ] as [number, number, number, number][]).map(([x1, y1, x2, y2], i) => (
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={accent} strokeWidth={1} strokeOpacity={active ? 1 : 0.55} />
      ))}

      {/* Core dot — heat colour on stroke only; fill/opacity remain accent-driven */}
      <circle
        r={CORE_R}
        fill={accent}
        fillOpacity={dim}
        stroke={heatColour(node.intensity)}
        strokeWidth={1.5}
      />

      {/* Heat intensity badge — upper-right of crosshair */}
      <text
        x={TICK_R + TICK_LEN + 2}
        y={-(TICK_R - 2)}
        style={{
          fontFamily: 'monospace',
          fontSize: 10,
          fill: heatColour(node.intensity),
          pointerEvents: 'none',
        }}
      >
        {node.intensity.toFixed(1)}
      </text>

      {/* Active label */}
      {active && (
        <text textAnchor="middle" y={TICK_R + TICK_LEN + 9}
          style={{ fontFamily: 'monospace', fontSize: 9, fill: accent, pointerEvents: 'none' }}>
          {node.id.replaceAll('_', ' ').toUpperCase()}
        </text>
      )}
    </g>
  )
}

export function WorldMap({
  activeRegion,
  onRegionClick,
}: {
  activeRegion: string | null
  onRegionClick: (region: string | null) => void
}) {
  const [tooltip, setTooltip] = useState<{
    x: number
    y: number
    node: GraphNode
    label: string
  } | null>(null)

  const { data, isError } = useQuery({
    queryKey: ['graph'],
    queryFn: () => fetchGraph(),
    staleTime: 300_000,
  })

  const nodes = data?.nodes ?? []
  const nodeMap = Object.fromEntries(nodes.map((n) => [n.id, n]))

  if (isError) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="font-mono text-[11px] uppercase tracking-widest text-red">
          graph unavailable
        </span>
      </div>
    )
  }

  return (
    <div className="relative h-full w-full">
      <ComposableMap
        projection="geoNaturalEarth1"
        projectionConfig={{ scale: 153, center: [0, 10] }}
        style={{ width: '100%', height: '100%' }}
      >
        <defs>
          <pattern id="land-dots" x="0" y="0" width="3" height="3" patternUnits="userSpaceOnUse">
            <circle cx="1.5" cy="1.5" r="0.6" fill="#1a3a5c" />
          </pattern>
          {/* Neon glow filter for region markers */}
          <filter id="neon-glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Sphere outline — planetary border */}
        <Sphere id="sphere" fill="#040d18" stroke="#1a3a5c" strokeWidth={0.6} />

        {/* Graticule — lat/lng grid */}
        <Graticule stroke="#1a3050" strokeWidth={0.2} strokeOpacity={0.35} />

        {/* Pass 1: solid dark landmass */}
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                fill="#0a1e36"
                stroke="none"
                strokeWidth={0}
                style={{
                  default: { outline: 'none' },
                  hover:   { outline: 'none' },
                  pressed: { outline: 'none' },
                }}
              />
            ))
          }
        </Geographies>

        {/* Pass 2: dot texture overlay */}
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey + '-dots'}
                geography={geo}
                fill="url(#land-dots)"
                stroke="none"
                style={{
                  default: { outline: 'none', pointerEvents: 'none' },
                  hover:   { outline: 'none' },
                  pressed: { outline: 'none' },
                }}
              />
            ))
          }
        </Geographies>

        {/* Region markers */}
        {Object.entries(CENTROIDS).map(([regionId, coords]) => {
          const node = nodeMap[regionId] ?? {
            id: regionId,
            article_count: 0,
            military_count: 0,
            total_weight: 0,
            intensity: 0,
            source_diversity: 0,
            sources: [],
            tickers_display: [],
          }
          const active = activeRegion === regionId
          const label = REGION_LABELS[regionId] ?? regionId

          return (
            <Marker key={regionId} coordinates={coords}>
              <RegionMarker
                node={node}
                active={active}
                label={label}
                onClick={() => onRegionClick(active ? null : regionId)}
                onHover={(e) => setTooltip({ x: e.clientX, y: e.clientY, node, label })}
                onMove={(e) => setTooltip((prev) => prev ? { ...prev, x: e.clientX, y: e.clientY } : prev)}
                onLeave={() => setTooltip(null)}
              />
            </Marker>
          )
        })}
      </ComposableMap>

      {data?.meta.sparse_data && (
        <div className="absolute bottom-2 left-2 font-mono text-[9px] uppercase tracking-widest text-ink-faint">
          low data — scores unreliable
        </div>
      )}

      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none bg-panel-2 border border-line px-2 py-1 font-mono text-[10px] text-ink"
          style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}
        >
          <div className="uppercase tracking-widest text-ink-faint">{tooltip.label}</div>
          <div>Articles: {tooltip.node.article_count}</div>
          <div>Military: {tooltip.node.military_count}</div>
          <div>Sources:  {tooltip.node.sources.join(', ') || '—'}</div>
          <div>Tickers:  {tooltip.node.tickers_display.join(', ') || '—'}</div>
        </div>
      )}
    </div>
  )
}
