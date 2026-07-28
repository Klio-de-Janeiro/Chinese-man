#pragma once

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>

#include "chinese_durak/card.hpp"

namespace chinese_durak {

constexpr std::uint8_t kMaxPlayers = 3;
constexpr std::uint8_t kMaxAttackSlots = 6;
constexpr std::uint8_t kNoPlayer = 255;

enum class Phase : std::uint8_t {
    WaitingForPlayers,
    OpeningAttack,
    Defense,
    AttackExtension,
    ThrowAfterTake,
    Finished,
};

struct PlayerState {
    CardMask hand = 0;
    bool active = false;
    std::uint8_t placement = 0;
    bool is_durak = false;

    [[nodiscard]]
    std::uint8_t hand_size() const noexcept {
        return static_cast<std::uint8_t>(std::popcount(hand));
    }

    [[nodiscard]]
    bool has_card(CardId card) const noexcept {
        return (hand & card_bit(card)) != 0;
    }
};

struct TableSlot {
    CardId attack = kInvalidCard;
    CardId defense = kInvalidCard;

    [[nodiscard]]
    bool occupied() const noexcept {
        return attack != kInvalidCard;
    }

    [[nodiscard]]
    bool covered() const noexcept {
        return defense != kInvalidCard;
    }
};

struct GameState {
    std::array<PlayerState, kMaxPlayers> players{};
    std::array<CardId, kDeckSize> deck{};
    std::array<TableSlot, kMaxAttackSlots> table{};
    CardMask discard = 0;

    std::size_t draw_position = 0;
    std::uint64_t version = 0;
    std::uint16_t decision_count = 0;
    std::uint8_t player_count = 0;
    std::uint8_t dealer = kNoPlayer;
    std::uint8_t main_attacker = kNoPlayer;
    std::uint8_t defender = kNoPlayer;
    std::uint8_t round_starter = kNoPlayer;
    std::uint8_t eligible_attackers = 0;
    std::uint8_t passed_attackers = 0;
    std::uint8_t attack_count = 0;
    std::uint8_t attack_limit = 0;
    Suit trump = Suit::Clubs;
    Phase phase = Phase::WaitingForPlayers;
    bool transfer_locked = false;
    bool take_declared = false;
    bool draw = false;

    [[nodiscard]]
    std::size_t deck_count() const noexcept {
        return kDeckSize - draw_position;
    }
};

}  // namespace chinese_durak
