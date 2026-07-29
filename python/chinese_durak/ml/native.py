"""Conversions between serializable ML values and pybind11 values."""

from __future__ import annotations

from typing import Any

from chinese_durak import Action, ActionKind, Phase, Suit

from .contracts import ActionView


def action_from_native(action: Any) -> ActionView:
    """Convert a native action without relying on enum integer values."""

    kinds = (
        (ActionKind.ATTACK, "attack"),
        (ActionKind.DEFEND, "defend"),
        (ActionKind.TRANSFER, "transfer"),
        (ActionKind.TAKE, "take"),
        (ActionKind.PASS_ATTACK, "pass_attack"),
    )

    for native_kind, name in kinds:
        if action.kind == native_kind:
            has_card = name in {"attack", "defend", "transfer"}
            return ActionView(
                kind=name,
                card=int(action.card) if has_card else None,
                target_slot=(
                    int(action.target_slot)
                    if name == "defend"
                    else None
                ),
            )

    raise ValueError(f"Unsupported native action kind: {action.kind}")


def action_to_native(action: ActionView) -> Action:
    """Convert a validated action view back to the native value object."""

    if action.kind == "attack" and action.card is not None:
        return Action.attack(action.card)

    if (
        action.kind == "defend"
        and action.card is not None
        and action.target_slot is not None
    ):
        return Action.defend(action.card, action.target_slot)

    if action.kind == "transfer" and action.card is not None:
        return Action.transfer(action.card)

    if action.kind == "take":
        return Action.take()

    if action.kind == "pass_attack":
        return Action.pass_attack()

    raise ValueError(f"Invalid action view: {action}")


def phase_name(phase: Any) -> str:
    """Return the stable string used by datasets and model metadata."""

    phases = (
        (Phase.WAITING_FOR_PLAYERS, "waiting_for_players"),
        (Phase.OPENING_ATTACK, "opening_attack"),
        (Phase.DEFENSE, "defense"),
        (Phase.ATTACK_EXTENSION, "attack_extension"),
        (Phase.THROW_AFTER_TAKE, "throw_after_take"),
        (Phase.FINISHED, "finished"),
    )

    for native_phase, name in phases:
        if phase == native_phase:
            return name

    raise ValueError(f"Unsupported native phase: {phase}")


def suit_index(suit: Any) -> int:
    """Convert a native suit enum into the stable card encoding index."""

    suits = (
        Suit.CLUBS,
        Suit.DIAMONDS,
        Suit.HEARTS,
        Suit.SPADES,
    )

    for index, native_suit in enumerate(suits):
        if suit == native_suit:
            return index

    raise ValueError(f"Unsupported native suit: {suit}")
