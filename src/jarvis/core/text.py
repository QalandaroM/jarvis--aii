"""Text normalization for user commands (typed now, transcribed from speech later)."""

from __future__ import annotations

import re

# "Jarvis, ...", "Джарвис ...", "Hey Jarvis: ..." — plus common speech-to-text misspellings.
_WAKE_WORD_RE = re.compile(
    r"^\s*(?:(?:hey|ok|okay|эй|окей)\s+)?"
    r"(?:jarvis|jarvis's|джарвис|джарвиз|жарвис)"
    r"(?=$|[\s,.:;!?-])[\s,.:;!?-]*",
    re.IGNORECASE,
)
_TRAILING_PUNCT_RE = re.compile(r"[\s.!?…]+$")


def strip_wake_word(text: str) -> str:
    """Remove a leading wake word: 'Jarvis, open YouTube' -> 'open YouTube'."""
    return _WAKE_WORD_RE.sub("", text, count=1).strip()


def normalize_command(text: str) -> str:
    """Canonical form used for matching built-in commands (stop/exit/help)."""
    command = strip_wake_word(text)
    command = _TRAILING_PUNCT_RE.sub("", command)
    return " ".join(command.lower().split())
