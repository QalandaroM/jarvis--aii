from __future__ import annotations

import logging
from collections.abc import Callable

import pytest

from jarvis.core.config import Settings
from jarvis.core.logging_setup import setup_logging
from jarvis.core.redaction import MASK, Redactor


@pytest.mark.parametrize(
    "text",
    [
        "key is sk-ant-api03-abcdefghijklmnop1234",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig",
        "password=hunter2hunter2",
        'api_key: "abc123def456"',
        "token = 'zzzzzzzz'",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        "AKIAABCDEFGHIJKLMNOP",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nabc\n-----END RSA PRIVATE KEY-----",
    ],
)
def test_patterns_are_masked(text: str) -> None:
    result = Redactor().redact(text)
    assert MASK in result
    for fragment in (
        "abcdefghijklmnop1234",
        "payload.sig",
        "hunter2",
        "abc123def456",
        "zzzzzzzz",
        "0123456789",
        "ABCDEFGHIJKLMNOP",
        "MIIEow",
    ):
        assert fragment not in result


def test_registered_secret_masked() -> None:
    redactor = Redactor()
    redactor.register_secret("my-very-private-value")
    assert redactor.redact("value=my-very-private-value!").count("my-very-private") == 0


def test_short_values_not_registered() -> None:
    redactor = Redactor()
    redactor.register_secret("ab")
    assert redactor.redact("abc tab") == "abc tab"


def test_plain_text_untouched() -> None:
    text = "Jarvis, открой YouTube и найди Python tutorials"
    assert Redactor().redact(text) == text


def test_redact_obj_masks_sensitive_keys() -> None:
    data = {"user": "Boss", "Password": "x", "nested": [{"api_key": "y"}, "sk-ant-" + "a" * 20]}
    result = Redactor().redact_obj(data)
    assert result["user"] == "Boss"
    assert result["Password"] == MASK
    assert result["nested"][0]["api_key"] == MASK
    assert result["nested"][1] == MASK


def test_log_file_never_contains_api_key(
    make_settings: Callable[..., Settings], monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "sk-ant-api03-REALLYSECRET000000"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    settings = make_settings()
    setup_logging(settings, Redactor())
    log = logging.getLogger("jarvis.test")
    log.info("calling API with %s", secret)
    try:
        raise RuntimeError(f"failed with key {secret}")
    except RuntimeError:
        log.exception("boom")
    for handler in logging.getLogger("jarvis").handlers:
        handler.flush()

    content = (settings.logs_dir / "jarvis.log").read_text(encoding="utf-8")
    assert "calling API with" in content
    assert "boom" in content
    assert "REALLYSECRET" not in content
