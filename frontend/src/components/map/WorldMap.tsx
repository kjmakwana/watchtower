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

function RegionMarker({ node, active, onClick }: {
  node: GraphNode
  active: boolean
  onClick: () => void
}) {
  const accent = active ? '#39ff85' : '#00c8ff'   // neon green if selected, neon blue otherwise
  const dim    = active ? 1 : 0.75

  return (
    <g onClick={onClick} style={{ cursor: 'pointer' }} filter="url(#neon-glow)">
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

      {/* Core dot */}
      <circle r={CORE_R} fill={accent} fillOpacity={dim} />

      {/* Active label */}
      {active && (
        <text textAnchor="middle" y={TICK_R + TICK_LEN + 9}
          style={{ fontFamily: 'monospace', fontSize: 9, fill: accent, pointerEvents: 'none' }}>
          {node.id.replace('_', ' ').toUpperCase()}
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
    <div className="h-full w-full">
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
          const node = nodeMap[regionId]
          if (!node) return null
          const active = activeRegion === regionId
          const label = REGION_LABELS[regionId] ?? regionId
          const milText = node.military_count > 0 ? ` (${node.military_count} MIL)` : ''

          return (
            <Marker key={regionId} coordinates={coords}>
              <title>{`${label} · ${node.article_count} stories${milText}`}</title>
              <RegionMarker
                node={node}
                active={active}
                onClick={() => onRegionClick(active ? null : regionId)}
              />
            </Marker>
          )
        })}
      </ComposableMap>
    </div>
  )
}
