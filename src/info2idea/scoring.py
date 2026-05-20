from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha1

from .models import Article, OpportunityScore


DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "AI tools": [
        "ai",
        "agent",
        "llm",
        "model",
        "automation",
        "workflow",
        "chatbot",
        "copilot",
        "prompt",
        "open source",
    ],
    "Content business": [
        "creator",
        "content",
        "newsletter",
        "short-form",
        "video",
        "youtube",
        "tiktok",
        "course",
        "audience",
        "template",
    ],
    "Indie dev": [
        "indie",
        "solo",
        "developer",
        "micro-saas",
        "saas",
        "plugin",
        "extension",
        "api",
        "github",
        "productivity",
    ],
    "Games": [
        "game",
        "gaming",
        "steam",
        "unity",
        "unreal",
        "asset",
        "mod",
        "ugc",
        "simulator",
        "engine",
    ],
}

MONEY_KEYWORDS = [
    "pay",
    "paid",
    "pricing",
    "subscription",
    "revenue",
    "sell",
    "marketplace",
    "customer",
    "business",
    "b2b",
    "cost",
    "budget",
    "growth",
    "launch",
    "users",
]

PAIN_KEYWORDS = [
    "problem",
    "pain",
    "hard",
    "manual",
    "slow",
    "expensive",
    "complex",
    "risk",
    "compliance",
    "support",
    "ops",
    "debug",
    "learn",
    "hire",
    "shortage",
]

ACTION_KEYWORDS = [
    "template",
    "tool",
    "automation",
    "dashboard",
    "agent",
    "generator",
    "monitor",
    "library",
    "course",
    "guide",
    "service",
    "pack",
]

REACH_KEYWORDS = [
    "community",
    "reddit",
    "github",
    "discord",
    "youtube",
    "newsletter",
    "steam",
    "product hunt",
    "marketplace",
    "open source",
    "creator",
    "students",
    "developers",
]

VALIDATION_KEYWORDS = [
    "demo",
    "prototype",
    "template",
    "landing",
    "waitlist",
    "preorder",
    "beta",
    "open source",
    "extension",
    "script",
    "guide",
    "pack",
]

TREND_KEYWORDS = [
    "new",
    "launch",
    "release",
    "trend",
    "growth",
    "fastest",
    "rising",
    "breakthrough",
    "emerging",
    "latest",
]

RISK_KEYWORDS = [
    "lawsuit",
    "ban",
    "blocked",
    "copyright",
    "privacy",
    "regulation",
    "compliance",
    "api cost",
    "expensive",
    "enterprise",
    "deepfake",
]

DIMENSION_WEIGHTS = {
    "willingness_to_pay": 22,
    "pain_intensity": 18,
    "reachability": 14,
    "solo_feasibility": 14,
    "seven_day_validation": 14,
    "content_potential": 8,
    "timing": 10,
}

SOURCE_CATEGORY_HINTS = {
    "ai_tools": "AI tools",
    "content": "Content business",
    "indie_dev": "Indie dev",
    "games": "Games",
}


