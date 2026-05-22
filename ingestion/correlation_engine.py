# ingestion/correlation_engine.py

import glob
import logging
import os
import re
from collections import Counter

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

from config.geo_map import MILITARY_KEYWORDS, REGION_GEO_MAP
from config.tickers import KEYWORD_TICKER_MAP

logger = logging.getLogger(__name__)

# ML region classifier (approach 3: ML for R1, keyword for R2)
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "Training", "models")
_model_files = sorted(glob.glob(os.path.join(_MODELS_DIR, "region_classifier_v1_*.joblib")))
if not _model_files:
    raise FileNotFoundError(f"No region_classifier_v1 model found in {_MODELS_DIR}")
_payload = joblib.load(_model_files[-1])
_CLF = _payload["classifier"]
_ENCODER = SentenceTransformer(_payload["encoder_model"])
GLOBAL_FALLBACK_THRESHOLD = 0.35

TITLE_WEIGHT = 3


def _build_corpus(title: str, summary: str) -> str:
    return ((title + " ") * TITLE_WEIGHT + summary).lower()


# DEPRECATED — replaced by enrich_article() which uses ML model 1 for the primary region.
# Kept for reference; do not call from new code.
def classify_region(title: str, summary: str, fallback: str) -> str:
    corpus = _build_corpus(title, summary)
    scores: Counter = Counter()
    for phrase, region in REGION_GEO_MAP.items():
        count = len(re.findall(r"\b" + re.escape(phrase) + r"\b", corpus))
        if count:
            scores[region] += count
    if not scores:
        return fallback
    top = scores.most_common(2)
    if len(top) > 1 and top[0][1] == top[1][1]:
        return fallback  # genuine tie — keep source-feed region
    return top[0][0]


def classify_regions(title: str, summary: str) -> list[str]:
    """
    Called by: Training/data_prep_region2.py; future enrich_article replacement
    Parameters:
        title   — article title
        summary — article summary/body
    Returns: list of 1-2 region strings; ["global"] when no keyword matches
    Basic working: scores regions by keyword hit count (title weighted x3),
                   returns top-1 always and top-2 when second score >= 30% of top;
                   ties at top returned alphabetically; second-place ties log a
                   warning and suppress the second region
    """
    corpus = _build_corpus(title, summary)
    scores: Counter = Counter()
    for phrase, region in REGION_GEO_MAP.items():
        count = len(re.findall(r"\b" + re.escape(phrase) + r"\b", corpus))
        if count:
            scores[region] += count

    if not scores:
        return ["global"]

    top_score = scores.most_common(1)[0][1]
    top_regions = sorted(r for r, s in scores.items() if s == top_score)

    if len(top_regions) >= 3:
        logger.warning("3-way tie among regions %s — assigning top-2 alphabetically", top_regions)
        return top_regions[:2]

    if len(top_regions) == 2:
        return top_regions  # two-way tie, both assigned alphabetically

    # Clear top winner
    best = top_regions[0]
    remaining = {r: s for r, s in scores.items() if r != best}

    if not remaining:
        return [best]

    second_score = max(remaining.values())

    if second_score < 0.30 * top_score:
        return [best]

    second_regions = sorted(r for r, s in remaining.items() if s == second_score)
    if len(second_regions) > 1:
        logger.warning(
            "2nd-place tie among regions %s (score=%d) — suppressing second region",
            second_regions, second_score,
        )
        return [best]

    return [best, second_regions[0]]


def classify_military(title: str, summary: str, fallback: bool) -> bool:
    if fallback:
        return True  # never demote a military-feed article
    corpus = _build_corpus(title, summary)
    return any(re.search(r"\b" + re.escape(kw) + r"\b", corpus) for kw in MILITARY_KEYWORDS)


def classify_tickers(title: str, summary: str) -> list[dict]:
    corpus = _build_corpus(title, summary)
    scores: dict[str, int] = {}
    for keyword, tickers in KEYWORD_TICKER_MAP.items():
        count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", corpus))
        if count:
            for t in tickers:
                scores[t] = scores.get(t, 0) + count
    return [{"ticker": t, "weight": w}
            for t, w in sorted(scores.items(), key=lambda x: -x[1])]


def enrich_article(article: dict) -> dict:
    """
    Called by: ingestion.ingestor.ingest_rss
    Parameters: article dict from rss_fetcher (must have title, summary, is_military)
    Returns: article dict with regions, region, is_military, tickers populated
    Basic working: ML model 1 assigns the primary region; classify_regions() keyword
                   engine assigns an optional second region; both written to article
    """
    title = article.get("title", "")
    summary = article.get("summary", "")

    # Primary region: ML model 1 with confidence threshold
    corpus = _build_corpus(title, summary)
    embedding = _ENCODER.encode([corpus], convert_to_numpy=True)
    proba = _CLF.predict_proba(embedding)[0]
    ml_r1 = str(_CLF.predict(embedding)[0]) if proba.max() >= GLOBAL_FALLBACK_THRESHOLD else "global"

    # Secondary region: keyword engine top-2 (30% threshold, ties suppressed)
    # Discard if it duplicates the primary region
    kw_regions = classify_regions(title, summary)
    kw_r2 = kw_regions[1] if len(kw_regions) == 2 else None
    if kw_r2 == ml_r1:
        kw_r2 = None

    regions = [ml_r1] if kw_r2 is None else [ml_r1, kw_r2]
    article["regions"] = regions
    article["region"] = regions[0]  # DEPRECATED — kept for clustering.py + backward compat

    article["is_military"] = classify_military(title, summary, article.get("is_military", False))
    tickers = classify_tickers(title, summary)
    article["tickers"] = tickers if tickers else None
    return article
