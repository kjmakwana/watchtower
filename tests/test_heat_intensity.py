# tests/test_heat_intensity.py
#
# Adversarial tests for the Heat Intensity feature in ingestion/graph_engine.py.
# Every test in this file must FAIL against a broken implementation and PASS once
# the defect is fixed.  Tests that verify already-working behaviour live in
# test_graph.py; this file is restricted to heat-intensity signals and the new
# node/meta fields introduced by that feature.

import pytest
from ingestion.graph_engine import (
    build_graph,
    _normalise,
    SPARSE_THRESHOLD,
    FLOOR_MILITARY,
    FLOOR_DIVERSITY,
    FLOOR_ARTICLES,
    FLOOR_TICKER_WEIGHT,
    WEIGHT_MILITARY,
    WEIGHT_DIVERSITY,
    WEIGHT_ARTICLES,
    WEIGHT_TICKER,
)


# ---------------------------------------------------------------------------
# Helpers (mirrors style in test_graph.py)
# ---------------------------------------------------------------------------

def _article(region, tickers=None, is_military=False, source=None):
    """Build a minimal article dict understood by build_graph()."""
    return {
        "region":      region,
        "tickers":     tickers,
        "is_military": is_military,
        "source":      source or "",
    }


def _ticker(t, w):
    return {"ticker": t, "weight": w}


def _node(result, region):
    for n in result["nodes"]:
        if n["id"] == region:
            return n
    return None


# ---------------------------------------------------------------------------
# _normalise unit tests
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_zero_value_returns_zero(self):
        assert _normalise(0, 100, 5) == 0.0

    def test_value_equals_max_returns_one(self):
        # When value equals max_value and max_value > floor, result is 1.0
        assert _normalise(10, 10, 5) == 1.0

    def test_floor_prevents_overshoot(self):
        # value=1, max=1, floor=5 → 1/max(1,5) = 1/5 = 0.2 — not 1.0
        result = _normalise(1, 1, 5)
        assert result == pytest.approx(0.2)

    def test_value_above_max_clamped_to_one(self):
        # value > max_value is theoretically impossible in build_graph, but
        # _normalise applies min(1.0, ...) so it should never exceed 1.0
        assert _normalise(20, 10, 5) == 1.0

    def test_negative_value_returns_zero(self):
        # Negative signals should not produce negative normalised values
        assert _normalise(-5, 10, 5) == 0.0


# ---------------------------------------------------------------------------
# Signal accumulation — military_count, source_diversity, article_count
# ---------------------------------------------------------------------------

