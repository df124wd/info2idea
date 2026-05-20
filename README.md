# Info2Idea

Info2Idea is a local-first opportunity radar for a solo builder. It tracks public information feeds, scores signals in your focus areas, and turns high-signal items into monetizable idea cards.

The first version is intentionally low-cost:

- Python standard library only
- SQLite for local storage
- RSS/Atom sources configured in JSON
- Built-in Web dashboard
- No paid LLM dependency required for the MVP

## What It Does

The current MVP follows this pipeline:

1. Fetch configured RSS/Atom feeds.
2. Normalize articles and deduplicate them in SQLite.
3. Score each article against your preferred domains: AI tools, content business, indie development, and games.
4. Generate an idea card when a signal is strong enough.
5. Show ideas and recent signals in a local dashboard.

Each idea card includes:

- Target user
- Pain point
- Product direction
- Monetization path
- MVP steps
- Content angle
- Validation plan
- Risks

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

## Configuration

Edit `config/sources.json` to add or remove sources:

```json
{
  "name": "Hacker News",
  "url": "https://news.ycombinator.com/rss",
  "category": "indie_dev",
  "weight": 1.0
}
```

Supported categories in the MVP:

- `ai_tools`
- `content`
- `indie_dev`
- `games`
- `mixed`

Local XML files are also supported, which makes tests and offline demos cheap.

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

## Roadmap

- Add LLM provider interface for deeper idea generation.
- Add source adapters for GitHub trending, Product Hunt API, Reddit, YouTube, Steam, and app stores.
- Add validation signals: search volume, GitHub stars, competitor pricing, social engagement, and landing-page signups.
- Add content generation: posts, scripts, newsletters, and outreach messages.
- Add product execution mode: generate MVP specs, tasks, and starter code.
- Add export to Markdown, Notion, or GitHub issues.
