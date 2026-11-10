---
name: hn_search
track: bonus
kind: live_api
provider: Hacker News (Algolia HN Search API)
requires_env: []
inputs: [query, limit, sort]
outputs: [items]
side_effect: false
---
# hn_search

Searches Hacker News stories through the free Algolia HN API
(`https://hn.algolia.com/api/v1/search`). No API key needed.

- `query`: keywords (required, must not be empty).
- `limit`: number of stories, clamped to 1–20 (default 5).
- `sort`: `relevance` (default) or `date` (newest first, uses `/search_by_date`).

Each item has the shared shape `title, url, source, summary, date` plus
`author, points, comments, discussion_url`. Text posts without an external link
("Ask HN") use the HN discussion page as `url`.

Errors (empty query, bad `sort`, network/HTTP failure) are returned as an error
dict `{"tool", "error", "message"}`; the function never raises.

Use it for tech-community discussion and opinions on a topic. Not for general web
search (`lookup`) or X/Twitter posts (`social_search`, `timeline`).
