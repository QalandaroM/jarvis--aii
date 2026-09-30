"""Anthropic API client factory. The API key is read from Settings, never from code."""

from __future__ import annotations

from typing import Any, Protocol

import anthropic
from anthropic.types.beta import BetaMessage

from jarvis.core.config import Settings


class CreateMessage(Protocol):
    """The one API call the Brain needs. Tests pass a fake with the same shape."""

    def __call__(self, **kwargs: Any) -> BetaMessage: ...


def create_message_function(settings: Settings) -> CreateMessage:
    if settings.anthropic_api_key is None:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
    )

    def create(**kwargs: Any) -> BetaMessage:
        # **kwargs defeats the SDK's overload typing; with stream=False the result is a message.
        message: BetaMessage = client.beta.messages.create(stream=False, **kwargs)
        return message

    return create


def check_model_access(settings: Settings) -> str:
    """Validate the API key and model name without spending tokens. Returns the model's name."""
    if settings.anthropic_api_key is None:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=15.0,
        max_retries=0,
    )
    return client.models.retrieve(settings.ai_model).display_name
