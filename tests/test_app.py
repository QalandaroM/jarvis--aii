from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from jarvis.app import JarvisApp, StubResponder
from jarvis.core.config import Settings


class RecordingResponder:
    def __init__(self) -> None:
        self.received: list[str] = []

    def respond(self, command: str) -> str:
        self.received.append(command)
        return f"ok: {command}"

    def reset(self) -> None:
        pass


class FailingResponder:
    def respond(self, command: str) -> str:
        raise RuntimeError("AI down")

    def reset(self) -> None:
        pass


@pytest.fixture
def settings(make_settings: Callable[..., Settings]) -> Settings:
    return make_settings()


@pytest.mark.parametrize("raw", ["Jarvis, stop", "стоп", "Джарвис, хватит!", "STOP"])
def test_stop_never_reaches_responder(settings: Settings, raw: str) -> None:
    responder = RecordingResponder()
    reply = JarvisApp(settings, responder).handle(raw)
    assert reply is not None
    assert "Остановлено" in reply.text
    assert not reply.should_exit
    assert responder.received == []


@pytest.mark.parametrize("raw", ["exit", "Jarvis, выход", "quit"])
def test_exit(settings: Settings, raw: str) -> None:
    reply = JarvisApp(settings, StubResponder()).handle(raw)
    assert reply is not None and reply.should_exit


def test_regular_command_goes_to_responder_without_wake_word(settings: Settings) -> None:
    responder = RecordingResponder()
    reply = JarvisApp(settings, responder).handle("Jarvis, открой YouTube")
    assert responder.received == ["открой YouTube"]
    assert reply is not None and reply.text == "ok: открой YouTube"


@pytest.mark.parametrize("raw", ["", "   ", "Jarvis,"])
def test_empty_input_ignored(settings: Settings, raw: str) -> None:
    assert JarvisApp(settings, RecordingResponder()).handle(raw) is None


def test_responder_error_reported_as_not_executed(settings: Settings) -> None:
    reply = JarvisApp(settings, FailingResponder()).handle("сделай что-нибудь")
    assert reply is not None
    assert "НЕ выполнена" in reply.text


def test_run_loop_until_exit(settings: Settings) -> None:
    inputs: Iterator[str] = iter(["", "привет", "exit", "never reached"])
    outputs: list[str] = []
    app = JarvisApp(
        settings, RecordingResponder(), input_fn=lambda _: next(inputs), output_fn=outputs.append
    )
    assert app.run() == 0
    assert outputs[1] == "ok: привет"
    assert "До связи" in outputs[-1]


def test_run_loop_handles_ctrl_c(settings: Settings) -> None:
    def interrupt(_: str) -> str:
        raise KeyboardInterrupt

    app = JarvisApp(settings, StubResponder(), input_fn=interrupt, output_fn=lambda _: None)
    assert app.run() == 0


def test_user_title_used(make_settings: Callable[..., Settings]) -> None:
    reply = JarvisApp(make_settings(user_title="Sir"), StubResponder()).handle("exit")
    assert reply is not None and "Sir" in reply.text


class ResettableResponder(RecordingResponder):
    def __init__(self) -> None:
        super().__init__()
        self.resets = 0

    def reset(self) -> None:
        self.resets += 1


@pytest.mark.parametrize("raw", ["reset", "Jarvis, новый разговор", "сброс"])
def test_reset_command(settings: Settings, raw: str) -> None:
    responder = ResettableResponder()
    reply = JarvisApp(settings, responder).handle(raw)
    assert reply is not None and "новый разговор" in reply.text
    assert responder.resets == 1
    assert responder.received == []


def test_ctrl_c_during_command_cancels_only_that_command(settings: Settings) -> None:
    class SlowResponder(RecordingResponder):
        def respond(self, command: str) -> str:
            if command == "долгий запрос":
                raise KeyboardInterrupt
            return super().respond(command)

    inputs: Iterator[str] = iter(["долгий запрос", "привет", "exit"])
    outputs: list[str] = []
    app = JarvisApp(
        settings, SlowResponder(), input_fn=lambda _: next(inputs), output_fn=outputs.append
    )
    assert app.run() == 0
    assert "Отменено, Boss." in outputs
    assert "ok: привет" in outputs


def test_stub_explains_missing_key(settings: Settings) -> None:
    reply = JarvisApp(settings, StubResponder()).handle("привет")
    assert reply is not None and "ANTHROPIC_API_KEY" in reply.text
