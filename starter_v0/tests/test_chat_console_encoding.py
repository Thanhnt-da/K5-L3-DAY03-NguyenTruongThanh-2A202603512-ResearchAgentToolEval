"""Regression test: the chat/UI tool loop must not crash on a Windows (cp1252) console.

Bug found while running the Streamlit UI on Windows: chat.run_model_tool_loop printed
"🔧 <tool>(...)" with a plain print(). On a cp1252 console that raised
UnicodeEncodeError on the first tool call, so every request that used a tool crashed
(in `python chat.py` and in app.py, which reuses the same loop). Fixed with
chat.console_log(), which replaces characters the console cannot encode.
"""
from __future__ import annotations

import io
import sys

import chat
from providers.base import ModelResponse, ToolCall


class OneCallThenAnswerProvider:
    """Fake model: first asks for one tool call, then answers in Vietnamese text."""

    def __init__(self) -> None:
        self.turn = 0

    def complete(self, messages, tools=None, *, model=None, temperature=0.0, tool_choice=None) -> ModelResponse:
        self.turn += 1
        if self.turn == 1:
            return ModelResponse(text=None, tool_calls=[ToolCall("format", {"items": [{"title": "Tin AI"}]})])
        return ModelResponse(text="Đây là bản tóm tắt.", tool_calls=[])


def _cp1252_stdout(monkeypatch) -> io.BytesIO:
    buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buffer, encoding="cp1252", errors="strict"))
    return buffer


def test_tool_loop_survives_cp1252_console(monkeypatch) -> None:
    buffer = _cp1252_stdout(monkeypatch)

    result = chat.run_model_tool_loop(
        provider=OneCallThenAnswerProvider(),
        messages=[{"role": "user", "content": "Tóm tắt tin AI"}],
        tools=[],
        model=None,
        max_tool_rounds=3,
    )

    assert result["status"] == "answered"
    assert result["assistant_text"] == "Đây là bản tóm tắt."
    assert [event["tool"] for event in result["tool_events"]] == ["format"]
    sys.stdout.flush()
    assert b"format(" in buffer.getvalue()  # the log line was still written, emoji replaced


def test_console_log_replaces_unencodable_characters(monkeypatch) -> None:
    buffer = _cp1252_stdout(monkeypatch)

    chat.console_log("🔧 Agent> Tin tức hôm nay")

    sys.stdout.flush()
    # cp1252 has "ô" but not the emoji or "ứ" -> only those become "?"
    assert buffer.getvalue().decode("cp1252").strip() == "? Agent> Tin t?c hôm nay"
