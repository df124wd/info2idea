from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

from .models import Article, FeedSource


USER_AGENT = "info2idea/0.1 (+local research tool)"
TAG_RE = re.compile(r"<[^>]+>")


def load_sources(path: str | Path) -> list[FeedSource]:
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as handle:
        raw_sources = json.load(handle)
    return [FeedSource.from_dict(item) for item in raw_sources]


def fetch_source(source: FeedSource, timeout: int = 20) -> list[Article]:
    if source.kind == "github_search":
        return _fetch_github_search(source, timeout)
    if source.kind == "github_issues":
        return _fetch_github_issues(source, timeout)
    if source.kind == "google_news":
        return _fetch_google_news(source, timeout)
    if source.kind == "hn_search":
        return _fetch_hn_search(source, timeout)
    if source.kind == "manual_json":
        return _fetch_manual_json(source)
    if source.kind == "reddit_rss":
        return _fetch_reddit_rss(source, timeout)
    if source.kind == "reddit_search":
        return _fetch_reddit_search(source, timeout)
    payload = _read_source_payload(source.url, timeout)
    return _stamp_source(parse_feed(payload, source), source)


def parse_feed(payload: bytes | str, source: FeedSource) -> list[Article]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    root = ET.fromstring(payload)
    if _local_name(root.tag) == "feed":
        return _parse_atom(root, source)
    return _parse_rss(root, source)


def _read_source_payload(url: str, timeout: int) -> bytes:
    if url.startswith(("http://", "https://")):
        return _read_http(url, timeout)
    return Path(url).read_bytes()


def _fetch_github_search(source: FeedSource, timeout: int) -> list[Article]:
    query = source.query or source.params.get("q", "")
    if not query:
        return []
    limit = max(1, min(source.limit, 50))
    url = "https://api.github.com/search/repositories?" + _encode_query(
        {
            "q": query,
            "sort": source.params.get("sort", "updated"),
            "order": source.params.get("order", "desc"),
            "per_page": str(limit),
        }
    )
    payload = json.loads(_read_http(url, timeout).decode("utf-8"))
    articles = []
    for item in payload.get("items", []):
        name = item.get("full_name") or item.get("name")
        html_url = item.get("html_url")
        if not name or not html_url:
            continue
        summary_parts = [
            item.get("description") or "",
            f"Stars: {item.get('stargazers_count', 0)}",
            f"Language: {item.get('language') or 'unknown'}",
            f"Open issues: {item.get('open_issues_count', 0)}",
        ]
        articles.append(
            Article(
                source=source.name,
                source_category=source.category,
                title=f"GitHub repo: {name}",
                url=html_url,
                summary=" | ".join(part for part in summary_parts if part),
                published_at=_parse_date(item.get("pushed_at") or item.get("updated_at") or ""),
                raw_id=str(item.get("id") or html_url),
                source_key=source.source_key,
            )
        )
    return articles


def _fetch_github_issues(source: FeedSource, timeout: int) -> list[Article]:
    query = source.query or source.params.get("q", "")
    if not query:
        return []
    limit = max(1, min(source.limit, 50))
    url = "https://api.github.com/search/issues?" + _encode_query(
        {
            "q": query,
            "sort": source.params.get("sort", "updated"),
            "order": source.params.get("order", "desc"),
            "per_page": str(limit),
        }
    )
    payload = json.loads(_read_http(url, timeout).decode("utf-8"))
    articles = []
    for item in payload.get("items", []):
        title = item.get("title") or ""
        html_url = item.get("html_url") or ""
        if not title or not html_url:
            continue
        repo_url = item.get("repository_url", "").rsplit("/", 1)[-1]
        labels = ", ".join(label.get("name", "") for label in item.get("labels", []) if label.get("name"))
        summary_parts = [
            item.get("body") or "",
            f"State: {item.get('state', 'unknown')}",
            f"Comments: {item.get('comments', 0)}",
            f"Repo: {repo_url}",
            f"Labels: {labels}" if labels else "",
        ]
        articles.append(
            Article(
                source=source.name,
                source_category=source.category,
                title=f"GitHub issue: {title}",
                url=html_url,
                summary=_truncate(" | ".join(part for part in summary_parts if part), 900),
                published_at=_parse_date(item.get("updated_at") or item.get("created_at") or ""),
                raw_id=str(item.get("id") or html_url),
                source_key=source.source_key,
            )
        )
    return articles


def _fetch_reddit_rss(source: FeedSource, timeout: int) -> list[Article]:
    url = source.url
    if not url and source.query:
        subreddit = source.query.strip().strip("/")
        url = f"https://www.reddit.com/r/{subreddit}/.rss"
    if not url:
        return []
    payload = _read_source_payload(url, timeout)
    return _stamp_source(parse_feed(payload, source), source)


def _fetch_reddit_search(source: FeedSource, timeout: int) -> list[Article]:
    query = source.query or source.params.get("q", "")
    if not query:
        return []
    subreddit = str(source.params.get("subreddit", "")).strip().strip("/")
    sort = str(source.params.get("sort", "new"))
    time_filter = str(source.params.get("time", "week"))
    base = f"https://www.reddit.com/r/{subreddit}/search.rss" if subreddit else "https://www.reddit.com/search.rss"
    url = base + "?" + _encode_query(
        {
            "q": query,
            "restrict_sr": "1" if subreddit else "0",
            "sort": sort,
            "t": time_filter,
        }
    )
    payload = _read_source_payload(url, timeout)
    return _stamp_source(parse_feed(payload, source), source)


