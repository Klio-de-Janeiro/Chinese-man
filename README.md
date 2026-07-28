# Китайский Дурак

Стартовый монорепозиторий сетевой карточной игры для 2–3 игроков.
В нём уже выделен независимый C++-движок, подготовлены Python bindings,
базовый FastAPI-сервис, тесты и Docker-инфраструктура с PostgreSQL.

Текущая версия правил движка: `chinese-durak/0.2.0-draft`.

## Что уже работает

- колода из 52 карт и раздача по 6 карт;
- выбор козыря и первого атакующего по младшему козырю;
- атака с ограничением `min(6, размер руки защищающегося в начале раунда)`;
- подкидывание по достоинствам, уже присутствующим на столе;
- защита старшей картой той же масти или козырем;
- перевод до первой защиты, включая обратный перевод в игре на двоих;
- команда «беру» и последующее подкидывание;
- успешная защита, отбой, добор и переход ролей;
- захват защищающимся всего стола, включая побитые пары;
- версия состояния как основа конкурентных команд и будущего replay;
- расчёт итоговых мест только на границе завершённого раунда.

Нативные тесты не зависят от стороннего тестового фреймворка. Они
собираются как обычная C++-программа и дополнительно регистрируются в CTest.

## Архитектура

```text
Web-клиент (следующий этап)
        │ HTTP / WebSocket
        ▼
FastAPI: комнаты, сессии, reconnect, persistence
        │ Python API
        ▼
pybind11-модуль chinese_durak._core
        │
        ▼
C++ GameEngine
  ├─ GameState
  ├─ Action validation
  ├─ State transitions
  └─ Action log / deterministic seed
        │
        ├─ PostgreSQL: snapshots и журналы
        └─ Self-play / ML simulator (этап 2)
```

Движок не знает об HTTP, базе данных, UI и сетевом времени. Сервер
авторитетно применяет действия через `GameEngine::apply`, а клиенты получают
только предназначенную им проекцию состояния.

Подробности находятся в [docs/architecture.md](docs/architecture.md), статус
реализации — в
[docs/implementation_status.md](docs/implementation_status.md), зафиксированные
правила — в каталоге `docs/spec`.

## Быстрый запуск через Docker Desktop

Требуются Docker Desktop с WSL 2 и PowerShell 7.

```powershell
Copy-Item .env.example .env
.\scripts\docker-up.ps1
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

Остановка контейнеров:

```powershell
.\scripts\docker-down.ps1
```

Команда сохраняет том PostgreSQL. `docker compose down --volumes` удалит
локальные данные базы.

## Локальная сборка на Windows

Нужны Python 3.11+, CMake 3.25+, Ninja и компилятор с поддержкой C++20.
Сценарий создаёт виртуальное окружение, ставит dev-зависимости и собирает
Python-модуль:

```powershell
.\scripts\bootstrap.ps1
.\scripts\test.ps1
```

Ручной вариант:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
cmake --preset native-debug
cmake --build --preset native-debug
ctest --preset native-debug
.\.venv\Scripts\python.exe -m pytest
```

## Минимальный Python API

```python
from chinese_durak import GameEngine

engine = GameEngine()
engine.start(player_count=2, seed=42, dealer=0)

state = engine.state
attacker = state["main_attacker"]
legal = engine.legal_actions(attacker)
engine.apply(attacker, legal[0])
```

Сетевой слой следующего milestone добавит к команде `expectedVersion`. Сервер
сравнит его с `state["version"]` до вызова движка. Так первое валидное
конкурентное подкидывание будет принято, а устаревшие команды получат новое
состояние и смогут повторить выбор.

## Структура репозитория

```text
engine/             C++20-модель, правила и нативные тесты
bindings/python/    pybind11-адаптер
python/             Python-пакет и smoke-тест bindings
apps/api/           FastAPI-сервис и API-тесты
docs/               архитектура, статус и спецификация правил
scripts/            PowerShell-команды для Windows
compose.yaml        API + PostgreSQL
```

## Следующий milestone

Следующий законченный срез — сервер комнат: создание игры, подключение
2–3 участников, приватные проекции состояния, WebSocket-события,
идемпотентные команды, reconnect в течение 120 секунд и сохранение
snapshot/action log в PostgreSQL. После него можно строить первый веб-стол,
не меняя контракт чистого игрового движка.
