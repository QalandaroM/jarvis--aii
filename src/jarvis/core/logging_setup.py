"""Logging configuration: rotating file log + optional console, with secret redaction."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from jarvis.core.config import Settings
from jarvis.core.redaction import Redactor

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_MAX_LOG_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 5


class RedactingFilter(logging.Filter):
    """Renders the message once, redacts it, and stores the safe version on the record."""

    def __init__(self, redactor: Redactor) -> None:
        super().__init__()
        self._redactor = redactor

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redactor.redact(record.getMessage())
        record.args = None
        if record.exc_info:
            # Tracebacks may contain secrets in local reprs or messages: render and redact now.
            record.exc_text = self._redactor.redact(
                logging.Formatter().formatException(record.exc_info)
            )
            record.exc_info = None
        return True


def setup_logging(settings: Settings, redactor: Redactor) -> None:
    """Configure the `jarvis` logger. Safe to call more than once (handlers are replaced)."""
    for secret in settings.secret_values():
        redactor.register_secret(secret)

    logger = logging.getLogger("jarvis")
    logger.setLevel(settings.log_level)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(LOG_FORMAT)
    redacting = RedactingFilter(redactor)

    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.logs_dir / "jarvis.log",
        maxBytes=_MAX_LOG_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redacting)
    logger.addHandler(file_handler)

    if settings.log_to_console:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        console.addFilter(redacting)
        logger.addHandler(console)
