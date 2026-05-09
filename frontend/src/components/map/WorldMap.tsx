import { useQuery } from '@tanstack/react-query'
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps'
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

function bubbleRadius(articleCount: number): number {
  return Math.max(5, Math.min(24, Math.sqrt(articleCount) * 3))
}

function bubbleColor(node: GraphNode, active: boolean): string {
  if (active) return '#c9a24a'
  if (node.military_count > 0) return '#b56353'
  return '#6f9b6e'
}

function bubbleOpacity(node: GraphNode, active: boolean): number {
  if (active) return 1
  if (node.military_count > 0) return 0.8
  return 0.7
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
        projection="geoMercator"
        projectionConfig={{ scale: 120, center: [15, 25] }}
        style={{ width: '100%', height: '100%' }}
      >
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                fill="#1a211d"
                stroke="#2c3530"
                strokeWidth={0.4}
                style={{
                  default: { outline: 'none' },
                  hover:   { outline: 'none' },
                  pressed: { outline: 'none' },
                }}
              />
            ))
          }
        </Geographies>

        {Object.entries(CENTROIDS).map(([regionId, coords]) => {
          const node = nodeMap[regionId]
          if (!node) return null
          const active = activeRegion === regionId
          const r = bubbleRadius(node.article_count)
          const label = REGION_LABELS[regionId] ?? regionId
          const milText = node.military_count > 0 ? ` (${node.military_count} MIL)` : ''

          return (
            <Marker
              key={regionId}
              coordinates={coords}
              onClick={() => onRegionClick(active ? null : regionId)}
            >
              <title>{`${label} · ${node.article_count} stories${milText}`}</title>
              <circle
                r={r}
                fill={bubbleColor(node, active)}
                fillOpacity={bubbleOpacity(node, active)}
                stroke={active ? '#c9a24a' : 'transparent'}
                strokeWidth={active ? 1.5 : 0}
                style={{ cursor: 'pointer' }}
              />
              {active && (
                <text
                  textAnchor="middle"
                  y={r + 10}
                  style={{ fontFamily: 'monospace', fontSize: 9, fill: '#c9a24a', pointerEvents: 'none' }}
                >
                  {label}
                </text>
              )}
            </Marker>
          )
        })}
      </ComposableMap>
    </div>
  )
}
