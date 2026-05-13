# routes/clusters.py

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Article

router = APIRouter()


@router.get("/api/clusters/top")
def get_top_clusters(
    limit: int = Query(5, ge=1, le=20),
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Called by: frontend TopStoriesTicker via GET /api/clusters/top
    Parameters:
        limit (int, 1-20)   — how many top clusters to return
        hours (int, 1-168)  — time window to search within
    Returns: top clusters by article count with representative title and region
    Basic working: groups articles by cluster_id, orders by count desc, then
                   fetches the representative article (id = cluster_id) for each
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    top = (
        db.query(Article.cluster_id, func.count(Article.id).label("article_count"))
        .filter(Article.cluster_id.isnot(None), Article.published_at >= cutoff)
        .group_by(Article.cluster_id)
        .order_by(func.count(Article.id).desc())
        .limit(limit)
        .all()
    )

    if not top:
        return {"clusters": []}

    cluster_ids = [row.cluster_id for row in top]
    reps = (
        db.query(Article.id, Article.title, Article.region)
        .filter(Article.id.in_(cluster_ids))
        .all()
    )
    rep_map = {r.id: r for r in reps}

    clusters = []
    for row in top:
        rep = rep_map.get(row.cluster_id)
        if rep:
            clusters.append({
                "cluster_id": row.cluster_id,
                "article_count": row.article_count,
                "title": rep.title,
                "region": rep.region,
            })

    return {"clusters": clusters}
