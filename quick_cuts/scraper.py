"""
Web content aggregator and image downloader for Quick Cuts.
Fetches news/articles and downloads images related to a query.
"""

from __future__ import annotations

import urllib.parse
import re
import os
import logging
from datetime import datetime
from pathlib import Path
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


def _get_bing_image_urls(query: str, limit: int) -> List[str]:
    """Fetch image URLs from Bing image search."""
    urls = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Request more than needed to account for failures
        search_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(query)}&first=0&count={limit * 2}"
        resp = requests.get(search_url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        # Extract image URLs from response using regex
        # Bing returns URLs in murl="..." format
        pattern = r'murl&quot;:&quot;(https?://[^&]+?)&quot;'
        matches = re.findall(pattern, resp.text)
        
        for url in matches:
            if url not in urls:
                urls.append(url)
            if len(urls) >= limit * 2:
                break
                
    except Exception:
        pass
    
    return urls


def _download_image(url: str, filepath: Path, timeout: int = 10) -> bool:
    """Download a single image. Returns True on success."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        resp.raise_for_status()
        
        # Check content type
        content_type = resp.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return False
        
        # Check minimum size (skip tiny images)
        content = resp.content
        if len(content) < 1000:
            return False
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        return True
    except Exception:
        return False


def fetch_images(query: str, limit: int = 10, output_dir: str = "input", logger=None) -> List[str]:
    """
    Download images related to a search query using Bing image search.
    
    Args:
        query: Search term
        limit: Max number of images to download
        output_dir: Directory to save images (default: input/)
        logger: Optional logger
        
    Returns:
        List of saved file paths
    """
    import json
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create safe query name for filenames
    safe_query = re.sub(r'[^\w\s-]', '', query)[:20].strip().replace(' ', '_')
    
    saved_files = []
    url_mapping = {}  # Exact mapping: filename -> source URL
    
    # Get image URLs from Bing
    urls = _get_bing_image_urls(query, limit)
    
    if not urls:
        if logger:
            logger.warning("No image URLs found")
        return saved_files
    
    # Download images one by one, tracking exact URL->filename mapping
    count = 0
    for url in urls:
        if count >= limit:
            break
        
        # Determine extension from URL
        ext = '.jpg'
        url_lower = url.lower()
        if '.png' in url_lower:
            ext = '.png'
        elif '.gif' in url_lower:
            ext = '.gif'
        elif '.webp' in url_lower:
            ext = '.webp'
        
        filename = f"{safe_query}_{count + 1:02d}{ext}"
        filepath = output_path / filename
        
        if _download_image(url, filepath):
            saved_files.append(str(filepath))
            url_mapping[filename] = url
            count += 1
    
    # Save copyright attributions with correct mapping
    if url_mapping:
        attr_dir = Path("copyright_attributions") / safe_query
        attr_dir.mkdir(parents=True, exist_ok=True)
        attr_file = attr_dir / f"{safe_query}.json"
        
        with open(attr_file, 'w') as f:
            json.dump(url_mapping, f, indent=2)
    
    return saved_files
