"""`jarvis doctor` — environment self-check. Never prints secret values."""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from jarvis.core.config import Settings

MIN_PYTHON = (3, 11)


class Status(Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str


def _check_python() -> Check:
    version = ".".join(map(str, sys.version_info[:3]))
    if sys.version_info[:2] >= MIN_PYTHON:
        return Check("Python", Status.OK, version)
    need = ".".join(map(str, MIN_PYTHON))
    return Check("Python", Status.FAIL, f"{version}, нужен {need}+")


def _check_env_file(env_path: Path) -> Check:
    if env_path.is_file():
        return Check(".env", Status.OK, f"найден: {env_path.resolve()}")
    return Check(".env", Status.WARN, "не найден — скопируйте .env.example в .env")


def _check_api_key(settings: Settings) -> Check:
    if settings.has_api_key:
        return Check("ANTHROPIC_API_KEY", Status.OK, "задан (значение скрыто)")
    return Check("ANTHROPIC_API_KEY", Status.WARN, "не задан — понадобится с Этапа 2")


def _check_data_dir(settings: Settings) -> Check:
    try:
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=settings.data_dir):
            pass
    except OSError as exc:
        return Check("Папка данных", Status.FAIL, f"{settings.data_dir}: {exc.strerror}")
    return Check("Папка данных", Status.OK, f"{settings.data_dir.resolve()} (запись разрешена)")


def run_checks(settings: Settings, env_path: Path = Path(".env")) -> list[Check]:
    checks: list[Callable[[], Check]] = [
        _check_python,
        lambda: _check_env_file(env_path),
        lambda: _check_api_key(settings),
        lambda: _check_data_dir(settings),
    ]
    return [check() for check in checks]


def run_doctor(settings: Settings, output_fn: Callable[[str], None] = print) -> int:
    results = run_checks(settings)
    for check in results:
        output_fn(f"[{check.status.value:>4}] {check.name}: {check.detail}")
    output_fn(f"Модель AI: {settings.ai_model} | язык: {settings.language}")
    failed = any(check.status is Status.FAIL for check in results)
    output_fn("Итог: есть ошибки." if failed else "Итог: окружение готово.")
    return 1 if failed else 0
