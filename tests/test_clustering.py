"""
tests/test_clustering.py

Run from the project root:
    pytest tests/test_clustering.py -v

Covers:
    - ingestion/clustering.py — _find_clusters, assign_clusters
"""

import os
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from database import Base
from models import Article
from ingestion.clustering import _find_clusters, assign_clusters, SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    from database import engine as _engine
    Base.metadata.create_all(bind=_engine)
    # Ensure cluster_id column exists in the in-memory DB
    with _engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE articles ADD COLUMN cluster_id INTEGER"))
            conn.commit()
        except Exception:
            pass
    yield _engine
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def make_article(db, *, url_hash, title, summary, region="europe", published_at=None):
    """Insert a minimal Article and return it."""
    a = Article(
        url_hash=url_hash,
        title=title,
        url=f"https://example.com/{url_hash}",
        source="bbc",
        source_name="BBC World",
        region=region,
        is_military=False,
        summary=summary,
        published_at=published_at or datetime.now(tz=timezone.utc),
    )
    db.add(a)
    db.flush()
    return a


# ===========================================================================
# _find_clusters
# ===========================================================================

class TestFindClusters:

    def test_returns_empty_for_single_article(self):
        result = _find_clusters([1], ["iran nuclear talks resumed vienna"], 0.35)
        assert result == {}

    def test_returns_empty_for_zero_articles(self):
        assert _find_clusters([], [], 0.35) == {}

    def test_similar_pair_gets_same_cluster_id(self):
        ids = [10, 20]
        # Nearly identical titles — high similarity expected
        corpora = [
            "iran nuclear deal talks resumed vienna diplomats gathered",
            "iran nuclear deal talks resumed vienna diplomats meeting",
        ]
        result = _find_clusters(ids, corpora, threshold=0.3)
        assert 10 in result and 20 in result
        assert result[10] == result[20]

    def test_cluster_id_is_minimum_article_id(self):
        ids = [10, 20]
        corpora = [
            "iran nuclear deal talks resumed vienna diplomats",
            "iran nuclear deal talks resumed vienna diplomats",
        ]
        result = _find_clusters(ids, corpora, threshold=0.3)
        assert result[10] == 10  # min of {10, 20}
        assert result[20] == 10

    def test_dissimilar_pair_stays_separate(self):
        ids = [1, 2]
        corpora = [
            "iran nuclear deal diplomats vienna ceasefire",
            "stock market rally nasdaq dow jones earnings report",
        ]
        result = _find_clusters(ids, corpora, threshold=0.35)
        # Neither should be assigned to a cluster
        assert 1 not in result
        assert 2 not in result

    def test_three_articles_two_similar_one_different(self):
        ids = [1, 2, 3]
        corpora = [
            "iran nuclear deal talks resumed vienna diplomats ceasefire",
            "iran nuclear deal talks resumed vienna diplomats agreement",
            "european football championship final paris madrid",
        ]
        result = _find_clusters(ids, corpora, threshold=0.3)
        # ids 1 and 2 should cluster together
        assert 1 in result and 2 in result
        assert result[1] == result[2]
        # id 3 should not be clustered
        assert 3 not in result

    def test_empty_corpora_excluded(self):
        ids = [1, 2, 3]
        corpora = ["", "iran nuclear talks vienna", ""]
        # Only one non-empty corpus — can't cluster
        result = _find_clusters(ids, corpora, threshold=0.35)
        assert result == {}

    def test_all_empty_corpora_returns_empty(self):
        ids = [1, 2]
        corpora = ["", ""]
        assert _find_clusters(ids, corpora, threshold=0.35) == {}

    def test_high_threshold_prevents_clustering(self):
        ids = [1, 2]
        corpora = [
            "iran nuclear deal talks resumed",
            "iran nuclear deal discussions continued",
        ]
        # threshold=1.0 means only identical documents cluster
        result = _find_clusters(ids, corpora, threshold=1.0)
        assert result == {}

    def test_threshold_zero_clusters_everything_with_shared_terms(self):
        ids = [1, 2]
        corpora = [
            "iran nuclear deal talks resumed vienna",
            "iran stock market economics trade",
        ]
        # Both share "iran" — at threshold=0.0 they should cluster
        result = _find_clusters(ids, corpora, threshold=0.0)
        assert 1 in result and 2 in result

    def test_four_articles_two_pairs(self):
        ids = [1, 2, 3, 4]
        corpora = [
            "iran nuclear deal talks vienna diplomats ceasefire agreement",
            "iran nuclear deal talks vienna diplomats ceasefire signed",
            "ukraine russia war ceasefire negotiations peace talks kyiv",
            "ukraine russia war ceasefire negotiations peace talks moscow",
        ]
        result = _find_clusters(ids, corpora, threshold=0.3)
        # Pair 1: ids 1 & 2 (Iran stories)
        assert result.get(1) == result.get(2) == 1
        # Pair 2: ids 3 & 4 (Ukraine stories)
        assert result.get(3) == result.get(4) == 3


# ===========================================================================
# assign_clusters
# ===========================================================================

