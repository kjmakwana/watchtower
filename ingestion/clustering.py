# ingestion/clustering.py

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from ingestion.text_utils import build_clean_corpus
from models import Article

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.35
WINDOW_HOURS = 24

REGIONS = [
    "europe", "middle_east", "apac", "se_asia",
    "s_asia", "americas", "africa", "global",
]


def _find_clusters(
    ids: list[int],
    corpora: list[str],
    threshold: float,
) -> dict[int, int]:
    """
    Called by: assign_clusters (this module)
    Parameters:
        ids      — article IDs in the same region/window bucket
        corpora  — cleaned corpus strings from build_clean_corpus, one per id
        threshold — minimum cosine similarity score to treat two articles as
                    the same story
    Returns: dict mapping article_id → cluster_id for non-singleton articles;
             singletons are absent (caller treats missing ids as NULL)
    Basic working: vectorises corpora with TF-IDF, computes pairwise cosine
                   similarity, then groups articles above threshold via
                   union-find; cluster_id = min article.id in each group
    """
    if len(ids) < 2:
        return {}

    # Filter out articles whose corpus is empty — zero vectors break cosine similarity
    valid = [(id_, corp) for id_, corp in zip(ids, corpora) if corp.strip()]
    if len(valid) < 2:
        return {}

    valid_ids, valid_corpora = zip(*valid)

    vec = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vec.fit_transform(valid_corpora)
    except ValueError:
        # Raised when every document is empty after stop-word removal
        return {}

    sim_matrix = cosine_similarity(tfidf_matrix)

    # Union-find — path compression only (good enough for small n)
    n = len(valid_ids)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path halving
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i, j] >= threshold:
                union(i, j)

    # Collect groups; cluster_id = min article.id in the group
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(valid_ids[i])

    result: dict[int, int] = {}
    for members in groups.values():
        if len(members) >= 2:
            cid = min(members)
            for mid in members:
                result[mid] = cid

    return result


def assign_clusters(
    db: Session,
    window_hours: int = WINDOW_HOURS,
    threshold: float = SIMILARITY_THRESHOLD,
) -> int:
    """
    Called by: ingestion.ingestor.ingest_rss, after _write_articles
    Parameters:
        db           — active SQLAlchemy session (articles already committed)
        window_hours — how far back to look when forming clusters (default 24h)
        threshold    — cosine similarity threshold passed to _find_clusters
    Returns: total count of articles assigned to a non-singleton cluster
    Basic working: for each region, fetches all articles in the time window,
                   resets their cluster_id to None, re-runs _find_clusters,
                   and writes the new cluster_id assignments back; idempotent
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
    total_clustered = 0

    for region in REGIONS:
        articles = (
            db.query(Article)
            .filter(Article.region == region, Article.published_at >= cutoff)
            .order_by(Article.id)
            .all()
        )
        if len(articles) < 2:
            continue

        ids = [a.id for a in articles]
        corpora = [build_clean_corpus(a.title, a.summary) for a in articles]
        assignments = _find_clusters(ids, corpora, threshold)

        # Reset then apply — ensures stale assignments from previous runs are cleared
        for article in articles:
            article.cluster_id = assignments.get(article.id)

        n_clustered = len(assignments)
        total_clustered += n_clustered
        if n_clustered:
            n_clusters = len(set(assignments.values()))
            logger.info(
                "Region %s: %d articles across %d clusters",
                region, n_clustered, n_clusters,
            )

    db.commit()
    return total_clustered
