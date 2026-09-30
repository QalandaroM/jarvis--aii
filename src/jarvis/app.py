"""JARVIS application loop: reads commands, handles built-ins, delegates the rest.

Built-in commands (stop / exit / help) are matched here, BEFORE anything reaches the
AI Brain, so "Jarvis, stop" works even if the AI is slow, offline or misbehaving.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from jarvis.core.config import Settings
from jarvis.core.text import normalize_command, strip_wake_word

logger = logging.getLogger(__name__)

STOP_COMMANDS = frozenset({"stop", "стоп", "остановись", "хватит", "отмена", "cancel", "abort"})
EXIT_COMMANDS = frozenset({"exit", "quit", "bye", "выход", "выйти", "пока"})
HELP_COMMANDS = frozenset({"help", "помощь", "?"})
RESET_COMMANDS = frozenset({"reset", "новый разговор", "сброс", "забудь разговор"})


class Responder(Protocol):
    """Anything that turns a user command into a reply. Implemented by the AI Brain."""

    def respond(self, command: str) -> str: ...

    def reset(self) -> None: ...


class StubResponder:
    """Used when the AI Brain can't start (no API key): JARVIS still runs built-in commands."""

    def respond(self, command: str) -> str:
        return (
            "AI Brain не подключён: не задан ANTHROPIC_API_KEY в .env. "
            f"Команда получена: «{command}»"
        )

    def reset(self) -> None:
        pass


@dataclass(frozen=True)
class Reply:
    text: str
    should_exit: bool = False


class JarvisApp:
    def __init__(
        self,
        settings: Settings,
        responder: Responder,
        *,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        self._settings = settings
        self._responder = responder
        self._input = input_fn
        self._output = output_fn

    @property
    def _title(self) -> str:
        return self._settings.user_title

    def handle(self, raw: str) -> Reply | None:
        """Process one line of input. Returns None for empty input."""
        command = strip_wake_word(raw)
        key = normalize_command(raw)
        if not key:
            return None

        if key in STOP_COMMANDS:
            logger.info("emergency stop requested (nothing running)")
            return Reply(f"Остановлено, {self._title}. Сейчас нет активных действий.")
        if key in EXIT_COMMANDS:
            return Reply(f"До связи, {self._title}.", should_exit=True)
        if key in HELP_COMMANDS:
            return Reply(self._help_text())
        if key in RESET_COMMANDS:
            self._responder.reset()
            return Reply(f"Начинаем новый разговор, {self._title}.")

        logger.info("user command received (%d chars)", len(command))
        try:
            return Reply(self._responder.respond(command))
        except Exception:
            # Never crash the loop and never pretend the command succeeded.
            logger.exception("responder failed")
            return Reply(f"{self._title}, произошла внутренняя ошибка. Команда НЕ выполнена.")

    def run(self) -> int:
        self._output(f"JARVIS онлайн. Слушаю, {self._title}. (help — справка, exit — выход)")
        logger.info("session started")
        while True:
            try:
                raw = self._input("> ")
            except (EOFError, KeyboardInterrupt):
                self._output("")
                break
            try:
                reply = self.handle(raw)
            except KeyboardInterrupt:
                # Ctrl+C while JARVIS is working cancels that command, not the whole session.
                logger.info("command cancelled with Ctrl+C")
                self._output(f"Отменено, {self._title}.")
                continue
            if reply is None:
                continue
            self._output(reply.text)
            if reply.should_exit:
                break
        logger.info("session ended")
        return 0

    def _help_text(self) -> str:
        return (
            "Команды:\n"
            "  stop / стоп   — экстренная остановка текущих действий\n"
            "  exit / выход  — завершить работу\n"
            "  reset / сброс — начать новый разговор\n"
            "  help / помощь — эта справка\n"
            "  Ctrl+C        — отменить текущий запрос\n"
            "Всё остальное передаётся AI Brain."
        )
