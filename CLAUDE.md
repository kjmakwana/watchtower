# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**Watchtower** is a geopolitical OSINT dashboard. The backend ingests news from RSS feeds and live market prices, classifies articles by region/military/tickers using a keyword engine, and serves the data via a FastAPI REST API. The frontend (Vite + React + Tailwind) visualises news, markets, and a region-to-region correlation graph. The main audience for this dashboard are analysts looking for a situation overview. Features may evolve as development takes place. 

## Architecture

### Backend data flow

```
RSS feeds → rss_fetcher.py → ingestor.py → [enrich_article()] → SQLite (articles table)
                                                    ↑
                                          correlation_engine.py
                                          (region, is_military, tickers)

yfinance / Alpha Vantage → market_fetcher.py → SQLite (market_prices table)
```

### API routes


| Endpoint           | File                | Notes                                            |
| ------------------ | ------------------- | ------------------------------------------------ |
| `GET /api/news`    | `routes/news.py`    | filters: region, source, military, limit, offset |
| `GET /api/markets` | `routes/markets.py` | filter: type (commodity/forex/equity)            |
| `GET /api/graph`   | `routes/graph.py`   | param: hours (default 168)                       |


### Region taxonomy

`global`, `europe`, `middle_east`, `apac`, `se_asia`, `s_asia`, `americas`, `africa`

`global` is the fallback when no geo-entity is detected — not a meaningful filter category.

### DB

SQLite at `geopol.db` (gitignored). Two tables: `articles` and `market_prices`. `tickers` column on articles is `JSON`, stores weighted list or `null`. No migration tooling — schema changes require dropping and re-creating the DB.

### DECISIONS.md

This file records the decisions we make and the rationale behind them. It is basically the record of the progress of this project.  Each entry records what was decided, what alternatives were considered, and why we moved in the direction we did. Items are ordered chronologically within each section. 

## Behavior Guidelines

- Before starting any task that touches more than one file, summarize 
  your plan in bullet points and wait for confirmation.
- Keep responses short. No preamble. Get to the output.
- If a task is ambiguous, ask clarifying questions, do not assume
- State any assumptions you make and their consequences.
- All functions should have documentation stating - 
    - from where it is called
    - parameters
    - what it returns
    - one line basic working
- Perform adversarial review when you write a new unit to find edge cases when logic may fail


## Hard Rules
- Always consider updates to .gitignore, README.md and requirements.txt 
  when you update any code.
- Always consider changes to DECISIONS.md when adding or editing a feature
- Don't delete files. Mark them as deprecated with a comment and file name suffix instead, 
  and flag them for manual removal.
- No data, env files should ever be pushed to git. Always double check