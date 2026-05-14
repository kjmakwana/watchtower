# scripts/eval_clustering.py
#
# Diagnostic: compute average intra-cluster cosine similarity for all clusters
# in the last N hours. High scores = articles genuinely about the same story.
# Low scores = threshold may be too loose.
#
# Usage (from project root):
#   python scripts/eval_clustering.py [--hours 24] [--min-size 2]

import argparse
import sys
from datetime import datetime, timedelta, timezone
from statistics import mean, median

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Project root must be on sys.path when running as a script
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from ingestion.clustering import _MODEL
from ingestion.text_utils import build_clean_corpus
from models import Article


def _avg_intra_sim(corpora: list[str]) -> float:
    """
    Called by: main (this module)
    Parameters: corpora — list of cleaned corpus strings for one cluster
    Returns: average pairwise cosine similarity (upper triangle, no diagonal)
    Basic working: encodes corpora with the shared sentence-transformer model,
                   computes cosine similarity matrix, averages all n*(n-1)/2
                   pairs from the upper triangle
    """
    embeddings = _MODEL.encode(corpora, convert_to_numpy=True, show_progress_bar=False)
    sim = cosine_similarity(embeddings)
    n = sim.shape[0]
    rows, cols = np.triu_indices(n, k=1)
    pairs = sim[rows, cols]
    return float(pairs.mean()) if len(pairs) > 0 else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate clustering quality via intra-cluster cosine similarity.")
    parser.add_argument("--hours",    type=int, default=24, help="Look-back window in hours (default: 24)")
    parser.add_argument("--min-size", type=int, default=2,  help="Minimum cluster size to include (default: 2)")
    args = parser.parse_args()

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=args.hours)

    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .filter(Article.cluster_id.isnot(None), Article.published_at >= cutoff)
            .order_by(Article.cluster_id, Article.id)
            .all()
        )
    finally:
        db.close()

    # Group by cluster_id
    clusters: dict[int, list[Article]] = {}
    for a in articles:
        clusters.setdefault(a.cluster_id, []).append(a)

    # Filter by min-size
    clusters = {cid: members for cid, members in clusters.items() if len(members) >= args.min_size}

    if not clusters:
        print(f"No clusters found with >= {args.min_size} members in the last {args.hours}h.")
        return

    # Compute avg_sim per cluster
    rows = []
    for cid, members in clusters.items():
        corpora = [build_clean_corpus(a.title or "", a.summary or "") for a in members]
        avg_sim = _avg_intra_sim(corpora)
        rep = next((a for a in members if a.id == cid), members[0])
        rows.append((cid, len(members), avg_sim, rep.title or ""))

    # Sort ascending (worst first)
    rows.sort(key=lambda r: r[2])

    total_articles = sum(r[1] for r in rows)
    print(f"\nCLUSTER EVALUATION — last {args.hours}h — {len(rows)} clusters, {total_articles} articles")
    print("-" * 73)
    print(f"{'cluster_id':>10}  {'size':>4}  {'avg_sim':>7}  title")

    for cid, size, avg_sim, title in rows:
        truncated = title[:55] + "..." if len(title) > 55 else title
        print(f"{cid:>10}  {size:>4}  {avg_sim:>7.3f}  {truncated}")

    scores = [r[2] for r in rows]
    mn, med = mean(scores), median(scores)
    lo, hi  = min(scores), max(scores)
    worst_cid = rows[0][0]
    best_cid  = rows[-1][0]

    print(f"\nSUMMARY")
    print(f"  Mean   : {mn:.3f}")
    print(f"  Median : {med:.3f}")
    print(f"  Min    : {lo:.3f}  (cluster {worst_cid})")
    print(f"  Max    : {hi:.3f}  (cluster {best_cid})")

    brackets = [
        ("0.0-0.3", 0.0, 0.3),
        ("0.3-0.5", 0.3, 0.5),
        ("0.5-0.7", 0.5, 0.7),
        ("0.7-1.0", 0.7, 1.01),
    ]
    print(f"\nDISTRIBUTION")
    for label, lo_b, hi_b in brackets:
        count = sum(1 for s in scores if lo_b <= s < hi_b)
        pct = 100 * count / len(scores)
        print(f"  {label}  : {count:>3} clusters  ({pct:.0f}%)")


if __name__ == "__main__":
    main()
