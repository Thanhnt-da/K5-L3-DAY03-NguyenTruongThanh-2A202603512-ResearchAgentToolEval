"""Unit tests for the team tool `hn_search` (tools/hn_search/tool.py).

These tests run OFFLINE: tests/conftest.py blocks real network calls, so every
HTTP request is replaced by the `fake_http` fixture. `fake_http(FakeResponse(...))`
returns a list `calls` that records every request the tool tried to send, so each
test can check BOTH:
  - what the tool sent (URL + params)  -> did it call the API correctly?
  - what the tool returned             -> did it map the response correctly?

Pattern per test: Arrange (fake response) -> Act (call tool) -> Assert.
"""
from __future__ import annotations

import requests

from conftest import FakeResponse
from tools import TOOL_FUNCTIONS

hn_search = TOOL_FUNCTIONS["hn_search"]


def _hit(object_id: str, **extra) -> dict:
    """Build one fake Algolia hit with sensible defaults."""
    hit = {
        "objectID": object_id,
        "title": f"Story {object_id}",
        "url": f"https://example.com/{object_id}",
        "author": "alice",
        "points": 100,
        "num_comments": 10,
        "created_at": "2026-11-10T12:00:00Z",
        "story_text": None,
    }
    hit.update(extra)
    return hit


# 1. Happy path ---------------------------------------------------------------

def test_hn_search_sends_expected_request_and_maps_items(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": [_hit("1"), _hit("2")]}))

    result = hn_search(query="AI agents", limit=2)

    # request
    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search"
    assert calls[0]["params"] == {"query": "AI agents", "tags": "story", "hitsPerPage": 2}
    # response mapping -> shared item shape
    assert result["tool"] == "search_hn"
    assert [item["title"] for item in result["items"]] == ["Story 1", "Story 2"]
    first = result["items"][0]
    assert first["url"] == "https://example.com/1"
    assert first["source"] == "example.com"
    assert first["points"] == 100 and first["comments"] == 10
    assert first["discussion_url"] == "https://news.ycombinator.com/item?id=1"


def test_hn_search_sort_date_uses_search_by_date_endpoint(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    result = hn_search(query="rust", sort="date")

    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search_by_date"
    assert result["sort"] == "date"
    assert result["items"] == []


def test_hn_search_text_post_without_url_links_to_discussion(fake_http) -> None:
    ask_hn = _hit("42", title="Ask HN: Best AI agent framework?", url=None,
                  story_text="Which one do <i>you</i> use&#x3F;")
    fake_http(FakeResponse({"hits": [ask_hn]}))

    item = hn_search(query="AI agent framework")["items"][0]

    assert item["url"] == "https://news.ycombinator.com/item?id=42"
    assert item["source"] == "news.ycombinator.com"
    assert item["summary"] == "Which one do you use?"  # HTML tags + entities stripped


# 2. Bad input from the model -----------------------------------------------

def test_hn_search_empty_query_returns_error_without_network(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": [_hit("1")]}))

    result = hn_search(query="   ")

    assert result["error"] == "ValueError"
    assert "query" in result["message"]
    assert calls == []  # validated BEFORE spending a request


def test_hn_search_invalid_sort_returns_error_without_network(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    result = hn_search(query="rust", sort="popular")

    assert result["error"] == "ValueError"
    assert calls == []


def test_hn_search_limit_string_zero_and_huge_are_clamped(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    hn_search(query="rust", limit="3")    # string from the model
    hn_search(query="rust", limit=0)      # too small
    hn_search(query="rust", limit=500)    # too big
    hn_search(query="rust", limit="abc")  # not a number -> default

    assert [c["params"]["hitsPerPage"] for c in calls] == [3, 1, 20, 5]


def test_hn_search_skips_hits_without_object_id(fake_http) -> None:
    broken = _hit("x")
    broken.pop("objectID")
    fake_http(FakeResponse({"hits": [broken, _hit("7")]}))

    result = hn_search(query="rust")

    assert [item["title"] for item in result["items"]] == ["Story 7"]


# 3. Failure path: errors come back as a dict, never raised -----------------

def test_hn_search_http_error_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse({"message": "rate limited"}, status_code=429))

    result = hn_search(query="rust")

    assert result["tool"] == "search_hn"
    assert result["error"] == "HTTPError"
    assert "items" not in result


def test_hn_search_network_failure_returns_error_dict(fake_http) -> None:
    fake_http(requests.ConnectionError("network down"))

    result = hn_search(query="rust")

    assert result["error"] == "ConnectionError"
    assert "network down" in result["message"]