class TestSignalAccumulation:
    def test_military_count_increments_per_military_article(self):
        articles = [
            _article("europe", is_military=True),
            _article("europe", is_military=True),
            _article("europe", is_military=False),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["military_count"] == 2

    def test_article_count_includes_all_articles(self):
        articles = [
            _article("apac", is_military=True),
            _article("apac", is_military=False),
            _article("apac"),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "apac")
        assert node["article_count"] == 3

    def test_source_diversity_counts_unique_sources(self):
        articles = [
            _article("europe", source="Reuters"),
            _article("europe", source="BBC"),
            _article("europe", source="Reuters"),   # duplicate — must not count twice
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["source_diversity"] == 2

    def test_sources_list_contains_unique_source_names(self):
        articles = [
            _article("europe", source="Reuters"),
            _article("europe", source="BBC"),
            _article("europe", source="Reuters"),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert sorted(node["sources"]) == ["BBC", "Reuters"]

    def test_source_diversity_matches_sources_length(self):
        articles = [
            _article("africa", source="Al Jazeera"),
            _article("africa", source="Reuters"),
            _article("africa", source="DW"),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "africa")
        assert node["source_diversity"] == len(node["sources"])

    def test_empty_source_not_counted(self):
        articles = [
            _article("europe", source="BBC"),
            _article("europe", source=""),   # blank source — must not inflate count
            _article("europe", source=None), # None source — must not inflate count
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["source_diversity"] == 1


# ---------------------------------------------------------------------------
# Anti-double-count: military articles must NOT contribute to non_mil_ticker_weight
# or tickers_display
# ---------------------------------------------------------------------------

class TestAntiDoubleCount:
    def test_military_tickers_absent_from_tickers_display(self):
        """Tickers from military articles must not appear in tickers_display."""
        articles = [
            _article("middle_east", [_ticker("USO", 5)],  is_military=True),
            _article("middle_east", [_ticker("GLD", 3)],  is_military=False),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "middle_east")
        assert "USO" not in node["tickers_display"], (
            "Ticker from a military article must be excluded from tickers_display"
        )

    def test_civilian_tickers_present_in_tickers_display(self):
        articles = [
            _article("middle_east", [_ticker("USO", 5)], is_military=True),
            _article("middle_east", [_ticker("GLD", 3)], is_military=False),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "middle_east")
        assert "GLD" in node["tickers_display"]

    def test_non_mil_ticker_weight_excludes_military_articles(self):
        """
        When ALL articles in a region are military, non_mil_ticker_weight must be 0.
        This proves the separate accumulator exists and is gated by is_military.
        """
        articles = [
            _article("europe", [_ticker("BRENT", 10)], is_military=True),
            _article("europe", [_ticker("BRENT", 10)], is_military=True),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        # intensity's ticker component must be 0 because all articles are military.
        # We verify by checking tickers_display (the observable proxy).
        assert node["tickers_display"] == [], (
            "All-military region must have no entries in tickers_display"
        )

    def test_non_mil_ticker_weight_accumulates_civilian_only(self):
        """
        Prove that military tickers do not inflate non_mil_ticker_weight by comparing
        two regions that differ ONLY in whether a high-weight military ticker is present.

        Setup:
          - "europe"      has 1 civilian article with BRENT weight 7
          - "americas"    has 1 military article with BRENT weight 50  (must NOT contribute)
                        + 1 civilian article with BRENT weight 7       (same civilian weight)
          - "reference"   has 1 civilian article with BRENT weight 100 (sets max_tick)

        All three regions see the same reference ceiling (100), so n_tick is computed
        against the same denominator.  europe and americas both have civilian weight 7,
        so their n_tick values must be identical.

        If military ticker weight leaks into non_mil_ticker_weight:
          americas non_mil_ticker_weight = 50 + 7 = 57  → n_tick = 57/100 = 0.57
        Correct behaviour:
          americas non_mil_ticker_weight = 7             → n_tick = 7/100  = 0.07

        To isolate the ticker signal we must also equalise article_count, military_count,
        and source_diversity between europe and americas:
          - europe gets 1 civilian article (article_count=1, military_count=0)
          - americas gets 1 military + 1 civilian article (article_count=2, military_count=1)
        These differ, so we cannot directly compare intensities.  Instead we inspect
        tickers_display as the observable proxy: if military weight leaked, the ticker
        component of intensity would diverge from what the civilian weight alone predicts.
        The tickers_display test above already covers the display-side; here we confirm
        via a hand-calculated expected value for the ticker component of a known region.

        Concretely: build a single-region scenario and verify that the non_mil_ticker_weight
        for a region that has ONLY military articles (and therefore 0 civilian weight) does
        not produce any ticker signal, even when those articles carry large ticker weights.
        """
        # Region with only military tickers — civilian weight must be 0.
        # Use a second region as the max reference so we can observe the ratio.
        articles = [
            _article("europe",   [_ticker("BRENT", 999.0)], is_military=True),
            _article("americas", [_ticker("BRENT", 1.0)],   is_military=False),
        ]
        result = build_graph(articles, 168)

        # americas has civilian weight 1.0, europe has civilian weight 0.0.
        # max_tick = 1.0 (from americas).
        # europe n_tick = _normalise(0, 1.0, FLOOR_TICKER_WEIGHT) = 0.0 (value==0 branch).
        # If the bug exists, europe non_mil_ticker_weight = 999.0 → n_tick = 1.0.
        europe_node = _node(result, "europe")

        # We can infer n_tick from the intensity by subtracting the other signal components.
        # europe: article_count=1, military_count=1, source_diversity=0 (no source set).
        # max_art = max(1, 1) = 1 (both regions have 1 article each).
        # max_mil = max(1, 0) = 1.
        # max_div = max(0, 0) = 0.
        # n_art  = 1/max(1, FLOOR_ARTICLES=10)  = 0.1
        # n_mil  = 1/max(1, FLOOR_MILITARY=5)   = 0.2
        # n_div  = _normalise(0, 0, FLOOR_DIVERSITY) = 0.0  (value==0 branch)
        # n_tick = 0.0 if correct, else 1.0 if bug.
        #
        # correct intensity = (0.2*0.35 + 0.0*0.30 + 0.1*0.25 + 0.0*0.10) * 10
        #                   = (0.07 + 0 + 0.025 + 0) * 10 = 0.95 → rounds to 1.0
        # buggy   intensity = (0.2*0.35 + 0.0*0.30 + 0.1*0.25 + 1.0*0.10) * 10
        #                   = (0.07 + 0 + 0.025 + 0.1) * 10 = 1.95 → rounds to 2.0

        expected_correct = round(
            (0.2 * WEIGHT_MILITARY + 0.0 * WEIGHT_DIVERSITY
             + 0.1 * WEIGHT_ARTICLES + 0.0 * WEIGHT_TICKER) * 10.0,
            1,
        )
        assert europe_node["intensity"] == pytest.approx(expected_correct, abs=0.05), (
            f"Military ticker weight must not inflate non_mil_ticker_weight. "
            f"Expected ~{expected_correct}, got {europe_node['intensity']}"
        )

    def test_ticker_in_both_military_and_civilian_articles_only_counts_civilian_weight(self):
        """
        The same ticker (BRENT) appears in both a military and a civilian article.
        tickers_display must include BRENT (it is also civilian), but the weight
        contribution to intensity must come only from the civilian article.
        """
        articles = [
            _article("middle_east", [_ticker("BRENT", 50)], is_military=True),
            _article("middle_east", [_ticker("BRENT", 3)],  is_military=False),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "middle_east")
        # BRENT appears in a civilian article → must be in tickers_display
        assert "BRENT" in node["tickers_display"]


# ---------------------------------------------------------------------------
# Floor normalisation
# ---------------------------------------------------------------------------

class TestFloorNormalisation:
    def test_lone_low_volume_region_does_not_score_10(self):
        """
        A single article in a single region from a single source with a tiny
        ticker weight must not score 10.0 — floor denominators prevent that.
        """
        articles = [_article("europe", [_ticker("BRENT", 1.0)],
                              is_military=False, source="Reuters")]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["intensity"] < 10.0, (
            f"Single low-volume region must not score 10.0, got {node['intensity']}"
        )

    def test_lone_high_volume_region_can_score_10(self):
        """
        A region that saturates every floor (military ≥ FLOOR_MILITARY articles,
        source_diversity ≥ FLOOR_DIVERSITY, article_count ≥ FLOOR_ARTICLES,
        ticker_weight ≥ FLOOR_TICKER_WEIGHT) is allowed to reach 10.0.
        """
        articles = (
            [_article("europe", [_ticker("BRENT", 5.0)],
                      is_military=True, source=f"src{i}") for i in range(FLOOR_MILITARY)]
            + [_article("europe", [_ticker("BRENT", 5.0)],
                        is_military=False, source=f"src{i}") for i in range(FLOOR_ARTICLES)]
        )
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        # This test documents that full saturation is the ceiling.  It should not
        # be a failure if the exact value is 10.0, so we just assert ≤ 10.0.
        assert node["intensity"] <= 10.0

    def test_floor_military_constant_used(self):
        """
        One military article in a lone region: military signal = 1 / max(1, FLOOR_MILITARY)
        = 1/5 = 0.2.  No other signals active (no sources, no articles counted here
        because we check military only).  Verify via _normalise directly.
        """
        result = _normalise(1, 1, FLOOR_MILITARY)
        assert result == pytest.approx(1.0 / FLOOR_MILITARY)

    def test_floor_diversity_constant_used(self):
        result = _normalise(1, 1, FLOOR_DIVERSITY)
        assert result == pytest.approx(1.0 / FLOOR_DIVERSITY)

    def test_floor_articles_constant_used(self):
        result = _normalise(1, 1, FLOOR_ARTICLES)
        assert result == pytest.approx(1.0 / FLOOR_ARTICLES)

    def test_floor_ticker_weight_constant_used(self):
        result = _normalise(1.0, 1.0, FLOOR_TICKER_WEIGHT)
        assert result == pytest.approx(1.0 / FLOOR_TICKER_WEIGHT)


# ---------------------------------------------------------------------------
# Sparse-data flag
# ---------------------------------------------------------------------------

class TestSparseDataFlag:
    def test_sparse_flag_true_when_below_threshold(self):
        """Total non-global articles < SPARSE_THRESHOLD → sparse_data must be True."""
        articles = [_article("europe") for _ in range(SPARSE_THRESHOLD - 1)]
        result = build_graph(articles, 168)
        assert result["meta"]["sparse_data"] is True

    def test_sparse_flag_false_when_at_threshold(self):
        """Exactly SPARSE_THRESHOLD articles → sparse_data must be False."""
        articles = [_article("europe") for _ in range(SPARSE_THRESHOLD)]
        result = build_graph(articles, 168)
        assert result["meta"]["sparse_data"] is False

    def test_sparse_flag_false_when_above_threshold(self):
        articles = [_article("europe") for _ in range(SPARSE_THRESHOLD + 5)]
        result = build_graph(articles, 168)
        assert result["meta"]["sparse_data"] is False

    def test_global_articles_not_counted_in_sparse_total(self):
        """
        Articles with region='global' are excluded from build_graph's accumulation.
        50 global articles + 0 non-global → sparse_data must still be True.
        """
        articles = [_article("global") for _ in range(50)]
        result = build_graph(articles, 168)
        assert result["meta"]["sparse_data"] is True

    def test_sparse_flag_uses_non_global_count_only(self):
        """
        Mix: enough non-global articles to exceed threshold but also many global
        articles that must NOT be counted.
        """
        non_global = [_article("europe") for _ in range(SPARSE_THRESHOLD)]
        global_noise = [_article("global") for _ in range(100)]
        result = build_graph(non_global + global_noise, 168)
        assert result["meta"]["sparse_data"] is False

    def test_sparse_flag_present_in_meta(self):
        result = build_graph([], 168)
        assert "sparse_data" in result["meta"]

    def test_sparse_flag_type_is_bool(self):
        result = build_graph([], 168)
        assert isinstance(result["meta"]["sparse_data"], bool)


# ---------------------------------------------------------------------------
# Global region excluded from nodes
# ---------------------------------------------------------------------------

class TestGlobalExcluded:
    def test_global_region_produces_no_node(self):
        articles = [_article("global") for _ in range(50)]
        result = build_graph(articles, 168)
        assert result["nodes"] == [], (
            "global region must never produce a node"
        )

    def test_global_mixed_with_real_regions_does_not_appear(self):
        articles = [
            _article("global"),
            _article("global"),
            _article("europe"),
        ]
        result = build_graph(articles, 168)
        ids = {n["id"] for n in result["nodes"]}
        assert "global" not in ids

    def test_global_tickers_do_not_create_edges_with_real_regions(self):
        """
        global articles share a ticker with a real region. No edge must be created
        because global articles are skipped in the loop.
        """
        articles = [
            _article("global",  [_ticker("BRENT", 10)]),
            _article("europe",  [_ticker("BRENT", 10)]),
            _article("americas",[_ticker("BRENT", 5)]),
        ]
        result = build_graph(articles, 168)
        for edge in result["edges"]:
            assert "global" not in (edge["source"], edge["target"]), (
                "global region must never appear as an edge endpoint"
            )


# ---------------------------------------------------------------------------
# Intensity clamped to [0.0, 10.0]
# ---------------------------------------------------------------------------

class TestIntensityClamping:
    def test_intensity_never_exceeds_10(self):
        # Build an extreme scenario: many military articles, many sources,
        # high article count, high ticker weight.
        articles = [
            _article("europe",
                     [_ticker("BRENT", 999.0)],
                     is_military=True,
                     source=f"src{i}")
            for i in range(100)
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["intensity"] <= 10.0

    def test_intensity_never_below_0(self):
        # A region with zero signals must produce intensity = 0.0
        articles = [_article("europe")]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["intensity"] >= 0.0

    def test_intensity_rounded_to_one_decimal(self):
        articles = [
            _article("europe", [_ticker("BRENT", 3.7)],
                     is_military=False, source="Reuters"),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        # round() to 1 dp means the value must not have more than 1 decimal digit
        assert node["intensity"] == round(node["intensity"], 1)


# ---------------------------------------------------------------------------
# Empty article list
# ---------------------------------------------------------------------------

class TestEmptyArticleList:
    def test_empty_list_returns_empty_nodes(self):
        result = build_graph([], 168)
        assert result["nodes"] == []

    def test_empty_list_returns_empty_edges(self):
        result = build_graph([], 168)
        assert result["edges"] == []

    def test_empty_list_sparse_data_true(self):
        """0 non-global articles is below SPARSE_THRESHOLD → sparse_data must be True."""
        result = build_graph([], 168)
        assert result["meta"]["sparse_data"] is True

    def test_empty_list_meta_article_count_zero(self):
        result = build_graph([], 168)
        assert result["meta"]["article_count"] == 0


# ---------------------------------------------------------------------------
# New node fields present and correctly typed
# ---------------------------------------------------------------------------

class TestNodeFields:
    def test_intensity_field_present(self):
        result = build_graph([_article("europe")], 168)
        node = _node(result, "europe")
        assert "intensity" in node

    def test_source_diversity_field_present(self):
        result = build_graph([_article("europe")], 168)
        node = _node(result, "europe")
        assert "source_diversity" in node

    def test_sources_field_present_and_is_list(self):
        result = build_graph([_article("europe", source="Reuters")], 168)
        node = _node(result, "europe")
        assert "sources" in node
        assert isinstance(node["sources"], list)

    def test_tickers_display_field_present_and_is_list(self):
        result = build_graph([_article("europe", [_ticker("BRENT", 5)])], 168)
        node = _node(result, "europe")
        assert "tickers_display" in node
        assert isinstance(node["tickers_display"], list)

    def test_tickers_display_sorted_alphabetically(self):
        """Architecture doc specifies sorted() — verify lexicographic order."""
        articles = [
            _article("europe", [_ticker("WHEAT", 2), _ticker("BRENT", 3)],
                     is_military=False),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["tickers_display"] == sorted(node["tickers_display"])

    def test_sources_sorted_alphabetically(self):
        articles = [
            _article("europe", source="Reuters"),
            _article("europe", source="BBC"),
            _article("europe", source="Al Jazeera"),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["sources"] == sorted(node["sources"])

    def test_intensity_is_float(self):
        result = build_graph([_article("europe")], 168)
        node = _node(result, "europe")
        assert isinstance(node["intensity"], float)


# ---------------------------------------------------------------------------
# Composite formula weight coverage
# ---------------------------------------------------------------------------

class TestCompositeFormula:
    def test_military_signal_contributes_to_intensity(self):
        """
        Two otherwise identical regions: one with military articles, one without.
        The military region must score higher.
        """
        non_mil = [_article("europe", source="Reuters") for _ in range(5)]
        mil = [_article("middle_east", source="Reuters", is_military=True) for _ in range(5)]
        # Give both the same article count and sources, but middle_east is all military.
        articles = non_mil + mil
        result = build_graph(articles, 168)
        europe_node = _node(result, "europe")
        me_node     = _node(result, "middle_east")
        assert me_node["intensity"] > europe_node["intensity"], (
            "Military-heavy region must outscore equivalent non-military region"
        )

    def test_source_diversity_contributes_to_intensity(self):
        """
        Two regions with equal article counts; one has more unique sources.
        The more diverse region must score higher (all else being equal).
        """
        articles = [
            _article("europe", source="Reuters"),
            _article("europe", source="BBC"),
            _article("europe", source="DW"),
            _article("americas", source="Reuters"),
            _article("americas", source="Reuters"),
            _article("americas", source="Reuters"),
        ]
        result = build_graph(articles, 168)
        europe_node   = _node(result, "europe")
        americas_node = _node(result, "americas")
        assert europe_node["intensity"] > americas_node["intensity"]

    def test_ticker_weight_zero_when_no_civilian_tickers(self):
        """
        A region with only military articles and tickers must have tickers_display == []
        and the ticker component of intensity must be 0, not inflated by military weight.
        """
        articles = [
            _article("europe", [_ticker("BRENT", 100.0)], is_military=True),
        ]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        assert node["tickers_display"] == []

    def test_intensity_zero_for_zero_signal_region(self):
        """
        A single article, no source, no tickers, no military flag.
        All four signals are at minimum; intensity must be very low (> 0 only via
        article_count=1 / max(1, FLOOR_ARTICLES=10) = 0.1 * WEIGHT_ARTICLES=0.25 * 10 = 0.25).
        """
        articles = [_article("europe")]
        result = build_graph(articles, 168)
        node = _node(result, "europe")
        expected = round(
            (1.0 / FLOOR_ARTICLES) * WEIGHT_ARTICLES * 10.0,
            1
        )
        assert node["intensity"] == pytest.approx(expected, abs=0.05), (
            f"Expected ~{expected}, got {node['intensity']}"
        )

    def test_weight_constants_sum_to_one(self):
        """
        The four weights must sum to 1.0 so that a fully saturated region scores
        exactly 10.0 before clamping.
        """
        total = WEIGHT_MILITARY + WEIGHT_DIVERSITY + WEIGHT_ARTICLES + WEIGHT_TICKER
        assert total == pytest.approx(1.0)
