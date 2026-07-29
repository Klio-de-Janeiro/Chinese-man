# Действия и сетевой протокол

Версия: `0.2.1-draft`

## 1. Принцип

Браузер передаёт серверу не новое состояние, а намерение игрока.

Неверно:

```json
{
  "newHand": [],
  "newTable": []
}
```

Правильно:

```json
{
  "kind": "defend",
  "cardId": 31,
  "targetSlot": 2
}
```

Только сервер формирует новое состояние.

## 2. Кодирование карт

Предлагаемая формула:

\[
\operatorname{cardId}
=
13 \cdot \operatorname{suit}
+ \operatorname{rank}.
\]

Масти:

```text
0 = clubs
1 = diamonds
2 = hearts
3 = spades
```

Достоинства:

```text
0 = 2
1 = 3
...
8 = 10
9 = J
10 = Q
11 = K
12 = A
```

Диапазон `cardId`:

```text
0..51
```

## 3. Игровые действия

### 3.1. Атака

```json
{
  "kind": "attack",
  "cardId": 7
}
```

### 3.2. Защита

```json
{
  "kind": "defend",
  "cardId": 31,
  "targetSlot": 2
}
```

### 3.3. Перевод

```json
{
  "kind": "transfer",
  "cardId": 18
}
```

### 3.4. Взятие

```json
{
  "kind": "take"
}
```

### 3.5. Пас атакующего

```json
{
  "kind": "pass_attack"
}
```

## 4. Оболочка команды

```json
{
  "type": "game.action",
  "gameId": "0198f0cf-8ac6-7bd9-934d-7f929c4d9112",
  "clientActionId": "0198f0d0-2e80-70d0-bef0-f9509fc57ca4",
  "expectedVersion": 17,
  "action": {
    "kind": "defend",
    "cardId": 31,
    "targetSlot": 2
  }
}
```

### `clientActionId`

Уникальный идентификатор попытки действия. Повторно полученная команда с тем же
идентификатором не применяется второй раз.

### `expectedVersion`

Версия состояния, которую видел клиент при выборе действия.

Если актуальная версия отличается, сервер возвращает ошибку
`STALE_STATE` и новый snapshot.

В фазах конкурентного подкидывания несколько игроков могут отправить команды
с одинаковой `expectedVersion`. Сервер применяет только первую корректную
команду, успевшую получить блокировку партии.

## 5. Серверный конвейер

```text
WebSocket-команда
        ↓
Проверка сессии и места игрока
        ↓
Проверка clientActionId
        ↓
Блокировка строки партии
        ↓
Проверка expectedVersion
        ↓
GameEngine.legalActions(player)
        ↓
GameEngine.apply(action)
        ↓
Сохранение action + snapshot
        ↓
COMMIT
        ↓
Персональная рассылка PlayerView
```

## 5.1. Семантика «кто быстрее подкинет»

Скорость определяется не временем на компьютере игрока, а порядком успешной
серверной фиксации.

Пример:

```text
A отправляет ATTACK для версии 42
C отправляет ATTACK для версии 42
        ↓
команда C первой блокирует партию
        ↓
команда C создаёт версию 43
        ↓
команда A получает STALE_STATE
```

Если карта A всё ещё допустима в версии `43`, клиент A может отправить новое
действие уже с `expectedVersion = 43`.

Клиентские timestamps не учитываются: ими можно манипулировать.

## 6. Типы сообщений сервера

### `game.snapshot`

Полное разрешённое представление состояния для конкретного игрока.

### `game.event`

Публичное или приватное событие для анимации.

### `game.error`

Ошибка команды.

### `room.presence`

Изменение подключения или готовности игрока.

### `game.paused`

Партия приостановлена из-за отключения.

### `game.finished`

Финальный результат.

## 7. PlayerView

Пример:

```json
{
  "gameId": "0198f0cf-8ac6-7bd9-934d-7f929c4d9112",
  "version": 18,
  "rulesVersion": "chinese-durak/0.2.1-draft",
  "phase": "defense",
  "viewerPlayerId": "player-b",
  "currentActorId": "player-b",
  "eligibleAttackerIds": [],
  "mainAttackerId": "player-a",
  "defenderId": "player-b",
  "trumpSuit": "hearts",
  "deckCount": 27,
  "attackCount": 2,
  "attackLimit": 6,
  "transferLocked": false,
  "takeDeclared": false,
  "passedAttackerIds": [],
  "ownHand": [4, 17, 31, 43, 48],
  "players": [
    {
      "id": "player-a",
      "seat": 0,
      "cardCount": 5,
      "connected": true,
      "role": "main_attacker"
    },
    {
      "id": "player-b",
      "seat": 1,
      "cardCount": 5,
      "connected": true,
      "role": "defender"
    },
    {
      "id": "player-c",
      "seat": 2,
      "cardCount": 6,
      "connected": true,
      "role": "additional_attacker"
    }
  ],
  "table": [
    {
      "slot": 0,
      "attackCardId": 5,
      "defenseCardId": null
    },
    {
      "slot": 1,
      "attackCardId": 18,
      "defenseCardId": null
    }
  ],
  "legalActions": []
}
```

