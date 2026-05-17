# Architecture: Heat Intensity

**Status:** Ready for implementation
**Last updated:** 2026-05-16
**Spec:** [heat-intensity.md](heat-intensity.md)

---

## Spec correction

`routes/graph.py` requires a one-line change despite the product spec saying the route is unchanged. `build_graph()` cannot compute `source_diversity` without `source`. Add `"source": a.source` to the article projection. Recorded in DECISIONS.md.

---

## 1. Backend — `ingestion/graph_engine.py`

### New module-level constants

Insert above `MILITARY_MULTIPLIER`:

```python
SPARSE_THRESHOLD = 20

FLOOR_MILITARY      = 5
FLOOR_DIVERSITY     = 3
FLOOR_ARTICLES      = 10
FLOOR_TICKER_WEIGHT = 20.0

WEIGHT_MILITARY  = 0.35
WEIGHT_DIVERSITY = 0.30
WEIGHT_ARTICLES  = 0.25
WEIGHT_TICKER    = 0.10
```

### New helper function

Place directly above `build_graph()`:

```python
def _normalise(value: float, max_value: float, floor: float) -> float:
    """
    Floor-normalise a per-region signal.

    Called from build_graph() once per signal per region.
    value     — the region's raw signal value
    max_value — max of that signal across all active regions
    floor     — the signal's minimum denominator
    returns   — float in [0.0, 1.0]
    """
    return min(1.0, value / max(max_value, floor)) if value > 0 else 0.0
```

### New accumulators inside `build_graph()`

Add alongside existing `region_scores`, `region_mil_scores`, `region_meta`:

```python
region_sources:               dict[str, set[str]] = defaultdict(set)
region_non_mil_ticker_weight: dict[str, float]    = defaultdict(float)
region_tickers_display:       dict[str, set[str]] = defaultdict(set)
```

### Article-loop additions

Inside the existing `for article in articles:` loop, after the `global` skip:

```python
source = article.get("source") or ""
if source:
    region_sources[region].add(source)

is_mil = bool(article.get("is_military"))

# Ticker accumulation — military articles excluded to prevent double-counting
for entry in (article.get("tickers") or []):
    if not is_mil:
        region_non_mil_ticker_weight[region] += entry["weight"]
        region_tickers_display[region].add(entry["ticker"])
```

The existing `region_scores` / `region_mil_scores` accumulation is unchanged.

### Node assembly — three-pass rewrite

Replace the current `# nodes` block:

**Pass 1 — collect raw signals:**

```python
raw = []
for region, meta in region_meta.items():
    raw.append({
        "id":                    region,
        "article_count":         meta["article_count"],
        "military_count":        meta["military_count"],
        "source_diversity":      len(region_sources[region]),
        "total_weight":          round(sum(region_scores[region].values())),
        "non_mil_ticker_weight": region_non_mil_ticker_weight[region],
        "sources":               sorted(region_sources[region]),
        "tickers_display":       sorted(region_tickers_display[region]),
    })
```

**Pass 2 — compute cross-region maxes:**

```python
max_mil  = max((r["military_count"]        for r in raw), default=0)
max_div  = max((r["source_diversity"]      for r in raw), default=0)
max_art  = max((r["article_count"]         for r in raw), default=0)
max_tick = max((r["non_mil_ticker_weight"] for r in raw), default=0.0)
```

**Pass 3 — normalise, score, emit nodes:**

```python
nodes = []
for r in raw:
    n_mil  = _normalise(r["military_count"],        max_mil,  FLOOR_MILITARY)
    n_div  = _normalise(r["source_diversity"],      max_div,  FLOOR_DIVERSITY)
    n_art  = _normalise(r["article_count"],         max_art,  FLOOR_ARTICLES)
    n_tick = _normalise(r["non_mil_ticker_weight"], max_tick, FLOOR_TICKER_WEIGHT)

    intensity = (
        n_mil  * WEIGHT_MILITARY
      + n_div  * WEIGHT_DIVERSITY
      + n_art  * WEIGHT_ARTICLES
      + n_tick * WEIGHT_TICKER
    ) * 10.0

    nodes.append({
        "id":               r["id"],
        "article_count":    r["article_count"],
        "military_count":   r["military_count"],
        "total_weight":     r["total_weight"],
        "intensity":        round(max(0.0, min(10.0, intensity)), 1),
        "source_diversity": r["source_diversity"],
        "sources":          r["sources"],
        "tickers_display":  r["tickers_display"],
    })
```

### Sparse-data flag

After the article loop, before assembling the return value:

```python
total_non_global = sum(m["article_count"] for m in region_meta.values())
sparse_data = total_non_global < SPARSE_THRESHOLD
```

Add `"sparse_data": sparse_data` to the returned `meta` dict.

---

## 2. Route change — `routes/graph.py`

One-line addition to the article projection:

```python
"source": a.source,
```

---

## 3. API shape

