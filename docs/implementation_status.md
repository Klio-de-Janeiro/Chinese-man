# Статус реализации

Версия приложения: `0.3.0`

Версия правил: `chinese-durak/0.2.1-draft`

## Готово

- [x] Структура C++20-библиотеки.
- [x] Компактная модель карт через `CardId` и `CardMask`.
- [x] Авторитетный `GameEngine`.
- [x] Поддержка двух и трёх игроков.
- [x] Базовый игровой цикл раунда.
- [x] Перевод до первой защиты.
- [x] Обратный перевод вдвоём.
- [x] Подкидывание после `TAKE`.
- [x] Перенос накопленного отбоя в руку взявшего игрока.
- [x] Конкурентные атакующие через множество `eligible_attackers`.
- [x] Native-тесты без внешнего test framework.
- [x] CMake и CTest.
- [x] pybind11 bindings.
- [x] Python smoke-тесты.
- [x] FastAPI health/readiness endpoints.
- [x] PostgreSQL 17 в Docker Compose.
- [x] PowerShell-команды для Windows.
- [x] Копия принятой спецификации в `docs/spec`.
- [x] Приватные комнаты на 2–3 игроков.
- [x] REST create/join/reconnect API.
- [x] WebSocket-синхронизация.
- [x] Персональные состояния без утечки чужих рук.
- [x] `expectedVersion` для конкурентных команд.
- [x] Пауза и reconnect timeout 120 секунд.
- [x] Адаптивный web-интерфейс Modern Arena.
- [x] LAN-запуск web + API через Docker Compose.
- [x] Безопасный разбор `snapshot`, `pong` и `error` WebSocket-сообщений.
- [x] PostgreSQL без конфликта с хостовым портом `5432`.
- [x] UUID действий с fallback для LAN-браузеров без `crypto.randomUUID()`.
- [x] Одна визуальная карта на достоинство с выбором масти.
- [x] Сортировка `2 → A` и подсветка козыря внутри группы.
- [x] Масть и достоинство открытого козыря в игровом снимке.
- [x] Приватный ML-контракт без скрытых карт.
- [x] Прямой self-play поверх C++-движка.
- [x] Random, greedy и heuristic reference agents.
- [x] Параллельная генерация Parquet-датасета.
- [x] Policy-value сеть с динамическими legal actions.
- [x] Imitation learning.
- [x] PPO self-play с историческими checkpoints.
- [x] Paired-seed evaluation со сменой мест.
- [x] Проверяемый экспорт ONNX.
- [x] ONNX Runtime с эвристическим fallback.
- [x] Комнаты «человек против AI».

## Не готово

- [ ] Постоянные комнаты в PostgreSQL.
- [ ] Транзакционная запись действий.
- [ ] Восстановление после перезапуска API.
- [ ] Идемпотентный `clientActionId`.
- [ ] Нагрузочные тесты.
- [ ] Обученные release-веса `bot_v1` после длительного GPU-run.
- [ ] Автоматический model registry и promotion gate.

## Проверки milestone

```text
Native engine (GCC 13.3, C++20):
- CMake configure/build: passed
- CTest: 1/1 passed
- ASan + UBSan: passed
- 100 random legal-play games with invariants: passed

Python 3.12:
- editable pybind11 build: passed
- non-editable wheel build: passed
- pytest: 19 passed, 1 optional PyTorch test skipped
- ruff: passed
- compileall: passed

ML simulator:
- 64 teacher games: 10,704 decisions in one Parquet shard
- two-process generation: 16 games, 2,710 decisions, two valid shards
- heuristic benchmark: 101.46 games/s and 8,833 decisions/s
- full human-versus-AI room completion: passed
- long PyTorch training and release ONNX export: not run in this workspace

Web:
- ESLint: passed
- Vinext production build: passed
- Sites artifact validation: passed
- rendered HTML test: passed
- Node tests: 12 passed
- real HTTP + two-WebSocket smoke test, including ping/pong: passed

Configuration:
- pyproject.toml parse: passed
- compose.yaml parse: passed

Docker runtime:
- not executed in the workspace because the Docker CLI/daemon is unavailable
- compose.yaml, web build and API wheel were verified separately
```
