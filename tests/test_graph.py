# tests/test_graph.py

import pytest
from ingestion.graph_engine import build_graph, MILITARY_MULTIPLIER


def _article(region, tickers=None, is_military=False):
    return {
        "region": region,
        "tickers": tickers,
        "is_military": is_military,
    }


def _ticker(t, w):
    return {"ticker": t, "weight": w}


def _edge(result, src, tgt):
    for e in result["edges"]:
        if {e["source"], e["target"]} == {src, tgt}:
            return e
    return None


def _node(result, region):
    for n in result["nodes"]:
        if n["id"] == region:
            return n
    return None


class TestBuildGraphNodes:
    def test_regions_become_nodes(self):
        articles = [_article("europe"), _article("middle_east")]
        result = build_graph(articles, 168)
        ids = {n["id"] for n in result["nodes"]}
        assert "europe" in ids
        assert "middle_east" in ids

    def test_global_excluded(self):
        articles = [_article("global"), _article("europe")]
        result = build_graph(articles, 168)
        ids = {n["id"] for n in result["nodes"]}
        assert "global" not in ids

    def test_article_count(self):
        articles = [_article("europe"), _article("europe"), _article("middle_east")]
        result = build_graph(articles, 168)
        assert _node(result, "europe")["article_count"] == 2
        assert _node(result, "middle_east")["article_count"] == 1

    def test_military_count(self):
        articles = [
            _article("europe", is_military=True),
            _article("europe", is_military=False),
        ]
        result = build_graph(articles, 168)
        assert _node(result, "europe")["military_count"] == 1

    def test_no_ticker_articles_counted_in_node(self):
        articles = [_article("europe", tickers=None), _article("europe", tickers=None)]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["article_count"] == 2
        assert node["total_weight"] == 0


class TestBuildGraphEdges:
    def test_shared_ticker_creates_edge(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 4)]),
            _article("middle_east", [_ticker("BRENT", 6)]),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        assert edge is not None

    def test_no_shared_ticker_no_edge(self):
        articles = [
            _article("europe",    [_ticker("NATGAS", 3)]),
            _article("americas",  [_ticker("SP500",  5)]),
        ]
        result = build_graph(articles, 168)
        assert _edge(result, "europe", "americas") is None

    def test_edge_weight_is_sum_of_both_sides(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 4)]),
            _article("middle_east", [_ticker("BRENT", 6)]),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        assert edge["weight"] == 10  # 4 + 6

    def test_military_multiplier_applied(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 4)], is_military=True),
            _article("middle_east", [_ticker("BRENT", 4)], is_military=False),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        # europe: 4 * 2.0 = 8, middle_east: 4 * 1.0 = 4 → total = 12
        assert edge["weight"] == round(4 * MILITARY_MULTIPLIER + 4)

    def test_military_weight_tracks_military_only(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 4)], is_military=True),
            _article("middle_east", [_ticker("BRENT", 4)], is_military=False),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        # only europe's contribution is military
        assert edge["military_weight"] == round(4 * MILITARY_MULTIPLIER)

    def test_dominant_ticker_is_highest_weight(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 8), _ticker("NATGAS", 2)]),
            _article("middle_east", [_ticker("BRENT", 6), _ticker("NATGAS", 1)]),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        assert edge["dominant_ticker"] == "BRENT"

    def test_edge_tickers_sorted_descending(self):
        articles = [
            _article("europe",      [_ticker("NATGAS", 2), _ticker("BRENT", 8)]),
            _article("middle_east", [_ticker("NATGAS", 1), _ticker("BRENT", 6)]),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        weights = [t["weight"] for t in edge["tickers"]]
        assert weights == sorted(weights, reverse=True)

    def test_ticker_category_set(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 5)]),
            _article("middle_east", [_ticker("BRENT", 5)]),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        assert edge["dominant_category"] == "commodity"
        assert edge["tickers"][0]["category"] == "commodity"

    def test_multiple_shared_tickers_all_appear(self):
        articles = [
            _article("europe",      [_ticker("BRENT", 4), _ticker("GOLD", 2)]),
            _article("middle_east", [_ticker("BRENT", 3), _ticker("GOLD", 1)]),
        ]
        result = build_graph(articles, 168)
        edge = _edge(result, "europe", "middle_east")
        ticker_names = [t["ticker"] for t in edge["tickers"]]
        assert "BRENT" in ticker_names
        assert "GOLD" in ticker_names


class TestBuildGraphMeta:
    def test_meta_window_hours(self):
        result = build_graph([], 24)
        assert result["meta"]["window_hours"] == 24

    def test_meta_article_count(self):
        articles = [_article("europe"), _article("middle_east")]
        result = build_graph(articles, 168)
        assert result["meta"]["article_count"] == 2

    def test_empty_articles(self):
        result = build_graph([], 168)
        assert result["nodes"] == []
        assert result["edges"] == []
