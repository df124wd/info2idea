from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Article, IdeaCard, OpportunityScore, SourceRunSummary


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    source_category TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT NOT NULL,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    score REAL,
    domain TEXT,
    confidence REAL,
    reasons TEXT,
    matched_keywords TEXT,
    source_key TEXT DEFAULT '',
    analysis_mode TEXT DEFAULT 'rules',
    ai_summary TEXT DEFAULT '',
    ai_opportunity TEXT DEFAULT '',
    ai_target_user TEXT DEFAULT '',
    ai_pain_point TEXT DEFAULT '',
    ai_monetization TEXT DEFAULT '',
    ai_content_angle TEXT DEFAULT '',
    ai_validation_plan TEXT DEFAULT '',
    ai_risks TEXT DEFAULT '',
    ai_model TEXT DEFAULT '',
    ai_error TEXT DEFAULT '',
    dimension_scores TEXT,
    risk_penalty REAL DEFAULT 0,
    recommendation TEXT DEFAULT 'archive',
    next_action TEXT DEFAULT '',
    topic_key TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS idea_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_url TEXT NOT NULL UNIQUE,
    source_key TEXT DEFAULT '',
    title TEXT NOT NULL,
    domain TEXT NOT NULL,
    score REAL NOT NULL,
    target_user TEXT NOT NULL,
    pain_point TEXT NOT NULL,
    product_idea TEXT NOT NULL,
    monetization TEXT NOT NULL,
    mvp_steps TEXT NOT NULL,
    content_angle TEXT NOT NULL,
    validation_plan TEXT NOT NULL,
    risks TEXT NOT NULL,
    recommendation TEXT DEFAULT 'validate',
    next_action TEXT DEFAULT '',
    topic_key TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunity_topics (
    topic_key TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    signal_count INTEGER NOT NULL DEFAULT 0,
    best_score REAL NOT NULL DEFAULT 0,
    average_score REAL NOT NULL DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    last_article_url TEXT NOT NULL,
    evidence TEXT NOT NULL,
    next_action TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    topic_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    preview TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_status (
    source_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    total_runs INTEGER NOT NULL DEFAULT 0,
    total_fetched INTEGER NOT NULL DEFAULT 0,
    total_new INTEGER NOT NULL DEFAULT 0,
    total_topics INTEGER NOT NULL DEFAULT 0,
    last_fetched_count INTEGER NOT NULL DEFAULT 0,
    last_new_count INTEGER NOT NULL DEFAULT 0,
    last_topic_count INTEGER NOT NULL DEFAULT 0,
    last_duration_ms INTEGER NOT NULL DEFAULT 0,
    last_preview TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    first_seen TEXT NOT NULL,
    last_started_at TEXT NOT NULL,
    last_finished_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    _migrate(connection)
    return connection


def upsert_article(connection: sqlite3.Connection, article: Article, score: OpportunityScore | None = None) -> bool:
    existing = connection.execute(
        "SELECT id FROM articles WHERE fingerprint = ? OR url = ?",
        (article.fingerprint, article.url),
    ).fetchone()
    if existing:
        return False

    connection.execute(
        """
        INSERT INTO articles (
            fingerprint, source, source_category, title, url, summary,
            published_at, fetched_at, score, domain, confidence, reasons, matched_keywords,
            source_key, analysis_mode, ai_summary, ai_opportunity, ai_target_user, ai_pain_point,
            ai_monetization, ai_content_angle, ai_validation_plan, ai_risks, ai_model, ai_error,
            dimension_scores, risk_penalty, recommendation, next_action, topic_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article.fingerprint,
            article.source,
            article.source_category,
            article.title,
            article.url,
            article.summary,
            _to_iso(article.published_at),
            _to_iso(article.fetched_at),
            score.total if score else None,
            score.domain if score else None,
            score.confidence if score else None,
            "\n".join(score.reasons) if score else "",
            ", ".join(score.matched_keywords) if score else "",
            article.source_key,
            score.analysis_mode if score else "rules",
            score.ai_insight.summary if score and score.ai_insight else "",
            score.ai_insight.opportunity if score and score.ai_insight else "",
            score.ai_insight.target_user if score and score.ai_insight else "",
            score.ai_insight.pain_point if score and score.ai_insight else "",
            score.ai_insight.monetization if score and score.ai_insight else "",
            score.ai_insight.content_angle if score and score.ai_insight else "",
            "\n".join(score.ai_insight.validation_plan) if score and score.ai_insight else "",
            "\n".join(score.ai_insight.risks) if score and score.ai_insight else "",
            score.ai_insight.model if score and score.ai_insight else "",
            score.ai_error if score else "",
            _json_dumps(score.dimension_scores) if score else "{}",
            score.risk_penalty if score else 0.0,
            score.recommendation if score else "archive",
            score.next_action if score else "",
            score.topic_key if score else "",
        ),
    )
    return True


def article_exists(connection: sqlite3.Connection, article: Article) -> bool:
    existing = connection.execute(
        "SELECT id FROM articles WHERE fingerprint = ? OR url = ?",
        (article.fingerprint, article.url),
    ).fetchone()
    return bool(existing)


def upsert_idea_card(connection: sqlite3.Connection, card: IdeaCard) -> bool:
    existing = connection.execute(
        "SELECT id FROM idea_cards WHERE article_url = ?",
        (card.article_url,),
    ).fetchone()
    if existing:
        return False
    connection.execute(
        """
        INSERT INTO idea_cards (
            article_url, source_key, title, domain, score, target_user, pain_point, product_idea,
            monetization, mvp_steps, content_angle, validation_plan, risks,
            recommendation, next_action, topic_key, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            card.article_url,
            card.source_key,
            card.title,
            card.domain,
            card.score,
            card.target_user,
            card.pain_point,
            card.product_idea,
            card.monetization,
            "\n".join(card.mvp_steps),
            card.content_angle,
            "\n".join(card.validation_plan),
            "\n".join(card.risks),
            card.recommendation,
            card.next_action,
            card.topic_key,
            _to_iso(card.created_at),
        ),
    )
    return True


def upsert_opportunity_topic(connection: sqlite3.Connection, article: Article, score: OpportunityScore) -> bool:
    now = _to_iso(datetime.now(timezone.utc)) or ""
    existing = connection.execute(
        "SELECT * FROM opportunity_topics WHERE topic_key = ?",
        (score.topic_key,),
    ).fetchone()
    evidence_line = f"{article.title} ({article.source}) - {score.total:.1f}"
    if not existing:
        connection.execute(
            """
            INSERT INTO opportunity_topics (
                topic_key, domain, status, title, signal_count, best_score, average_score,
                first_seen, last_seen, last_article_url, evidence, next_action, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                score.topic_key,
                score.domain,
                _status_from_score(score),
                article.title,
                1,
                score.total,
                score.total,
                _to_iso(article.fetched_at) or now,
                _to_iso(article.fetched_at) or now,
                article.url,
                evidence_line,
                score.next_action,
                now,
            ),
        )
        return True

    signal_count = int(existing["signal_count"]) + 1
    best_score = max(float(existing["best_score"]), score.total)
    average_score = ((float(existing["average_score"]) * int(existing["signal_count"])) + score.total) / signal_count
    status = _promote_status(str(existing["status"]), score, signal_count)
    evidence = _append_evidence(str(existing["evidence"]), evidence_line)
    connection.execute(
        """
        UPDATE opportunity_topics
        SET domain = ?,
            status = ?,
            signal_count = ?,
            best_score = ?,
            average_score = ?,
            last_seen = ?,
            last_article_url = ?,
            evidence = ?,
            next_action = ?,
            updated_at = ?
        WHERE topic_key = ?
        """,
        (
            score.domain,
            status,
            signal_count,
            best_score,
            round(average_score, 2),
            _to_iso(article.fetched_at) or now,
            article.url,
            evidence,
            score.next_action,
            now,
            score.topic_key,
        ),
    )
    return False


def record_source_run(connection: sqlite3.Connection, summary: SourceRunSummary) -> None:
    now = _to_iso(datetime.now(timezone.utc)) or ""
    started_at = _to_iso(summary.started_at) or now
    finished_at = _to_iso(summary.finished_at) or now
    connection.execute(
        """
        INSERT INTO source_runs (
            source_key, name, kind, category, status, fetched_count, new_count, topic_count,
            duration_ms, preview, error, started_at, finished_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            summary.source_key,
            summary.name,
            summary.kind,
            summary.category,
            summary.status,
            summary.fetched_count,
            summary.new_count,
            summary.topic_count,
            summary.duration_ms,
            summary.preview,
            summary.error,
            started_at,
            finished_at,
        ),
    )
    existing = connection.execute(
        "SELECT source_key FROM source_status WHERE source_key = ?",
        (summary.source_key,),
    ).fetchone()
    if not existing:
        connection.execute(
            """
            INSERT INTO source_status (
                source_key, name, kind, category, status, total_runs, total_fetched, total_new,
                total_topics, last_fetched_count, last_new_count, last_topic_count, last_duration_ms,
                last_preview, last_error, first_seen, last_started_at, last_finished_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.source_key,
                summary.name,
                summary.kind,
                summary.category,
                summary.status,
                1,
                summary.fetched_count,
                summary.new_count,
                summary.topic_count,
                summary.fetched_count,
                summary.new_count,
                summary.topic_count,
                summary.duration_ms,
                summary.preview,
                summary.error,
                started_at,
                started_at,
                finished_at,
                now,
            ),
        )
        return

    connection.execute(
        """
        UPDATE source_status
        SET name = ?,
            kind = ?,
            category = ?,
            status = ?,
            total_runs = total_runs + 1,
            total_fetched = total_fetched + ?,
            total_new = total_new + ?,
            total_topics = total_topics + ?,
            last_fetched_count = ?,
            last_new_count = ?,
            last_topic_count = ?,
            last_duration_ms = ?,
            last_preview = ?,
            last_error = ?,
            last_started_at = ?,
            last_finished_at = ?,
            updated_at = ?
        WHERE source_key = ?
        """,
        (
            summary.name,
            summary.kind,
            summary.category,
            summary.status,
            summary.fetched_count,
            summary.new_count,
            summary.topic_count,
            summary.fetched_count,
            summary.new_count,
            summary.topic_count,
            summary.duration_ms,
            summary.preview,
            summary.error,
            started_at,
            finished_at,
            now,
            summary.source_key,
        ),
    )


def list_idea_cards(connection: sqlite3.Connection, limit: int = 50, status: str | None = None) -> list[dict]:
    where = ""
    params: list[object] = []
    if status:
        where = "WHERE recommendation = ?"
        params.append(status)
    params.append(limit)
    rows = connection.execute(
        f"""
        SELECT *
        FROM idea_cards
        {where}
        ORDER BY score DESC, created_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_articles(connection: sqlite3.Connection, limit: int = 100, status: str | None = None) -> list[dict]:
    where = ""
    params: list[object] = []
    if status:
        where = "WHERE recommendation = ?"
        params.append(status)
    params.append(limit)
    rows = connection.execute(
        f"""
        SELECT *
        FROM articles
        {where}
        ORDER BY COALESCE(score, 0) DESC, fetched_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_source_status(connection: sqlite3.Connection, limit: int = 100, status: str | None = None) -> list[dict]:
    where = ""
    params: list[object] = []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    params.append(limit)
    rows = connection.execute(
        f"""
        SELECT *
        FROM source_status
        {where}
        ORDER BY
            CASE status
                WHEN 'ok' THEN 0
                WHEN 'empty' THEN 1
                WHEN 'disabled' THEN 2
                ELSE 3
            END,
            last_new_count DESC,
            last_finished_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_source_runs(connection: sqlite3.Connection, limit: int = 100, source_key: str | None = None) -> list[dict]:
    where = ""
    params: list[object] = []
    if source_key:
        where = "WHERE source_key = ?"
        params.append(source_key)
    params.append(limit)
    rows = connection.execute(
        f"""
        SELECT *
        FROM source_runs
        {where}
        ORDER BY finished_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_opportunity_topics(connection: sqlite3.Connection, limit: int = 50, status: str | None = None) -> list[dict]:
    where = ""
    params: list[object] = []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    params.append(limit)
    rows = connection.execute(
        f"""
        SELECT *
        FROM opportunity_topics
        {where}
        ORDER BY
            CASE status
                WHEN 'build_now' THEN 0
                WHEN 'validate_7_days' THEN 1
                WHEN 'watch' THEN 2
                ELSE 3
            END,
            best_score DESC,
            signal_count DESC,
            last_seen DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def stats(connection: sqlite3.Connection) -> dict[str, int | str]:
    article_count = connection.execute("SELECT COUNT(*) AS count FROM articles").fetchone()["count"]
    idea_count = connection.execute("SELECT COUNT(*) AS count FROM idea_cards").fetchone()["count"]
    topic_count = connection.execute("SELECT COUNT(*) AS count FROM opportunity_topics").fetchone()["count"]
    watch_count = connection.execute("SELECT COUNT(*) AS count FROM opportunity_topics WHERE status = 'watch'").fetchone()["count"]
    archive_count = connection.execute("SELECT COUNT(*) AS count FROM opportunity_topics WHERE status = 'archive'").fetchone()["count"]
    source_count = connection.execute("SELECT COUNT(*) AS count FROM source_status").fetchone()["count"]
    healthy_source_count = connection.execute("SELECT COUNT(*) AS count FROM source_status WHERE status = 'ok'").fetchone()["count"]
    ai_article_count = connection.execute("SELECT COUNT(*) AS count FROM articles WHERE analysis_mode = 'ai'").fetchone()["count"]
    latest = connection.execute("SELECT MAX(fetched_at) AS latest FROM articles").fetchone()["latest"]
    return {
        "articles": article_count,
        "ideas": idea_count,
        "topics": topic_count,
        "watching": watch_count,
        "archived": archive_count,
        "sources": source_count,
        "healthy_sources": healthy_source_count,
        "ai_analyzed": ai_article_count,
        "latest_fetch": latest or "",
    }


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _migrate(connection: sqlite3.Connection) -> None:
    article_columns = _columns(connection, "articles")
    _add_missing_columns(
        connection,
        "articles",
        article_columns,
        {
            "dimension_scores": "TEXT",
            "risk_penalty": "REAL DEFAULT 0",
            "recommendation": "TEXT DEFAULT 'archive'",
            "next_action": "TEXT DEFAULT ''",
            "topic_key": "TEXT DEFAULT ''",
            "source_key": "TEXT DEFAULT ''",
            "analysis_mode": "TEXT DEFAULT 'rules'",
            "ai_summary": "TEXT DEFAULT ''",
            "ai_opportunity": "TEXT DEFAULT ''",
            "ai_target_user": "TEXT DEFAULT ''",
            "ai_pain_point": "TEXT DEFAULT ''",
            "ai_monetization": "TEXT DEFAULT ''",
            "ai_content_angle": "TEXT DEFAULT ''",
            "ai_validation_plan": "TEXT DEFAULT ''",
            "ai_risks": "TEXT DEFAULT ''",
            "ai_model": "TEXT DEFAULT ''",
            "ai_error": "TEXT DEFAULT ''",
        },
    )
    idea_columns = _columns(connection, "idea_cards")
    _add_missing_columns(
        connection,
        "idea_cards",
        idea_columns,
        {
            "recommendation": "TEXT DEFAULT 'validate'",
            "next_action": "TEXT DEFAULT ''",
            "topic_key": "TEXT DEFAULT ''",
            "source_key": "TEXT DEFAULT ''",
        },
    )


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def _add_missing_columns(connection: sqlite3.Connection, table: str, existing: set[str], columns: dict[str, str]) -> None:
    for name, definition in columns.items():
        if name not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _json_dumps(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _status_from_score(score: OpportunityScore) -> str:
    return score.recommendation


def _promote_status(current: str, score: OpportunityScore, signal_count: int) -> str:
    ranked = ["archive", "watch", "validate_7_days", "build_now"]
    candidate = score.recommendation
    if current == "archive" and signal_count >= 2 and score.total >= 45:
        candidate = "watch"
    if current == "watch" and signal_count >= 3 and score.total >= 60:
        candidate = "validate_7_days"
    return max(current, candidate, key=lambda status: ranked.index(status) if status in ranked else 0)


def _append_evidence(existing: str, line: str, limit: int = 8) -> str:
    lines = [item for item in [*existing.splitlines(), line] if item.strip()]
    deduped: list[str] = []
    for item in lines:
        if item not in deduped:
            deduped.append(item)
    return "\n".join(deduped[-limit:])
