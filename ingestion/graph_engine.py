# ingestion/graph_engine.py

from collections import defaultdict
from datetime import datetime, timezone

from config.tickers import TICKER_CATEGORY

MILITARY_MULTIPLIER = 2.0


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

    for article in articles:
        region = article.get("region", "")
        if not region or region == "global":
            continue

        region_meta[region]["article_count"] += 1
        if article.get("is_military"):
            region_meta[region]["military_count"] += 1

        tickers = article.get("tickers") or []
        multiplier = MILITARY_MULTIPLIER if article.get("is_military") else 1.0
        for entry in tickers:
            ticker = entry["ticker"]
            weight = entry["weight"] * multiplier
            region_scores[region][ticker] += weight
            if article.get("is_military"):
                region_mil_scores[region][ticker] += weight

    # nodes
    nodes = []
    for region, meta in region_meta.items():
        total_weight = sum(region_scores[region].values())
        nodes.append({
            "id": region,
            "article_count": meta["article_count"],
            "military_count": meta["military_count"],
            "total_weight": round(total_weight),
        })

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
        },
    }
