# Watchtower

A geopolitical OSINT dashboard for analysts. Ingests news from RSS feeds, classifies articles by region and military relevance using a keyword engine, tracks live market prices, and surfaces everything through a React dashboard.

> Status: In active development. Endpoints and schemas may change.

---

## Features

### Backend
- **RSS ingestion** — pulls from configured feeds every 15 minutes, deduplicates by URL
- **Content classification engine** — gazetteer-based keyword scoring assigns each article a region, military flag, and weighted ticker list (no ML/NER dependency)
- **Market price tracking** — fetches 30+ instruments (commodities, forex, equities) every 2 minutes via yfinance with Alpha Vantage fallback
- **Region-to-region impact graph** — edge-weighted graph where nodes are regions and edges represent shared ticker exposure, with a 2× multiplier for military articles
- **SQLite with WAL mode** — concurrent reads alongside background writes without lock contention

### Frontend
- **News panel** — live article feed with source, region, MIL tag, time-ago, and ticker chips; refreshes on mount
- **Market pulse panel** — prices grouped by asset type (commodity / forex / equity) with green/red change%, auto-refreshes every 2 minutes
- **Breaking ticker** — top-of-screen news bar
- World map and correlation graph panels — placeholders, in progress

### API
| Endpoint | Description |
|---|---|
| `GET /api/news` | Articles with filters: `region`, `source`, `military`, `limit`, `offset` |
| `GET /api/markets` | Cached prices with filter: `type` (commodity/forex/equity) |
| `GET /api/graph` | Region impact graph with param: `hours` (default 168) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Scheduling | APScheduler |
| RSS parsing | feedparser |
| Market data | yfinance, Alpha Vantage (fallback) |
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS |
| Data fetching | TanStack Query v5 |
| Testing | pytest |

---

## Setup

### Backend

```bash
pip install -r requirements.txt
```

Create a `.env` file (all optional):
```bash
DATABASE_URL=sqlite:///./geopol.db
ALPHA_VANTAGE_API_KEY=your_key_here   # only if yfinance fails for a ticker
```

Run:
```bash
uvicorn main:app --reload --port 8000
```

On startup the scheduler immediately runs an RSS ingest and market fetch, then repeats on schedule.

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Create `frontend/.env.local` to override the API base URL (optional):
```bash
VITE_API_URL=http://localhost:8000
```

---

## Configuration

- **RSS feeds** — `config/feeds.py` (`RSS_FEEDS`)
- **Market tickers** — `config/tickers.py` (`ALL_TICKERS`, category maps)
- **Geo-entity keywords** — `config/geo_map.py` (gazetteer + military keywords)

---

## Project Layout

```
├── main.py                      # FastAPI app + lifespan
├── scheduler.py                 # APScheduler jobs
├── database.py / models.py      # SQLAlchemy engine + ORM tables
├── config/
│   ├── feeds.py                 # RSS feed list
│   ├── tickers.py               # tracked instruments
│   └── geo_map.py               # gazetteer + military keywords
├── ingestion/
│   ├── rss_fetcher.py           # feed parsing + normalization
│   ├── ingestor.py              # DB writes
│   ├── market_fetcher.py        # yfinance + fallback + DB upserts
│   ├── correlation_engine.py    # region/military/ticker classification
│   └── graph_engine.py          # region impact graph computation
├── routes/
│   ├── news.py
│   ├── markets.py
│   └── graph.py
├── tests/
└── frontend/
    └── src/
        ├── components/
        │   ├── chrome/          # TopBar, BreakingTicker
        │   ├── news/            # NewsPanel, ArticleCard
        │   └── markets/         # MarketsPanel, MarketRow
        └── lib/                 # api.ts, types.ts
```

---

## Testing

```bash
pytest -v
```
