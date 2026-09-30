from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import anthropic
import pytest

from jarvis.ai.brain import FALLBACK_BETA, AIBrain
from jarvis.ai.prompts import SUMMARY_REQUEST
from jarvis.core.config import Settings
from tests.fakes import (
    FakeCreate,
    connection_error,
    make_message,
    status_error,
    timeout_error,
)

NOW = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)


def make_brain(settings: Settings, fake: FakeCreate) -> AIBrain:
    return AIBrain(settings, fake, clock=lambda: NOW)


@pytest.fixture
def settings(make_settings: Callable[..., Settings]) -> Settings:
    return make_settings(anthropic_api_key="sk-ant-test-0000000000000000")


def test_reply_and_request_shape(settings: Settings) -> None:
    fake = FakeCreate(make_message("Привет, Boss."))
    assert make_brain(settings, fake).respond("привет") == "Привет, Boss."

    call = fake.calls[0]
    assert call["model"] == settings.ai_model
    assert call["output_config"] == {"effort": settings.ai_effort}
    assert call["cache_control"] == {"type": "ephemeral"}
    assert call["fallbacks"] == "default"
    assert call["betas"] == [FALLBACK_BETA]
    assert "thinking" not in call  # always on for this model; sending "disabled" would 400
    assert "tool_choice" not in call
    user = call["messages"][-1]
    assert user["role"] == "user"
    assert "<context>local_time: 2026-09-30" in user["content"]
    assert user["content"].endswith("привет")


def test_fallbacks_can_be_disabled(make_settings: Callable[..., Settings]) -> None:
    fake = FakeCreate(make_message("ok"))
    make_brain(make_settings(ai_fallbacks=False), fake).respond("hi")
    assert "fallbacks" not in fake.calls[0]
    assert "betas" not in fake.calls[0]


def test_history_is_append_only(settings: Settings) -> None:
    fake = FakeCreate(make_message("one"), make_message("two"), make_message("three"))
    brain = make_brain(settings, fake)
    for text in ("a", "b", "c"):
        brain.respond(text)

    first, second, third = (c["messages"] for c in fake.calls)
    assert len(first) == 1 and len(second) == 3 and len(third) == 5
    # Every earlier request is an exact prefix of the next one (plus its reply).
    assert second[: len(first)] == first
    assert third[: len(second)] == second
    assert second[1]["role"] == "assistant"
    # The system prompt never changes within a session.
    assert len({c["system"] for c in fake.calls}) == 1


def test_thinking_blocks_are_kept_in_history(settings: Settings) -> None:
    thinking = {"type": "thinking", "thinking": "", "signature": "sig123"}
    fake = FakeCreate(make_message(thinking, "answer"), make_message("next"))
    brain = make_brain(settings, fake)
    brain.respond("q1")
    brain.respond("q2")
    stored = fake.calls[1]["messages"][1]["content"]
    assert [b.type for b in stored] == ["thinking", "text"]


def test_refusal_is_not_committed(settings: Settings) -> None:
    fake = FakeCreate(make_message(stop_reason="refusal"), make_message("ok"))
    brain = make_brain(settings, fake)
    assert "не могу" in brain.respond("что-то запрещённое")
    brain.respond("нормальный вопрос")
    assert len(fake.calls[1]["messages"]) == 1


def test_truncated_reply_is_marked(settings: Settings) -> None:
    fake = FakeCreate(make_message("длинный ответ", stop_reason="max_tokens"))
    assert "обрезан" in make_brain(settings, fake).respond("расскажи всё")


@pytest.mark.parametrize(
    "stop_reason", ["tool_use", "pause_turn", "model_context_window_exceeded", "compaction", None]
)
def test_unexpected_stop_reason_fails_closed(settings: Settings, stop_reason: str | None) -> None:
    fake = FakeCreate(make_message("partial", stop_reason=stop_reason), make_message("ok"))
    brain = make_brain(settings, fake)
    assert "не удалось обработать" in brain.respond("x")
    brain.respond("y")
    assert len(fake.calls[1]["messages"]) == 1  # nothing from the bad turn was stored


def test_empty_reply_fails_closed(settings: Settings) -> None:
    fake = FakeCreate(make_message())
    assert "не удалось обработать" in make_brain(settings, fake).respond("x")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (timeout_error(), "не ответил вовремя"),
        (connection_error(), "нет связи"),
        (status_error(anthropic.AuthenticationError, 401), "API-ключ отклонён"),
        (status_error(anthropic.PermissionDeniedError, 403), "нет доступа"),
        (status_error(anthropic.NotFoundError, 404), "не найдена"),
        (status_error(anthropic.RateLimitError, 429), "лимит запросов"),
        (status_error(anthropic.BadRequestError, 400), "отклонён API"),
        (status_error(anthropic.InternalServerError, 500), "временно недоступен"),
        (status_error(anthropic.APIStatusError, 529), "временно недоступен"),
    ],
)
def test_api_errors_become_honest_replies(
    settings: Settings, error: Exception, expected: str
) -> None:
    fake = FakeCreate(error, make_message("ok"))
    brain = make_brain(settings, fake)
    reply = brain.respond("привет")
    assert expected in reply
    assert "не удалось получить ответ" in reply
    brain.respond("ещё раз")
    assert len(fake.calls[1]["messages"]) == 1


def test_error_log_does_not_leak_api_key(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    fake = FakeCreate(status_error(anthropic.AuthenticationError, 401))
    make_brain(settings, fake).respond("hi")
    assert "sk-ant-test" not in caplog.text


def test_long_conversation_is_summarized_and_restarted(
    make_settings: Callable[..., Settings],
) -> None:
    settings = make_settings(ai_max_turns=2)
    fake = FakeCreate(
        make_message("r1"),
        make_message("r2"),
        make_message("Пользователь готовит проект на Python."),  # summary
        make_message("r3"),
    )
    brain = make_brain(settings, fake)
    brain.respond("q1")
    brain.respond("q2")
    brain.respond("q3")

    summary_call, after = fake.calls[2], fake.calls[3]
    assert summary_call["messages"][-1]["content"] == SUMMARY_REQUEST
    assert len(summary_call["messages"]) == 5  # full old history + summary request
    assert len(after["messages"]) == 1  # fresh conversation
    content = after["messages"][0]["content"]
    assert "<conversation_summary>" in content and "проект на Python" in content
    assert content.endswith("q3")


def test_summary_survives_a_failed_request(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings(ai_max_turns=2)
    fake = FakeCreate(
        make_message("r1"),
        make_message("r2"),
        make_message("summary"),
        connection_error(),
        make_message("r3"),
    )
    brain = make_brain(settings, fake)
    brain.respond("q1")
    brain.respond("q2")
    brain.respond("q3")  # summary, then the request fails
    brain.respond("q4")
    assert "<conversation_summary>" in fake.calls[4]["messages"][0]["content"]


def test_failed_summary_still_restarts(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings(ai_max_turns=2)
    fake = FakeCreate(
        make_message("r1"), make_message("r2"), connection_error(), make_message("r3")
    )
    brain = make_brain(settings, fake)
    brain.respond("q1")
    brain.respond("q2")
    assert brain.respond("q3") == "r3"
    assert len(fake.calls[3]["messages"]) == 1
    assert "<conversation_summary>" not in fake.calls[3]["messages"][0]["content"]


def test_reset(settings: Settings) -> None:
    fake = FakeCreate(make_message("r1"), make_message("r2"))
    brain = make_brain(settings, fake)
    brain.respond("q1")
    brain.reset()
    brain.respond("q2")
    assert len(fake.calls[1]["messages"]) == 1
