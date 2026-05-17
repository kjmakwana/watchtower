# Spec: Heat Intensity

**Status:** Ready for implementation  
**Last updated:** 2026-05-16

---

## Problem and goal

Region markers on the world map are visually identical regardless of activity level. An analyst scanning the map cannot distinguish a region with one overnight article from a region in active escalation. Heat Intensity adds a composite signal — displayed as a colour band and numeric badge — that reflects genuine geopolitical intensity rather than raw journalism volume.

---

## User-facing behaviour

1. Each region marker on the world map gains a colour band and a numeric badge (0.0–10.0).
2. The badge and colour update whenever the graph query refreshes (current `staleTime`: 5 minutes).
3. Hovering a marker shows a tooltip near the cursor containing:
   - Article count (total)
   - Military article count
   - Unique source names (list)
   - Active tickers for the region (list)
4. Clicking a marker filters the news feed to that region (existing behaviour, unchanged).
5. When total article count across all non-global regions falls below the sparse-data threshold, a warning indicator is shown on the map (exact UI TBD by implementer — e.g., a faint label or icon).
6. The `global` region is never shown on the map and never participates in scoring.

---

## Data model changes

### `GET /api/graph` — node object additions

Each node in the `nodes` array must include the following new fields:

| Field | Type | Description |
|---|---|---|
| `intensity` | `float` | Composite score, 0.0–10.0 |
| `source_diversity` | `int` | Count of unique sources for this region in the time window |
| `sources` | `list[str]` | List of unique source names (for tooltip) |
| `tickers_display` | `list[str]` | Deduplicated ticker symbols for the region (for tooltip), excluding tickers from military articles |
| `sparse_data` | `bool` | Top-level flag on the response `meta` object (not per-node) |

The existing fields (`id`, `article_count`, `military_count`, `total_weight`) are unchanged.

`sparse_data` is added to the existing `meta` object on the response root:

```json
"meta": {
  "window_hours": 168,
  "generated_at": "...",
  "article_count": 42,
  "sparse_data": false
}
```

### Frontend type changes

`GraphNode` in `frontend/src/lib/types.ts` gains:

```ts
intensity: number
source_diversity: number
sources: string[]
tickers_display: string[]
```

`GraphResponse.meta` gains:

```ts
sparse_data: boolean
```

---

## Backend logic

### Location

All scoring logic lives in `ingestion/graph_engine.py` inside `build_graph()`. The route `routes/graph.py` is unchanged.

### Per-region signal collection

During the existing article loop, collect additionally:

- `sources`: the set of unique `source` values per region (maps to `source_diversity = len(sources)`)
- `non_military_ticker_weight`: sum of ticker weights for articles where `is_military` is false (used for `total_ticker_weight` signal — see anti-double-count rule below)

### Anti-double-count rule for ticker weight

`total_ticker_weight` for intensity scoring must exclude tickers from articles already counted toward `military_count`. Concretely: accumulate ticker weights only from articles where `is_military == False`. The existing `region_scores` dict (which applies `MILITARY_MULTIPLIER`) is used for edge calculations and must not be changed. A separate accumulator is needed for the non-military ticker weight used in intensity.

### Floor normalisation

Each signal is normalised independently across active regions (all regions with at least one article, excluding `global`):

```
normalised(signal, region) = signal_value(region) / max(max_value_across_regions, FLOOR)
```

Floor baselines (exact values are open questions — see below, but implementer should define constants):

| Signal | Suggested floor |
|---|---|
| `military_count` | 5 |
| `source_diversity` | 3 |
| `article_count` | 10 |
| `total_ticker_weight` | 20 |

These floors prevent a single article in a quiet region from normalising to 1.0 and scoring 10/10.

### Composite formula

```
intensity = normalise(military_count)       * 0.35
          + normalise(source_diversity)     * 0.30
          + normalise(article_count)        * 0.25
          + normalise(total_ticker_weight)  * 0.10
```

Score is then multiplied by 10 and rounded to one decimal place. Result is clamped to [0.0, 10.0].

### Sparse-data flag

`sparse_data = True` when `sum(article_count for all non-global regions) < SPARSE_THRESHOLD`.

Suggested starting value: `SPARSE_THRESHOLD = 20`. This constant should be defined at module level in `graph_engine.py`.

