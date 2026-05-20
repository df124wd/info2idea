from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_pipeline
from .server import serve
from .storage import connect, list_articles, list_idea_cards, list_opportunity_topics, list_source_runs, list_source_status, stats


def main() -> None:
    parser = argparse.ArgumentParser(prog="info2idea", description="Turn information feeds into monetizable idea cards.")
    parser.add_argument("--db", default="data/info2idea.db", help="SQLite database path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch feeds, score articles, and generate idea cards.")
    run_parser.add_argument("--sources", default="config/sources.json", help="JSON feed source config.")
    run_parser.add_argument("--min-score", type=float, default=24.0, help="Minimum score for idea card generation.")
    run_parser.add_argument("--timeout", type=int, default=20, help="Network timeout per source in seconds.")

    list_parser = subparsers.add_parser("ideas", help="Print idea cards as JSON.")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--status", default=None, help="Filter by recommendation.")

    article_parser = subparsers.add_parser("articles", help="Print scored articles as JSON.")
    article_parser.add_argument("--limit", type=int, default=50)
    article_parser.add_argument("--status", default=None, help="Filter by recommendation.")

    topic_parser = subparsers.add_parser("topics", help="Print long-term opportunity topics as JSON.")
    topic_parser.add_argument("--limit", type=int, default=50)
    topic_parser.add_argument("--status", default=None, help="Filter by topic status.")

    source_parser = subparsers.add_parser("sources", help="Print source health status as JSON.")
    source_parser.add_argument("--limit", type=int, default=100)
    source_parser.add_argument("--status", default=None, help="Filter by source status.")

    run_history_parser = subparsers.add_parser("source-runs", help="Print source run history as JSON.")
    run_history_parser.add_argument("--limit", type=int, default=100)
    run_history_parser.add_argument("--source-key", default=None)

    subparsers.add_parser("stats", help="Print database stats as JSON.")

    serve_parser = subparsers.add_parser("serve", help="Start the local dashboard.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--sources", default="config/sources.json")

    args = parser.parse_args()
    db_path = Path(args.db)

    if args.command == "run":
        result = run_pipeline(args.sources, db_path, min_score=args.min_score, timeout=args.timeout)
        _print_json(
            {
                "fetched": result.fetched,
                "inserted_articles": result.inserted_articles,
                "inserted_ideas": result.inserted_ideas,
                "inserted_topics": result.inserted_topics,
                "source_runs": result.source_runs,
                "ai_analyzed": result.ai_analyzed,
                "failed_sources": result.failed_sources or {},
            }
        )
        return

    if args.command == "serve":
        serve(args.host, args.port, str(db_path), args.sources)
        return

    connection = connect(db_path)
    try:
        if args.command == "ideas":
            _print_json(list_idea_cards(connection, args.limit, args.status))
        elif args.command == "articles":
            _print_json(list_articles(connection, args.limit, args.status))
        elif args.command == "topics":
            _print_json(list_opportunity_topics(connection, args.limit, args.status))
        elif args.command == "sources":
            _print_json(list_source_status(connection, args.limit, args.status))
        elif args.command == "source-runs":
            _print_json(list_source_runs(connection, args.limit, args.source_key))
        elif args.command == "stats":
            _print_json(stats(connection))
    finally:
        connection.close()


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
