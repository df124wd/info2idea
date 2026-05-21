from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .inbox import deep_dive_article
from .pipeline import run_pipeline
from .storage import (
    connect,
    list_articles,
    list_idea_cards,
    list_inbox_signals,
    list_opportunity_topics,
    list_signal_feedback,
    list_source_quality,
    list_source_runs,
    list_source_status,
    list_today_high_value_signals,
    stats,
    update_signal_feedback,
)


WEB_DIR = Path(__file__).with_name("web")


class DashboardHandler(BaseHTTPRequestHandler):
    db_path = Path("data/info2idea.db")
    sources_path = Path("config/sources.json")

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path == "/api/stats":
            self._json_response(_with_connection(self.db_path, stats))
            return
        if parsed.path == "/api/ideas":
            limit = _limit(parsed.query, default=50)
            status = _status(parsed.query)
            self._json_response(_with_connection(self.db_path, lambda connection: list_idea_cards(connection, limit, status)))
            return
        if parsed.path == "/api/articles":
            limit = _limit(parsed.query, default=100)
            status = _status(parsed.query)
            self._json_response(_with_connection(self.db_path, lambda connection: list_articles(connection, limit, status)))
            return
        if parsed.path == "/api/inbox":
            limit = _limit(parsed.query, default=50)
            inbox_status = parse_qs(parsed.query).get("inbox_status", [""])[0].strip() or None
            domain = parse_qs(parsed.query).get("domain", [""])[0].strip() or None
            minimum_score = _optional_float_param(parsed.query, "min_score")
            self._json_response(
                _with_connection(
                    self.db_path,
                    lambda connection: list_inbox_signals(connection, limit, inbox_status, domain, minimum_score),
                )
            )
            return
        feedback_match = re.fullmatch(r"/api/signals/(\d+)/feedback", parsed.path)
        if feedback_match:
            article_id = int(feedback_match.group(1))
            limit = _limit(parsed.query, default=20)
            self._json_response(_with_connection(self.db_path, lambda connection: list_signal_feedback(connection, article_id, limit)))
            return
        if parsed.path == "/api/topics":
            limit = _limit(parsed.query, default=50)
            status = _status(parsed.query)
            self._json_response(_with_connection(self.db_path, lambda connection: list_opportunity_topics(connection, limit, status)))
            return
        if parsed.path == "/api/sources":
            limit = _limit(parsed.query, default=100)
            status = _status(parsed.query)
            self._json_response(_with_connection(self.db_path, lambda connection: list_source_status(connection, limit, status)))
            return
        if parsed.path == "/api/source-quality":
            limit = _limit(parsed.query, default=100)
            self._json_response(_with_connection(self.db_path, lambda connection: list_source_quality(connection, limit)))
            return
        if parsed.path == "/api/source-runs":
            limit = _limit(parsed.query, default=100)
            source_key = parse_qs(parsed.query).get("source_key", [""])[0].strip() or None
            self._json_response(_with_connection(self.db_path, lambda connection: list_source_runs(connection, limit, source_key)))
            return
        if parsed.path == "/api/today":
            limit = _limit(parsed.query, default=20)
            minimum_score = _float_param(parsed.query, "min_score", 50.0)
            self._json_response(_with_connection(self.db_path, lambda connection: list_today_high_value_signals(connection, limit, minimum_score)))
            return
        if parsed.path in {"/", "/index.html"}:
            self._serve_file(WEB_DIR / "index.html")
            return
        self._serve_file(WEB_DIR / parsed.path.lstrip("/"))

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            result = run_pipeline(self.sources_path, self.db_path)
            self._json_response(
                {
                    "fetched": result.fetched,
                    "inserted_articles": result.inserted_articles,
                    "inserted_ideas": result.inserted_ideas,
                    "inserted_topics": result.inserted_topics,
                    "source_runs": result.source_runs,
                    "ai_analyzed": result.ai_analyzed,
                    "failed_sources": result.failed_sources or {},
                }
            )
            return
        feedback_match = re.fullmatch(r"/api/signals/(\d+)/feedback", parsed.path)
        if feedback_match:
            article_id = int(feedback_match.group(1))
            payload = self._read_json_body()
            action = str(payload.get("action", "")).strip()
            note = str(payload.get("note", "")).strip()
            try:
                updated = _with_connection(self.db_path, lambda connection: _update_feedback(connection, article_id, action, note))
            except ValueError as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if not updated:
                self.send_error(HTTPStatus.NOT_FOUND, "Signal not found")
                return
            self._json_response(updated)
            return
        deep_dive_match = re.fullmatch(r"/api/signals/(\d+)/deep-dive", parsed.path)
        if deep_dive_match:
            article_id = int(deep_dive_match.group(1))
            updated = _with_connection(self.db_path, lambda connection: _deep_dive(connection, article_id))
            if not updated:
                self.send_error(HTTPStatus.NOT_FOUND, "Signal not found")
                return
            self._json_response(updated)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json_response(self, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        if not body.strip():
            return {}
        parsed = json.loads(body)
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed


def serve(host: str = "127.0.0.1", port: int = 8765, db_path: str = "data/info2idea.db", sources_path: str = "config/sources.json") -> None:
    handler = DashboardHandler
    handler.db_path = Path(db_path)
    handler.sources_path = Path(sources_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Info2Idea dashboard: http://{host}:{port}")
    server.serve_forever()


def _with_connection(db_path: Path, callback):
    connection = connect(db_path)
    try:
        result = callback(connection)
        connection.commit()
        return result
    finally:
        connection.close()


def _update_feedback(connection, article_id: int, action: str, note: str) -> dict | None:
    return update_signal_feedback(connection, article_id, action, note)


def _deep_dive(connection, article_id: int) -> dict | None:
    return deep_dive_article(connection, article_id)


def _limit(query: str, default: int) -> int:
    raw = parse_qs(query).get("limit", [str(default)])[0]
    try:
        return max(1, min(500, int(raw)))
    except ValueError:
        return default


def _status(query: str) -> str | None:
    raw = parse_qs(query).get("status", [""])[0].strip()
    return raw or None


def _float_param(query: str, name: str, default: float) -> float:
    raw = parse_qs(query).get(name, [str(default)])[0]
    try:
        return float(raw)
    except ValueError:
        return default


def _optional_float_param(query: str, name: str) -> float | None:
    raw = parse_qs(query).get(name, [""])[0].strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
