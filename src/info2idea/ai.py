from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .models import AIInsight, Article, OpportunityScore
from .scoring import DIMENSION_WEIGHTS, score_article


DEFAULT_AI_MODEL = "gpt-4o-mini"
AI_SCORE_THRESHOLD = 50.0


def ai_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def maybe_enhance_score(article: Article, score: OpportunityScore, threshold: float = AI_SCORE_THRESHOLD) -> OpportunityScore:
    if not ai_enabled():
        return score
    if score.total < threshold:
        return score
    return enhance_score_with_ai(article, score)


def enhance_score_with_ai(article: Article, score: OpportunityScore) -> OpportunityScore:
    model = os.getenv("INFO2IDEA_AI_MODEL", DEFAULT_AI_MODEL)
    try:
        insight = analyze_article_with_openai(article, score, model=model)
    except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        score.ai_error = str(exc)
        return score
    return merge_ai_insight(score, insight)


def analyze_article_with_openai(article: Article, score: OpportunityScore, model: str = DEFAULT_AI_MODEL) -> AIInsight:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Info2Idea's opportunity analyst. Evaluate public signals for a student solo builder. "
                    "Return strict JSON only. Be skeptical about monetization and favor ideas testable within 7 days."
                ),
            },
            {
                "role": "user",
                "content": _analysis_prompt(article, score),
            },
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return _insight_from_json(parsed, model=model, raw_response=content)


def merge_ai_insight(score: OpportunityScore, insight: AIInsight) -> OpportunityScore:
    score.ai_insight = insight
    score.analysis_mode = "ai"
    score.ai_error = ""
    if insight.reasons:
        score.reasons = _dedupe([*insight.reasons, *score.reasons])[:8]
    if insight.dimension_scores:
        merged = dict(score.dimension_scores)
        for key in DIMENSION_WEIGHTS:
            if key in insight.dimension_scores:
                merged[key] = _clamp(insight.dimension_scores[key], 0.0, 5.0)
        score.dimension_scores = {key: round(value, 2) for key, value in merged.items()}
        score.total = round(_weighted_score(score.dimension_scores) - score.risk_penalty + insight.score_delta, 2)
    else:
        score.total = round(score.total + insight.score_delta, 2)
    score.total = round(_clamp(score.total, 0.0, 100.0), 2)
    score.confidence = round(_clamp(score.confidence + insight.confidence_delta, 0.0, 0.98), 2)
    score.recommendation = _recommendation(score.total)
    score.next_action = _next_action(score.recommendation)
    return score


def local_ai_like_insight(article: Article, score: OpportunityScore) -> AIInsight:
    baseline = score_article(article)
    return AIInsight(
        summary=_truncate(article.summary or article.title, 220),
        opportunity=f"Package the signal into a narrow {baseline.domain.lower()} experiment for one reachable niche.",
        target_user=_target_user(baseline.domain),
        pain_point=_pain_point(article, baseline.domain),
        monetization=_monetization(baseline.domain),
        content_angle=_content_angle(article, baseline.domain),
        validation_plan=[
            "Find 10 similar posts, issues, or comments from the same niche.",
            "Ship one small artifact: checklist, script, template, or landing page.",
            "Ask 20 target users whether they would pay or trade time for it.",
        ],
        risks=[
            "The signal may be hype without repeated buyer pain.",
            "Distribution may be harder than the MVP build.",
        ],
        reasons=baseline.reasons,
        dimension_scores=baseline.dimension_scores,
        score_delta=0.0,
        confidence_delta=0.0,
        model="local-rules",
    )