---

## Frontend behaviour

### Colour scale thresholds

| Score range | Colour | Hex |
|---|---|---|
| 0.0 – 3.9 | Green | `#22c55e` |
| 4.0 – 6.9 | Amber | `#f59e0b` |
| 7.0 – 10.0 | Red | `#ef4444` |

These are the band boundaries; implementer must decide whether to interpolate continuously or use discrete steps. Discrete steps are acceptable for v1.

### Badge

- Positioned inside or adjacent to the existing `RegionMarker` SVG group
- Displays the `intensity` float to one decimal place (e.g., `6.4`)
- Text colour matches the band colour
- Font: monospace, consistent with existing label style

### Colour integration with existing marker accent

Currently the marker accent colour is either neon-green (active/selected) or neon-blue (inactive). The heat colour must not override the selection state accent. One approach: keep the existing ring/crosshair accent logic and add the heat colour only to the badge text and a new thin fill or stroke on the core dot. Exact integration is at the implementer's discretion.

### Tooltip

Triggered on `onMouseEnter` / `onMouseLeave` on the `<g>` element. Positioned near the cursor (not fixed). Contains:

```
[Region label]
Articles:  12
Military:   3
Sources:   Reuters, BBC, Al Jazeera
Tickers:   USO, GLD
```

Replace the existing `<title>` SVG tooltip with this custom implementation. The native `<title>` tooltip can be removed or kept as an accessibility fallback.

### Sparse-data warning

When `meta.sparse_data === true`, show a map-level indicator. Suggested: faint monospace label at the bottom of the map area reading `LOW DATA — SCORES UNRELIABLE`. Exact placement and styling are at the implementer's discretion.

### Click behaviour

Unchanged. Clicking a marker calls `onRegionClick(regionId)` which filters the news feed via existing `NewsFilters`.

---

## Files affected

| File | Change |
|---|---|
| `ingestion/graph_engine.py` | Add signal collection, floor normalisation, composite scoring, sparse-data flag |
| `routes/graph.py` | No changes expected |
| `frontend/src/lib/types.ts` | Extend `GraphNode` and `GraphResponse.meta` |
| `frontend/src/components/map/WorldMap.tsx` | Add badge, heat colour, tooltip, sparse-data warning |

---

## Out of scope

- Spike detection against a 30-day rolling baseline (deferred — requires persistent historical snapshots)
- Cluster-derived signals (`cluster_count`, corroboration score) — deferred, requires `cluster_id` propagation into `graph_engine.py`
- Animating the colour transition when scores change between refreshes
- Per-region intensity history or sparklines
- Exporting or sharing intensity data
- Any change to the `/api/news`, `/api/markets`, or clustering routes

---

## Open questions

1. **Floor baseline values** — The suggested floors (military: 5, diversity: 3, articles: 10, ticker weight: 20) are reasonable starting points but should be validated against 7 days of live data before shipping. Who confirms these?

2. **Sparse-data threshold** — `SPARSE_THRESHOLD = 20` is a placeholder. What is the minimum article count below which scores are meaningless for this dataset?

3. **Tooltip positioning** — The map uses `react-simple-maps` `<Marker>` components inside an SVG. Tooltip must be rendered in the DOM (not inside the SVG) to support rich HTML. Implementer must decide between a portal-based approach or a floating-div positioned via `onMouseMove` coordinates. No prior pattern exists in this codebase.

4. **Heat colour vs. selection accent** — The current marker has two states (active neon-green, inactive neon-blue). Adding a third colour dimension (heat) risks visual ambiguity. The spec requires heat colour on the badge; whether to bleed heat colour into the marker rings or core dot is a UI judgment call the implementer should make and record in DECISIONS.md.

5. **`tickers_display` scope** — The spec says exclude tickers from military articles. Should this mean: (a) exclude articles flagged `is_military`, or (b) apply the existing `MILITARY_MULTIPLIER` logic and only exclude the inflated contribution? Decision (a) is simpler and consistent with the anti-double-count intent. Confirm before coding.

6. **`sources` field size** — No cap is defined on the `sources` list. A busy region could have 15+ sources. Should the API return all unique sources or cap at N (e.g., top 5 by article count) to bound payload and tooltip length?
