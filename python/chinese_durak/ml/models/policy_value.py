"""Small recurrent policy-value network for variable legal action sets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt

import torch
from torch import Tensor, nn

from ..constants import (
    ACTION_KINDS,
    DECK_SIZE,
    GLOBAL_FEATURE_DIM,
    MAX_PLAYERS,
    MAX_TABLE_SLOTS,
    PHASES,
)


@dataclass(frozen=True)
class ModelConfig:
    """Define the compact network dimensions."""

    card_dim: int = 64
    history_dim: int = 96
    action_dim: int = 128
    hidden_dim: int = 256
    dropout: float = 0.1

    def to_dict(self) -> dict[str, int | float]:
        """Return checkpoint-safe configuration values."""

        return asdict(self)


class CardEmbedding(nn.Module):
    """Embed card identity, zone, and trump status."""

    def __init__(self, dimension: int) -> None:
        """Create rank, suit, zone, and trump embeddings."""

        super().__init__()
        self.rank = nn.Embedding(14, dimension, padding_idx=0)
        self.suit = nn.Embedding(5, dimension, padding_idx=0)
        self.zone = nn.Embedding(4, dimension, padding_idx=0)
        self.trump = nn.Embedding(2, dimension)
        self.norm = nn.LayerNorm(dimension)

    def forward(
        self,
        cards: Tensor,
        zones: Tensor,
        trump_suit: Tensor,
    ) -> Tensor:
        """Embed card tokens where zero denotes padding."""

        valid = cards > 0
        raw_cards = (cards - 1).clamp_min(0)
        ranks = torch.where(valid, raw_cards % 13 + 1, 0)
        suits = torch.where(valid, raw_cards // 13 + 1, 0)
        is_trump = (
            valid
            & ((suits - 1) == trump_suit.unsqueeze(-1))
        ).long()
        values = (
            self.rank(ranks)
            + self.suit(suits)
            + self.zone(zones)
            + self.trump(is_trump)
        )
        return self.norm(values) * valid.unsqueeze(-1)


class CardSetEncoder(nn.Module):
    """Pool an unordered variable-size card set."""

    def __init__(self, card_embedding: CardEmbedding, dimension: int) -> None:
        """Reuse the shared card embedding and project its pooled value."""

        super().__init__()
        self.card_embedding = card_embedding
        self.projection = nn.Sequential(
            nn.Linear(dimension, dimension),
            nn.GELU(),
            nn.LayerNorm(dimension),
        )

    def forward(
        self,
        cards: Tensor,
        zones: Tensor,
        trump_suit: Tensor,
    ) -> Tensor:
        """Return a masked mean representation."""

        values = self.card_embedding(cards, zones, trump_suit)
        mask = (cards > 0).unsqueeze(-1)
        denominator = mask.sum(dim=1).clamp_min(1)
        pooled = (values * mask).sum(dim=1) / denominator
        return self.projection(pooled)


class HistoryEncoder(nn.Module):
    """Encode the last public actions with a GRU."""

    def __init__(self, dimension: int) -> None:
        """Create categorical embeddings and one recurrent layer."""

        super().__init__()
        self.actor = nn.Embedding(MAX_PLAYERS + 1, dimension, padding_idx=0)
        self.kind = nn.Embedding(
            len(ACTION_KINDS) + 1,
            dimension,
            padding_idx=0,
        )
        self.card = nn.Embedding(
            DECK_SIZE + 1,
            dimension,
            padding_idx=0,
        )
        self.target = nn.Embedding(
            MAX_TABLE_SLOTS + 1,
            dimension,
            padding_idx=0,
        )
        self.phase = nn.Embedding(
            len(PHASES) + 1,
            dimension,
            padding_idx=0,
        )
        self.gru = nn.GRU(dimension, dimension, batch_first=True)
        self.norm = nn.LayerNorm(dimension)

    def forward(
        self,
        history: Tensor,
        lengths: Tensor,
    ) -> Tensor:
        """Return the recurrent output at the last real event."""

        values = (
            self.actor(history[..., 0])
            + self.kind(history[..., 1])
            + self.card(history[..., 2])
            + self.target(history[..., 3])
            + self.phase(history[..., 4])
        )
        outputs, _ = self.gru(values)
        indices = (lengths.clamp_min(1) - 1).view(-1, 1, 1)
        indices = indices.expand(-1, 1, outputs.shape[-1])
        selected = outputs.gather(1, indices).squeeze(1)
        selected = selected * (lengths > 0).unsqueeze(-1)
        return self.norm(selected)


class ActionEncoder(nn.Module):
    """Embed dynamic legal actions for state-action scoring."""

    def __init__(self, dimension: int) -> None:
        """Create embeddings for kind, card, target, and trump status."""

        super().__init__()
        self.kind = nn.Embedding(
            len(ACTION_KINDS) + 1,
            dimension,
            padding_idx=0,
        )
        self.rank = nn.Embedding(14, dimension, padding_idx=0)
        self.suit = nn.Embedding(5, dimension, padding_idx=0)
        self.target = nn.Embedding(
            MAX_TABLE_SLOTS + 1,
            dimension,
            padding_idx=0,
        )
        self.trump = nn.Embedding(2, dimension)
        self.network = nn.Sequential(
            nn.Linear(dimension, dimension),
            nn.GELU(),
            nn.LayerNorm(dimension),
        )

    def forward(
        self,
        actions: Tensor,
        trump_suit: Tensor,
    ) -> Tensor:
        """Return one embedding for every padded legal action."""

        cards = actions[..., 1]
        valid_card = cards > 0
        raw_cards = (cards - 1).clamp_min(0)
        ranks = torch.where(valid_card, raw_cards % 13 + 1, 0)
        suits = torch.where(valid_card, raw_cards // 13 + 1, 0)
        is_trump = (
            valid_card
            & ((suits - 1) == trump_suit.unsqueeze(-1))
        ).long()
        values = (
            self.kind(actions[..., 0])
            + self.rank(ranks)
            + self.suit(suits)
            + self.target(actions[..., 2])
            + self.trump(is_trump)
        )
        return self.network(values)


class PolicyValueNetwork(nn.Module):
    """Score legal actions and estimate the acting player's outcome."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        """Build a compact DeepSets plus GRU architecture."""

        super().__init__()
        self.config = config or ModelConfig()
        card_embedding = CardEmbedding(self.config.card_dim)
        self.hand_encoder = CardSetEncoder(
            card_embedding,
            self.config.card_dim,
        )
        self.table_encoder = CardSetEncoder(
            card_embedding,
            self.config.card_dim,
        )
        self.history_encoder = HistoryEncoder(self.config.history_dim)
        state_input = (
            self.config.card_dim * 2
            + self.config.history_dim
            + GLOBAL_FEATURE_DIM
        )
        self.state_network = nn.Sequential(
            nn.Linear(state_input, self.config.hidden_dim),
            nn.GELU(),
            nn.Dropout(self.config.dropout),
            nn.Linear(
                self.config.hidden_dim,
                self.config.hidden_dim,
            ),
            nn.GELU(),
            nn.LayerNorm(self.config.hidden_dim),
        )
        self.action_encoder = ActionEncoder(self.config.action_dim)
        self.policy_projection = nn.Linear(
            self.config.hidden_dim,
            self.config.action_dim,
        )
        self.value_head = nn.Sequential(
            nn.Linear(self.config.hidden_dim, self.config.hidden_dim // 2),
            nn.GELU(),
            nn.Linear(self.config.hidden_dim // 2, 1),
            nn.Tanh(),
        )

    def forward(
        self,
        hand_cards: Tensor,
        table_cards: Tensor,
        table_zones: Tensor,
        history: Tensor,
        history_lengths: Tensor,
        global_features: Tensor,
        actions: Tensor,
        action_mask: Tensor,
        trump_suit: Tensor,
    ) -> tuple[Tensor, Tensor]:
        """Return masked policy logits and scalar values."""

        hand_zones = (hand_cards > 0).long()
        hand_state = self.hand_encoder(
            hand_cards,
            hand_zones,
            trump_suit,
        )
        table_state = self.table_encoder(
            table_cards,
            table_zones,
            trump_suit,
        )
        history_state = self.history_encoder(
            history,
            history_lengths,
        )
        state = self.state_network(
            torch.cat(
                (
                    hand_state,
                    table_state,
                    history_state,
                    global_features,
                ),
                dim=-1,
            )
        )
        action_state = self.action_encoder(actions, trump_suit)
        policy_state = self.policy_projection(state).unsqueeze(1)
        logits = (policy_state * action_state).sum(dim=-1)
        logits = logits / sqrt(self.config.action_dim)
        logits = logits.masked_fill(~action_mask, -1.0e9)
        values = self.value_head(state).squeeze(-1)
        return logits, values
