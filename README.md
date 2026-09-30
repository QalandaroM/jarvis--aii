# JARVIS

Персональный AI-ассистент, который понимает команды на естественном языке и выполняет
**разрешённые** действия на компьютере через систему инструментов (tools) под контролем
Safety Layer.

> Статус: **Этап 1 — базовый проект и окружение.** AI Brain подключается на Этапе 2.
> Архитектура, выбор технологий и модель безопасности: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Требования

- Python **3.11+** (`python --version`)
- Git

## Установка

```bash
git clone https://github.com/QalandaroM/jarvis--aii.git
cd jarvis--aii
git checkout claude/jarvis-ai-assistant-jwoha9

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -e ".[dev]"

# Windows: copy .env.example .env
cp .env.example .env
```

Откройте `.env` и при желании впишите `ANTHROPIC_API_KEY` (обязателен с Этапа 2).

## Запуск

Запускайте из корня проекта (там лежит `.env`):

```bash
jarvis doctor     # проверка окружения
jarvis            # текстовый режим
python -m jarvis  # то же самое без entry point
```

Встроенные команды (обрабатываются **до** AI, работают всегда):

| Команда | Действие |
|---|---|
| `stop`, `стоп`, `Jarvis, stop` | экстренная остановка текущей цепочки действий |
| `exit`, `выход` | завершить работу |
| `help`, `помощь` | справка |

## Тесты и проверки качества

```bash
pytest          # unit-тесты
ruff check .    # линтер (включая правила безопасности bandit — S)
mypy src        # проверка типов
```

## Где что хранится

| Что | Где |
|---|---|
| Секреты (API keys) | `.env` (в `.gitignore`) |
| Настройки | `.env` / переменные окружения `JARVIS_*` |
| Логи | `data/logs/jarvis.log` (секреты маскируются) |
| Память, audit log | `data/` (появятся на Этапах 12 и 14) |

## План разработки

1. ✅ Базовый проект и окружение
2. AI Brain
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
