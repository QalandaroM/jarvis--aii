"""Application settings.

Values come from (highest priority first): environment variables, the `.env` file,
then the defaults below. Secrets are typed as `SecretStr`, so they never show up in
`repr()`, logs or tracebacks by accident — read them explicitly with `.get_secret_value()`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AI_MODEL = "claude-opus-5-5"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- AI Brain ---
    # ANTHROPIC_API_KEY is the name the official SDK uses, so accept it without the prefix.
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "JARVIS_ANTHROPIC_API_KEY"),
    )
    ai_model: str = DEFAULT_AI_MODEL

    # --- Personalization ---
    user_title: str = Field(default="Boss", min_length=1, max_length=40)
    language: Literal["ru", "en"] = "ru"

    # --- Storage & logging ---
    data_dir: Path = Path("data")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_to_console: bool = False

    @field_validator("anthropic_api_key", mode="before")
    @classmethod
    def _empty_key_is_none(cls, value: object) -> object:
        # `ANTHROPIC_API_KEY=` in .env should mean "not set", not "empty key".
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def has_api_key(self) -> bool:
        return self.anthropic_api_key is not None

    def secret_values(self) -> list[str]:
        """Every secret value held by the settings — used to register them for redaction."""
        secrets = [self.anthropic_api_key]
        return [s.get_secret_value() for s in secrets if s is not None]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
