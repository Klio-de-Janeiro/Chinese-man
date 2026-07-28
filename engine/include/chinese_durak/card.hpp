#pragma once

#include <cstdint>
#include <string>
#include <string_view>

namespace chinese_durak {

using CardId = std::uint8_t;
using CardMask = std::uint64_t;

constexpr CardId kDeckSize = 52;
constexpr CardId kInvalidCard = 255;

enum class Suit : std::uint8_t {
    Clubs = 0,
    Diamonds = 1,
    Hearts = 2,
    Spades = 3,
};

enum class Rank : std::uint8_t {
    Two = 0,
    Three = 1,
    Four = 2,
    Five = 3,
    Six = 4,
    Seven = 5,
    Eight = 6,
    Nine = 7,
    Ten = 8,
    Jack = 9,
    Queen = 10,
    King = 11,
    Ace = 12,
};

[[nodiscard]]
constexpr bool is_valid_card(CardId card) noexcept {
    return card < kDeckSize;
}

[[nodiscard]]
constexpr CardId make_card(Suit suit, Rank rank) noexcept {
    return static_cast<CardId>(
        static_cast<CardId>(suit) * 13U
        + static_cast<CardId>(rank)
    );
}

[[nodiscard]]
constexpr Suit suit_of(CardId card) noexcept {
    return static_cast<Suit>(card / 13U);
}

[[nodiscard]]
constexpr Rank rank_of(CardId card) noexcept {
    return static_cast<Rank>(card % 13U);
}

[[nodiscard]]
constexpr CardMask card_bit(CardId card) noexcept {
    return CardMask{1} << card;
}

[[nodiscard]]
constexpr bool beats(
    CardId defense,
    CardId attack,
    Suit trump
) noexcept {
    const Suit defense_suit = suit_of(defense);
    const Suit attack_suit = suit_of(attack);

    if (defense_suit == attack_suit) {
        return rank_of(defense) > rank_of(attack);
    }

    return defense_suit == trump && attack_suit != trump;
}

[[nodiscard]]
std::string_view suit_symbol(Suit suit) noexcept;

[[nodiscard]]
std::string_view rank_symbol(Rank rank) noexcept;

[[nodiscard]]
std::string card_name(CardId card);

}  // namespace chinese_durak
