from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from jarvis.ai.prompts import build_system_prompt, format_user_turn
from jarvis.core.config import Settings


def test_system_prompt_is_stable(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings()
    assert build_system_prompt(settings) == build_system_prompt(settings)


def test_system_prompt_content(make_settings: Callable[..., Settings]) -> None:
    prompt = build_system_prompt(make_settings(user_title="Sir", language="en"))
    assert '"Sir"' in prompt
    assert "Reply in English" in prompt
    assert "<untrusted_data>" in prompt  # prompt-injection rules present
    assert "no tools are connected yet" in prompt  # honest about current abilities
    assert "Never claim that an action was performed" in prompt


def test_system_prompt_lists_tools(make_settings: Callable[..., Settings]) -> None:
    prompt = build_system_prompt(make_settings(), ["open_url", "web_search"])
    assert "open_url, web_search" in prompt
    assert "no tools are connected yet" not in prompt


def test_user_turn_has_context_and_command() -> None:
    turn = format_user_turn("открой YouTube", datetime(2026, 1, 2, 3, 4, tzinfo=UTC))
    assert turn.startswith("<context>local_time: ")
    assert turn.endswith("открой YouTube")
    assert "<conversation_summary>" not in turn


def test_user_turn_with_summary() -> None:
    turn = format_user_turn("дальше", datetime(2026, 1, 2, tzinfo=UTC), summary="итог")
    assert "<conversation_summary>\nитог\n</conversation_summary>" in turn
