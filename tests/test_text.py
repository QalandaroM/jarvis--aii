from __future__ import annotations

import pytest

from jarvis.core.text import normalize_command, strip_wake_word


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Jarvis, открой YouTube", "открой YouTube"),
        ("джарвис открой Chrome", "открой Chrome"),
        ("Hey Jarvis: what time is it?", "what time is it?"),
        ("  JARVIS!!  stop", "stop"),
        ("открой YouTube", "открой YouTube"),
        ("Jarvisland is a place", "Jarvisland is a place"),  # not a wake word
    ],
)
def test_strip_wake_word(raw: str, expected: str) -> None:
    assert strip_wake_word(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Jarvis, stop", "stop"),
        ("Джарвис, СТОП!", "стоп"),
        ("  stop.  ", "stop"),
        ("Jarvis", ""),
        ("Open   YouTube", "open youtube"),
    ],
)
def test_normalize_command(raw: str, expected: str) -> None:
    assert normalize_command(raw) == expected