Поле `ownHand` всегда содержит только руку получателя сообщения.

В `DEFENSE` поле `currentActorId` содержит защитника, а
`eligibleAttackerIds` пусто.

В `ATTACK_EXTENSION` и `THROW_AFTER_TAKE`:

- `currentActorId` равен `null`;
- `eligibleAttackerIds` содержит всех атакующих;
- каждый клиент получает собственный список `legalActions`;
- пасовавший игрок не получает `ATTACK`, пока другой игрок не добавит карту.

## 8. Представление легальных действий

Для первой версии можно отправлять явный список:

```json
[
  {
    "kind": "defend",
    "cardId": 31,
    "targetSlot": 0
  },
  {
    "kind": "transfer",
    "cardId": 17
  },
  {
    "kind": "take"
  }
]
```

Это проще и безопаснее, чем заставлять frontend повторять правила.

Позже для нейросети этот список преобразуется в фиксированную битовую маску.

## 9. Публичные игровые события

```text
GAME_STARTED
CARD_ATTACKED
CARD_DEFENDED
ATTACK_TRANSFERRED
TAKE_DECLARED
ATTACKER_PASSED
ROUND_BEATEN
TABLE_TAKEN
CARDS_DRAWN
PLAYER_FINISHED
GAME_FINISHED
```

`CARDS_DRAWN` имеет две формы:

- публичная: кто и сколько карт получил;
- приватная: идентификаторы карт только получателю.

## 10. Коды ошибок

| Код | Причина |
|---|---|
| `UNAUTHENTICATED` | Нет действительной игровой сессии |
| `NOT_A_PLAYER` | Пользователь не занимает место в партии |
| `GAME_NOT_ACTIVE` | Партия ещё не началась или завершена |
| `NOT_YOUR_TURN` | Сейчас действует другой игрок |
| `NOT_ELIGIBLE_ATTACKER` | Игрок не входит в множество атакующих |
| `ATTACKER_ALREADY_PASSED` | Игрок уже пасовал после последней атаки |
| `STALE_STATE` | Клиент использовал устаревшую версию |
| `DUPLICATE_ACTION` | Команда уже была обработана |
| `CARD_NOT_IN_HAND` | Выбранной карты нет в руке |
| `INVALID_TARGET` | Слот защиты не существует |
| `ILLEGAL_ATTACK_RANK` | Достоинство нельзя подкинуть |
| `CARD_DOES_NOT_BEAT` | Карта не бьёт выбранную атаку |
| `TRANSFER_LOCKED` | В раунде уже началась защита |
| `TAKE_ALREADY_DECLARED` | Защитник уже объявил взятие |
| `DEFENSE_CLOSED_AFTER_TAKE` | После «Беру» нельзя защищаться или переводить |
| `INVALID_TRANSFER_RANK` | Достоинство не подходит для перевода |
| `ATTACK_LIMIT_REACHED` | Достигнут лимит атак |
| `NEW_DEFENDER_HAS_TOO_FEW_CARDS` | Перевод превышает возможности нового защитника |
| `INTERNAL_RULE_VIOLATION` | Нарушен инвариант движка |

## 11. Переподключение

После восстановления WebSocket клиент отправляет:

```json
{
  "type": "game.resume",
  "gameId": "0198f0cf-8ac6-7bd9-934d-7f929c4d9112",
  "lastKnownVersion": 17
}
```

Сервер отвечает актуальным полным `game.snapshot`.

Клиент не обязан воспроизводить все пропущенные события. Snapshot является
источником истины, а события используются для анимаций.

При отключении игрока:

1. сервер переводит партию в состояние паузы;
2. запускается окно переподключения на 120 секунд;
3. обычный игровой таймер не используется;
4. после истечения срока отключившемуся засчитывается техническое поражение;
5. сервер не выбирает карты за игрока.

## 12. Правила безопасности

Сервер MUST:

- получать идентификатор игрока из подписанной сессии, а не из action payload;
- не отправлять порядок колоды;
- не отправлять чужие руки;
- не доверять `legalActions`, присланным клиентом;
- ограничивать частоту команд;
- проверять размер и схему каждого сообщения;
- не записывать полные приватные руки в обычные application logs.
