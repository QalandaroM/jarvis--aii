"""Test doubles for the Claude API — no network, no API key, no cost."""

from __future__ import annotations

from typing import Any

import anthropic
import httpx2
from anthropic.types.beta import BetaMessage

_REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def make_message(
    *blocks: dict[str, Any] | str, stop_reason: str | None = "end_turn"
) -> BetaMessage:
    content = [{"type": "text", "text": b} if isinstance(b, str) else b for b in blocks]
    return BetaMessage.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    )


def status_error(cls: type[anthropic.APIStatusError], code: int) -> anthropic.APIStatusError:
    return cls("test error", response=httpx2.Response(code, request=_REQUEST), body=None)


def connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=_REQUEST)


def timeout_error() -> anthropic.APITimeoutError:
    return anthropic.APITimeoutError(request=_REQUEST)


class FakeCreate:
    """Callable standing in for `client.beta.messages.create`; replays scripted outcomes."""

    def __init__(self, *outcomes: BetaMessage | Exception) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> BetaMessage:
        # Snapshot the messages list: the caller must not rely on us keeping its reference.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
