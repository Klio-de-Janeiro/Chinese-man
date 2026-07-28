#include <algorithm>
#include <bit>
#include <cstdint>
#include <iostream>
#include <random>
#include <string_view>
#include <vector>

#include "chinese_durak/game_engine.hpp"

namespace {

using chinese_durak::Action;
using chinese_durak::ActionKind;
using chinese_durak::CardId;
using chinese_durak::CardMask;
using chinese_durak::GameEngine;
using chinese_durak::GameState;
using chinese_durak::Phase;
using chinese_durak::Rank;
using chinese_durak::Suit;
using chinese_durak::beats;
using chinese_durak::card_bit;
using chinese_durak::kDeckSize;
using chinese_durak::make_card;
using chinese_durak::rank_of;
using chinese_durak::suit_of;

int failures = 0;

void expect(bool condition, std::string_view message) {
    if (!condition) {
        std::cerr << "FAILED: " << message << '\n';
        ++failures;
    }
}

[[nodiscard]]
bool contains_kind(
    const std::vector<Action>& actions,
    ActionKind kind
) {
    return std::any_of(
        actions.begin(),
        actions.end(),
        [kind](const Action& action) {
            return action.kind == kind;
        }
    );
}

[[nodiscard]]
Action first_action(
    const std::vector<Action>& actions,
    ActionKind kind
) {
    const auto iterator = std::find_if(
        actions.begin(),
        actions.end(),
        [kind](const Action& action) {
            return action.kind == kind;
        }
    );

    if (iterator == actions.end()) {
        throw std::runtime_error("Expected action was not found");
    }

    return *iterator;
}

[[nodiscard]]
bool state_is_consistent(const GameState& state) {
    CardMask occupied = 0;

    const auto add_zone = [&occupied](CardMask zone) {
        if ((occupied & zone) != 0) {
            return false;
        }

        occupied |= zone;
        return true;
    };

    CardMask stock = 0;

    for (
        std::size_t index = state.draw_position;
        index < kDeckSize;
        ++index
    ) {
        stock |= card_bit(state.deck[index]);
    }

    if (!add_zone(stock)) {
        return false;
    }

    for (
        std::uint8_t player = 0;
        player < state.player_count;
        ++player
    ) {
        if (!add_zone(state.players[player].hand)) {
            return false;
        }
    }

    CardMask table = 0;

    for (std::uint8_t slot = 0; slot < state.attack_count; ++slot) {
        const auto& value = state.table[slot];

        if (!value.occupied()) {
            return false;
        }

        table |= card_bit(value.attack);

        if (value.covered()) {
            table |= card_bit(value.defense);
        }
    }

    if (!add_zone(table) || !add_zone(state.discard)) {
        return false;
    }

    if (std::popcount(occupied) != kDeckSize) {
        return false;
    }

    if (
        state.attack_count > state.attack_limit
        || state.attack_limit > 6
    ) {
        return false;
    }

    if (
        state.phase != Phase::Finished
        && (
            !state.players[state.main_attacker].active
            || !state.players[state.defender].active
        )
    ) {
        return false;
    }

    return (
        state.eligible_attackers
        & static_cast<std::uint8_t>(1U << state.defender)
    ) == 0;
}

void test_card_rules() {
    const CardId seven_clubs =
        make_card(Suit::Clubs, Rank::Seven);
    const CardId nine_clubs =
        make_card(Suit::Clubs, Rank::Nine);
    const CardId two_hearts =
        make_card(Suit::Hearts, Rank::Two);
    const CardId ace_spades =
        make_card(Suit::Spades, Rank::Ace);

    expect(suit_of(seven_clubs) == Suit::Clubs, "card suit encoding");
    expect(rank_of(seven_clubs) == Rank::Seven, "card rank encoding");
    expect(
        beats(nine_clubs, seven_clubs, Suit::Hearts),
        "higher card of the same suit must beat"
    );
    expect(
        beats(two_hearts, ace_spades, Suit::Hearts),
        "trump must beat a non-trump"
    );
    expect(
        !beats(ace_spades, two_hearts, Suit::Hearts),
        "non-trump must not beat a trump"
    );
}

void test_initial_state() {
    GameEngine engine;
    engine.start(3, 42, 1);
    const auto& state = engine.state();

    expect(state.player_count == 3, "three-player game must start");
    expect(state.dealer == 1, "dealer must be stored in game state");
    expect(state.deck_count() == 34, "three players leave 34 cards");
    expect(state.version == 1, "initial state version must be one");
    expect(
        state.phase == Phase::OpeningAttack,
        "game must start with opening attack"
    );

    CardMask all_hands = 0;
    for (std::uint8_t player = 0; player < 3; ++player) {
        expect(
            state.players[player].hand_size() == 6,
            "every player must receive six cards"
        );
        expect(
            (all_hands & state.players[player].hand) == 0,
            "initial hands must not overlap"
        );
        all_hands |= state.players[player].hand;
    }

    bool found_trump = false;
    Rank lowest = Rank::Ace;
    std::uint8_t expected_attacker = 0;

    for (std::uint8_t player = 0; player < 3; ++player) {
        for (CardId card = 0; card < 52; ++card) {
            if (
                state.players[player].has_card(card)
                && suit_of(card) == state.trump
                && (!found_trump || rank_of(card) < lowest)
            ) {
                found_trump = true;
                lowest = rank_of(card);
                expected_attacker = player;
            }
        }
    }

    if (found_trump) {
        expect(
            state.main_attacker == expected_attacker,
            "lowest trump owner must attack first"
        );
    }

    expect(
        engine.legal_actions(state.main_attacker).size() == 6,
        "opening attacker must be able to play every hand card"
    );
}

void test_first_attacker_fallback() {
    bool scenario_found = false;

    for (std::uint64_t seed = 0; seed < 10000; ++seed) {
        GameEngine engine;
        engine.start(3, seed, 1);
        const auto& state = engine.state();

        bool initial_hand_has_trump = false;

        for (std::uint8_t player = 0; player < 3; ++player) {
            for (CardId card = 0; card < 52; ++card) {
                if (
                    state.players[player].has_card(card)
                    && suit_of(card) == state.trump
                ) {
                    initial_hand_has_trump = true;
                }
            }
        }

        if (initial_hand_has_trump) {
            continue;
        }

        expect(
            state.main_attacker == 2,
            "player after dealer must attack when hands have no trumps"
        );
        scenario_found = true;
        break;
    }

    expect(
        scenario_found,
        "a deterministic no-trump opening scenario must exist"
    );
}

void test_take_round() {
    GameEngine engine;
    engine.start(2, 7);

    const std::uint8_t attacker = engine.state().main_attacker;
    const std::uint8_t defender = engine.state().defender;
    const Action attack = first_action(
        engine.legal_actions(attacker),
        ActionKind::Attack
    );

    engine.apply(attacker, attack);

    expect(
        engine.state().phase == Phase::Defense,
        "opening attack must enter defense"
    );
    expect(engine.state().attack_count == 1, "table must contain attack");
    expect(
        contains_kind(
            engine.legal_actions(defender),
            ActionKind::Take
        ),
        "defender must always be allowed to take"
    );

    engine.apply(defender, Action::take());
    expect(
        engine.state().phase == Phase::ThrowAfterTake,
        "take must open post-take throwing"
    );

    engine.apply(attacker, Action::pass_attack());

    expect(
        engine.state().phase == Phase::OpeningAttack,
        "all passes must resolve take and start next round"
    );
    expect(engine.state().attack_count == 0, "table must be cleared");
    expect(
        engine.state().players[defender].hand_size() >= 7,
        "taking player must receive the table"
    );
}

void test_successful_defense_round() {
    bool scenario_found = false;

    for (std::uint64_t seed = 0; seed < 1000; ++seed) {
        GameEngine candidate;
        candidate.start(2, seed);

        const std::uint8_t attacker = candidate.state().main_attacker;
        const std::uint8_t defender = candidate.state().defender;
        const auto attacks = candidate.legal_actions(attacker);

        for (const Action& attack : attacks) {
            GameEngine attempt = candidate;
            attempt.apply(attacker, attack);
            const auto defenses = attempt.legal_actions(defender);

            if (!contains_kind(defenses, ActionKind::Defend)) {
                continue;
            }

            attempt.apply(
                defender,
                first_action(defenses, ActionKind::Defend)
            );

            expect(
                attempt.state().phase == Phase::AttackExtension,
                "covered attack must open attack extension"
            );

            attempt.apply(attacker, Action::pass_attack());

            expect(
                attempt.state().phase == Phase::OpeningAttack,
                "all passes must resolve beaten round"
            );
            expect(
                std::popcount(attempt.state().discard) == 2,
                "beaten pair must move to discard"
            );
            expect(
                attempt.state().main_attacker == defender,
                "successful defender must attack next"
            );

            scenario_found = true;
            break;
        }

        if (scenario_found) {
            break;
        }
    }

    expect(scenario_found, "a deterministic defense scenario must exist");
}

void test_transfer() {
    bool scenario_found = false;

    for (std::uint64_t seed = 0; seed < 1000; ++seed) {
        GameEngine candidate;
        candidate.start(2, seed);

        const std::uint8_t attacker = candidate.state().main_attacker;
        const std::uint8_t defender = candidate.state().defender;

        for (const Action& attack : candidate.legal_actions(attacker)) {
            GameEngine attempt = candidate;
            attempt.apply(attacker, attack);
            const auto actions = attempt.legal_actions(defender);

            if (!contains_kind(actions, ActionKind::Transfer)) {
                continue;
            }

            attempt.apply(
                defender,
                first_action(actions, ActionKind::Transfer)
            );

            expect(
                attempt.state().main_attacker == defender,
                "transferring player must become main attacker"
            );
            expect(
                attempt.state().defender == attacker,
                "two-player transfer must return defense to attacker"
            );
            expect(
                attempt.state().attack_count == 2,
                "transfer card must become another attack"
            );

            scenario_found = true;
            break;
        }

        if (scenario_found) {
            break;
        }
    }

    expect(scenario_found, "a deterministic transfer scenario must exist");
}

void test_illegal_action() {
    GameEngine engine;
    engine.start(2, 11);

    bool rejected = false;

    try {
        engine.apply(engine.state().defender, Action::take());
    } catch (const chinese_durak::GameError&) {
        rejected = true;
    }

    expect(rejected, "illegal out-of-phase action must be rejected");
}

void test_random_legal_play() {
    std::mt19937_64 generator(20260728);

    for (std::uint64_t game = 0; game < 100; ++game) {
        GameEngine engine;
        const std::uint8_t player_count =
            static_cast<std::uint8_t>(2U + game % 2U);
        engine.start(
            player_count,
            generator(),
            static_cast<std::uint8_t>(game % player_count)
        );

        while (engine.state().phase != Phase::Finished) {
            expect(
                state_is_consistent(engine.state()),
                "random-play state must preserve all invariants"
            );

            std::vector<std::pair<std::uint8_t, Action>> choices;

            for (
                std::uint8_t player = 0;
                player < player_count;
                ++player
            ) {
                for (const Action& action : engine.legal_actions(player)) {
                    choices.emplace_back(player, action);
                }
            }

            expect(
                !choices.empty(),
                "a running game must have at least one legal action"
            );

            if (choices.empty()) {
                break;
            }

            const auto& [player, action] = choices[
                generator() % choices.size()
            ];
            engine.apply(player, action);
        }

        expect(
            state_is_consistent(engine.state()),
            "finished random-play state must preserve all invariants"
        );
    }
}

}  // namespace

int main() {
    test_card_rules();
    test_initial_state();
    test_first_attacker_fallback();
    test_take_round();
    test_successful_defense_round();
    test_transfer();
    test_illegal_action();
    test_random_legal_play();

    if (failures != 0) {
        std::cerr << failures << " test checks failed\n";
        return 1;
    }

    std::cout << "All engine checks passed\n";
    return 0;
}
