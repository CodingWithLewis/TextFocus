"""
Web content aggregator for Quick Cuts.
Fetches news/articles related to a query from public sources.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional, Iterable

import requests
import feedparser

DEFAULT_SOURCES = ["news", "hn"]


def _isoformat_from_struct(time_struct) -> str:
    try:
        if not time_struct:
            return ""
        dt = datetime(*time_struct[:6])
        return dt.isoformat()
    except Exception:
        return ""


def _fetch_google_news(query: str, limit: int, session: requests.Session, logger=None) -> List[Dict]:
    items = []
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
    items = []
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
    items = []
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
                "title": title,
                "url": url_field,
                "snippet": hit.get("_highlightResult", {}).get("title", {}).get("value", "") or title,
                "published_at": created_at.replace("Z", "+00:00") if created_at else ""
            })
    except Exception as e:
        if logger:
            logger.warning(f"Hacker News fetch failed: {e}")
    return items


def aggregate_content(query: str, limit: int = 10, sources: Optional[Iterable[str]] = None, logger=None) -> List[Dict]:
    """
    Aggregate content related to a query from selected sources.
    
    Args:
        query: Search keyword or phrase
        limit: Max items per source
        sources: List of source groups: ["news", "hn"]
        logger: Optional logger
        
    Returns:
        List of items with source, title, url, snippet, published_at
    """
    if not query or not isinstance(query, str):
        return []

    sources = list(sources) if sources else DEFAULT_SOURCES
    limit = max(1, min(int(limit or 10), 50))

    headers = {"User-Agent": "QuickCutsBot/1.0"}
    items = []
    
    with requests.Session() as session:
        session.headers.update(headers)

        if "news" in sources:
            items.extend(_fetch_google_news(query, limit, session, logger=logger))
            items.extend(_fetch_bing_news(query, limit, session, logger=logger))

        if "hn" in sources:
            items.extend(_fetch_hacker_news(query, limit, session, logger=logger))

    # Deduplicate by URL
    seen = set()
    deduped = []
    for it in items:
        url = it.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(it)

    return deduped
