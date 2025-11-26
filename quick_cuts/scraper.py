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


def _get_duckduckgo_image_urls(query: str, limit: int, offset: int = 0, exclude_urls: set = None) -> List[str]:
    """Fetch image URLs from DuckDuckGo Images with pagination."""
    urls = []
    exclude_urls = exclude_urls or set()
    
    # Use session with proper headers (required by DDG)
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://duckduckgo.com/',
    }
    
    try:
        # First get the vqd token
        token_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}&iar=images&iax=images&ia=images"
        resp = session.get(token_url, headers=headers, timeout=10)
        
        # Extract vqd token
        vqd_match = re.search(r'vqd[=:]["\']?([a-zA-Z0-9_-]+)', resp.text)
        if not vqd_match:
            return urls
            
        vqd = vqd_match.group(1)
        
        # Fetch images with pagination (s = offset)
        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={urllib.parse.quote(query)}&vqd={vqd}&f=,,,,,&p=1&s={offset}"
        resp = session.get(api_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                results = data.get('results', [])
                for item in results:
                    img_url = item.get('image', '')
                    if img_url and img_url not in exclude_urls and img_url not in urls:
                        urls.append(img_url)
                        if len(urls) >= limit * 2:
                            break
            except:
                pass
                
    except Exception:
        pass
    
    return urls


def _get_google_image_urls(query: str, limit: int, offset: int = 0, exclude_urls: set = None) -> List[str]:
    """Fetch image URLs from Google Images with pagination."""
    urls = []
    exclude_urls = exclude_urls or set()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        # Google Images search with pagination (start parameter)
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch&start={offset}"
        resp = requests.get(search_url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        # Google embeds image URLs in various formats in the page
        # Pattern 1: Direct image URLs in data attributes
        patterns = [
            r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp|gif))',  # Array format
            r'"ou":"(https?://[^"]+)"',  # Original URL format
            r'imgurl=(https?://[^&"]+)',  # URL parameter format
        ]
        
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, resp.text, re.IGNORECASE)
            all_matches.extend(matches)
        
        # Filter and dedupe
        seen = set()
        for url in all_matches:
            # Skip Google's own URLs and tiny thumbnails
            if 'google.com' in url or 'gstatic.com' in url:
                continue
            if 'encrypted-tbn' in url:
                continue
            if url in seen or url in exclude_urls:
                continue
            
            # Unescape URL
            url = url.replace('\\u003d', '=').replace('\\u0026', '&')
            
            seen.add(url)
            urls.append(url)
            
            if len(urls) >= limit * 2:
                break
                
    except Exception:
        pass
    
    return urls


def _get_image_urls(query: str, limit: int, offset: int = 0, exclude_urls: set = None) -> List[str]:
    """Fetch image URLs from multiple sources."""
    exclude_urls = exclude_urls or set()
    
    # Use DuckDuckGo as primary (better pagination support)
    urls = _get_duckduckgo_image_urls(query, limit, offset=offset, exclude_urls=exclude_urls)
    
    # Fallback to Google if DDG doesn't return enough
    if len(urls) < limit:
        google_urls = _get_google_image_urls(query, limit - len(urls), offset=offset, exclude_urls=exclude_urls | set(urls))
        urls.extend(google_urls)
    
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


def fetch_images(
    query: str, 
    limit: int = 10, 
    output_dir: str = "input", 
    logger=None,
    offset: int = 0,
    exclude_urls: set = None,
    filename_start: int = 1
) -> tuple:
    """
    Download images related to a search query using Bing image search.
    
    Args:
        query: Search term
        limit: Max number of images to download
        output_dir: Directory to save images (default: input/)
        logger: Optional logger
        offset: Pagination offset for Bing search
        exclude_urls: Set of URLs to skip (already downloaded)
        filename_start: Starting number for filenames
        
    Returns:
        Tuple of (saved_files list, downloaded_urls set)
    """
    import json
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create safe query name for filenames
    safe_query = re.sub(r'[^\w\s-]', '', query)[:20].strip().replace(' ', '_')
    
    saved_files = []
    url_mapping = {}  # Exact mapping: filename -> source URL
    downloaded_urls = set()
    exclude_urls = exclude_urls or set()
    
    # Get image URLs from multiple sources
    urls = _get_image_urls(query, limit, offset=offset, exclude_urls=exclude_urls)
    
    if not urls:
        if logger:
            logger.warning("No image URLs found")
        return saved_files, downloaded_urls
    
    # Download images one by one, tracking exact URL->filename mapping
    count = 0
    file_num = filename_start
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
        
        filename = f"{safe_query}_{file_num:02d}{ext}"
        filepath = output_path / filename
        
        if _download_image(url, filepath):
            saved_files.append(str(filepath))
            url_mapping[filename] = url
            downloaded_urls.add(url)
            count += 1
            file_num += 1
    
    # Save copyright attributions with correct mapping
    if url_mapping:
        attr_dir = Path("copyright_attributions") / safe_query
        attr_dir.mkdir(parents=True, exist_ok=True)
        attr_file = attr_dir / f"{safe_query}.json"
        
        # Merge with existing attributions
        existing = {}
        if attr_file.exists():
            try:
                with open(attr_file, 'r') as f:
                    existing = json.load(f)
            except:
                pass
        existing.update(url_mapping)
        
        with open(attr_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    return saved_files, downloaded_urls