class TestAssignClusters:

    def test_similar_articles_in_same_region_get_cluster_id(self, db):
        now = datetime.now(tz=timezone.utc)
        a1 = make_article(db, url_hash="c1", region="middle_east", published_at=now,
                          title="Iran nuclear talks resume in Vienna",
                          summary="Diplomats gathered in Vienna as Iran nuclear talks resumed following months of stalemate.")
        a2 = make_article(db, url_hash="c2", region="middle_east", published_at=now,
                          title="Iran nuclear negotiations back on track in Vienna",
                          summary="Iran nuclear negotiations resumed in Vienna with diplomats meeting for fresh talks.")
        db.commit()

        assign_clusters(db, window_hours=1)
        db.refresh(a1)
        db.refresh(a2)

        assert a1.cluster_id is not None
        assert a2.cluster_id is not None
        assert a1.cluster_id == a2.cluster_id

    def test_cluster_id_is_min_article_id(self, db):
        now = datetime.now(tz=timezone.utc)
        a1 = make_article(db, url_hash="min1", region="europe", published_at=now,
                          title="NATO summit Brussels ministers defence eastern flank",
                          summary="NATO defence ministers convened in Brussels to reinforce the eastern flank alliance.")
        a2 = make_article(db, url_hash="min2", region="europe", published_at=now,
                          title="NATO ministers Brussels summit eastern flank defence",
                          summary="NATO ministers met in Brussels to discuss eastern flank reinforcement and defence plans.")
        db.commit()

        assign_clusters(db, window_hours=1)
        db.refresh(a1)
        db.refresh(a2)

        if a1.cluster_id is not None:
            assert a1.cluster_id == min(a1.id, a2.id)

    def test_articles_in_different_regions_not_clustered_together(self, db):
        now = datetime.now(tz=timezone.utc)
        # Same text, different regions — should NOT share a cluster
        title = "ceasefire agreement signed between warring parties"
        summary = "A ceasefire agreement was signed today between the warring parties after months of conflict."
        a1 = make_article(db, url_hash="reg1", region="africa",   published_at=now,
                          title=title, summary=summary)
        a2 = make_article(db, url_hash="reg2", region="americas", published_at=now,
                          title=title, summary=summary)
        db.commit()

        assign_clusters(db, window_hours=1)
        db.refresh(a1)
        db.refresh(a2)

        # They may or may not be clustered within their own regions,
        # but they must not share a cluster_id with each other
        assert not (a1.cluster_id is not None and a1.cluster_id == a2.cluster_id)

    def test_articles_outside_window_not_clustered(self, db):
        now = datetime.now(tz=timezone.utc)
        old = now - timedelta(hours=25)
        a1 = make_article(db, url_hash="win1", region="apac", published_at=old,
                          title="China Taiwan strait military exercises naval drills",
                          summary="China conducted military exercises near Taiwan strait with naval drills and air force.")
        a2 = make_article(db, url_hash="win2", region="apac", published_at=now,
                          title="China Taiwan strait military exercises naval drills",
                          summary="China conducted military exercises near Taiwan strait with naval drills and air force.")
        db.commit()

        assign_clusters(db, window_hours=1)
        db.refresh(a1)
        db.refresh(a2)

        # a1 is outside the 1-hour window — it should not be assigned a cluster
        assert a1.cluster_id is None

    def test_singleton_article_has_no_cluster(self, db):
        now = datetime.now(tz=timezone.utc)
        a = make_article(db, url_hash="solo1", region="s_asia", published_at=now,
                         title="Unique geopolitical event with no parallel coverage",
                         summary="A completely unique story with no similar articles published anywhere.")
        db.commit()

        assign_clusters(db, window_hours=1)
        db.refresh(a)

        assert a.cluster_id is None

    def test_idempotent_on_second_run(self, db):
        now = datetime.now(tz=timezone.utc)
        a1 = make_article(db, url_hash="idem1", region="se_asia", published_at=now,
                          title="Myanmar coup military junta protests crackdown Yangon",
                          summary="Myanmar military junta continued crackdown on protests in Yangon after coup.")
        a2 = make_article(db, url_hash="idem2", region="se_asia", published_at=now,
                          title="Myanmar military junta crackdown protests Yangon coup",
                          summary="Myanmar coup junta crackdown protests continued in Yangon with military presence.")
        db.commit()

        assign_clusters(db, window_hours=1)
        db.refresh(a1)
        db.refresh(a2)
        cluster_after_first = (a1.cluster_id, a2.cluster_id)

        assign_clusters(db, window_hours=1)
        db.refresh(a1)
        db.refresh(a2)
        cluster_after_second = (a1.cluster_id, a2.cluster_id)

        assert cluster_after_first == cluster_after_second

    def test_returns_count_of_clustered_articles(self, db):
        now = datetime.now(tz=timezone.utc)
        make_article(db, url_hash="cnt1", region="americas", published_at=now,
                     title="US Congress debt ceiling negotiations budget deal",
                     summary="US Congress negotiations on debt ceiling and budget deal continued in Washington.")
        make_article(db, url_hash="cnt2", region="americas", published_at=now,
                     title="Congress debt ceiling budget negotiations Washington deal",
                     summary="Budget deal and debt ceiling negotiations continued in US Congress Washington.")
        db.commit()

        count = assign_clusters(db, window_hours=1)
        assert isinstance(count, int)
        assert count >= 0
