# Китайский Дурак

Играбельный локальный web-MVP переводного «Китайского Дурака» для 2–3
участников. Один игрок запускает проект через Docker Desktop, создаёт
приватную комнату и отправляет ссылку остальным устройствам в той же сети.

Версия приложения: `0.2.0`.

Версия правил: `chinese-durak/0.2.0-draft`.

## Что реализовано

- создание приватной комнаты без регистрации;
- комнаты на двух или трёх игроков;
- подключение по ссылке или шестизначному коду;
- приватный токен места, сохранённый только в браузере;
- WebSocket-обновления без перезагрузки страницы;
- персональная проекция: игрок видит только свою руку;
- авторитетная проверка действий C++-движком;
- защита от устаревших конкурентных команд через `expectedVersion`;
- атака, защита, перевод, «Беру», доподкидывание и «Бито»;
- пауза и 120 секунд на переподключение;
- журнал последних действий;
- индикаторы мастей над каждой картой руки;
- адаптивный интерфейс для компьютера, планшета и телефона;
- демонстрационный стол, который можно открыть без сервера комнаты.

Комнаты и текущие партии пока хранятся в памяти API-процесса. Перезапуск
контейнера `api` завершит активные комнаты. PostgreSQL уже присутствует в
инфраструктуре; постоянные snapshots и action log — следующий этап.

## Самый быстрый запуск

Требуются:

- Windows 10/11;
- Docker Desktop;
- PowerShell;
- оба устройства подключены к одной локальной сети.

Откройте PowerShell в корне проекта:

```powershell
Copy-Item .env.example .env
.\scripts\docker-up.ps1
```

Сценарий напечатает две ссылки:

```text
Игра на этом компьютере:
  http://localhost:3000

Ссылка для игроков в локальной сети:
  http://192.168.x.x:3000
```

Далее:

1. Откройте `http://localhost:3000`.
2. Укажите имя и выберите два игрока.
3. Нажмите «Создать приватную комнату».
4. Скопируйте ссылку-приглашение. Сценарий запуска автоматически подставит
   в неё LAN-адрес вместо `localhost`.
5. Откройте ссылку на втором компьютере или телефоне.
6. Второй игрок вводит своё имя и занимает свободное место.
7. После подключения всех участников движок автоматически раздаст карты.

Остановить приложение:

```powershell
.\scripts\docker-down.ps1
```

Том PostgreSQL при этом сохраняется.

## Если второе устройство не открывает ссылку

Сначала повторно выведите LAN-адрес:

```powershell
.\scripts\network-info.ps1
```

Проверьте:

1. Оба устройства подключены к одному Wi-Fi или одному роутеру.
2. В Windows выбран тип сети «Частная сеть».
3. Docker Desktop работает.
4. Порты `3000` и `8000` не заняты.
5. Брандмауэр Windows разрешил Docker Desktop принимать подключения.

При необходимости откройте PowerShell от администратора и добавьте отдельные
правила:

```powershell
New-NetFirewallRule `
  -DisplayName "Chinese Durak Web" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 3000 `
  -Action Allow

New-NetFirewallRule `
  -DisplayName "Chinese Durak API" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow
```

## Проверка сервисов

Web-интерфейс:

```text
http://localhost:3000
```

Проверка C++-движка внутри API:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Проверка API вместе с PostgreSQL:

```powershell
Invoke-RestMethod http://localhost:8000/ready
```

Swagger:

```text
http://localhost:8000/docs
```

Логи:

```powershell
docker compose logs -f web api
```

## Локальная сборка без Docker

Нужны Node.js 22+, Python 3.12 и компилятор C++20. На Windows рекомендуется
Visual Studio Build Tools с компонентом «Разработка классических приложений
на C++».

```powershell
.\scripts\bootstrap.ps1
.\scripts\test.ps1
```

Запуск API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn `
  app.main:app `
  --app-dir apps/api `
  --host 0.0.0.0 `
  --port 8000
```

В другом окне PowerShell:

```powershell
npm run dev -- --host 0.0.0.0 --port 3000
```

Реальный smoke-тест двух WebSocket-клиентов:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_multiplayer.py
```

## Архитектура

```text
Браузер игрока A ─┐
                  ├─ REST + WebSocket ─> FastAPI RoomService
Браузер игрока B ─┘                         │
                                           ├─ seat token
                                           ├─ expectedVersion
                                           ├─ private PlayerView
                                           └─ pybind11
                                                │
                                                ▼
                                          C++ GameEngine
                                                │
                      ┌─────────────────────────┴─────────────┐
                      ▼                                       ▼
                GameState                               legal_actions()
```

Главное правило архитектуры: React и FastAPI не решают, можно ли положить
карту. Они только передают команду. Единственным источником игровых правил
остаётся `GameEngine`.

## Структура

```text
app/                    React/Vinext UI
apps/api/               FastAPI, комнаты и WebSocket
apps/web/Dockerfile     локальный web-контейнер
engine/                 чистый C++20 GameEngine
bindings/python/        pybind11-модуль
python/                 Python package и smoke-тесты
docs/spec/              принятая спецификация правил
scripts/                запуск, тесты и LAN-диагностика
compose.yaml            web + API + PostgreSQL
```

Подробный статус находится в
[`docs/implementation_status.md`](docs/implementation_status.md).
