"""Tool Unit Test Challenge — unit tests for the starter tools.

Patterns are copied from test_tools_examples.py; fixtures are in conftest.py.

Rules:
- Offline only: mock HTTP with `fake_http`, set fake keys with `monkeypatch.setenv`.
- One behaviour per test. Name the test after the behaviour, not the function.
- Assert BOTH the request the tool sends AND the result it returns.

Tests for the team's own tool (`hn_search`) live in tests/test_tool_hn_search.py.
"""
from __future__ import annotations

from conftest import FakeResponse
from tools import TOOL_FUNCTIONS

clarify = TOOL_FUNCTIONS["clarify"]
format_tool = TOOL_FUNCTIONS["format"]
send = TOOL_FUNCTIONS["send"]
lookup = TOOL_FUNCTIONS["lookup"]
fetch = TOOL_FUNCTIONS["fetch"]
timeline = TOOL_FUNCTIONS["timeline"]
social_search = TOOL_FUNCTIONS["social_search"]
policy = TOOL_FUNCTIONS["policy"]


# ---------------- clarify ----------------

def test_clarify_choice_returns_options_and_awaits_user() -> None:
    result = clarify(question="Bạn muốn nguồn nào?", response_type="choice", options=["Web", "X"])

    assert result["options"] == ["Web", "X"]
    assert result["response_type"] == "choice"
    assert result["question"] == "Bạn muốn nguồn nào?"
    assert result["awaiting_user"] is True


# ---------------- format ----------------

def test_format_sections_groups_items_by_section() -> None:
    items = [
        {"title": "a1", "section": "A"},
        {"title": "b1", "section": "B"},
        {"title": "a2", "section": "A"},
    ]
    markdown = format_tool(items=items, template="sections")["markdown"]

    assert markdown.count("## A") == 1
    assert markdown.count("## B") == 1
    # both A items sit under the single "## A" heading, before "## B"
    a_block = markdown.split("## B")[0]
    assert "a1" in a_block and "a2" in a_block


def test_format_thread_numbers_items() -> None:
    items = [{"title": "first"}, {"title": "second"}, {"title": "third"}]
    markdown = format_tool(items=items, template="thread")["markdown"]

    posts = markdown.split("\n\n")
    assert [post.split(" ")[0] for post in posts] == ["1/", "2/", "3/"]
    assert posts[1].startswith("2/ second")


def test_format_empty_items_does_not_crash() -> None:
    for empty in (None, []):
        result = format_tool(items=empty, template="sections")
        assert result["item_count"] == 0
        assert result["markdown"] == ""


def test_format_non_dict_items_do_not_crash() -> None:
    # Regression test (bug found while writing these tests): a model may send items as
    # plain strings or a single object. render_digest called item.get(...) on them and
    # raised AttributeError instead of returning a result.
    from_strings = format_tool(items=["Tin 1", "Tin 2"], template="bullets")
    from_one_object = format_tool(items={"title": "Tin duy nhất"}, template="bullets")

    assert from_strings["item_count"] == 2
    assert "- Tin 1" in from_strings["markdown"]
    assert from_one_object["item_count"] == 1
    assert "Tin duy nhất" in from_one_object["markdown"]


# ---------------- send (guardrail) ----------------

def test_send_confirmed_posts_to_telegram(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001")
    calls = fake_http(FakeResponse({"ok": True}))

    result = send(text="Bản tin AI", confirmed=True)

    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert "bot123:abc" in calls[0]["url"]
    assert calls[0]["url"].endswith("/sendMessage")
    assert calls[0]["json"]["chat_id"] == "-1001"
    assert calls[0]["json"]["text"] == "Bản tin AI"
    assert result["status"] == "sent"


def test_send_confirmed_without_env_returns_error_and_no_request(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True}))

    result = send(text="Bản tin AI", confirmed=True)  # conftest clears TELEGRAM_* env vars

    assert calls == []
    assert result["error"] == "RuntimeError"
    assert "TELEGRAM_BOT_TOKEN" in result["message"]


# ---------------- lookup ----------------

