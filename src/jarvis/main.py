"""Entry point: `jarvis [chat|doctor]` or `python -m jarvis`."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from jarvis import __version__
from jarvis.ai.brain import AIBrain
from jarvis.ai.client import create_message_function
from jarvis.app import JarvisApp, Responder, StubResponder
from jarvis.core.config import Settings, get_settings
from jarvis.core.logging_setup import setup_logging
from jarvis.core.redaction import Redactor
from jarvis.doctor import run_doctor


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis", description="JARVIS — персональный AI-ассистент"
    )
    parser.add_argument("--version", action="version", version=f"jarvis {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("chat", help="текстовый режим (по умолчанию)")
    doctor = sub.add_parser("doctor", help="проверить окружение и настройки")
    doctor.add_argument(
        "--online", action="store_true", help="также проверить API-ключ и модель (нужен интернет)"
    )
    return parser


def _load_settings() -> Settings | None:
    try:
        return get_settings()
    except ValidationError as exc:
        # Pydantic's message names the field and the problem; secrets are SecretStr and hidden.
        print(f"Ошибка в настройках (.env / переменные окружения):\n{exc}", file=sys.stderr)
        return None


def main(argv: Sequence[str] | None = None) -> int:
    # Windows consoles may default to a legacy code page; make Cyrillic output safe.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    args = _build_parser().parse_args(argv)
    settings = _load_settings()
    if settings is None:
        return 2

    if args.command == "doctor":
        return run_doctor(settings, online=args.online)

    setup_logging(settings, Redactor())
    log = logging.getLogger("jarvis")
    log.info("JARVIS %s starting (model=%s)", __version__, settings.ai_model)
    return JarvisApp(settings, _build_responder(settings)).run()


def _build_responder(settings: Settings) -> Responder:
    if not settings.has_api_key:
        logging.getLogger("jarvis").warning("no API key: AI Brain disabled")
        return StubResponder()
    return AIBrain(settings, create_message_function(settings))


if __name__ == "__main__":
    raise SystemExit(main())
