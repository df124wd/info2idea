from __future__ import annotations

from .models import Article, IdeaCard, OpportunityScore


DOMAIN_PLAYBOOKS = {
    "AI tools": {
        "target_user": "Small teams, indie makers, and student builders who need useful automation without hiring a specialist.",
        "product": "a lightweight AI workflow tool that turns the specific workflow in this article into a repeatable checklist, agent, or dashboard",
        "monetization": "Start with a free demo, then charge $9-19/month for saved workflows, exports, or team usage.",
        "content": "Publish a teardown: what changed, who feels the pain, and how to automate one small piece today.",
    },
    "Content business": {
        "target_user": "Creators, students, and niche operators who need repeatable content systems more than generic inspiration.",
        "product": "a content kit with data sources, scripts, templates, prompts, and a weekly publishing workflow",
        "monetization": "Sell a $19-49 digital pack first; later add a paid community, cohort, or done-for-you setup service.",
        "content": "Turn the insight into a 5-post series: trend, example, template, tool stack, and monetization proof.",
    },
    "Indie dev": {
        "target_user": "Solo developers and micro-SaaS founders looking for narrow, fast-to-ship products.",
        "product": "a tiny SaaS, browser extension, or developer utility focused on one painful repeated task",
        "monetization": "Use a simple subscription or lifetime deal; validate with preorders before polishing.",
        "content": "Write a build-in-public post explaining the problem, MVP, pricing, and first-user target list.",
    },
    "Games": {
        "target_user": "Solo game developers, modders, and small studios that buy time-saving assets and production knowledge.",
        "product": "a game asset pack, mechanic prototype, editor plugin, or production guide inspired by the trend",
        "monetization": "Sell on itch.io, Gumroad, Unity Asset Store, or as a sponsored devlog funnel.",
        "content": "Make a short devlog showing the mechanic or asset workflow from blank project to usable result.",
    },
}

DEFAULT_PLAYBOOK = {
    "target_user": "Niche operators who are already spending time or money on this problem.",
    "product": "a narrow productized tool or service that removes one repeated manual step",
    "monetization": "Validate with a paid service first, then turn the repeated work into software or templates.",
    "content": "Publish a practical teardown with a small artifact people can use immediately.",
}


def build_idea_card(article: Article, score: OpportunityScore) -> IdeaCard:
    playbook = DOMAIN_PLAYBOOKS.get(score.domain, DEFAULT_PLAYBOOK)
    insight = score.ai_insight
    subject = _subject(article.title)
    pain_point = insight.pain_point if insight and insight.pain_point else _pain_point(article, score.domain)
    product_idea = insight.opportunity if insight and insight.opportunity else f"Build {playbook['product']} for the '{subject}' opportunity."
    validation_plan = insight.validation_plan if insight and insight.validation_plan else [
        "Check search and community demand with HN, Reddit, Product Hunt, GitHub, YouTube, and keyword suggestions.",
        "Find 3 paid alternatives or adjacent products; if none exist, validate willingness to pay before coding more.",
        "Track replies, clicks, email signups, and paid intent in a simple spreadsheet.",
    ]
    risks = insight.risks if insight and insight.risks else [
        "The article may describe hype rather than a painful repeated problem.",
        "The buyer might be too broad; narrow the first version to one niche and one workflow.",
        "Distribution can be harder than building; reserve time for posts, DMs, and demos.",
    ]

    return IdeaCard(
        article_url=article.url,
        title=article.title,
        domain=score.domain,
        score=score.total,
        target_user=insight.target_user if insight and insight.target_user else playbook["target_user"],
        pain_point=pain_point,
        product_idea=product_idea,
        monetization=insight.monetization if insight and insight.monetization else playbook["monetization"],
        mvp_steps=[
            "Collect 10 concrete examples from the same niche and summarize the repeated workflow.",
            "Create a landing page or README with the promise, target user, screenshots/mockups, and pricing hypothesis.",
            "Ship the smallest artifact in 3-5 days: script, template, dashboard, extension, or concierge service.",
            "DM or post to 20 relevant users and ask for a paid pilot, preorder, or call.",
        ],
        content_angle=insight.content_angle if insight and insight.content_angle else playbook["content"],
        validation_plan=validation_plan,
        risks=risks,
        recommendation=score.recommendation,
        next_action=score.next_action,
        topic_key=score.topic_key,
        source_key=article.source_key,
    )


def _subject(title: str) -> str:
    title = title.strip()
    if len(title) <= 90:
        return title
    return f"{title[:87].rstrip()}..."


def _pain_point(article: Article, domain: str) -> str:
    summary = article.summary.strip()
    if summary:
        return f"The signal suggests a repeated pain in {domain.lower()}: {summary[:220]}"
    return f"The signal suggests people in {domain.lower()} may need a faster, cheaper, or more repeatable way to respond to this trend."
