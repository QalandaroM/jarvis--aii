"""AI Brain: sends the conversation to Claude and turns the response into a reply.

Stage 2 scope: conversation only. The Brain never executes anything; from Stage 5 on it
will return tool-call PROPOSALS that go through the Safety Layer before anything runs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

import anthropic
from anthropic.types.beta import BetaMessage, BetaMessageParam

from jarvis.ai.client import CreateMessage
from jarvis.ai.conversation import Conversation
from jarvis.ai.prompts import SUMMARY_REQUEST, build_system_prompt, format_user_turn
from jarvis.core.config import Settings

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
_COMPLETE_STOP_REASONS = frozenset({"end_turn", "stop_sequence"})


def response_text(response: BetaMessage) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


class AIBrain:
    def __init__(
        self,
        settings: Settings,
        create_message: CreateMessage,
        *,
        clock: Callable[[], datetime] = datetime.now,
        tool_names: Sequence[str] = (),
    ) -> None:
        self._settings = settings
        self._create = create_message
        self._clock = clock
        # Built once per session and never changed (see prompts.py).
        self._system = build_system_prompt(settings, tool_names)
        self._conversation = Conversation(settings.ai_max_turns)

    @property
    def _title(self) -> str:
        return self._settings.user_title

    def respond(self, command: str) -> str:
        if self._conversation.is_full:
            self._summarize_and_restart()

        user_text = format_user_turn(command, self._clock(), self._conversation.pending_summary)
        try:
            response = self._request(self._conversation.with_user_turn(user_text))
        except anthropic.APIError as exc:
            return self._api_error_reply(exc)
        return self._reply_from(user_text, response)

    def reset(self) -> None:
        self._conversation.restart()
        logger.info("conversation reset by user")

    # --- internals -------------------------------------------------------------------------

    def _request(self, messages: list[BetaMessageParam]) -> BetaMessage:
        kwargs: dict[str, Any] = {
            "model": self._settings.ai_model,
            "max_tokens": self._settings.ai_max_tokens,
            "system": self._system,
            "messages": messages,
            "output_config": {"effort": self._settings.ai_effort},
            "cache_control": {"type": "ephemeral"},
        }
        if self._settings.ai_fallbacks:
            kwargs["fallbacks"] = "default"
            kwargs["betas"] = [FALLBACK_BETA]

        response = self._create(**kwargs)
        usage = response.usage
        logger.info(
            "ai response: model=%s stop=%s in=%s out=%s cache_read=%s request_id=%s",
            response.model,
            response.stop_reason,
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_read_input_tokens,
            getattr(response, "_request_id", None),
        )
        return response

    def _reply_from(self, user_text: str, response: BetaMessage) -> str:
        text = response_text(response)
        stop = response.stop_reason

        if stop == "refusal":
            # Not committed: a declined turn must not become part of the context.
            return f"{self._title}, с этим запросом я помочь не могу."
        if stop in _COMPLETE_STOP_REASONS and text:
            self._conversation.commit(user_text, response.content)
            return text
        if stop == "max_tokens" and text:
            self._conversation.commit(user_text, response.content)
            return f"{text}\n(ответ обрезан — достигнут лимит длины)"

        # tool_use / pause_turn / empty / unknown: nothing we can safely act on in this stage.
        logger.warning("unusable ai response: stop=%s text_len=%d", stop, len(text))
        return f"{self._title}, не удалось обработать ответ AI. Попробуйте переформулировать."

    def _summarize_and_restart(self) -> None:
        summary: str | None = None
        try:
            response = self._request(self._conversation.with_user_turn(SUMMARY_REQUEST))
            if response.stop_reason in {*_COMPLETE_STOP_REASONS, "max_tokens"}:
                summary = response_text(response) or None
        except anthropic.APIError as exc:
            logger.warning("conversation summary failed: %s", type(exc).__name__)
        logger.info(
            "conversation restarted after %d turns (summary=%s)",
            self._conversation.turns,
            summary is not None,
        )
        self._conversation.restart(summary)

    def _api_error_reply(self, exc: anthropic.APIError) -> str:
        request_id = getattr(exc, "request_id", None)
        logger.error(
            "ai request failed: %s: %s request_id=%s", type(exc).__name__, exc.message, request_id
        )
        prefix = f"{self._title}, не удалось получить ответ AI: "
        # Most specific first: APITimeoutError is a subclass of APIConnectionError.
        if isinstance(exc, anthropic.APITimeoutError):
            return prefix + "сервис не ответил вовремя."
        if isinstance(exc, anthropic.APIConnectionError):
            return prefix + "нет связи. Проверьте интернет."
        if isinstance(exc, anthropic.AuthenticationError):
            return prefix + "API-ключ отклонён. Проверьте ANTHROPIC_API_KEY в .env."
        if isinstance(exc, anthropic.PermissionDeniedError):
            return prefix + "у ключа нет доступа к этой модели."
        if isinstance(exc, anthropic.NotFoundError):
            return prefix + f"модель «{self._settings.ai_model}» не найдена (JARVIS_AI_MODEL)."
        if isinstance(exc, anthropic.RateLimitError):
            return prefix + "превышен лимит запросов. Попробуйте через минуту."
        if isinstance(exc, anthropic.BadRequestError):
            return prefix + "запрос отклонён API (подробности в логе)."
        if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
            return prefix + "сервис временно недоступен. Попробуйте позже."
        return prefix + "неизвестная ошибка (подробности в логе)."
