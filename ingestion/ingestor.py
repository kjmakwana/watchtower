import logging

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from database import get_db
from ingestion.clustering import assign_clusters
from ingestion.correlation_engine import enrich_article
from ingestion.rss_fetcher import fetch_all_feeds
from models import Article


def _filter_new(articles: list[dict], db: Session) -> list[dict]:
    """
    Called by: ingest_rss
    Parameters:
        articles — raw article dicts from fetch_all_feeds (not yet enriched)
        db       — active SQLAlchemy session
    Returns: subset of articles whose url_hash is not already in the DB
    Basic working: bulk-fetches existing url_hashes for the candidate set and
                   filters to only unseen articles, so enrich_article is never
                   called on duplicates
    """
    hashes = {a["url_hash"] for a in articles}
    existing = {
        row[0]
        for row in db.query(Article.url_hash).filter(Article.url_hash.in_(hashes)).all()
    }
    return [a for a in articles if a["url_hash"] not in existing]



logger = logging.getLogger(__name__)



def _write_articles(articles: list[dict], db: Session) -> int:
    """Shared DB write logic — insert with dedup, return count of new rows."""
    new_count = 0
    for article in articles:
        stmt = (
            sqlite_insert(Article)
            .values(**article)
            .on_conflict_do_nothing(index_elements=["url_hash"])
        )
        result = db.execute(stmt)
        if result.rowcount:
            new_count += 1
    db.commit()
    return new_count

def ingest_rss(db: Session | None = None) -> int:
    """
    Fetch all RSS feeds and insert new articles into the DB.
    Returns the count of newly inserted articles.
    Handles its own session if none is passed in (for APScheduler use).
    """
    own_session = db is None
    if own_session:
        db = next(get_db())

    try:
        fetched = fetch_all_feeds()
        new_articles = _filter_new(fetched, db)
        logger.info("Fetched %d articles, %d new", len(fetched), len(new_articles))
        enriched = [enrich_article(a) for a in new_articles]
        new_count = _write_articles(enriched, db)
        assign_clusters(db)
        logger.info("Ingested %d new articles", new_count)
        return new_count

    except Exception as exc:
        db.rollback()
        logger.error("ingest_rss failed: %s", exc, exc_info=True)
        return 0

    finally:
        if own_session:
            db.close()


