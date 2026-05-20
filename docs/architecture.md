# Architecture

Info2Idea is built around a small, replaceable pipeline:

```text
Sources -> Fetch -> Normalize -> Score -> Idea Card -> Store -> Dashboard
```

## Modules

- `feeds.py`: loads sources and parses RSS/Atom into normalized articles.
- `scoring.py`: scores articles using focus-domain, pain, monetization, actionability, and recency signals.
- `idea_engine.py`: turns a scored article into a structured business idea card.
- `storage.py`: persists articles and idea cards in SQLite.
- `pipeline.py`: orchestrates one full collection and analysis run.
- `server.py`: serves the dashboard and JSON APIs.
- `web/`: static dashboard assets.

## Why This Stack

The first version optimizes for your current constraints:

- You are a student with coding ability and limited budget.
- You can invest 2-3 hours per day.
- The system should be useful for yourself before becoming a product.
- It may later become open source, so a simple local setup matters.

That is why the MVP avoids paid infrastructure and heavy frameworks. The architecture still leaves room for upgrades:

- SQLite can become PostgreSQL.
- Keyword scoring can become hybrid LLM + embeddings.
- RSS sources can be joined by browser automation and official APIs.
- The static dashboard can become Next.js when the product surface needs accounts, saved views, or collaboration.

## Next Iteration

The highest-leverage next step is not adding more feeds. It is adding validation signals:

- Are there paid competitors?
- Are people searching for this?
- Are people complaining about this in communities?
- Can a solo builder ship a useful first artifact in under one week?

Those signals will make the system less like a news reader and more like a practical money radar.
