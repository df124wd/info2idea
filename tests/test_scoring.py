import unittest

from info2idea.models import Article
from info2idea.scoring import score_article


class ScoringTests(unittest.TestCase):
    def test_ai_tool_signal_scores_into_focus_domain(self) -> None:
        article = Article(
            source="Sample",
            source_category="ai_tools",
            title="AI agents automate customer support workflows for small SaaS teams",
            url="https://example.com/signal",
            summary="Small teams pay for automation tools because support is slow, manual, and expensive.",
        )

        score = score_article(article)

        self.assertEqual(score.domain, "AI tools")
        self.assertGreaterEqual(score.total, 24)
        self.assertIn("automation", score.matched_keywords)
        self.assertIn("willingness_to_pay", score.dimension_scores)
        self.assertIn(score.recommendation, {"build_now", "validate_7_days", "watch", "archive"})
        self.assertTrue(score.topic_key)
