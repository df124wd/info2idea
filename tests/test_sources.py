import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from info2idea.feeds import fetch_source
from info2idea.inbox import deep_dive_article
from info2idea.models import FeedSource, SourceRunSummary
from info2idea.scoring import score_article
from info2idea.storage import (
    connect,
    list_articles,
    list_inbox_signals,
    list_source_quality,
    list_source_runs,
    list_source_status,
    list_signal_feedback,
    list_today_high_value_signals,
    record_source_run,
    update_signal_feedback,
    upsert_article,
)


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
                quality = list_source_quality(connection)
                self.assertEqual(quality[0]["quality_score"], 100.0)
                self.assertEqual(quality[0]["error_rate"], 0.0)
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
                today = list_today_high_value_signals(connection, minimum_score=10)
                self.assertTrue(inserted)
                self.assertEqual(rows[0]["analysis_mode"], "rules")
                self.assertEqual(rows[0]["ai_error"], "temporary AI failure")
                self.assertEqual(len(today), 1)
            finally:
                connection.close()

    def test_inbox_feedback_and_deep_dive_workflow(self) -> None:
        from pathlib import Path

        with TemporaryDirectory() as temp_dir:
            connection = connect(Path(temp_dir) / "inbox.db")
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
                upsert_article(connection, article, score)
                connection.commit()

                inbox = list_inbox_signals(connection, minimum_score=10)
                self.assertEqual(len(inbox), 1)
                self.assertEqual(inbox[0]["inbox_status"], "new")

                updated = update_signal_feedback(connection, inbox[0]["id"], "interested", "Looks promising")
                connection.commit()
                self.assertEqual(updated["inbox_status"], "interested")
                feedback = list_signal_feedback(connection, inbox[0]["id"])
                self.assertEqual(feedback[0]["action"], "interested")

                deepened = deep_dive_article(connection, inbox[0]["id"])
                connection.commit()
                self.assertIsNotNone(deepened)
                self.assertIn(deepened["analysis_mode"], {"ai", "local_ai"})
                self.assertTrue(deepened["ai_opportunity"])
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
