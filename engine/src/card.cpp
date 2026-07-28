#include "chinese_durak/card.hpp"

#include <array>
#include <stdexcept>

namespace chinese_durak {
namespace {

constexpr std::array<std::string_view, 4> kSuitSymbols{
    "C",
    "D",
    "H",
    "S",
};

constexpr std::array<std::string_view, 13> kRankSymbols{
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "J",
    "Q",
    "K",
    "A",
};

}  // namespace

std::string_view suit_symbol(Suit suit) noexcept {
    return kSuitSymbols[static_cast<std::size_t>(suit)];
}

std::string_view rank_symbol(Rank rank) noexcept {
    return kRankSymbols[static_cast<std::size_t>(rank)];
}

std::string card_name(CardId card) {
    if (!is_valid_card(card)) {
        throw std::invalid_argument("Invalid card identifier");
    }

    return std::string(rank_symbol(rank_of(card)))
        + std::string(suit_symbol(suit_of(card)));
}

}  // namespace chinese_durak
