#pragma once

#include <cstdint>

#include "chinese_durak/card.hpp"

namespace chinese_durak {

enum class ActionKind : std::uint8_t {
    Attack,
    Defend,
    Transfer,
    Take,
    PassAttack,
};

struct Action {
    ActionKind kind;
    CardId card = kInvalidCard;
    std::uint8_t target_slot = 0;

    [[nodiscard]]
    static constexpr Action attack(CardId value) noexcept {
        return {ActionKind::Attack, value, 0};
    }

    [[nodiscard]]
    static constexpr Action defend(
        CardId value,
        std::uint8_t slot
    ) noexcept {
        return {ActionKind::Defend, value, slot};
    }

    [[nodiscard]]
    static constexpr Action transfer(CardId value) noexcept {
        return {ActionKind::Transfer, value, 0};
    }

    [[nodiscard]]
    static constexpr Action take() noexcept {
        return {ActionKind::Take, kInvalidCard, 0};
    }

    [[nodiscard]]
    static constexpr Action pass_attack() noexcept {
        return {ActionKind::PassAttack, kInvalidCard, 0};
    }

    bool operator==(const Action&) const = default;
};

}  // namespace chinese_durak