def _analysis_prompt(article: Article, score: OpportunityScore) -> str:
    return json.dumps(
        {
            "task": "Analyze this signal and improve the opportunity score.",
            "builder_context": {
                "focus_domains": ["AI tools", "content business", "indie dev", "games"],
                "monetization": ["software subscription", "digital product/course", "content traffic", "service", "automation tool"],
                "constraints": ["college student", "2-3 hours per day", "low budget", "can code"],
            },
            "article": {
                "source": article.source,
                "category": article.source_category,
                "title": article.title,
                "url": article.url,
                "summary": article.summary,
            },
            "rule_score": {
                "total": score.total,
                "domain": score.domain,
                "confidence": score.confidence,
                "dimension_scores": score.dimension_scores,
                "risk_penalty": score.risk_penalty,
                "recommendation": score.recommendation,
                "reasons": score.reasons,
            },
            "return_schema": {
                "summary": "one sentence",
                "opportunity": "specific product/content/service idea",
                "target_user": "narrow first buyer or audience",
                "pain_point": "concrete pain or demand",
                "monetization": "low-budget path to revenue",
                "content_angle": "one content angle for distribution",
                "validation_plan": ["3 short steps"],
                "risks": ["2-3 risks"],
                "reasons": ["2-5 score reasons"],
                "dimension_scores": {
                    "willingness_to_pay": "0-5",
                    "pain_intensity": "0-5",
                    "reachability": "0-5",
                    "solo_feasibility": "0-5",
                    "seven_day_validation": "0-5",
                    "content_potential": "0-5",
                    "timing": "0-5",
                },
                "score_delta": "-10 to 10",
                "confidence_delta": "-0.2 to 0.2",
            },
        },
        ensure_ascii=False,
    )


def _insight_from_json(data: dict, model: str, raw_response: str) -> AIInsight:
    return AIInsight(
        summary=str(data.get("summary", "")).strip(),
        opportunity=str(data.get("opportunity", "")).strip(),
        target_user=str(data.get("target_user", "")).strip(),
        pain_point=str(data.get("pain_point", "")).strip(),
        monetization=str(data.get("monetization", "")).strip(),
        content_angle=str(data.get("content_angle", "")).strip(),
        validation_plan=[str(item).strip() for item in data.get("validation_plan", []) if str(item).strip()],
        risks=[str(item).strip() for item in data.get("risks", []) if str(item).strip()],
        reasons=[str(item).strip() for item in data.get("reasons", []) if str(item).strip()],
        dimension_scores={key: float(value) for key, value in dict(data.get("dimension_scores", {})).items()},
        score_delta=_clamp(float(data.get("score_delta", 0.0)), -10.0, 10.0),
        confidence_delta=_clamp(float(data.get("confidence_delta", 0.0)), -0.2, 0.2),
        model=model,
        raw_response=raw_response,
    )


def _weighted_score(dimensions: dict[str, float]) -> float:
    total = 0.0
    for key, weight in DIMENSION_WEIGHTS.items():
        total += (_clamp(dimensions.get(key, 0.0), 0.0, 5.0) / 5.0) * weight
    return total


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


def _target_user(domain: str) -> str:
    if domain == "AI tools":
        return "Solo operators and small teams already paying with time for repetitive AI workflows."
    if domain == "Content business":
        return "Creators and students who want a repeatable publishing or research workflow."
    if domain == "Games":
        return "Solo game makers and small studios looking for time-saving assets or production shortcuts."
    return "Indie builders and micro-SaaS operators with one repeated workflow problem."


def _pain_point(article: Article, domain: str) -> str:
    text = article.summary or article.title
    return f"{domain} signal: {_truncate(text, 180)}"


def _monetization(domain: str) -> str:
    if domain == "Content business":
        return "Start with a $19-49 template, research pack, or mini-course before building software."
    if domain == "Games":
        return "Sell a small asset pack, prototype, plugin, or devlog-backed guide."
    return "Validate with a paid setup service or $9-19/month lightweight subscription."


def _content_angle(article: Article, domain: str) -> str:
    return f"Publish a practical teardown for {domain.lower()}: what changed, who hurts, and one small fix."


def _dedupe(items: list[str]) -> list[str]:
    output = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _truncate(value: str, limit: int) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."
