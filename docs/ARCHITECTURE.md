# JARVIS — архитектура

## 1. Технологический стек

| Задача | Выбор | Почему |
|---|---|---|
| Язык | **Python 3.11+** | Лучшая экосистема для AI, голоса и автоматизации ОС; официальный Anthropic SDK; `tomllib` в stdlib |
| AI Brain | **Anthropic Claude API** (официальный SDK `anthropic`), модель `claude-opus-5-5` | Нативный tool use (JSON Schema + `strict: true`), сильное планирование многошаговых задач. Цикл tool use пишем **сами** (manual loop), чтобы между «модель предложила вызов» и «вызов выполнен» всегда стоял наш Safety Layer |
| Speech-to-Text | **faster-whisper** (локально) + `sounddevice` для микрофона | Работает офлайн, голос не уходит в облако, хорошо понимает русский |
| Text-to-Speech | **Piper** (локально, нейронные голоса, есть русские) с fallback на **pyttsx3** (голоса ОС) | Офлайн, бесплатно, без передачи текста наружу |
| Поиск в интернете | Серверный tool Claude **web search** | Официальный, без отдельного ключа; результаты — недоверенные данные |
| Браузер | `webbrowser` (stdlib) для «открой сайт» + **Playwright** для управления | Playwright — официальный, поддерживаемый, изолированный профиль браузера |
| Системная информация | **psutil** | Кроссплатформенно, без shell |
| Запуск приложений | `subprocess` со **списком аргументов** (без `shell=True`) + allowlist приложений | Нет shell-инъекций |
| Напоминания | **APScheduler** + SQLite job store | Переживает перезапуск |
| Память / история | **SQLite** (stdlib `sqlite3`) | Один локальный файл, транзакции, без сервера |
| Настройки | **pydantic-settings** (`.env` + переменные окружения), политики — TOML | Строгая валидация при старте, `SecretStr` для секретов |
| Секреты | `.env` (в `.gitignore`), позже опционально `keyring` (хранилище ОС) | Никаких ключей в коде |
| Emergency Stop | `threading.Event` (CancellationToken) + голос/текст «stop» + горячая клавиша (`pynput`) | Проверяется между каждым шагом и внутри долгих tools |
| Тесты / качество | pytest, ruff (включая правила bandit `S`), mypy strict | |

## 2. Поток обработки команды

```
User ─► Voice/Text Input ─► Speech-to-Text ─► [Built-in: stop/exit/help] ─► AI Brain
                                                                              │
                                                       план + предложенный tool call
                                                                              ▼
                                  ┌──────────────── для КАЖДОГО шага ──────────────────┐
                                  │ Emergency Stop? ─► Safety Layer (валидация, риск,   │
                                  │ лимиты, fail-closed) ─► Permission Manager          │
                                  │ (подтверждение пользователя) ─► Tool Execution      │
                                  │ (timeout) ─► Result Validation ─► Audit Log          │
                                  └─────────────────────────────────────────────────────┘
                                                                              │
                                         фактический результат (как ДАННЫЕ) ─► AI Brain
                                                                              ▼
                                                        Text-to-Speech / текст ─► User
```

Ключевые правила:

- **AI только предлагает.** Модель возвращает `tool_use`; выполняет его наш код и только после Safety Layer.
- **Stop обрабатывается до AI** — работает, даже если AI завис или недоступен.
- **Fail closed.** Неизвестный tool, невалидные аргументы, неизвестный уровень риска → отказ / уточнение.
- **Внешний контент = данные.** Результаты tools передаются модели как `tool_result`, помечены как недоверенные; они не могут менять системный промпт, политику или разрешения.
- **Результат — только фактический.** Ответ пользователю строится из реального `ToolResult` (success / partial / failed).

## 3. Структура проекта

```
jarvis--aii/
├── pyproject.toml            # зависимости, entry point, настройки ruff/mypy/pytest
├── .env.example              # шаблон настроек (реальный .env — в .gitignore)
├── docs/ARCHITECTURE.md
├── config/                   # (Этап 6+) policy.toml, apps.toml — allowlist'ы и уровни риска
├── data/                     # runtime: logs/, memory.db, audit.jsonl (в .gitignore)
├── src/jarvis/
│   ├── main.py               # CLI: jarvis [chat|doctor]
│   ├── app.py                # цикл ввода, встроенные команды, делегирование в AI
│   ├── doctor.py             # самопроверка окружения
│   ├── core/                 # общая инфраструктура
│   │   ├── config.py         #   Settings (pydantic-settings)
│   │   ├── logging_setup.py  #   логирование с маскировкой секретов
│   │   ├── redaction.py      #   Redactor — общий для логов и audit
│   │   └── text.py           #   wake word, нормализация команд
│   ├── ai/                   # (2, 13) brain.py, prompts.py, planner.py
│   ├── voice/                # (3, 4) stt.py, tts.py, microphone.py
│   ├── tools/                # (5, 8–11) base.py, registry.py, builtin/*.py
│   ├── safety/               # (6, 15) policy.py, validators.py, paths.py, limits.py
│   ├── permissions/          # (7) manager.py — подтверждения пользователя
│   ├── memory/               # (12) short_term.py, long_term.py, history.py
│   └── audit/                # (14) logger.py, emergency_stop.py
└── tests/
```

Каждый tool — отдельный класс с декларацией (имя, описание, JSON Schema параметров, уровень
риска, разрешения, timeout) и методом `run()`. Регистрация — одной строкой в реестре;
остальная система (Safety, Permissions, AI) не меняется при добавлении нового tool.

## 4. Модель безопасности (сводка)

| Уровень | Примеры | Поведение |
|---|---|---|
| LOW | открыть сайт/приложение из allowlist, поиск, чтение обычного файла, sysinfo | автоматически |
| MEDIUM | создать/изменить файл, изменить настройки | подтверждение (настраивается) |
| HIGH | удаление, выключение ПК, необратимые действия, передача данных наружу | **всегда** явное подтверждение прямо перед выполнением, с описанием последствий |
| UNKNOWN | всё, что не удалось классифицировать | **запрещено** (fail closed) |

Подтверждение — только однозначное «да» на конкретное действие; оно не распространяется на
другие действия и не сохраняется как постоянное разрешение.
