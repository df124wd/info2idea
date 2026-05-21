# Info2Idea

Info2Idea is a local-first opportunity radar for a solo builder. It tracks public information feeds, scores signals in your focus areas, and turns both strong and weak signals into a long-term opportunity memory.

The first version is intentionally low-cost:

- Python standard library only
- SQLite for local storage
- RSS/Atom, Google News, HN, GitHub, Reddit, and manual JSON sources configured in JSON
- Built-in Web dashboard
- No paid LLM dependency required; AI analysis is an optional enhancement

## What It Does

The current MVP follows this pipeline:

1. Fetch configured news, community, GitHub, RSS/Atom, and manual signal sources.
2. Normalize articles and deduplicate them in SQLite.
3. Score each article against your preferred domains: AI tools, content business, indie development, and games.
4. Optionally ask AI to analyze stronger new signals and refine the opportunity judgment.
5. Classify each signal into build now, validate in 7 days, watch, or archive.
6. Store weak signals as reusable topics so they can return later with more evidence.
7. Generate an idea card when a signal is strong enough.
8. Show source health, ideas, topics, recent signals, filters, and score dimensions in a local dashboard.
9. Review today's signal inbox, give feedback, and trigger a DeepSeek deep dive on selected signals.

Each idea card includes:

- Target user
- Pain point
- Product direction
- Monetization path
- MVP steps
- Content angle
- Validation plan
- Risks
- Recommendation
- Next action

## Quick Start

Create a virtual environment if you want one, then run from the repo root:

```powershell
python -m pip install -e .
python -m info2idea.cli --db data/sample.db run --sources config/sample_sources.json --min-score 10
python scripts/run_dashboard.py --db data/sample.db --sources config/sample_sources.json
```

Open:

```text
http://127.0.0.1:8765
```

For real feeds:

```powershell
python -m info2idea.cli run
python scripts/run_dashboard.py
```

To inspect long-term topics:

```powershell
python -m info2idea.cli topics --limit 20
```

To inspect the source-quality and today views used by the dashboard:

```powershell
python -m info2idea.cli source-quality --limit 50
python -m info2idea.cli today --limit 20 --min-score 50
```

## Configuration

Edit `config/sources.json` to add or remove sources:

```json
{
  "name": "Hacker News",
  "kind": "rss",
  "url": "https://news.ycombinator.com/rss",
  "category": "indie_dev",
  "weight": 1.0
}
```

Supported source kinds in the MVP:

- `rss`
- `reddit_rss`
- `reddit_search`
- `github_search`
- `github_issues`
- `google_news`
- `hn_search`
- `manual_json`

Supported categories in the MVP:

- `ai_tools`
- `content`
- `indie_dev`
- `games`
- `mixed`

Local XML files are also supported, which makes tests and offline demos cheap.

You can also use manual JSON signal files for platforms that are hard to crawl cleanly at the start.

## Source Monitoring

Every collection run records source health:

- source status: `ok`, `empty`, `error`, or `disabled`
- fetched count
- newly inserted signal count
- newly created topic count
- duration
- latest error message
- preview titles

Use the CLI:

```powershell
python -m info2idea.cli sources --limit 50
python -m info2idea.cli source-runs --limit 100
```

This is important because the product is meant to watch markets over time. A quiet source, a broken source, and a source producing strong new signals should not look the same.

## Optional AI Analysis

The scoring model works without AI. By default it uses deterministic rules so the project stays free and reliable.

If `DEEPSEEK_API_KEY` is set, the pipeline only sends stronger new signals to AI for deeper analysis. The API call uses the OpenAI-compatible chat completions format, with DeepSeek as the default provider. AI can add:

- one-sentence signal summary
- sharper target user and pain point
- concrete monetization angle
- content/distribution angle
- 7-day validation plan
- risks
- refined score dimensions

PowerShell example:

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
$env:INFO2IDEA_AI_MODEL = "deepseek-v4-flash"
python -m info2idea.cli run
```

Without a key, `analysis_mode` stays `rules`. With a successful AI pass, it becomes `ai`.

Useful switches:

```powershell
$env:INFO2IDEA_AI_ENABLED = "off"
$env:INFO2IDEA_AI_BASE_URL = "https://api.deepseek.com"
$env:INFO2IDEA_AI_MAX_TOKENS = "1600"
```

Use `INFO2IDEA_AI_ENABLED=off` when you only want to test source health without spending tokens.

## Signal Inbox

The dashboard includes a daily signal inbox. Each signal can be marked as:

- `interested`: worth tracking or deepening
- `later`: not urgent, but keep it visible
- `ignored`: noise or not relevant
- `new`: unreviewed

The inbox also has a `DeepSeek Dive` button. With `DEEPSEEK_API_KEY`, it asks DeepSeek for a sharper analysis and writes the result back to the signal. Without a key, it falls back to a local rules-based analysis so the workflow still works offline.

Backend APIs:

```text
GET  /api/inbox
POST /api/signals/{id}/feedback
POST /api/signals/{id}/deep-dive
```

## Testing

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

## Deployment Options

### Cheapest Personal Deployment

Run it on your laptop:

```powershell
python -m info2idea.cli run
python -m info2idea.cli serve
```

Use Windows Task Scheduler to run the fetch command once or twice per day.

### Low-Cost VPS Deployment

Use a small VPS and run:

```bash
python -m pip install -e .
python -m info2idea.cli run
python -m info2idea.cli serve --host 0.0.0.0 --port 8765
```

Add a cron job:

```cron
0 8,20 * * * cd /opt/info2idea && python -m info2idea.cli run
```

For public access, put Caddy or Nginx in front of the dashboard and add basic auth.

## Dependency Management

Use `uv` with `pyproject.toml` and a project-local `.venv`.

Recommended flow:

```powershell
uv sync
uv run python -m info2idea.cli run
uv run python scripts/run_dashboard.py
```

Why this setup:

- `pyproject.toml` keeps project metadata and dependencies in one place.
- `uv` is fast, reproducible, and good for small solo projects.
- `.venv` stays isolated and can be deleted and recreated anytime.
- Conda is overkill here unless you later need heavy data science or GPU stacks.

## Roadmap

- Add more source adapters for Product Hunt API, YouTube, Steam, app stores, Bilibili, and Xiaohongshu workflows.
- Add validation signals: search volume, GitHub stars, competitor pricing, social engagement, and landing-page signups.
- Add content generation: posts, scripts, newsletters, and outreach messages.
- Add product execution mode: generate MVP specs, tasks, and starter code.
- Add export to Markdown, Notion, or GitHub issues.
