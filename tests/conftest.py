"""Shared fixtures: every test runs with a clean environment and a temp working dir."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from jarvis.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.startswith("JARVIS_") or name == "ANTHROPIC_API_KEY":
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)  # a developer's real .env is never picked up
    get_settings.cache_clear()


@pytest.fixture
def make_settings(tmp_path: Path) -> Callable[..., Settings]:
    def _make(**overrides: Any) -> Settings:
        overrides.setdefault("data_dir", tmp_path / "data")
        return Settings(_env_file=None, **overrides)

    return _make
