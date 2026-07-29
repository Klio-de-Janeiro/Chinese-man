import { useState } from "react";

import {
  cardLabel,
  cardValue,
  groupHandByRank,
  SUIT_NAMES,
} from "../game/cards";
import type {
  ConnectionStatus,
  LegalAction,
  PlayerView,
  Snapshot,
} from "../game/types";
import { Card, CardBack, SuitSelector } from "./cards";

export function GameScreen({
  snapshot,
  connectionStatus,
  isDemo,
  onAction,
  onCopyInvite,
  copied,
  onLeave,
  notice,
}: {
  snapshot: Snapshot;
  connectionStatus: ConnectionStatus;
  isDemo: boolean;
  onAction: (action: LegalAction) => void;
  onCopyInvite: () => void;
  copied: boolean;
  onLeave: () => void;
  notice: string | null;
}) {
  const game = snapshot.game;
  const [selection, setSelection] = useState<{
    version: number;
    card: number | null;
    slot: number | null;
  }>({
    version: game?.version ?? 0,
    card: null,
    slot: null,
  });

  if (game === null) {
    return null;
  }

  const selectedCard =
    selection.version === game.version ? selection.card : null;
  const selectedSlot =
    selection.version === game.version ? selection.slot : null;
  const you = snapshot.players.find((player) => player.isYou);
  const opponents = snapshot.players.filter((player) => !player.isYou);
  const hand = you?.hand ?? [];
  const handGroups = groupHandByRank(hand, game.trump);
  const legalActions = game.legalActions;
  const legalCards = new Set(
    legalActions.flatMap((action) =>
      action.card === null ? [] : [action.card],
    ),
  );
  const cardActions = legalActions.filter(
    (action) => action.card === selectedCard,
  );
  const takeAction = legalActions.find((action) => action.kind === "take");
  const passAction = legalActions.find(
    (action) => action.kind === "pass_attack",
  );
  const tableCardCount = game.table.reduce(
    (count, slot) => count + (slot.defense === null ? 1 : 2),
    0,
  );
  const isYourTurn = legalActions.length > 0;

  function roleFor(player: PlayerView): string {
    if (player.index === game.defender) {
      return "Защищается";
    }

    if (player.index === game.mainAttacker) {
      return "Атакует";
    }

    return "Подкидывает";
  }

  function statusText(): string {
    if (snapshot.room.status === "paused") {
      return "Партия на паузе — ждём возвращения игрока";
    }

    if (snapshot.room.status === "finished") {
      return game.draw ? "Партия завершена вничью" : "Партия завершена";
    }

    if (!isYourTurn) {
      return "Ход соперника";
    }

    if (game.phase === "defense") {
      const uncovered = game.table.find((slot) => slot.defense === null);
      return uncovered
        ? `Ваш ход — отбейте ${cardLabel(uncovered.attack)}`
        : "Ваш ход — выберите действие";
    }

    if (game.phase === "opening_attack") {
      return "Ваш ход — начните атаку";
    }

    if (game.phase === "throw_after_take") {
      return "Защитник берёт — можно подкинуть";
    }

    return "Ваш ход — подкиньте карту или завершите раунд";
  }

  function chooseCard(card: number): void {
    const actions = legalActions.filter((action) => action.card === card);

    if (actions.length === 0) {
      return;
    }

    const selectedDefense = actions.find(
      (action) =>
        action.kind === "defend" && action.targetSlot === selectedSlot,
    );

    if (selectedDefense && actions.length === 1) {
      onAction(selectedDefense);
      return;
    }

    if (actions.length === 1 && actions[0].kind !== "defend") {
      onAction(actions[0]);
      return;
    }

    setSelection({
      version: game.version,
      card,
      slot: selectedSlot,
    });
  }

  return (
    <main className="game-shell">
      <header className="game-topbar">
        <button
          type="button"
          className="room-pill"
          onClick={onCopyInvite}
          title="Скопировать ссылку-приглашение"
        >
          <span className="room-pill__icon">♟</span>
          Комната #{snapshot.room.id}
          <small>{copied ? "Скопировано" : "Пригласить"}</small>
        </button>

        <div className="topbar-stat">
          <span
            className={[
              "connection-dot",
              connectionStatus === "connected" ? "is-online" : "",
            ].join(" ")}
          />
          <strong>
            {snapshot.room.connectedPlayers}/{snapshot.room.maxPlayers}
          </strong>
          <span>игрока</span>
        </div>

        <div className="topbar-stat">
          <span>Козырь</span>
          <strong
            className={
              game.trump === "hearts" || game.trump === "diamonds"
                ? "red-suit"
                : ""
            }
          >
            {SUIT_NAMES[game.trump]} {cardValue(game.trumpCard).rank}
          </strong>
        </div>

        <div className="topbar-stat topbar-stat--muted">
          <span>Колода</span>
          <strong>{game.deckCount}</strong>
          <span>Отбой {game.discardCount}</span>
        </div>

        <button type="button" className="exit-button" onClick={onLeave}>
          {isDemo ? "Закрыть демо" : "Выйти"}
        </button>
      </header>

      {snapshot.room.status === "paused" ? (
        <div className="pause-banner">
          <span>⏸</span>
          Один из игроков отключился. Ходы приостановлены на 120 секунд.
        </div>
      ) : null}

      {notice ? (
        <div className="toast" role="status">
          {notice}
        </div>
      ) : null}

      <div className="game-layout">
        <section className="arena">
          <div className="opponents">
            {opponents.map((opponent) => (
              <div className="opponent" key={opponent.id}>
                <div className="player-name">
                  <strong>{opponent.nickname}</strong>
                  <span
                    className={
                      opponent.connected ? "is-online" : "is-offline"
                    }
                  />
                  <small>{roleFor(opponent)}</small>
                </div>
                <div className="opponent-hand">
                  {Array.from({
                    length: Math.min(opponent.cardCount, 10),
                  }).map((_, index) => (
                    <CardBack key={index} index={index} />
                  ))}
                  <span className="card-count">{opponent.cardCount}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="table-heading">
            <span>
              Стол: <strong>{tableCardCount}/12</strong>
            </span>
            <span>
              Атак: <strong>{game.attackCount}/{game.attackLimit}</strong>
            </span>
            <span>Версия {game.version}</span>
          </div>

          <div className="table-grid">
            {Array.from({ length: 6 }).map((_, index) => {
              const slot = game.table[index];
              const canSelect =
                slot &&
                slot.defense === null &&
                legalActions.some(
                  (action) =>
                    action.kind === "defend" &&
                    action.targetSlot === slot.slot,
                );

              return (
                <button
                  type="button"
                  className={[
                    "table-slot",
                    selectedSlot === slot?.slot ? "is-selected" : "",
                    canSelect ? "is-targetable" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={index}
                  onClick={() => {
                    if (canSelect && slot) {
                      setSelection({
                        version: game.version,
                        card: selectedCard,
                        slot: slot.slot,
                      });
                    }
                  }}
                  disabled={!canSelect}
                  aria-label={
                    slot
                      ? `Атакующая карта ${cardLabel(slot.attack)}`
                      : `Пустое место ${index + 1}`
                  }
                >
                  <span className="table-slot__number">{index + 1}</span>
                  {slot ? (
                    <span className="table-pair">
                      <Card card={slot.attack} compact />
                      {slot.defense !== null ? (
                        <span className="defense-card">
                          <Card card={slot.defense} compact />
                        </span>
                      ) : null}
                    </span>
                  ) : (
                    <span className="empty-slot">+</span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="action-row">
            <button
              type="button"
              className="danger-action"
              disabled={!takeAction}
              onClick={() => takeAction && onAction(takeAction)}
            >
              Беру
            </button>
            <button
              type="button"
              className="primary-action"
              disabled={!passAction}
              onClick={() => passAction && onAction(passAction)}
            >
              {game.phase === "attack_extension" ? "Бито" : "Пас"}
            </button>
          </div>

          <div
            className={[
              "turn-status",
              isYourTurn ? "turn-status--active" : "",
            ].join(" ")}
          >
            <span>{isYourTurn ? "◷" : "◎"}</span>
            <strong>{statusText()}</strong>
          </div>

          {selectedCard !== null && cardActions.length > 0 ? (
            <div className="card-action-menu">
              <span>{cardLabel(selectedCard)}: выберите действие</span>
              <div>
                {cardActions.map((action, index) => (
                  <button
                    type="button"
                    key={`${action.kind}-${action.targetSlot}-${index}`}
                    onClick={() => onAction(action)}
                  >
                    {action.kind === "attack"
                      ? "Атаковать"
                      : action.kind === "transfer"
                        ? "Перевести"
                        : `Отбить карту ${(action.targetSlot ?? 0) + 1}`}
                  </button>
                ))}
                <button
                  type="button"
                  className="card-action-menu__cancel"
                  onClick={() =>
                    setSelection({
                      version: game.version,
                      card: null,
                      slot: selectedSlot,
                    })
                  }
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : null}

          <div className="your-zone">
            <div className="your-zone__heading">
              <span>
                <strong>{you?.nickname}</strong>
                <i className="is-online" />
              </span>
              <small>{you ? roleFor(you) : ""}</small>
            </div>

            <div className="your-hand">
              {handGroups.map((group) => {
                const firstLegalCard = group.cards.find((card) =>
                  legalCards.has(card),
                );
                const displayedCard =
                  selectedCard !== null &&
                  group.cards.includes(selectedCard)
                    ? selectedCard
                    : (firstLegalCard ?? group.representativeCard);
                const isLegal = legalCards.has(displayedCard);

                return (
                  <div
                    className={[
                      "hand-card",
                      group.containsTrump ? "hand-card--trump" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={group.rankIndex}
                  >
                    <SuitSelector
                      cards={group.cards}
                      trump={game.trump}
                      selectedCard={selectedCard}
                      legalCards={legalCards}
                      onSelect={chooseCard}
                    />
                    <Card
                      card={displayedCard}
                      selected={selectedCard === displayedCard}
                      legal={group.cards.some((card) => legalCards.has(card))}
                      onClick={
                        isLegal ? () => chooseCard(displayedCard) : undefined
                      }
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <aside className="activity-panel">
          <div className="activity-panel__heading">
            <div>
              <small>Replay log</small>
              <h2>Последние действия</h2>
            </div>
            <span>{snapshot.events.length}</span>
          </div>

          <div className="activity-list">
            {[...snapshot.events].reverse().map((event) => (
              <article key={event.id}>
                <span className={`event-icon event-icon--${event.kind}`}>
                  {event.kind === "action"
                    ? "↗"
                    : event.kind === "join"
                      ? "+"
                      : "◆"}
                </span>
                <div>
                  <time>
                    {new Date(event.at).toLocaleTimeString("ru-RU", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                  <p>{event.message}</p>
                </div>
              </article>
            ))}
          </div>

          <div className="activity-panel__footer">
            <span>Сервер — единственный арбитр правил</span>
            <small>{snapshot.rulesVersion}</small>
          </div>
        </aside>
      </div>
    </main>
  );
}
