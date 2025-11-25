#!/usr/bin/env python3
"""
Lightweight web content aggregator for Quick Cuts.
Fetches articles/posts related to a query from stable, publicly accessible sources
without requiring API keys.

Sources implemented:
- Google News RSS
- Bing News RSS
- Hacker News (Algolia API)

Return format (list of items):
{
  "source": str,         # e.g., "google_news", "bing_news", "hacker_news"
  "title": str,
  "url": str,
  "snippet": str,
  "published_at": str    # ISO 8601 if available, else empty string
}

Notes:
- Network operations have sane timeouts.
- Errors per-source are caught and logged via optional logger; failures do not abort aggregation.
- The implementation avoids scraping brittle HTML. RSS/APIs are preferred for reliability.
"""
from __future__ import annotations

import json
import time
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional, Iterable

import requests
import feedparser

DEFAULT_SOURCES = ["news", "hn"]  # "news" => Google & Bing RSS; "hn" => Hacker News


def _isoformat_from_struct(time_struct) -> str:
    try:
        if not time_struct:
            return ""
        # feedparser returns time.struct_time in UTC by convention
        dt = datetime(*time_struct[:6])
        return dt.isoformat()
    except Exception:
        return ""


def _fetch_google_news(query: str, limit: int, session: requests.Session, logger=None) -> List[Dict]:
    items: List[Dict] = []
    try:
        q = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:limit]:
            items.append({
                "source": "google_news",
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "snippet": entry.get("summary", "") or entry.get("title", ""),
                "published_at": _isoformat_from_struct(entry.get("published_parsed"))
            })
    except Exception as e:
        if logger:
            logger.warning(f"Google News fetch failed: {e}")
    return items


def _fetch_bing_news(query: str, limit: int, session: requests.Session, logger=None) -> List[Dict]:
    items: List[Dict] = []
    try:
        q = urllib.parse.quote_plus(query)
        url = f"https://www.bing.com/news/search?q={q}&format=rss"
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:limit]:
            items.append({
                "source": "bing_news",
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "snippet": entry.get("summary", "") or entry.get("title", ""),
                "published_at": _isoformat_from_struct(entry.get("published_parsed"))
            })
    except Exception as e:
        if logger:
            logger.warning(f"Bing News fetch failed: {e}")
    return items


def _fetch_hacker_news(query: str, limit: int, session: requests.Session, logger=None) -> List[Dict]:
    items: List[Dict] = []
    try:
        q = urllib.parse.quote_plus(query)
        url = f"https://hn.algolia.com/api/v1/search?query={q}&tags=story"
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for hit in data.get("hits", [])[:limit]:
            title = hit.get("title") or hit.get("story_title") or ""
            url_field = hit.get("url") or hit.get("story_url") or ""
            created_at = hit.get("created_at", "")
            items.append({
                "source": "hacker_news",
                "title": title or "",
                "url": url_field or "",
                "snippet": hit.get("_highlightResult", {}).get("title", {}).get("value", "") or title or "",
                "published_at": created_at.replace("Z", "+00:00") if created_at else ""
            })
    except Exception as e:
        if logger:
            logger.warning(f"Hacker News fetch failed: {e}")
    return items


def aggregate_content(query: str, limit: int = 10, sources: Optional[Iterable[str]] = None, logger=None) -> List[Dict]:
    """
    Aggregate content related to a query from selected sources.
    :param query: keyword or phrase to search
    :param limit: max items per source
    :param sources: iterable of source groups: ["news", "hn"]
    :param logger: optional logger
    :return: list of normalized items
    """
    if not query or not isinstance(query, str):
        return []

    sources = list(sources) if sources else DEFAULT_SOURCES
    limit = max(1, min(int(limit or 10), 50))

    headers = {
        "User-Agent": "QuickCutsBot/1.0 (+https://example.com)"
    }

    items: List[Dict] = []
    with requests.Session() as session:
        session.headers.update(headers)

        if "news" in sources:
            items.extend(_fetch_google_news(query, limit, session, logger=logger))
            items.extend(_fetch_bing_news(query, limit, session, logger=logger))

        if "hn" in sources:
            items.extend(_fetch_hacker_news(query, limit, session, logger=logger))

    # Deduplicate by URL, preserving order
    seen = set()
    deduped: List[Dict] = []
    for it in items:
        url = it.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(it)

    return deduped
