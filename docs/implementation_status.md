# Статус реализации

Версия приложения: `0.2.0`

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
- [x] Приватные комнаты на 2–3 игроков.
- [x] REST create/join/reconnect API.
- [x] WebSocket-синхронизация.
- [x] Персональные состояния без утечки чужих рук.
- [x] `expectedVersion` для конкурентных команд.
- [x] Пауза и reconnect timeout 120 секунд.
- [x] Адаптивный web-интерфейс Modern Arena.
- [x] LAN-запуск web + API через Docker Compose.

## Не готово

- [ ] Постоянные комнаты в PostgreSQL.
- [ ] Транзакционная запись действий.
- [ ] Восстановление после перезапуска API.
- [ ] Идемпотентный `clientActionId`.
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
- pytest: 7 passed
- ruff: passed
- compileall: passed

Web:
- ESLint: passed
- Vinext production build: passed
- Sites artifact validation: passed
- rendered HTML test: passed

Configuration:
- pyproject.toml parse: passed
- compose.yaml parse: passed

Docker runtime:
- not executed in the workspace because the Docker CLI/daemon is unavailable
- compose.yaml, web build and API wheel were verified separately
```
