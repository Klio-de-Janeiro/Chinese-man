#pragma once

#include <cstdint>
#include <stdexcept>
#include <vector>

#include "chinese_durak/action.hpp"
#include "chinese_durak/game_state.hpp"
#include "chinese_durak/ruleset.hpp"

namespace chinese_durak {

class GameError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class GameEngine {
public:
    explicit GameEngine(RuleSet rules = {});

    /**
     * Starts a deterministic game for tests and future self-play.
     */
    void start(
        std::uint8_t player_count,
        std::uint64_t seed,
        std::uint8_t dealer = 0
    );

    /**
     * Returns actions accepted from the specified player's current view.
     */
    [[nodiscard]]
    std::vector<Action> legal_actions(std::uint8_t player) const;

    /**
     * Validates and applies one authoritative action.
     */
    void apply(std::uint8_t player, const Action& action);

    [[nodiscard]]
    const GameState& state() const noexcept;

    [[nodiscard]]
    const RuleSet& rules() const noexcept;

private:
    RuleSet rules_;
    GameState state_;

    void deal_initial_hands();
    void select_first_attacker();
    void apply_attack(std::uint8_t player, CardId card);
    void apply_defense(
        std::uint8_t player,
        CardId card,
        std::uint8_t target_slot
    );
    void apply_transfer(std::uint8_t player, CardId card);
    void apply_take();
    void apply_pass(std::uint8_t player);
    void resolve_take();
    void resolve_beaten();
    void refill_hands();
    void update_results();
    void begin_round(std::uint8_t preferred_attacker);
    void clear_table() noexcept;

    [[nodiscard]]
    bool is_legal(std::uint8_t player, const Action& action) const;

    [[nodiscard]]
    bool all_attacks_covered() const noexcept;

    [[nodiscard]]
    bool table_contains_rank(Rank rank) const noexcept;

    [[nodiscard]]
    std::uint8_t active_players_mask() const noexcept;

    [[nodiscard]]
    std::uint8_t next_active_player(std::uint8_t player) const;

    [[nodiscard]]
    std::uint8_t first_active_at_or_after(std::uint8_t player) const;
};

}  // namespace chinese_durak
