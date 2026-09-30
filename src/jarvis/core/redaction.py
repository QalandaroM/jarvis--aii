"""Secret redaction for logs and the audit trail.

Two layers:
1. Exact values registered at runtime (e.g. the API key loaded from `.env`).
2. Pattern-based detection of common secret formats (API keys, bearer tokens,
   `password=...` pairs, private key blocks).

Redaction is best-effort defence in depth: code should still avoid logging secrets.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Mapping
from typing import Any

MASK = "***REDACTED***"

# Dict keys whose values are always masked, whatever they contain.
_SENSITIVE_KEY_RE = re.compile(
    r"(pass(word|wd)?|pwd|secret|token|api[_-]?key|auth(orization)?|cookie|session[_-]?id|"
    r"private[_-]?key|credential)",
    re.IGNORECASE,
)

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # PEM private keys (multi-line).
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        MASK,
    ),
    # Anthropic / OpenAI-style keys.
    (re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{16,}"), MASK),
    # GitHub tokens.
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), MASK),
    # AWS access key id.
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), MASK),
    # Authorization: Bearer <token>
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/\-]+=*"), rf"\1 {MASK}"),
    # key=value / key: value pairs with a sensitive key name.
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?token|"
            r"refresh[_-]?token|cookie)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
        ),
        rf"\1\2{MASK}",
    ),
)

# Registered values shorter than this are ignored: masking "a" or "12" would shred logs.
_MIN_SECRET_LENGTH = 6


class Redactor:
    """Thread-safe redactor. Share one instance across the logger and the audit log."""

    def __init__(self) -> None:
        self._secrets: set[str] = set()
        self._lock = threading.Lock()

    def register_secret(self, value: str | None) -> None:
        if value and len(value) >= _MIN_SECRET_LENGTH:
            with self._lock:
                self._secrets.add(value)

    def redact(self, text: str) -> str:
        with self._lock:
            # Longest first, so a secret that contains another is fully masked.
            known = sorted(self._secrets, key=len, reverse=True)
        for secret in known:
            text = text.replace(secret, MASK)
        for pattern, replacement in _PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def redact_obj(self, obj: Any) -> Any:
        """Recursively redact strings in dicts/lists; mask values under sensitive keys."""
        if isinstance(obj, str):
            return self.redact(obj)
        if isinstance(obj, Mapping):
            return {
                key: MASK
                if isinstance(key, str) and _SENSITIVE_KEY_RE.search(key)
                else self.redact_obj(value)
                for key, value in obj.items()
            }
        if isinstance(obj, list | tuple):
            return type(obj)(self.redact_obj(item) for item in obj)
        return obj
