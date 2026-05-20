from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .feeds import fetch_source, load_sources
from .idea_engine import build_idea_card
from .models import Article
from .scoring import score_article
from .storage import connect, upsert_article, upsert_idea_card, upsert_opportunity_topic


@dataclass
class PipelineResult:
    fetched: int = 0
    inserted_articles: int = 0
    inserted_ideas: int = 0
    inserted_topics: int = 0
    failed_sources: dict[str, str] | None = None


def run_pipeline(
    sources_path: str | Path = "config/sources.json",
    db_path: str | Path = "data/info2idea.db",
    min_score: float = 24.0,
    timeout: int = 20,
) -> PipelineResult:
    sources = load_sources(sources_path)
    connection = connect(db_path)
    result = PipelineResult(failed_sources={})

    try:
        for source in sources:
            if not source.enabled:
                continue
            try:
                articles = fetch_source(source, timeout=timeout)
            except Exception as exc:  # noqa: BLE001 - source errors should not stop the whole run.
                result.failed_sources[source.name] = str(exc)
                continue

            result.fetched += len(articles)
            for article in articles:
                scored = score_article(article)
                if upsert_article(connection, article, scored):
                    result.inserted_articles += 1
                if upsert_opportunity_topic(connection, article, scored):
                    result.inserted_topics += 1
                if scored.total >= min_score:
                    card = build_idea_card(article, scored)
                    if upsert_idea_card(connection, card):
                        result.inserted_ideas += 1
            connection.commit()
    finally:
        connection.close()

    return result


def analyze_articles(articles: list[Article], min_score: float = 24.0) -> list[tuple[Article, object]]:
    analyzed = []
    for article in articles:
        scored = score_article(article)
        if scored.total >= min_score:
            analyzed.append((article, scored))
    return analyzed
