from __future__ import annotations

import pytest

from jarvis.ai.conversation import Conversation, history_content
from tests.fakes import make_message

FALLBACK = {
    "type": "fallback",
    "from": {"model": "claude-opus-5-5"},
    "to": {"model": "claude-opus-4-8"},
    "trigger": {"type": "refusal", "category": "cyber"},
}
THINKING = {"type": "thinking", "thinking": "", "signature": "s"}


def test_history_content_without_fallback_is_unchanged() -> None:
    blocks = make_message(THINKING, "hi").content
    assert history_content(blocks) == blocks


def test_history_content_after_fallback_keeps_only_safe_blocks() -> None:
    blocks = make_message(THINKING, "partial", FALLBACK, THINKING, "final").content
    kept = history_content(blocks)
    assert [b.type for b in kept] == ["text", "thinking", "text"]
    assert kept[0].type == "text" and kept[0].text == "partial"


def test_with_user_turn_does_not_mutate() -> None:
    conv = Conversation(max_turns=5)
    conv.with_user_turn("hello")
    assert conv.with_user_turn("again") == [{"role": "user", "content": "again"}]


def test_commit_and_full() -> None:
    conv = Conversation(max_turns=2)
    conv.commit("q1", make_message("a1").content)
    assert not conv.is_full
    conv.commit("q2", make_message("a2").content)
    assert conv.is_full and conv.turns == 2
    assert len(conv.with_user_turn("q3")) == 5


def test_commit_rejects_empty_content() -> None:
    with pytest.raises(ValueError):
        Conversation(max_turns=2).commit("q", [])


def test_restart_carries_summary_until_commit() -> None:
    conv = Conversation(max_turns=2)
    conv.commit("q1", make_message("a1").content)
    conv.restart("summary")
    assert conv.turns == 0
    assert conv.pending_summary == "summary"
    conv.commit("q2", make_message("a2").content)
    assert conv.pending_summary is None
