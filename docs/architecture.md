# Architecture

Info2Idea is built around a small, replaceable pipeline:

```text
Sources -> Fetch -> Normalize -> Rule Score -> Optional AI Analysis -> Topic Memory -> Idea Card -> Store -> Dashboard
```

## Modules

- `feeds.py`: loads sources and parses RSS/Atom into normalized articles.
- `ai.py`: optionally calls an LLM for deeper analysis of stronger new signals and merges the result into the score.
- `scoring.py`: scores articles using focus-domain, pain, monetization, actionability, validation, reach, and recency signals.
- `idea_engine.py`: turns a scored article into a structured business idea card.
- `storage.py`: persists articles, opportunity topics, idea cards, source runs, and source health in SQLite.
- `inbox.py`: powers the daily review workflow, feedback updates, and per-signal DeepSeek deep dives.
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
- Rule scoring can be enhanced by LLM analysis and later embeddings.
- RSS sources can be joined by browser automation and official APIs.
- The static dashboard can become Next.js when the product surface needs accounts, saved views, or collaboration.

## Database Direction

Use SQLite for the personal MVP and early open-source version. It is the right default while the system is single-user, local-first, cheap to run, and mostly append-heavy.

Move to PostgreSQL when any of these become true:

- dashboard needs login, sharing, or multiple users
- source jobs run on a VPS or worker separate from the dashboard
- you need reliable concurrent writes, queues, or job locks
- you add embeddings/vector search through `pgvector`
- you need cloud backups, analytics queries, and migrations as product discipline

Recommended path:

1. Keep SQLite now, but isolate storage functions behind `storage.py`.
2. Add schema migration files before the schema grows much further.
3. When productizing, migrate to PostgreSQL with `articles`, `source_runs`, `source_status`, `opportunity_topics`, and `idea_cards` as first tables.
4. Add `pgvector` only after you have enough archived signals for semantic recall to matter.

## Current Dashboard

The dashboard is meant to be an information workbench, not just a list of links:

- top metrics for signals, ideas, topics, source health, and AI-analyzed rows
- source health cards with status, duration, latest counts, and errors
- source quality panel with error, empty, and yield rates
- signal inbox for today's review queue
- per-signal actions: interested, later, ignored, and DeepSeek deep dive
- filters for source status and opportunity status
- high-signal idea cards
- topic and recent-signal side panels
- score dimension bars for recent signals
- AI summaries and opportunity notes when available

## Next Iteration

After source monitoring and dashboard clarity, the highest-leverage next step is validation signals:

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
