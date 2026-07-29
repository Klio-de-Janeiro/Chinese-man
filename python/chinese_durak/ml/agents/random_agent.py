"""Uniform random legal policy."""

from random import Random

from ..contracts import PlayerObservation


class RandomAgent:
    """Sample uniformly from actions already approved by GameEngine."""

    name = "random"

    def choose_action(
        self,
        observation: PlayerObservation,
        random: Random,
    ) -> int:
        """Return one uniformly sampled legal action index."""

        return random.randrange(len(observation.legal_actions))
