from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from jarvis.core.config import DEFAULT_AI_MODEL, Settings


def test_defaults(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings()
    assert settings.ai_model == DEFAULT_AI_MODEL
    assert settings.user_title == "Boss"
    assert settings.language == "ru"
    assert not settings.has_api_key


def test_reads_env_file(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=sk-ant-test-1234567890abcdef\n"
        "JARVIS_USER_TITLE=Sir\n"
        "JARVIS_LOG_LEVEL=debug\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env)
    assert settings.has_api_key
    assert settings.user_title == "Sir"
    assert settings.log_level == "DEBUG"


def test_env_var_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LANGUAGE", "en")
    assert Settings(_env_file=None).language == "en"


def test_empty_api_key_means_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    assert not Settings(_env_file=None).has_api_key


def test_api_key_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-supersecret-value-123456")
    settings = Settings(_env_file=None)
    assert "supersecret" not in repr(settings)
    assert "supersecret" not in str(settings.model_dump())
    assert settings.secret_values() == ["sk-ant-supersecret-value-123456"]


def test_invalid_language_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LANGUAGE", "klingon")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_ai_defaults(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings()
    assert settings.ai_effort == "low"
    assert settings.ai_fallbacks is True
    assert settings.ai_max_turns == 30


def test_invalid_effort_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_AI_EFFORT", "turbo")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
