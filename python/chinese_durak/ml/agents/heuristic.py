"""Resource-aware teacher policy for imitation learning."""

from random import Random

from ..contracts import ActionView, PlayerObservation


class HeuristicAgent:
    """Preserve trumps and prefer the cheapest useful legal action."""

    name = "heuristic-v1"

    def choose_action(
        self,
        observation: PlayerObservation,
        random: Random,
    ) -> int:
        """Return the minimum-cost action with random tie breaking."""

        scores = [
            self._score(action, observation)
            for action in observation.legal_actions
        ]
        best_score = min(scores)
        candidates = [
            index
            for index, score in enumerate(scores)
            if score == best_score
        ]
        return random.choice(candidates)

    def _score(
        self,
        action: ActionView,
        observation: PlayerObservation,
    ) -> float:
        """Estimate the resource cost of one legal action."""

        if action.kind == "take":
            return 100.0 + observation.attack_count
        if action.kind == "pass_attack":
            return 18.0
        if action.card is None:
            return 200.0

        rank = action.card % 13
        suit = action.card // 13
        trump_cost = 24.0 if suit == observation.trump_suit else 0.0
        card_cost = rank + trump_cost
        if action.kind == "defend":
            return card_cost
        if action.kind == "transfer":
            return card_cost + 4.0
        if observation.phase == "throw_after_take":
            return card_cost - 20.0
        return card_cost + 5.0