def score_article(article: Article) -> OpportunityScore:
    text = f"{article.title} {article.summary}".lower()
    matched = _keyword_hits(text)
    domain_counts = {
        domain: sum(1 for keyword in keywords if _contains(text, keyword))
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    hinted_domain = SOURCE_CATEGORY_HINTS.get(article.source_category)
    if hinted_domain:
        domain_counts[hinted_domain] = domain_counts.get(hinted_domain, 0) + 1

    domain, domain_hits = max(domain_counts.items(), key=lambda item: item[1])
    money_hits = sum(1 for keyword in MONEY_KEYWORDS if _contains(text, keyword))
    pain_hits = sum(1 for keyword in PAIN_KEYWORDS if _contains(text, keyword))
    action_hits = sum(1 for keyword in ACTION_KEYWORDS if _contains(text, keyword))
    recency_bonus = _recency_bonus(article)
    title_bonus = 0.4 if len(article.title.split()) <= 14 else 0.0

    reach_hits = sum(1 for keyword in REACH_KEYWORDS if _contains(text, keyword))
    validation_hits = sum(1 for keyword in VALIDATION_KEYWORDS if _contains(text, keyword))
    trend_hits = sum(1 for keyword in TREND_KEYWORDS if _contains(text, keyword))
    risk_hits = sum(1 for keyword in RISK_KEYWORDS if _contains(text, keyword))
    dimensions = {
        "willingness_to_pay": _cap_5(1.0 + 0.9 * money_hits + 0.25 * domain_hits),
        "pain_intensity": _cap_5(0.8 + 1.0 * pain_hits + 0.25 * action_hits),
        "reachability": _cap_5(0.7 + 0.8 * reach_hits + _source_reach_bonus(article)),
        "solo_feasibility": _cap_5(1.0 + 0.75 * action_hits + _domain_feasibility_bonus(domain)),
        "seven_day_validation": _cap_5(0.8 + 0.85 * validation_hits + 0.35 * action_hits),
        "content_potential": _cap_5(0.8 + 0.7 * reach_hits + 0.6 * trend_hits + _content_bonus(domain)),
        "timing": _cap_5(0.7 + 0.65 * trend_hits + recency_bonus),
    }
    risk_penalty = min(10.0, 2.5 * risk_hits)
    score = round(_weighted_score(dimensions) - risk_penalty, 2)
    score = max(0.0, min(100.0, score))
    recommendation = _recommendation(score)
    next_action = _next_action(recommendation)

    reasons = []
    if domain_hits:
        reasons.append(f"Matches your focus area: {domain}.")
    if pain_hits:
        reasons.append("Mentions a concrete pain point or workflow bottleneck.")
    if money_hits:
        reasons.append("Contains monetization or buyer-intent signals.")
    if action_hits:
        reasons.append("Suggests something a solo builder can package into a tool, template, course, or service.")
    if reach_hits:
        reasons.append("Mentions reachable communities, marketplaces, or distribution surfaces.")
    if validation_hits:
        reasons.append("Looks testable with a small demo, template, script, or content artifact.")
    if recency_bonus:
        reasons.append("Recent enough to be useful for trend spotting.")
    if risk_penalty:
        reasons.append("Contains risk signals, so it should be watched carefully before building.")
    if not reasons:
        reasons.append("Weak signal, kept for awareness but not a priority.")

    confidence = min(0.95, 0.22 + 0.05 * len(matched) + 0.08 * domain_hits + 0.05 * pain_hits + 0.04 * money_hits)
    return OpportunityScore(
        total=score,
        domain=domain,
        confidence=round(confidence, 2),
        reasons=reasons,
        matched_keywords=matched[:20],
        dimension_scores={key: round(value, 2) for key, value in dimensions.items()},
        risk_penalty=round(risk_penalty, 2),
        recommendation=recommendation,
        next_action=next_action,
        topic_key=_topic_key(article, domain, matched),
    )


def apply_source_weight(score: OpportunityScore, weight: float) -> OpportunityScore:
    score.source_weight = weight
    score.total = round(max(0.0, min(100.0, score.total * weight)), 2)
    score.recommendation = _recommendation(score.total)
    score.next_action = _next_action(score.recommendation)
    return score


def _keyword_hits(text: str) -> list[str]:
    counter: Counter[str] = Counter()
    for keywords in DOMAIN_KEYWORDS.values():
        for keyword in keywords:
            if _contains(text, keyword):
                counter[keyword] += 1
    for keyword in MONEY_KEYWORDS + PAIN_KEYWORDS + ACTION_KEYWORDS + REACH_KEYWORDS + VALIDATION_KEYWORDS + TREND_KEYWORDS:
        if _contains(text, keyword):
            counter[keyword] += 1
    return [keyword for keyword, _ in counter.most_common()]


def _contains(text: str, keyword: str) -> bool:
    if " " in keyword or "-" in keyword:
        return keyword in text
    return bool(re.search(rf"\b{re.escape(keyword)}\b", text))


def _recency_bonus(article: Article) -> float:
    if not article.published_at:
        return 0.8
    now = datetime.now(timezone.utc)
    age_days = max(0, (now - article.published_at).total_seconds() / 86400)
    if age_days <= 2:
        return 2.0
    if age_days <= 7:
        return 1.2
    if age_days <= 30:
        return 0.5
    return 0.0


def _cap_5(value: float) -> float:
    return max(0.0, min(5.0, value))


def _weighted_score(dimensions: dict[str, float]) -> float:
    total = 0.0
    for key, weight in DIMENSION_WEIGHTS.items():
        total += (dimensions[key] / 5.0) * weight
    return total


def _source_reach_bonus(article: Article) -> float:
    if article.source_category in {"indie_dev", "games", "content"}:
        return 0.6
    if article.source_category == "ai_tools":
        return 0.4
    return 0.0


def _domain_feasibility_bonus(domain: str) -> float:
    if domain in {"AI tools", "Content business", "Indie dev"}:
        return 0.7
    if domain == "Games":
        return 0.35
    return 0.2


def _content_bonus(domain: str) -> float:
    if domain in {"Content business", "AI tools", "Games"}:
        return 0.6
    return 0.3


def _recommendation(score: float) -> str:
    if score >= 80:
        return "build_now"
    if score >= 65:
        return "validate_7_days"
    if score >= 50:
        return "watch"
    return "archive"


def _next_action(recommendation: str) -> str:
    if recommendation == "build_now":
        return "Draft a one-page MVP spec today and find 10 target users before writing production code."
    if recommendation == "validate_7_days":
        return "Run a 7-day validation: landing page, small demo, content post, and 20 targeted messages."
    if recommendation == "watch":
        return "Keep this in the watchlist and look for repeated signals, paid competitors, or community complaints."
    return "Archive the signal, but revive it automatically if this topic appears again with stronger evidence."


def _topic_key(article: Article, domain: str, matched: list[str]) -> str:
    tokens = _topic_tokens(article, matched)
    basis = "|".join([domain, *tokens[:6]]) or article.title.lower()
    return sha1(basis.encode("utf-8")).hexdigest()[:16]


def _topic_tokens(article: Article, matched: list[str]) -> list[str]:
    text = f"{article.title} {article.summary}".lower()
    words = re.findall(r"[a-z0-9][a-z0-9-]{2,}", text)
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "are",
        "new",
        "how",
        "into",
        "use",
        "using",
        "tools",
    }
    ranked = [word for word in words if word not in stop]
    return list(dict.fromkeys([*matched, *ranked]))
