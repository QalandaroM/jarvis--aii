from __future__ import annotations

from collections.abc import Callable

import anthropic

from jarvis.core.config import Settings
from jarvis.doctor import Status, _check_api_online, run_checks, run_doctor
from tests.fakes import status_error


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


def test_online_check_ok(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings(anthropic_api_key="sk-ant-api03-0000000000000000")
    check = _check_api_online(settings, probe=lambda _: "Claude Opus 5.5")
    assert check.status is Status.OK and "Claude Opus 5.5" in check.detail


def test_online_check_bad_key(make_settings: Callable[..., Settings]) -> None:
    settings = make_settings(anthropic_api_key="sk-ant-api03-0000000000000000")

    def probe(_: Settings) -> str:
        raise status_error(anthropic.AuthenticationError, 401)

    check = _check_api_online(settings, probe=probe)
    assert check.status is Status.FAIL and "отклонён" in check.detail


def test_online_check_without_key(make_settings: Callable[..., Settings]) -> None:
    assert _check_api_online(make_settings()).status is Status.FAIL
