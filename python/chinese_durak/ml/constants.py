"""Stable ML schema constants shared by training and inference."""

ML_SCHEMA_VERSION = "chinese-durak-ml/1"
ENCODER_VERSION = "player-view/1"

DECK_SIZE = 52
MAX_PLAYERS = 3
MAX_TABLE_SLOTS = 6
MAX_TABLE_CARDS = MAX_TABLE_SLOTS * 2
MAX_HISTORY = 64
MAX_HAND_SIZE = DECK_SIZE

CARD_PAD_TOKEN = 0
ACTION_PAD_TOKEN = 0

ACTION_KINDS = (
    "attack",
    "defend",
    "transfer",
    "take",
    "pass_attack",
)
ACTION_KIND_TO_ID = {
    kind: index for index, kind in enumerate(ACTION_KINDS)
}

PHASES = (
    "waiting_for_players",
    "opening_attack",
    "defense",
    "attack_extension",
    "throw_after_take",
    "finished",
)
PHASE_TO_ID = {
    phase: index for index, phase in enumerate(PHASES)
}

GLOBAL_FEATURE_NAMES = (
    "phase_waiting",
    "phase_opening_attack",
    "phase_defense",
    "phase_attack_extension",
    "phase_throw_after_take",
    "phase_finished",
    "players_two",
    "players_three",
    "role_main_attacker",
    "role_defender",
    "role_other",
    "deck_fraction",
    "discard_fraction",
    "own_hand_fraction",
    "cards_relative_0",
    "cards_relative_1",
    "cards_relative_2",
    "active_relative_0",
    "active_relative_1",
    "active_relative_2",
    "placement_relative_0",
    "placement_relative_1",
    "placement_relative_2",
    "eligible_relative_0",
    "eligible_relative_1",
    "eligible_relative_2",
    "passed_relative_0",
    "passed_relative_1",
    "passed_relative_2",
    "attack_count_fraction",
    "attack_limit_fraction",
    "dealer_relative_0",
    "dealer_relative_1",
    "dealer_relative_2",
    "main_attacker_relative_0",
    "main_attacker_relative_1",
    "main_attacker_relative_2",
    "defender_relative_0",
    "defender_relative_1",
    "defender_relative_2",
    "transfer_locked",
    "take_declared",
    "draw",
    "covered_slots_fraction",
)
GLOBAL_FEATURE_DIM = len(GLOBAL_FEATURE_NAMES)
