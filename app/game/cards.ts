const RANKS = [
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "J",
  "Q",
  "K",
  "A",
];

export const SUITS = ["♣", "♦", "♥", "♠"];

export const SUIT_NAMES = {
  clubs: "♣",
  diamonds: "♦",
  hearts: "♥",
  spades: "♠",
};

export function cardValue(card: number): {
  rank: string;
  suit: string;
  red: boolean;
} {
  const suitIndex = Math.floor(card / 13);
  return {
    rank: RANKS[card % 13],
    suit: SUITS[suitIndex],
    red: suitIndex === 1 || suitIndex === 2,
  };
}

export function cardLabel(card: number): string {
  const value = cardValue(card);
  return `${value.rank}${value.suit}`;
}