```json
{
  "nodes": [
    {
      "id": "middle_east",
      "article_count": 18,
      "military_count": 7,
      "total_weight": 142,
      "intensity": 8.3,
      "source_diversity": 5,
      "sources": ["Al Jazeera", "BBC", "Bloomberg", "Reuters", "WSJ"],
      "tickers_display": ["BNO", "USO"]
    },
    {
      "id": "europe",
      "article_count": 9,
      "military_count": 1,
      "total_weight": 54,
      "intensity": 3.7,
      "source_diversity": 4,
      "sources": ["BBC", "DW", "FT", "Reuters"],
      "tickers_display": ["EWG", "EZU"]
    }
  ],
  "edges": [],
  "meta": {
    "window_hours": 168,
    "generated_at": "2026-05-16T14:00:00+00:00",
    "article_count": 42,
    "sparse_data": false
  }
}
```

---

## 4. Frontend type changes — `frontend/src/lib/types.ts`

```ts
export interface GraphNode {
  id: string
  article_count: number
  military_count: number
  total_weight: number
  intensity: number
  source_diversity: number
  sources: string[]
  tickers_display: string[]
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta: {
    window_hours: number
    generated_at: string
    article_count: number
    sparse_data: boolean
  }
}
```

---

## 5. Frontend component changes — `WorldMap.tsx`

### Heat colour helper

```ts
const HEAT_GREEN = '#22c55e'
const HEAT_AMBER = '#f59e0b'
const HEAT_RED   = '#ef4444'

function heatColour(intensity: number): string {
  if (intensity >= 7.0) return HEAT_RED
  if (intensity >= 4.0) return HEAT_AMBER
  return HEAT_GREEN
}
```

Discrete bands for v1; no interpolation.

### Tooltip state

```ts
const [tooltip, setTooltip] = useState<{
  x: number
  y: number
  node: GraphNode
  label: string
} | null>(null)
```

`onMouseMove` updates `{ x: e.clientX, y: e.clientY, node, label }`; `onMouseLeave` sets `null`.

### Tooltip rendering

Rendered as a sibling of `<ComposableMap>`, after `</ComposableMap>`:

```tsx
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
```

Remove the existing `<title>` element from `<Marker>`. The wrapper div needs `relative` added for sparse-data label positioning.

### `RegionMarker` prop additions

```ts
function RegionMarker({ node, active, label, onClick, onHover, onLeave, onMove }: {
  node: GraphNode
  active: boolean
  label: string
  onClick: () => void
  onHover: (e: React.MouseEvent) => void
  onLeave: () => void
  onMove: (e: React.MouseEvent) => void
})
```

Attach to the existing `<g>`: `onMouseEnter={onHover}`, `onMouseMove={onMove}`, `onMouseLeave={onLeave}`.

### Heat colour on marker

Add a thin heat stroke to the core dot only — existing ring/crosshair accent logic is untouched:

```tsx
<circle
  r={CORE_R}
  fill={accent}
  fillOpacity={dim}
  stroke={heatColour(node.intensity)}
  strokeWidth={1.5}
/>
```

### Badge

New `<text>` inside `RegionMarker`, upper-right of marker:

```tsx
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
```

### Sparse-data warning

```tsx
{data?.meta.sparse_data && (
  <div className="absolute bottom-2 left-2 font-mono text-[9px] uppercase tracking-widest text-ink-faint">
    low data — scores unreliable
  </div>
)}
```

---

## 6. Resolved open questions

| # | Question | Decision |
|---|---|---|
| 1 | Floor baseline values | Use spec's suggested values as constants. Revisit after one week of production data. |
| 2 | Sparse-data threshold | `SPARSE_THRESHOLD = 20`. Same revisit cadence. |
| 3 | Tooltip positioning | Floating `position: fixed` div, coordinates from `onMouseMove` clientX/Y. No portal, no SVG `foreignObject`. |
| 4 | Heat colour vs. selection accent | Heat colour on badge text + 1.5px stroke on core dot only. Rings, crosshair, and fill stay neon-green/blue. |
| 5 | `tickers_display` scope | Exclude articles where `is_military == True` entirely (option A). No partial/weighted exclusion. |
| 6 | `sources` field size | No cap in v1. Revisit with `SOURCES_DISPLAY_LIMIT = 8` if needed; do not add pre-emptively. |

---

## 7. Implementation order

1. **`ingestion/graph_engine.py`** — constants, `_normalise` helper, new accumulators, three-pass node assembly, sparse-data flag
2. **`routes/graph.py`** — add `"source": a.source` to article projection
3. Manual `GET /api/graph` check — confirm new fields present and values look sane
4. **`frontend/src/lib/types.ts`** — extend `GraphNode` and `GraphResponse.meta`; TypeScript build must pass before touching the component
5. **`frontend/src/components/map/WorldMap.tsx`** — heat colour helper, badge, core-dot stroke, tooltip state + floating div, sparse-data warning, `RegionMarker` prop additions, remove `<title>`
6. **Manual QA** — hover each region (tooltip contents correct), badge colour transitions at 3.9→4.0 and 6.9→7.0, selection accent dominates on click, sparse-data warning appears when expected
7. **`DECISIONS.md`** — append entry covering tooltip approach, heat-colour integration, route deviation, floor/threshold revisit plan
8. **`README.md`** — update API docs to reflect new node and meta fields
