"""Simple baseline that tries to remove a card whenever possible."""

from random import Random

from ..contracts import PlayerObservation


class GreedyAgent:
    """Prefer card-playing actions and high non-trump ranks."""

    name = "greedy"

    def choose_action(
        self,
        observation: PlayerObservation,
        random: Random,
    ) -> int:
        """Return the strongest immediate hand-reducing action."""

        candidates = [
            (index, action)
            for index, action in enumerate(observation.legal_actions)
            if action.card is not None
        ]
        if not candidates:
            return random.randrange(len(observation.legal_actions))

        return max(
            candidates,
            key=lambda item: (
                (item[1].card or 0) // 13
                != observation.trump_suit,
                (item[1].card or 0) % 13,
                -item[0],
            ),
        )[0]
