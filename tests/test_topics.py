import unittest

from info2idea.models import Article
from info2idea.scoring import score_article
from info2idea.storage import connect, list_opportunity_topics, upsert_opportunity_topic


class TopicTests(unittest.TestCase):
    def test_repeated_weak_signal_stays_available_in_topic_pool(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as temp_dir:
            connection = connect(Path(temp_dir) / "topics.db")
            try:
                article = Article(
                    source="Manual",
                    source_category="content",
                    title="Students keep asking how to make a first AI side project",
                    url="manual://signal/1",
                    summary="Repeated comments suggest tutorial demand, but paid intent is still unclear.",
                )
                score = score_article(article)

                upsert_opportunity_topic(connection, article, score)
                topics = list_opportunity_topics(connection)

                self.assertEqual(len(topics), 1)
                self.assertEqual(topics[0]["signal_count"], 1)
                self.assertIn(topics[0]["status"], {"watch", "archive", "validate_7_days", "build_now"})
            finally:
                connection.close()
