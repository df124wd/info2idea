import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from info2idea.feeds import fetch_source
from info2idea.models import FeedSource, SourceRunSummary
from info2idea.storage import connect, list_source_runs, list_source_status, record_source_run


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
