# Architecture

Info2Idea is built around a small, replaceable pipeline:

```text
Sources -> Fetch -> Normalize -> Score -> Topic Memory -> Idea Card -> Store -> Dashboard
```

## Modules

- `feeds.py`: loads sources and parses RSS/Atom into normalized articles.
- `scoring.py`: scores articles using focus-domain, pain, monetization, actionability, validation, reach, and recency signals.
- `idea_engine.py`: turns a scored article into a structured business idea card.
- `storage.py`: persists articles, opportunity topics, idea cards, source runs, and source health in SQLite.
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

The topic memory layer matters just as much:

- Weak signals are archived, not discarded.
- Repeated weak signals become topics.
- Topics can move from archive to watch to validate to build now as evidence accumulates.

## Source Strategy

The system separates low-risk automatic sources from higher-friction sources:

- RSS/Atom: stable news, product, and blog monitoring.
- Google News RSS: keyword-based market and startup trend monitoring.
- Hacker News search: technical and indie-dev trend monitoring.
- GitHub repository search: open-source product and tooling momentum.
- GitHub issue search: workflow pain, missing features, and developer complaints.
- Reddit RSS/search: community pain, demand language, and early distribution surfaces.
- Manual JSON: Bilibili, Xiaohongshu, Steam, newsletters, or any platform where a manual first pass is safer than brittle scraping.

Each source run is stored, so the dashboard can show whether a source is healthy, empty, noisy, or broken.
