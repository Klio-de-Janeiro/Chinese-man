"""Agent interface shared by heuristic and learned policies."""

from __future__ import annotations

from random import Random
from typing import Protocol

from ..contracts import PlayerObservation


class Agent(Protocol):
    """Select an index from observation.legal_actions."""

    name: str

    def choose_action(
        self,
        observation: PlayerObservation,
        random: Random,
    ) -> int:
        """Return one valid action index."""

        ...
