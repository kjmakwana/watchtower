# routes/graph.py

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from ingestion.graph_engine import build_graph
from models import Article

router = APIRouter()


@router.get("/api/graph")
def get_graph(
    hours: int = Query(168, ge=1, le=720, description="Time window in hours (default 7 days)"),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = db.query(Article).filter(Article.published_at >= cutoff).all()
    article_dicts = [
        {
            "region":      a.region,
            "tickers":     a.tickers,
            "is_military": a.is_military,
            "source":      a.source,
        }
        for a in articles
    ]
    return build_graph(article_dicts, hours)
