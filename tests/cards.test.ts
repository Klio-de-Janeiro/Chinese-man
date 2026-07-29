import assert from "node:assert/strict";
import test from "node:test";

import { groupHandByRank } from "../app/game/cards.ts";

test("groups cards with the same rank into one visual group", () => {
  const groups = groupHandByRank([7, 20, 33, 46], "hearts");

  assert.equal(groups.length, 1);
  assert.deepEqual(groups[0].cards, [7, 20, 33, 46]);
  assert.equal(groups[0].representativeCard, 33);
  assert.equal(groups[0].containsTrump, true);
});

test("places trump groups first and sorts them by ascending rank", () => {
  const groups = groupHandByRank(
    [
      16, // 5♦
      38, // A♥
      1, // 3♣
      31, // 7♥
      26, // 2♥
      7, // 9♣
      33, // 9♥
    ],
    "hearts",
  );

  assert.deepEqual(
    groups.map((group) => ({
      rank: group.rankIndex,
      trump: group.containsTrump,
    })),
    [
      { rank: 0, trump: true },
      { rank: 5, trump: true },
      { rank: 7, trump: true },
      { rank: 12, trump: true },
      { rank: 1, trump: false },
      { rank: 3, trump: false },
    ],
  );
});

test("does not mutate the authoritative hand array", () => {
  const hand = [38, 1, 26, 16];

  groupHandByRank(hand, "hearts");

  assert.deepEqual(hand, [38, 1, 26, 16]);
});
