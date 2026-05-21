from __future__ import annotations

import json
from datetime import datetime

from .ai import enhance_score_with_ai, local_ai_like_insight
from .models import Article, OpportunityScore
from .scoring import score_article
from .storage import get_article, update_article_ai_analysis


def deep_dive_article(connection, article_id: int) -> dict | None:
    row = get_article(connection, article_id)
    if not row:
        return None
    article = _article_from_row(row)
    score = _score_from_row(row, article)
    enhanced = enhance_score_with_ai(article, score)
    if enhanced.analysis_mode != "ai":
        enhanced.ai_insight = local_ai_like_insight(article, score)
        enhanced.analysis_mode = "local_ai"
        enhanced.ai_error = enhanced.ai_error or "DeepSeek not available; using local analysis fallback."
    update_article_ai_analysis(connection, article_id, enhanced)
    return get_article(connection, article_id)


def _article_from_row(row: dict) -> Article:
    return Article(
        source=str(row.get("source", "")),
        source_category=str(row.get("source_category", "")),
        title=str(row.get("title", "")),
        url=str(row.get("url", "")),
        summary=str(row.get("summary", "")),
        published_at=_parse_datetime(row.get("published_at")),
        raw_id=str(row.get("fingerprint", "")) or None,
        source_key=str(row.get("source_key", "")),
        fetched_at=_parse_datetime(row.get("fetched_at")) or datetime.now().astimezone(),
    )


def _score_from_row(row: dict, article: Article) -> OpportunityScore:
    fallback = score_article(article)
    return OpportunityScore(
        total=float(row.get("score") or fallback.total),
        domain=str(row.get("domain") or fallback.domain),
        confidence=float(row.get("confidence") or fallback.confidence),
        reasons=_split_lines(str(row.get("reasons") or "")) or fallback.reasons,
        matched_keywords=_split_csv(str(row.get("matched_keywords") or "")) or fallback.matched_keywords,
        dimension_scores=_loads_dimensions(row.get("dimension_scores")) or fallback.dimension_scores,
        risk_penalty=float(row.get("risk_penalty") or fallback.risk_penalty),
        recommendation=str(row.get("recommendation") or fallback.recommendation),
        next_action=str(row.get("next_action") or fallback.next_action),
        topic_key=str(row.get("topic_key") or fallback.topic_key),
    )


def _loads_dimensions(value: object) -> dict[str, float]:
    if isinstance(value, dict):
        return {str(key): float(score) for key, score in value.items()}
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): float(score) for key, score in parsed.items()}


def _split_lines(value: str) -> list[str]:
    return [item.strip() for item in value.splitlines() if item.strip()]


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
