# Статус реализации

Версия каркаса: `0.1.0`

Версия правил: `chinese-durak/0.2.0-draft`

## Готово

- [x] Структура C++20-библиотеки.
- [x] Компактная модель карт через `CardId` и `CardMask`.
- [x] Авторитетный `GameEngine`.
- [x] Поддержка двух и трёх игроков.
- [x] Базовый игровой цикл раунда.
- [x] Перевод до первой защиты.
- [x] Обратный перевод вдвоём.
- [x] Подкидывание после `TAKE`.
- [x] Конкурентные атакующие через множество `eligible_attackers`.
- [x] Native-тесты без внешнего test framework.
- [x] CMake и CTest.
- [x] pybind11 bindings.
- [x] Python smoke-тесты.
- [x] FastAPI health/readiness endpoints.
- [x] PostgreSQL 17 в Docker Compose.
- [x] PowerShell-команды для Windows.
- [x] Копия принятой спецификации в `docs/spec`.

## Не готово

- [ ] Постоянные комнаты.
- [ ] REST API лобби.
- [ ] WebSocket игровой сессии.
- [ ] Транзакционная запись действий.
- [ ] Персональный `PlayerView`.
- [ ] Переподключение.
- [ ] Frontend.
- [ ] Нагрузочные тесты.
- [ ] Нейросеть.

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
- pytest: 4 passed
- ruff: passed
- compileall: passed

Configuration:
- pyproject.toml parse: passed
- compose.yaml parse: passed

Docker runtime:
- not executed in the workspace because the Docker CLI/daemon is unavailable
- compose.yaml and the wheel used by its builder stage were verified separately
```
