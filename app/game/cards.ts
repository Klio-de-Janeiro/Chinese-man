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
} as const;

export type SuitName = keyof typeof SUIT_NAMES;

const SUIT_ORDER: SuitName[] = [
  "clubs",
  "diamonds",
  "hearts",
  "spades",
];

export type HandRankGroup = {
  rankIndex: number;
  cards: number[];
  containsTrump: boolean;
  representativeCard: number;
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

export function groupHandByRank(
  hand: number[],
  trump: SuitName,
): HandRankGroup[] {
  const trumpSuitIndex = SUIT_ORDER.indexOf(trump);
  const cardsByRank = new Map<number, number[]>();

  for (const card of hand) {
    const rankIndex = card % 13;
    const cards = cardsByRank.get(rankIndex) ?? [];
    cards.push(card);
    cardsByRank.set(rankIndex, cards);
  }

  return Array.from(cardsByRank, ([rankIndex, cards]) => {
    const sortedCards = [...cards].sort(
      (left, right) => Math.floor(left / 13) - Math.floor(right / 13),
    );
    const trumpCard = sortedCards.find(
      (card) => Math.floor(card / 13) === trumpSuitIndex,
    );

    return {
      rankIndex,
      cards: sortedCards,
      containsTrump: trumpCard !== undefined,
      representativeCard: trumpCard ?? sortedCards[0],
    };
  }).sort((left, right) => {
    if (left.containsTrump !== right.containsTrump) {
      return left.containsTrump ? -1 : 1;
    }

    return left.rankIndex - right.rankIndex;
  });
}
