from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from .feeds import fetch_source, load_sources
from .idea_engine import build_idea_card
from .models import Article, SourceRunSummary
from .scoring import apply_source_weight, score_article
from .storage import connect, record_source_run, upsert_article, upsert_idea_card, upsert_opportunity_topic


@dataclass
class PipelineResult:
    fetched: int = 0
    inserted_articles: int = 0
    inserted_ideas: int = 0
    inserted_topics: int = 0
    source_runs: int = 0
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
            started_at = datetime.now(timezone.utc)
            started_perf = perf_counter()
            if not source.enabled:
                record_source_run(
                    connection,
                    SourceRunSummary(
                        source_key=source.source_key,
                        name=source.name,
                        kind=source.kind,
                        category=source.category,
                        status="disabled",
                        fetched_count=0,
                        new_count=0,
                        topic_count=0,
                        duration_ms=0,
                        preview="",
                        error="",
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                    ),
                )
                result.source_runs += 1
                connection.commit()
                continue
            try:
                articles = fetch_source(source, timeout=timeout)
            except Exception as exc:  # noqa: BLE001 - source errors should not stop the whole run.
                result.failed_sources[source.name] = str(exc)
                record_source_run(
                    connection,
                    SourceRunSummary(
                        source_key=source.source_key,
                        name=source.name,
                        kind=source.kind,
                        category=source.category,
                        status="error",
                        fetched_count=0,
                        new_count=0,
                        topic_count=0,
                        duration_ms=_duration_ms(started_perf),
                        preview="",
                        error=str(exc),
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                    ),
                )
                result.source_runs += 1
                connection.commit()
                continue

            new_articles = 0
            new_topics = 0
            result.fetched += len(articles)
            for article in articles:
                if not article.source_key:
                    article.source_key = source.source_key
                scored = apply_source_weight(score_article(article), source.weight)
                if upsert_article(connection, article, scored):
                    result.inserted_articles += 1
                    new_articles += 1
                if upsert_opportunity_topic(connection, article, scored):
                    result.inserted_topics += 1
                    new_topics += 1
                if scored.total >= min_score:
                    card = build_idea_card(article, scored)
                    if upsert_idea_card(connection, card):
                        result.inserted_ideas += 1
            record_source_run(
                connection,
                SourceRunSummary(
                    source_key=source.source_key,
                    name=source.name,
                    kind=source.kind,
                    category=source.category,
                    status="ok" if articles else "empty",
                    fetched_count=len(articles),
                    new_count=new_articles,
                    topic_count=new_topics,
                    duration_ms=_duration_ms(started_perf),
                    preview=_preview(articles),
                    error="",
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                ),
            )
            result.source_runs += 1
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


def _duration_ms(started_perf: float) -> int:
    return int((perf_counter() - started_perf) * 1000)


def _preview(articles: list[Article], limit: int = 3) -> str:
    return "\n".join(article.title for article in articles[:limit])
