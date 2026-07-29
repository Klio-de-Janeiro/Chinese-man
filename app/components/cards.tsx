import type { CSSProperties } from "react";

import {
  cardLabel,
  cardValue,
  type SuitName,
  SUIT_NAMES,
} from "../game/cards";

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
  const className = [
    "playing-card",
    compact ? "playing-card--compact" : "",
    value.red ? "playing-card--red" : "",
    selected ? "playing-card--selected" : "",
    legal ? "playing-card--legal" : "",
    onClick ? "" : "playing-card--disabled",
  ]
    .filter(Boolean)
    .join(" ");
  const contents = (
    <>
      <span className="playing-card__corner">
        <strong>{value.rank}</strong>
        <span>{value.suit}</span>
      </span>
      <span className="playing-card__center">{value.suit}</span>
      <span className="playing-card__corner playing-card__corner--bottom">
        <strong>{value.rank}</strong>
        <span>{value.suit}</span>
      </span>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        className={className}
        onClick={onClick}
        aria-label={`Карта ${value.rank}${value.suit}`}
      >
        {contents}
      </button>
    );
  }

  return (
    <span
      className={className}
      role="img"
      aria-label={`Карта ${value.rank}${value.suit}`}
    >
      {contents}
    </span>
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

export function SuitSelector({
  cards,
  trump,
  selectedCard,
  legalCards,
  onSelect,
}: {
  cards: number[];
  trump: SuitName;
  selectedCard: number | null;
  legalCards: Set<number>;
  onSelect: (card: number) => void;
}) {
  return (
    <span className="suit-presence" aria-label="Масти этого достоинства">
      {cards.map((card) => {
        const value = cardValue(card);
        const isLegal = legalCards.has(card);
        const isTrump = value.suit === SUIT_NAMES[trump];

        return (
          <button
            type="button"
            key={card}
            className={[
              "suit-presence__item",
              value.red ? "is-red" : "",
              isTrump ? "is-trump" : "",
              selectedCard === card ? "is-selected" : "",
              isLegal ? "is-legal" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            disabled={!isLegal}
            onClick={() => onSelect(card)}
            aria-label={[
              cardLabel(card),
              isTrump ? "козырь" : "",
              isLegal ? "можно сыграть" : "сейчас сыграть нельзя",
            ]
              .filter(Boolean)
              .join(", ")}
          >
            {value.suit}
          </button>
        );
      })}
    </span>
  );
}