def _fetch_google_news(source: FeedSource, timeout: int) -> list[Article]:
    query = source.query or source.params.get("q", "")
    if not query:
        return []
    language = source.params.get("hl", "en-US")
    region = source.params.get("gl", "US")
    ceid = source.params.get("ceid", "US:en")
    url = "https://news.google.com/rss/search?" + _encode_query(
        {
            "q": query,
            "hl": language,
            "gl": region,
            "ceid": ceid,
        }
    )
    payload = _read_source_payload(url, timeout)
    articles = _stamp_source(parse_feed(payload, source), source)
    return articles[: max(1, source.limit)]


def _fetch_hn_search(source: FeedSource, timeout: int) -> list[Article]:
    query = source.query or source.params.get("query", "")
    if not query:
        return []
    tags = str(source.params.get("tags", "story"))
    numeric_filters = str(source.params.get("numericFilters", ""))
    params = {
        "query": query,
        "tags": tags,
        "hitsPerPage": str(max(1, min(source.limit, 50))),
    }
    if numeric_filters:
        params["numericFilters"] = numeric_filters
    url = "https://hn.algolia.com/api/v1/search_by_date?" + _encode_query(params)
    payload = json.loads(_read_http(url, timeout).decode("utf-8"))
    articles = []
    for item in payload.get("hits", []):
        title = item.get("title") or item.get("story_title") or ""
        item_url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}"
        if not title or not item_url:
            continue
        summary_parts = [
            f"Points: {item.get('points', 0)}",
            f"Comments: {item.get('num_comments', 0)}",
            f"Author: {item.get('author', 'unknown')}",
        ]
        articles.append(
            Article(
                source=source.name,
                source_category=source.category,
                title=f"HN: {title}",
                url=item_url,
                summary=" | ".join(summary_parts),
                published_at=_parse_date(item.get("created_at", "")),
                raw_id=str(item.get("objectID") or item_url),
                source_key=source.source_key,
            )
        )
    return articles


def _fetch_manual_json(source: FeedSource) -> list[Article]:
    path = Path(source.url)
    if not path.exists():
        return []
    raw_items = json.loads(path.read_text(encoding="utf-8"))
    articles = []
    for index, item in enumerate(raw_items):
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", f"manual://{source.name}/{index}")).strip()
        if not title:
            continue
        articles.append(
            Article(
                source=str(item.get("source", source.name)),
                source_category=str(item.get("category", source.category)),
                title=title,
                url=url,
                summary=str(item.get("summary", "")).strip(),
                published_at=_parse_date(str(item.get("published_at", ""))),
                raw_id=str(item.get("id", url)),
                source_key=source.source_key,
            )
        )
    return articles


def _read_http(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _encode_query(params: dict[str, str]) -> str:
    from urllib.parse import urlencode

    return urlencode(params)


def _parse_rss(root: ET.Element, source: FeedSource) -> list[Article]:
    items = root.findall(".//item")
    articles: list[Article] = []
    for item in items:
        title = _clean(_child_text(item, "title"))
        url = _clean(_child_text(item, "link"))
        summary = _clean(_child_text(item, "description") or _child_text(item, "encoded"))
        raw_id = _clean(_child_text(item, "guid")) or url
        published_at = _parse_date(_child_text(item, "pubDate") or _child_text(item, "date"))
        if title and url:
            articles.append(
                Article(
                    source=source.name,
                    source_category=source.category,
                    title=title,
                    url=url,
                    summary=summary,
                    published_at=published_at,
                    raw_id=raw_id,
                )
            )
    return articles


def _parse_atom(root: ET.Element, source: FeedSource) -> list[Article]:
    articles: list[Article] = []
    for entry in _children_by_local_name(root, "entry"):
        title = _clean(_child_text(entry, "title"))
        url = _atom_link(entry)
        summary = _clean(_child_text(entry, "summary") or _child_text(entry, "content"))
        raw_id = _clean(_child_text(entry, "id")) or url
        published_at = _parse_date(_child_text(entry, "published") or _child_text(entry, "updated"))
        if title and url:
            articles.append(
                Article(
                    source=source.name,
                    source_category=source.category,
                    title=title,
                    url=url,
                    summary=summary,
                    published_at=published_at,
                    raw_id=raw_id,
                )
            )
    return articles


def _child_text(parent: ET.Element, name: str) -> str:
    for child in list(parent):
        if _local_name(child.tag) == name:
            return "".join(child.itertext()).strip()
    return ""


def _children_by_local_name(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local_name(child.tag) == name]


def _atom_link(entry: ET.Element) -> str:
    fallback = ""
    for child in list(entry):
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "alternate")
        if rel == "alternate" and href:
            return href
        if href and not fallback:
            fallback = href
    return fallback


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _clean(value: str) -> str:
    value = TAG_RE.sub(" ", value or "")
    return " ".join(unescape(value).split())


def _stamp_source(articles: list[Article], source: FeedSource) -> list[Article]:
    for article in articles:
        article.source_key = source.source_key
    return articles


def _truncate(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