def test_lookup_without_timeframe_omits_time_range(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = lookup(query="robotics", timeframe=None)

    assert "time_range" not in calls[0]["json"]
    assert calls[0]["json"]["query"] == "robotics"
    assert result["items"] == []


# ---------------- fetch ----------------

def test_fetch_maps_firecrawl_response(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    calls = fake_http(FakeResponse({"data": {
        "markdown": "# Hello\nBody text",
        "metadata": {"title": "T", "sourceURL": "https://www.example.com/post"},
    }}))

    result = fetch(url="https://www.example.com/post")

    assert calls[0]["url"] == "https://api.firecrawl.dev/v1/scrape"
    assert calls[0]["json"]["url"] == "https://www.example.com/post"
    item = result["items"][0]
    assert item["title"] == "T"
    assert item["url"] == "https://www.example.com/post"
    assert item["source"] == "example.com"
    assert item["summary"] == "# Hello\nBody text"


def test_fetch_truncates_markdown_to_4000_chars(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    fake_http(FakeResponse({"data": {"markdown": "x" * 10_000, "metadata": {}}}))

    item = fetch(url="https://example.com/long")["items"][0]

    assert len(item["summary"]) == 4000
    assert item["title"] == "https://example.com/long"  # no metadata title -> falls back to the url


# ---------------- timeline / social_search ----------------

def _tweet(tweet_id: str) -> dict:
    return {"tweet_id": tweet_id, "screen_name": "sama", "text": f"tweet {tweet_id}", "created_at": "Mon Nov 10"}


def test_timeline_respects_limit_and_skips_items_without_id(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-test")
    no_id = {"screen_name": "sama", "text": "no id"}
    calls = fake_http(FakeResponse({"timeline": [no_id] + [_tweet(str(i)) for i in range(1, 7)]}))

    result = timeline(screenname="sama", limit=3)

    assert calls[0]["url"].endswith("/timeline.php")
    assert calls[0]["params"] == {"screenname": "sama"}
    assert calls[0]["headers"]["x-rapidapi-key"] == "rapid-test"
    assert len(result["items"]) == 3
    assert [item["url"] for item in result["items"]] == [
        "https://x.com/sama/status/1",
        "https://x.com/sama/status/2",
        "https://x.com/sama/status/3",
    ]


def test_social_search_passes_search_type(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-test")
    calls = fake_http(FakeResponse({"timeline": [_tweet("9")]}))

    top = social_search(query="GPT-6", search_type="Top")
    latest = social_search(query="GPT-6", search_type="Latest")

    assert calls[0]["url"].endswith("/search.php")
    assert calls[0]["params"] == {"query": "GPT-6", "search_type": "Top"}
    assert calls[1]["params"] == {"query": "GPT-6", "search_type": "Latest"}
    assert top["search_type"] == "Top" and latest["search_type"] == "Latest"
    assert top["items"][0]["url"] == "https://x.com/sama/status/9"


# ---------------- policy (local knowledge + trust boundary) ----------------

def test_policy_empty_query_returns_no_results() -> None:
    for empty in ("", "   "):
        result = policy(query=empty)
        assert result["results"] == []


def test_policy_area_filter_only_returns_that_area() -> None:
    result = policy(query="personal data retention", policy_area="data_privacy", top_k=5)

    assert result["results"], "expected at least one data_privacy section"
    assert {hit["policy_area"] for hit in result["results"]} == {"data_privacy"}


def test_policy_instruction_like_lines_go_to_untrusted_text() -> None:
    # company_policy/source-citation-policy.md contains a quoted line that tries to give
    # the assistant orders. It must be quarantined in untrusted_text, never in facts.
    result = policy(query="citation source verified tweet", policy_area="source_citation", top_k=10)

    flagged = [
        (hit, line)
        for hit in result["results"]
        for line in hit["untrusted_text"]
        if line.lower().startswith("assistant:")
    ]
    assert flagged, "the injected 'Assistant:' line should be returned as untrusted_text"
    for hit, line in flagged:
        assert line not in hit["facts"]
        assert "assistant:" not in hit["facts"].lower()
    assert "untrusted" in result["trust_boundary"]
