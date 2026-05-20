from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .pipeline import run_pipeline
from .storage import connect, list_articles, list_idea_cards, list_opportunity_topics, stats


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
            self._json_response(_with_connection(self.db_path, lambda connection: list_idea_cards(connection, limit)))
            return
        if parsed.path == "/api/articles":
            limit = _limit(parsed.query, default=100)
            status = _status(parsed.query)
            self._json_response(_with_connection(self.db_path, lambda connection: list_articles(connection, limit, status)))
            return
        if parsed.path == "/api/topics":
            limit = _limit(parsed.query, default=50)
            status = _status(parsed.query)
            self._json_response(_with_connection(self.db_path, lambda connection: list_opportunity_topics(connection, limit, status)))
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
                    "failed_sources": result.failed_sources or {},
                }
            )
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
        return callback(connection)
    finally:
        connection.close()


def _limit(query: str, default: int) -> int:
    raw = parse_qs(query).get("limit", [str(default)])[0]
    try:
        return max(1, min(500, int(raw)))
    except ValueError:
        return default


def _status(query: str) -> str | None:
    raw = parse_qs(query).get("status", [""])[0].strip()
    return raw or None
