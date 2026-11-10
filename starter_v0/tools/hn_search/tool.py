"""hn_search — search Hacker News stories via the free Algolia HN API (no API key).

How a tool in this lab is shaped (same pattern as tools/lookup/tool.py):
1. One plain Python function. The MODEL never sees this code; it only sees the
   name/description/parameters in artifacts/tools.yaml. The agent then calls this
   function with the arguments the model chose.
2. Every argument has a default, because the model may leave arguments out.
3. Everything runs inside try/except and returns a dict. A tool must NEVER raise:
   on failure it returns an error dict, so the model can read what went wrong
   instead of the whole agent crashing.
4. Results are mapped to the same "item" shape the other tools use
   (title, url, source, summary, date), so `format` can render any of them.
"""
from __future__ import annotations

import html
import re
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err

# Two endpoints of the same API: one ranks by relevance, one by newest first.
SEARCH_URL = "https://hn.algolia.com/api/v1/search"
SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"

MAX_LIMIT = 20  # keep tool output small: long outputs cost tokens and confuse the model


def _clean_limit(limit: Any) -> int:
    """Models sometimes send limit as "5", 0, -3 or 500. Turn any of those into 1..MAX_LIMIT."""
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 5
    return max(1, min(value, MAX_LIMIT))


def _strip_html(text: str | None) -> str:
    """story_text comes back as HTML (e.g. '<i>..</i>', '&#x2F;'). Return plain text."""
    if not text:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()


def _hit_to_item(hit: dict[str, Any]) -> dict[str, Any]:
    """Map one Algolia 'hit' to the shared item shape."""
    story_id = hit.get("objectID") or ""
    discussion_url = HN_ITEM_URL.format(id=story_id) if story_id else ""
    # "Ask HN" / "Show HN" text posts have no external url -> link to the HN thread instead.
    url = hit.get("url") or discussion_url
    return {
        "title": hit.get("title") or "",
        "url": url,
        "source": domain(hit["url"]) if hit.get("url") else "news.ycombinator.com",
        "summary": _strip_html(hit.get("story_text"))[:500],
        "date": hit.get("created_at"),
        "author": hit.get("author"),
        "points": hit.get("points"),
        "comments": hit.get("num_comments"),
        "discussion_url": discussion_url,
    }


def search_hn(query: str = "", limit: int = 5, sort: str = "relevance") -> dict[str, Any]:
    """Search Hacker News stories.

    query: keywords, e.g. "AI agents".
    limit: number of stories to return (clamped to 1..20).
    sort:  "relevance" (most relevant/popular) or "date" (newest first).
    """
    try:
        # Validate input BEFORE spending a network call. Bad input from the model
        # becomes a clear error message the model can react to.
        query = (query or "").strip()
        if not query:
            raise ValueError("query must not be empty")
        if sort not in ("relevance", "date"):
            raise ValueError(f"sort must be 'relevance' or 'date', got {sort!r}")

        n = _clean_limit(limit)
        url = SEARCH_BY_DATE_URL if sort == "date" else SEARCH_URL
        response = requests.get(
            url,
            params={"query": query, "tags": "story", "hitsPerPage": n},
            timeout=TIMEOUT,
        )
        response.raise_for_status()  # turns HTTP 4xx/5xx into an exception -> caught below
        hits = response.json().get("hits") or []

        items = [_hit_to_item(hit) for hit in hits if hit.get("objectID")][:n]
        return {"tool": "search_hn", "query": query, "sort": sort, "items": items}
    except Exception as exc:
        return err("search_hn", exc)
