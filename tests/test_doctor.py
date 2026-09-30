from __future__ import annotations

from collections.abc import Callable

from jarvis.core.config import Settings
from jarvis.doctor import Status, run_checks, run_doctor


def test_doctor_passes_without_key_but_warns(make_settings: Callable[..., Settings]) -> None:
    checks = {c.name: c for c in run_checks(make_settings())}
    assert checks["Python"].status is Status.OK
    assert checks["ANTHROPIC_API_KEY"].status is Status.WARN
    assert checks["Папка данных"].status is Status.OK


def test_doctor_never_prints_key(make_settings: Callable[..., Settings]) -> None:
    secret = "sk-ant-api03-DOCTORSECRET00000"
    settings = make_settings(anthropic_api_key=secret)
    lines: list[str] = []
    assert run_doctor(settings, output_fn=lines.append) == 0
    output = "\n".join(lines)
    assert "задан" in output
    assert "DOCTORSECRET" not in output
