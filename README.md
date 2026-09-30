# JARVIS

Персональный AI-ассистент для **Windows**, который понимает команды на естественном языке
и выполняет **разрешённые** действия на компьютере через систему инструментов (tools) под
контролем Safety Layer.

> Статус: **Этап 2 — AI Brain.** JARVIS разговаривает через Claude API, помнит контекст
> разговора и честно говорит, что действия на компьютере пока не подключены (tools — с Этапа 5).
> Архитектура и модель безопасности: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Требования

- Windows 10/11
- Python **3.11+** — https://www.python.org/downloads/ (при установке отметьте *Add python.exe to PATH*)
- Git — https://git-scm.com/download/win
- API-ключ Anthropic — https://console.anthropic.com/settings/keys

## Установка (PowerShell)

```powershell
git clone https://github.com/QalandaroM/jarvis--aii.git
cd jarvis--aii
git checkout claude/jarvis-ai-assistant-jwoha9

py -3.11 -m venv .venv          # или: python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"

copy .env.example .env
notepad .env                    # впишите ANTHROPIC_API_KEY=sk-ant-...
```

Уже установили Этап 1? Достаточно `git pull` и снова `pip install -e ".[dev]"`
(добавилась зависимость `anthropic`). Новые настройки — в `.env.example`.

## Запуск

Запускайте из корня проекта (там лежит `.env`), с активированным `.venv`:

```powershell
jarvis doctor            # проверка окружения (без интернета)
jarvis doctor --online   # + проверка API-ключа и модели (токены не тратятся)
jarvis                   # текстовый режим
python -m jarvis         # то же самое без entry point
```

Встроенные команды (обрабатываются **до** AI, работают всегда):

| Команда | Действие |
|---|---|
| `stop`, `стоп`, `Jarvis, stop` | экстренная остановка текущей цепочки действий |
| `reset`, `сброс`, `новый разговор` | забыть текущий разговор |
| `exit`, `выход` | завершить работу |
| `help`, `помощь` | справка |
| `Ctrl+C` во время ответа | отменить текущий запрос (сессия продолжается) |

## Тесты и проверки качества

```powershell
pytest          # unit-тесты (без сети и без API-ключа)
ruff check .    # линтер (включая правила безопасности bandit — S)
mypy src        # проверка типов
```

## Где что хранится

| Что | Где |
|---|---|
| Секреты (API keys) | `.env` (в `.gitignore`) |
| Настройки | `.env` / переменные окружения `JARVIS_*` |
| Логи | `data\logs\jarvis.log` (секреты маскируются, текст команд не пишется) |
| Контекст разговора | только в памяти процесса (долговременная память — Этап 12) |

## План разработки

1. ✅ Базовый проект и окружение
2. ✅ AI Brain
3. Speech-to-Text
4. Text-to-Speech
5. Tool Registry
6. Safety Layer
7. Permission Manager
8. Первый безопасный tool
9. Управление приложениями
10. Браузер
11. Файловая система
12. Память
13. Планирование нескольких действий
14. Audit Logger и Emergency Stop
15. Тесты и усиление безопасности
