# ingestion/graph_engine.py

from collections import defaultdict
from datetime import datetime, timezone

from config.tickers import TICKER_CATEGORY

SPARSE_THRESHOLD = 20

FLOOR_MILITARY      = 5
FLOOR_DIVERSITY     = 3
FLOOR_ARTICLES      = 10
FLOOR_TICKER_WEIGHT = 20.0

WEIGHT_MILITARY  = 0.35
WEIGHT_DIVERSITY = 0.30
WEIGHT_ARTICLES  = 0.25
WEIGHT_TICKER    = 0.10

MILITARY_MULTIPLIER = 2.0


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


def build_graph(articles: list[dict], hours: int) -> dict:
    """
    Aggregate a list of article dicts into a region-to-region impact graph.

    Each article dict must have: region (str), tickers (list[dict] | None),
    is_military (bool).

    Returns a dict with nodes, edges, and meta ready for JSON serialization.
    """
    region_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    region_mil_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    region_meta: dict[str, dict] = defaultdict(lambda: {"article_count": 0, "military_count": 0})
    region_sources:               dict[str, set[str]] = defaultdict(set)
    region_non_mil_ticker_weight: dict[str, float]    = defaultdict(float)
    region_tickers_display:       dict[str, set[str]] = defaultdict(set)

    for article in articles:
        region = article.get("region", "")
        if not region or region == "global":
            continue

        region_meta[region]["article_count"] += 1
        if article.get("is_military"):
            region_meta[region]["military_count"] += 1

        source = article.get("source") or ""
        if source:
            region_sources[region].add(source)

        is_mil = bool(article.get("is_military"))

        tickers = article.get("tickers") or []
        multiplier = MILITARY_MULTIPLIER if is_mil else 1.0
        for entry in tickers:
            ticker = entry["ticker"]
            weight = entry["weight"] * multiplier
            region_scores[region][ticker] += weight
            if is_mil:
                region_mil_scores[region][ticker] += weight

        # Ticker accumulation — military articles excluded to prevent double-counting
        for entry in tickers:
            if not is_mil:
                region_non_mil_ticker_weight[region] += entry["weight"]
                region_tickers_display[region].add(entry["ticker"])

    # nodes — three-pass: collect raw signals, compute cross-region maxes, normalise and score
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

    max_mil  = max((r["military_count"]        for r in raw), default=0)
    max_div  = max((r["source_diversity"]      for r in raw), default=0)
    max_art  = max((r["article_count"]         for r in raw), default=0)
    max_tick = max((r["non_mil_ticker_weight"] for r in raw), default=0.0)

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

    total_non_global = sum(m["article_count"] for m in region_meta.values())
    sparse_data = total_non_global < SPARSE_THRESHOLD

    # edges — all unique region pairs
    regions = list(region_scores.keys())
    edges = []
    for i, r1 in enumerate(regions):
        for r2 in regions[i + 1:]:
            shared = set(region_scores[r1].keys()) & set(region_scores[r2].keys())
            if not shared:
                continue

            ticker_contribs = []
            for t in shared:
                contrib = region_scores[r1][t] + region_scores[r2][t]
                mil_contrib = region_mil_scores[r1].get(t, 0) + region_mil_scores[r2].get(t, 0)
                ticker_contribs.append({
                    "ticker": t,
                    "weight": round(contrib),
                    "military_weight": round(mil_contrib),
                    "category": TICKER_CATEGORY.get(t, "unknown"),
                })

            ticker_contribs.sort(key=lambda x: -x["weight"])
            dominant = ticker_contribs[0]
            total_weight = sum(tc["weight"] for tc in ticker_contribs)
            total_mil_weight = sum(tc["military_weight"] for tc in ticker_contribs)

            edges.append({
                "source": r1,
                "target": r2,
                "weight": total_weight,
                "military_weight": total_mil_weight,
                "dominant_ticker": dominant["ticker"],
                "dominant_category": dominant["category"],
                "tickers": [{k: v for k, v in tc.items() if k != "military_weight"}
                            for tc in ticker_contribs],
            })

    edges.sort(key=lambda e: -e["weight"])

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "window_hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "article_count": len(articles),
            "sparse_data": sparse_data,
        },
    }
