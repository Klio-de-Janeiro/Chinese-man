#include "chinese_durak/game_engine.hpp"

#include <algorithm>
#include <array>
#include <numeric>
#include <random>
#include <string>

namespace chinese_durak {
namespace {

[[nodiscard]]
bool has_player(std::uint8_t mask, std::uint8_t player) noexcept {
    return (mask & static_cast<std::uint8_t>(1U << player)) != 0;
}

void add_card(CardMask& hand, CardId card) noexcept {
    hand |= card_bit(card);
}

void remove_card(CardMask& hand, CardId card) noexcept {
    hand &= ~card_bit(card);
}

}  // namespace

GameEngine::GameEngine(RuleSet rules)
    : rules_(rules) {
    if (rules_.initial_hand_size == 0) {
        throw GameError("Initial hand size must be positive");
    }

    if (
        rules_.max_attacks == 0
        || rules_.max_attacks > kMaxAttackSlots
    ) {
        throw GameError("Maximum attacks must be in range 1..6");
    }
}

void GameEngine::start(
    std::uint8_t player_count,
    std::uint64_t seed,
    std::uint8_t dealer
) {
    if (player_count < 2 || player_count > kMaxPlayers) {
        throw GameError("Player count must be 2 or 3");
    }

    if (dealer >= player_count) {
        throw GameError("Dealer must be an active player");
    }

    state_ = {};
    state_.player_count = player_count;
    state_.dealer = dealer;

    std::iota(state_.deck.begin(), state_.deck.end(), CardId{0});
    std::mt19937_64 generator(seed);
    std::shuffle(state_.deck.begin(), state_.deck.end(), generator);

    for (std::uint8_t player = 0; player < player_count; ++player) {
        state_.players[player].active = true;
    }

    deal_initial_hands();
    state_.trump_card = state_.deck.back();
    state_.trump = suit_of(state_.trump_card);
    select_first_attacker();
    state_.round_starter = state_.main_attacker;
    state_.defender = next_active_player(state_.main_attacker);
    state_.eligible_attackers = static_cast<std::uint8_t>(
        active_players_mask()
        & ~static_cast<std::uint8_t>(1U << state_.defender)
    );
    state_.attack_limit = std::min(
        rules_.max_attacks,
        state_.players[state_.defender].hand_size()
    );
    state_.phase = Phase::OpeningAttack;
    state_.version = 1;
}

std::vector<Action> GameEngine::legal_actions(
    std::uint8_t player
) const {
    std::vector<Action> actions;

    if (
        player >= state_.player_count
        || !state_.players[player].active
        || state_.phase == Phase::Finished
    ) {
        return actions;
    }

    const PlayerState& player_state = state_.players[player];

    if (
        state_.phase == Phase::OpeningAttack
        && player == state_.main_attacker
    ) {
        for (CardId card = 0; card < kDeckSize; ++card) {
            if (player_state.has_card(card)) {
                actions.push_back(Action::attack(card));
            }
        }
        return actions;
    }

    if (state_.phase == Phase::Defense && player == state_.defender) {
        for (std::uint8_t slot = 0; slot < state_.attack_count; ++slot) {
            const TableSlot& table_slot = state_.table[slot];

            if (table_slot.covered()) {
                continue;
            }

            for (CardId card = 0; card < kDeckSize; ++card) {
                if (
                    player_state.has_card(card)
                    && beats(card, table_slot.attack, state_.trump)
                ) {
                    actions.push_back(Action::defend(card, slot));
                }
            }
        }

        if (
            rules_.transfer_enabled
            && !state_.transfer_locked
            && state_.attack_count < state_.attack_limit
        ) {
            const std::uint8_t new_defender =
                next_active_player(state_.defender);
            const std::uint8_t new_limit = std::min(
                state_.attack_limit,
                state_.players[new_defender].hand_size()
            );

            if (state_.attack_count + 1U <= new_limit) {
                const Rank attack_rank =
                    rank_of(state_.table.front().attack);

                for (CardId card = 0; card < kDeckSize; ++card) {
                    if (
                        player_state.has_card(card)
                        && rank_of(card) == attack_rank
                    ) {
                        actions.push_back(Action::transfer(card));
                    }
                }
            }
        }

        actions.push_back(Action::take());
        return actions;
    }

    const bool attack_phase =
        state_.phase == Phase::AttackExtension
        || state_.phase == Phase::ThrowAfterTake;

    if (
        attack_phase
        && has_player(state_.eligible_attackers, player)
        && !has_player(state_.passed_attackers, player)
    ) {
        if (state_.attack_count < state_.attack_limit) {
            for (CardId card = 0; card < kDeckSize; ++card) {
                if (
                    player_state.has_card(card)
                    && table_contains_rank(rank_of(card))
                ) {
                    actions.push_back(Action::attack(card));
                }
            }
        }

        actions.push_back(Action::pass_attack());
    }

    return actions;
}

void GameEngine::apply(
    std::uint8_t player,
    const Action& action
) {
    if (!is_legal(player, action)) {
        throw GameError("Illegal action");
    }

    switch (action.kind) {
        case ActionKind::Attack:
            apply_attack(player, action.card);
            break;
        case ActionKind::Defend:
            apply_defense(player, action.card, action.target_slot);
            break;
        case ActionKind::Transfer:
            apply_transfer(player, action.card);
            break;
        case ActionKind::Take:
            apply_take();
            break;
        case ActionKind::PassAttack:
            apply_pass(player);
            break;
    }

    ++state_.decision_count;
    ++state_.version;

    if (state_.decision_count >= rules_.max_decisions) {
        state_.draw = true;
        state_.phase = Phase::Finished;
    }
}

const GameState& GameEngine::state() const noexcept {
    return state_;
}

const RuleSet& GameEngine::rules() const noexcept {
    return rules_;
}

void GameEngine::deal_initial_hands() {
    for (
        std::uint8_t round = 0;
        round < rules_.initial_hand_size;
        ++round
    ) {
        for (
            std::uint8_t player = 0;
            player < state_.player_count;
            ++player
        ) {
            const CardId card = state_.deck[state_.draw_position++];
            add_card(state_.players[player].hand, card);
        }
    }
}

void GameEngine::select_first_attacker() {
    std::uint8_t selected = kNoPlayer;
    Rank lowest_rank = Rank::Ace;
    bool trump_found = false;

    for (
        std::uint8_t player = 0;
        player < state_.player_count;
        ++player
    ) {
        for (CardId card = 0; card < kDeckSize; ++card) {
            if (
                state_.players[player].has_card(card)
                && suit_of(card) == state_.trump
                && (!trump_found || rank_of(card) < lowest_rank)
            ) {
                selected = player;
                lowest_rank = rank_of(card);
                trump_found = true;
            }
        }
    }

    state_.main_attacker = trump_found
        ? selected
        : next_active_player(state_.dealer);
}

void GameEngine::apply_attack(
    std::uint8_t player,
    CardId card
) {
    remove_card(state_.players[player].hand, card);

    TableSlot& slot = state_.table[state_.attack_count];
    slot.attack = card;
    slot.defense = kInvalidCard;
    ++state_.attack_count;
    state_.passed_attackers = 0;

    if (state_.phase == Phase::ThrowAfterTake) {
        if (state_.attack_count >= state_.attack_limit) {
            resolve_take();
        }
        return;
    }

    state_.phase = Phase::Defense;
}

void GameEngine::apply_defense(
    std::uint8_t player,
    CardId card,
    std::uint8_t target_slot
) {
    remove_card(state_.players[player].hand, card);
    state_.table[target_slot].defense = card;
    state_.transfer_locked = true;

    if (all_attacks_covered()) {
        state_.eligible_attackers = static_cast<std::uint8_t>(
            active_players_mask()
            & ~static_cast<std::uint8_t>(1U << state_.defender)
        );
        state_.passed_attackers = 0;
        state_.phase = Phase::AttackExtension;
    }
}

void GameEngine::apply_transfer(
    std::uint8_t player,
    CardId card
) {
    remove_card(state_.players[player].hand, card);

    TableSlot& slot = state_.table[state_.attack_count];
    slot.attack = card;
    slot.defense = kInvalidCard;
    ++state_.attack_count;

    state_.main_attacker = player;
    state_.defender = next_active_player(player);
    state_.eligible_attackers = static_cast<std::uint8_t>(
        active_players_mask()
        & ~static_cast<std::uint8_t>(1U << state_.defender)
    );
    state_.attack_limit = std::min(
        state_.attack_limit,
        state_.players[state_.defender].hand_size()
    );
    state_.passed_attackers = 0;
}

void GameEngine::apply_take() {
    PlayerState& player = state_.players[state_.defender];
    player.hand |= state_.discard;
    state_.discard = 0;
    state_.take_declared = true;
    state_.passed_attackers = 0;

    if (
        !rules_.throw_after_take
        || state_.attack_count >= state_.attack_limit
    ) {
        resolve_take();
        return;
    }

    state_.phase = Phase::ThrowAfterTake;
}

void GameEngine::apply_pass(std::uint8_t player) {
    state_.passed_attackers |= static_cast<std::uint8_t>(1U << player);

    if (
        (
            state_.passed_attackers
            & state_.eligible_attackers
        ) != state_.eligible_attackers
    ) {
        return;
    }

    if (state_.phase == Phase::ThrowAfterTake) {
        resolve_take();
        return;
    }

    resolve_beaten();
}

void GameEngine::resolve_take() {
    const std::uint8_t taking_player = state_.defender;
    PlayerState& player = state_.players[taking_player];

    for (std::uint8_t slot = 0; slot < state_.attack_count; ++slot) {
        add_card(
            player.hand,
            state_.table[slot].attack
        );

        if (state_.table[slot].covered()) {
            add_card(
                player.hand,
                state_.table[slot].defense
            );
        }
    }

    clear_table();
    refill_hands();
    update_results();

    if (state_.phase != Phase::Finished) {
        begin_round(next_active_player(taking_player));
    }
}

void GameEngine::resolve_beaten() {
    const std::uint8_t successful_defender = state_.defender;

    for (std::uint8_t slot = 0; slot < state_.attack_count; ++slot) {
        add_card(state_.discard, state_.table[slot].attack);

        if (state_.table[slot].covered()) {
            add_card(state_.discard, state_.table[slot].defense);
        }
    }

    clear_table();
    refill_hands();
    update_results();

    if (state_.phase != Phase::Finished) {
        begin_round(first_active_at_or_after(successful_defender));
    }
}

void GameEngine::refill_hands() {
    std::array<std::uint8_t, kMaxPlayers> order{};
    std::uint8_t order_size = 0;

    order[order_size++] = state_.main_attacker;

    for (
        std::uint8_t offset = 1;
        offset < state_.player_count;
        ++offset
    ) {
        const std::uint8_t player = static_cast<std::uint8_t>(
            (state_.main_attacker + offset) % state_.player_count
        );

        if (
            player != state_.defender
            && state_.players[player].active
        ) {
            order[order_size++] = player;
        }
    }

    if (state_.players[state_.defender].active) {
        order[order_size++] = state_.defender;
    }

    for (std::uint8_t index = 0; index < order_size; ++index) {
        PlayerState& player = state_.players[order[index]];

        while (
            player.hand_size() < rules_.initial_hand_size
            && state_.draw_position < kDeckSize
        ) {
            add_card(
                player.hand,
                state_.deck[state_.draw_position++]
            );
        }
    }
}

void GameEngine::update_results() {
    if (state_.draw_position < kDeckSize) {
        return;
    }

    std::uint8_t active_before = 0;
    std::uint8_t finishing_count = 0;

    for (
        std::uint8_t player = 0;
        player < state_.player_count;
        ++player
    ) {
        if (state_.players[player].active) {
            ++active_before;

            if (state_.players[player].hand == 0) {
                ++finishing_count;
            }
        }
    }

    if (finishing_count == 0) {
        return;
    }

    if (
        state_.player_count == 2
        && active_before == 2
        && finishing_count == 2
    ) {
        state_.draw = true;
        state_.phase = Phase::Finished;
        return;
    }

    const std::uint8_t placement = static_cast<std::uint8_t>(
        state_.player_count - active_before + 1U
    );

    for (
        std::uint8_t player = 0;
        player < state_.player_count;
        ++player
    ) {
        PlayerState& player_state = state_.players[player];

        if (player_state.active && player_state.hand == 0) {
            player_state.active = false;
            player_state.placement = placement;
        }
    }

    std::uint8_t remaining = 0;
    std::uint8_t last_player = kNoPlayer;

    for (
        std::uint8_t player = 0;
        player < state_.player_count;
        ++player
    ) {
        if (state_.players[player].active) {
            ++remaining;
            last_player = player;
        }
    }

    if (remaining == 1) {
        state_.players[last_player].placement = state_.player_count;
        state_.players[last_player].is_durak = true;
        state_.phase = Phase::Finished;
    } else if (remaining == 0) {
        state_.draw = true;
        state_.phase = Phase::Finished;
    }
}

void GameEngine::begin_round(std::uint8_t preferred_attacker) {
    const std::uint8_t attacker =
        first_active_at_or_after(preferred_attacker);

    state_.main_attacker = attacker;
    state_.round_starter = attacker;
    state_.defender = next_active_player(attacker);
    state_.eligible_attackers = static_cast<std::uint8_t>(
        active_players_mask()
        & ~static_cast<std::uint8_t>(1U << state_.defender)
    );
    state_.passed_attackers = 0;
    state_.attack_count = 0;
    state_.attack_limit = std::min(
        rules_.max_attacks,
        state_.players[state_.defender].hand_size()
    );
    state_.transfer_locked = false;
    state_.take_declared = false;
    state_.phase = Phase::OpeningAttack;
}

void GameEngine::clear_table() noexcept {
    for (TableSlot& slot : state_.table) {
        slot = {};
    }

    state_.attack_count = 0;
    state_.passed_attackers = 0;
    state_.take_declared = false;
    state_.transfer_locked = false;
}

bool GameEngine::is_legal(
    std::uint8_t player,
    const Action& action
) const {
    const std::vector<Action> actions = legal_actions(player);
    return std::find(actions.begin(), actions.end(), action) != actions.end();
}

bool GameEngine::all_attacks_covered() const noexcept {
    for (std::uint8_t slot = 0; slot < state_.attack_count; ++slot) {
        if (!state_.table[slot].covered()) {
            return false;
        }
    }

    return state_.attack_count > 0;
}

bool GameEngine::table_contains_rank(Rank rank) const noexcept {
    for (std::uint8_t slot = 0; slot < state_.attack_count; ++slot) {
        if (rank_of(state_.table[slot].attack) == rank) {
            return true;
        }

        if (
            state_.table[slot].covered()
            && rank_of(state_.table[slot].defense) == rank
        ) {
            return true;
        }
    }

    return false;
}

std::uint8_t GameEngine::active_players_mask() const noexcept {
    std::uint8_t mask = 0;

    for (
        std::uint8_t player = 0;
        player < state_.player_count;
        ++player
    ) {
        if (state_.players[player].active) {
            mask |= static_cast<std::uint8_t>(1U << player);
        }
    }

    return mask;
}

std::uint8_t GameEngine::next_active_player(
    std::uint8_t player
) const {
    for (
        std::uint8_t offset = 1;
        offset <= state_.player_count;
        ++offset
    ) {
        const std::uint8_t candidate = static_cast<std::uint8_t>(
            (player + offset) % state_.player_count
        );

        if (state_.players[candidate].active) {
            return candidate;
        }
    }

    throw GameError("No active player available");
}

std::uint8_t GameEngine::first_active_at_or_after(
    std::uint8_t player
) const {
    for (
        std::uint8_t offset = 0;
        offset < state_.player_count;
        ++offset
    ) {
        const std::uint8_t candidate = static_cast<std::uint8_t>(
            (player + offset) % state_.player_count
        );

        if (state_.players[candidate].active) {
            return candidate;
        }
    }

    throw GameError("No active player available");
}

}  // namespace chinese_durak
