# Implementation Log: Heat Intensity

**Feature:** Heat Intensity
**Date:** 2026-05-16
**Arch doc:** `docs/specs/heat-intensity-architecture.md`

---

## Files modified

### `ingestion/graph_engine.py`

- Added 9 module-level constants above `MILITARY_MULTIPLIER`: `SPARSE_THRESHOLD`, four `FLOOR_*` values, four `WEIGHT_*` values.
- Added `_normalise(value, max_value, floor)` helper function directly above `build_graph()`.
- Added three accumulators in `build_graph()`: `region_sources`, `region_non_mil_ticker_weight`, `region_tickers_display`.
- Extended the article loop: added source tracking and non-military ticker weight/display accumulation. Replaced the inline `article.get("is_military")` check with a `is_mil` local variable used by both the original ticker loop and the new accumulation block.
- Replaced the single-pass `# nodes` block with a three-pass assembly: Pass 1 collects raw signals, Pass 2 computes cross-region maxes, Pass 3 normalises, scores, and emits node dicts with the full new schema.
- Added `sparse_data` flag after the article loop, before the edge computation.
- Added `"sparse_data": sparse_data` to the returned `meta` dict.

### `routes/graph.py`

- Added `"source": a.source` to the article projection dict passed to `build_graph()`.

### `frontend/src/lib/types.ts`

- Extended `GraphNode` with: `intensity: number`, `source_diversity: number`, `sources: string[]`, `tickers_display: string[]`.
- Extended `GraphResponse.meta` with: `sparse_data: boolean`.

### `frontend/src/components/map/WorldMap.tsx`

- Added `import { useState }` (was missing from original imports).
- Added `HEAT_GREEN`, `HEAT_AMBER`, `HEAT_RED` constants.
- Added `heatColour(intensity)` helper function.
- Extended `RegionMarker` prop signature with `label`, `onHover`, `onLeave`, `onMove`.
- Attached `onMouseEnter`, `onMouseMove`, `onMouseLeave` to the marker `<g>` element.
- Updated core dot `<circle>` to add `stroke={heatColour(node.intensity)}` and `strokeWidth={1.5}`.
- Added heat intensity badge `<text>` element (upper-right of crosshair).
- Removed native `<title>` SVG element from the `<Marker>` wrapper.
- Added `label` to the `<Marker>` render loop locals (no longer derived from `milText`; `milText` removed).
- Added `tooltip` state in `WorldMap` component.
- Added `relative` class to the wrapper `<div>`.
- Added sparse-data warning div (absolute bottom-left, shown when `data?.meta.sparse_data`).
- Added floating tooltip div (fixed positioning, `pointer-events-none`, shown when `tooltip !== null`).
- Passed `onHover`, `onMove`, `onLeave` lambdas from `WorldMap` to `RegionMarker`.

### `DECISIONS.md`

- Appended "Map Heat Intensity — Implementation" entry covering: tooltip DOM approach, heat colour vs. selection accent, `routes/graph.py` deviation from spec, floor/threshold revisit plan.

### `README.md`

- Extended the API section with a `GET /api/graph` node schema table and updated `meta` field table.

---

## Functions written

| Function | File | Description |
|---|---|---|
| `_normalise` | `ingestion/graph_engine.py` | Floor-normalise a per-region signal to [0.0, 1.0] |
| `heatColour` | `frontend/src/components/map/WorldMap.tsx` | Map 0–10 intensity to a discrete hex colour (green/amber/red) |

---

## Deviations from architecture doc

None. The architecture doc already records the one deviation from the product spec (`routes/graph.py` adding `"source": a.source`). All function signatures, field names, constant values, and rendering structure match the arch doc exactly.

---

## Assumptions

- `a.source` on the SQLAlchemy `Article` model is the feed source name string (e.g., `"Reuters"`), not a URL. This is consistent with the existing `Article` model used in `routes/news.py` and matches the `source` field returned by `GET /api/news`.
- The `label` prop on `RegionMarker` is included per the architecture doc interface but is not used inside the component body — it is passed in by the parent to allow future use (e.g., accessibility, label overrides) without a prop-signature change.
- `node.intensity.toFixed(1)` will always produce a valid string since `intensity` is clamped to [0.0, 10.0] before being stored on the node.

---

## Schema / data changes

None. No database columns added or removed. No migration required.

---

## Dependency / config file changes

None. No new packages added. `requirements.txt`, `package.json`, and `.gitignore` are unchanged.
