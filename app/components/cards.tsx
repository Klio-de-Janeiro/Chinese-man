import type { CSSProperties } from "react";
import { useMemo } from "react";

import { cardValue, SUITS } from "../game/cards";

export function Card({
  card,
  compact = false,
  selected = false,
  legal = false,
  onClick,
}: {
  card: number;
  compact?: boolean;
  selected?: boolean;
  legal?: boolean;
  onClick?: () => void;
}) {
  const value = cardValue(card);

  return (
    <button
      type="button"
      className={[
        "playing-card",
        compact ? "playing-card--compact" : "",
        value.red ? "playing-card--red" : "",
        selected ? "playing-card--selected" : "",
        legal ? "playing-card--legal" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={onClick}
      disabled={!onClick}
      aria-label={`Карта ${value.rank}${value.suit}`}
    >
      <span className="playing-card__corner">
        <strong>{value.rank}</strong>
        <span>{value.suit}</span>
      </span>
      <span className="playing-card__center">{value.suit}</span>
      <span className="playing-card__corner playing-card__corner--bottom">
        <strong>{value.rank}</strong>
        <span>{value.suit}</span>
      </span>
    </button>
  );
}

export function CardBack({ index }: { index: number }) {
  return (
    <span
      className="card-back"
      style={{ "--card-index": index } as CSSProperties}
      aria-hidden="true"
    >
      <span className="card-back__pattern" />
    </span>
  );
}

export function SuitPresence({ hand }: { hand: number[] }) {
  const present = useMemo(
    () => new Set(hand.map((card) => Math.floor(card / 13))),
    [hand],
  );

  return (
    <span className="suit-presence" aria-label="Масти в вашей руке">
      {SUITS.map((suit, index) => (
        <span
          key={suit}
          className={[
            "suit-presence__item",
            present.has(index) ? "is-present" : "",
            index === 1 || index === 2 ? "is-red" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {suit}
        </span>
      ))}
    </span>
  );
}
