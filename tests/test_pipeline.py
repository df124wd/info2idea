import unittest

from info2idea.pipeline import run_pipeline
from info2idea.storage import connect, list_idea_cards, list_opportunity_topics, stats


class PipelineTests(unittest.TestCase):
    def test_run_pipeline_with_sample_feed(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            from pathlib import Path

            db_path = Path(temp_dir) / "info2idea.db"
            result = run_pipeline("config/sample_sources.json", db_path, min_score=10)

            self.assertEqual(result.fetched, 3)
            self.assertEqual(result.inserted_articles, 3)
            self.assertGreaterEqual(result.inserted_ideas, 1)
            self.assertEqual(result.failed_sources, {})

            connection = connect(db_path)
            try:
                self.assertEqual(stats(connection)["articles"], 3)
                self.assertEqual(stats(connection)["topics"], 3)
                ideas = list_idea_cards(connection)
                self.assertTrue(ideas)
                self.assertIn("product_idea", ideas[0])
                topics = list_opportunity_topics(connection)
                self.assertTrue(topics)
                self.assertIn("status", topics[0])
            finally:
                connection.close()
