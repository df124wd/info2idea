from pathlib import Path
import unittest

from info2idea.feeds import load_sources, parse_feed


class FeedTests(unittest.TestCase):
    def test_parse_sample_feed(self) -> None:
        source = load_sources("config/sample_sources.json")[0]
        payload = Path("config/sample_feed.xml").read_text(encoding="utf-8")

        articles = parse_feed(payload, source)

        self.assertEqual(len(articles), 3)
        self.assertTrue(articles[0].title.startswith("AI agents"))
        self.assertEqual(articles[0].source, "Local Sample Feed")
        self.assertIsNotNone(articles[0].published_at)
