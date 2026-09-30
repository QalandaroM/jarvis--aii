"""Entry point: `jarvis [chat|doctor]` or `python -m jarvis`."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from jarvis import __version__
from jarvis.app import JarvisApp, StubResponder
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
    sub.add_parser("doctor", help="проверить окружение и настройки")
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
        return run_doctor(settings)

    setup_logging(settings, Redactor())
    logging.getLogger("jarvis").info("JARVIS %s starting", __version__)
    return JarvisApp(settings, StubResponder()).run()


if __name__ == "__main__":
    raise SystemExit(main())
