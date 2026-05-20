import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from info2idea.feeds import fetch_source
from info2idea.models import FeedSource, SourceRunSummary
from info2idea.scoring import score_article
from info2idea.storage import connect, list_articles, list_source_runs, list_source_status, record_source_run, upsert_article


class SourceTests(unittest.TestCase):
    def test_manual_json_source_stamps_source_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "signals.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "id": "manual-1",
                            "title": "Creators want a reusable AI video workflow",
                            "url": "manual://video-workflow",
                            "summary": "Repeated comments mention automation, templates, and paid courses.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            source = FeedSource(name="Manual", kind="manual_json", url=str(path), category="content")

            articles = fetch_source(source)

            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].source_key, source.source_key)

    def test_source_run_summary_updates_status_tables(self) -> None:
        with TemporaryDirectory() as temp_dir:
            connection = connect(Path(temp_dir) / "sources.db")
            try:
                summary = SourceRunSummary(
                    source_key="source-1",
                    name="Sample Source",
                    kind="rss",
                    category="indie_dev",
                    status="ok",
                    fetched_count=3,
                    new_count=2,
                    topic_count=1,
                    duration_ms=42,
                    preview="A\nB",
                )

                record_source_run(connection, summary)
                connection.commit()

                statuses = list_source_status(connection)
                runs = list_source_runs(connection)
                self.assertEqual(statuses[0]["last_new_count"], 2)
                self.assertEqual(statuses[0]["total_runs"], 1)
                self.assertEqual(runs[0]["duration_ms"], 42)
            finally:
                connection.close()

    def test_article_persists_analysis_fields(self) -> None:
        with TemporaryDirectory() as temp_dir:
            connection = connect(Path(temp_dir) / "analysis.db")
            try:
                article = fetch_source(
                    FeedSource(
                        name="Manual",
                        kind="manual_json",
                        url=str(_write_signal_file(Path(temp_dir))),
                        category="ai_tools",
                    )
                )[0]
                score = score_article(article)
                score.ai_error = "temporary AI failure"

                inserted = upsert_article(connection, article, score)
                connection.commit()

                rows = list_articles(connection)
                self.assertTrue(inserted)
                self.assertEqual(rows[0]["analysis_mode"], "rules")
                self.assertEqual(rows[0]["ai_error"], "temporary AI failure")
            finally:
                connection.close()


def _write_signal_file(directory: Path) -> Path:
    path = directory / "one-signal.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "manual-2",
                    "title": "Small teams want AI automation dashboards",
                    "url": "manual://ai-dashboard",
                    "summary": "Teams pay for simple tools when manual reporting is slow.",
                }
            ]
        ),
        encoding="utf-8",
    )
    return path
