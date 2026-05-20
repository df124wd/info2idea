from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str = ""
    category: str = "general"
    weight: float = 1.0
    kind: str = "rss"
    enabled: bool = True
    query: str = ""
    limit: int = 20
    freshness_days: float = 3.0
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedSource":
        return cls(
            name=str(data["name"]).strip(),
            url=str(data.get("url", "")).strip(),
            category=str(data.get("category", "general")).strip() or "general",
            weight=float(data.get("weight", 1.0)),
            kind=str(data.get("kind", data.get("type", "rss"))).strip() or "rss",
            enabled=_as_bool(data.get("enabled", True)),
            query=str(data.get("query", "")).strip(),
            limit=int(data.get("limit", 20)),
            freshness_days=float(data.get("freshness_days", 3.0)),
            params=dict(data.get("params", {})),
        )

    @property
    def source_key(self) -> str:
        payload = {
            "kind": self.kind,
            "url": self.url,
            "query": self.query,
            "category": self.category,
            "limit": self.limit,
            "params": self.params,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha1(encoded.encode("utf-8")).hexdigest()[:16]


@dataclass
class Article:
    source: str
    source_category: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    raw_id: str | None = None
    source_key: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def fingerprint(self) -> str:
        return self.raw_id or self.url or self.title


@dataclass
class AIInsight:
    summary: str = ""
    opportunity: str = ""
    target_user: str = ""
    pain_point: str = ""
    monetization: str = ""
    content_angle: str = ""
    validation_plan: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    dimension_scores: dict[str, float] = field(default_factory=dict)
    score_delta: float = 0.0
    confidence_delta: float = 0.0
    model: str = ""
    raw_response: str = ""


@dataclass
class OpportunityScore:
    total: float
    domain: str
    confidence: float
    reasons: list[str]
    matched_keywords: list[str]
    dimension_scores: dict[str, float] = field(default_factory=dict)
    risk_penalty: float = 0.0
    recommendation: str = "archive"
    next_action: str = "Archive and revisit if this topic appears again."
    topic_key: str = ""
    source_weight: float = 1.0
    analysis_mode: str = "rules"
    ai_insight: AIInsight | None = None
    ai_error: str = ""


@dataclass
class IdeaCard:
    article_url: str
    title: str
    domain: str
    score: float
    target_user: str
    pain_point: str
    product_idea: str
    monetization: str
    mvp_steps: list[str]
    content_angle: str
    validation_plan: list[str]
    risks: list[str]
    recommendation: str = "validate"
    next_action: str = ""
    topic_key: str = ""
    source_key: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SourceRunSummary:
    source_key: str
    name: str
    kind: str
    category: str
    status: str
    fetched_count: int
    new_count: int
    topic_count: int
    duration_ms: int
    preview: str = ""
    error: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}
