#include <cstdint>
#include <string>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "chinese_durak/game_engine.hpp"

namespace py = pybind11;
namespace cd = chinese_durak;

namespace {

py::list hand_cards(const cd::PlayerState& player) {
    py::list cards;

    for (cd::CardId card = 0; card < cd::kDeckSize; ++card) {
        if (player.has_card(card)) {
            cards.append(card);
        }
    }

    return cards;
}

py::dict state_snapshot(const cd::GameState& state) {
    py::list players;

    for (
        std::uint8_t player = 0;
        player < state.player_count;
        ++player
    ) {
        const cd::PlayerState& player_state = state.players[player];

        py::dict value;
        value["id"] = player;
        value["hand"] = hand_cards(player_state);
        value["card_count"] = player_state.hand_size();
        value["active"] = player_state.active;
        value["placement"] = player_state.placement;
        value["is_durak"] = player_state.is_durak;
        players.append(value);
    }

    py::list table;

    for (std::uint8_t slot = 0; slot < state.attack_count; ++slot) {
        const cd::TableSlot& table_slot = state.table[slot];

        py::dict value;
        value["slot"] = slot;
        value["attack"] = table_slot.attack;
        value["defense"] = table_slot.covered()
            ? py::cast(table_slot.defense)
            : py::none();
        table.append(value);
    }

    py::dict snapshot;
    snapshot["version"] = state.version;
    snapshot["phase"] = state.phase;
    snapshot["player_count"] = state.player_count;
    snapshot["dealer"] = state.dealer;
    snapshot["main_attacker"] = state.main_attacker;
    snapshot["defender"] = state.defender;
    snapshot["eligible_attackers"] = state.eligible_attackers;
    snapshot["passed_attackers"] = state.passed_attackers;
    snapshot["attack_count"] = state.attack_count;
    snapshot["attack_limit"] = state.attack_limit;
    snapshot["deck_count"] = state.deck_count();
    snapshot["trump"] = state.trump;
    snapshot["transfer_locked"] = state.transfer_locked;
    snapshot["take_declared"] = state.take_declared;
    snapshot["draw"] = state.draw;
    snapshot["players"] = players;
    snapshot["table"] = table;
    return snapshot;
}

}  // namespace

PYBIND11_MODULE(_core, module) {
    module.doc() = "Authoritative C++ engine for Chinese Durak";
    module.attr("RULES_VERSION") = cd::RuleSet::kVersion;

    py::register_exception<cd::GameError>(module, "GameError");

    py::enum_<cd::Suit>(module, "Suit")
        .value("CLUBS", cd::Suit::Clubs)
        .value("DIAMONDS", cd::Suit::Diamonds)
        .value("HEARTS", cd::Suit::Hearts)
        .value("SPADES", cd::Suit::Spades);

    py::enum_<cd::Rank>(module, "Rank")
        .value("TWO", cd::Rank::Two)
        .value("THREE", cd::Rank::Three)
        .value("FOUR", cd::Rank::Four)
        .value("FIVE", cd::Rank::Five)
        .value("SIX", cd::Rank::Six)
        .value("SEVEN", cd::Rank::Seven)
        .value("EIGHT", cd::Rank::Eight)
        .value("NINE", cd::Rank::Nine)
        .value("TEN", cd::Rank::Ten)
        .value("JACK", cd::Rank::Jack)
        .value("QUEEN", cd::Rank::Queen)
        .value("KING", cd::Rank::King)
        .value("ACE", cd::Rank::Ace);

    py::enum_<cd::Phase>(module, "Phase")
        .value(
            "WAITING_FOR_PLAYERS",
            cd::Phase::WaitingForPlayers
        )
        .value("OPENING_ATTACK", cd::Phase::OpeningAttack)
        .value("DEFENSE", cd::Phase::Defense)
        .value("ATTACK_EXTENSION", cd::Phase::AttackExtension)
        .value("THROW_AFTER_TAKE", cd::Phase::ThrowAfterTake)
        .value("FINISHED", cd::Phase::Finished);

    py::enum_<cd::ActionKind>(module, "ActionKind")
        .value("ATTACK", cd::ActionKind::Attack)
        .value("DEFEND", cd::ActionKind::Defend)
        .value("TRANSFER", cd::ActionKind::Transfer)
        .value("TAKE", cd::ActionKind::Take)
        .value("PASS_ATTACK", cd::ActionKind::PassAttack);

    py::class_<cd::Action>(module, "Action")
        .def_readonly("kind", &cd::Action::kind)
        .def_readonly("card", &cd::Action::card)
        .def_readonly("target_slot", &cd::Action::target_slot)
        .def_static("attack", &cd::Action::attack)
        .def_static("defend", &cd::Action::defend)
        .def_static("transfer", &cd::Action::transfer)
        .def_static("take", &cd::Action::take)
        .def_static("pass_attack", &cd::Action::pass_attack)
        .def("__repr__", [](const cd::Action& action) {
            return "Action(kind="
                + std::to_string(
                    static_cast<std::uint8_t>(action.kind)
                )
                + ", card="
                + std::to_string(action.card)
                + ", target_slot="
                + std::to_string(action.target_slot)
                + ")";
        });

    py::class_<cd::RuleSet>(module, "RuleSet")
        .def(py::init<>())
        .def_readwrite(
            "initial_hand_size",
            &cd::RuleSet::initial_hand_size
        )
        .def_readwrite("max_attacks", &cd::RuleSet::max_attacks)
        .def_readwrite("max_decisions", &cd::RuleSet::max_decisions)
        .def_readwrite(
            "transfer_enabled",
            &cd::RuleSet::transfer_enabled
        )
        .def_readwrite(
            "throw_after_take",
            &cd::RuleSet::throw_after_take
        );

    py::class_<cd::GameEngine>(module, "GameEngine")
        .def(py::init<cd::RuleSet>(), py::arg("rules") = cd::RuleSet{})
        .def(
            "start",
            &cd::GameEngine::start,
            py::arg("player_count"),
            py::arg("seed"),
            py::arg("dealer") = 0
        )
        .def("legal_actions", &cd::GameEngine::legal_actions)
        .def("apply", &cd::GameEngine::apply)
        .def_property_readonly("state", [](const cd::GameEngine& engine) {
            return state_snapshot(engine.state());
        });

    module.def("make_card", &cd::make_card);
    module.def("card_name", &cd::card_name);
    module.def("beats", &cd::beats);
}
