from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    category: str = "general"
    weight: float = 1.0
    kind: str = "rss"
    enabled: bool = True
    query: str = ""
    limit: int = 20
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedSource":
        return cls(
            name=str(data["name"]).strip(),
            url=str(data.get("url", "")).strip(),
            category=str(data.get("category", "general")).strip() or "general",
            weight=float(data.get("weight", 1.0)),
            kind=str(data.get("kind", data.get("type", "rss"))).strip() or "rss",
            enabled=bool(data.get("enabled", True)),
            query=str(data.get("query", "")).strip(),
            limit=int(data.get("limit", 20)),
            params=dict(data.get("params", {})),
        )


@dataclass
class Article:
    source: str
    source_category: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    raw_id: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def fingerprint(self) -> str:
        return self.raw_id or self.url or self.title


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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
