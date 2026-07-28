#pragma once

#include <cstdint>
#include <string_view>

namespace chinese_durak {

struct RuleSet {
    static constexpr std::string_view kVersion =
        "chinese-durak/0.2.0-draft";

    std::uint8_t initial_hand_size = 6;
    std::uint8_t max_attacks = 6;
    std::uint16_t max_decisions = 500;
    bool transfer_enabled = true;
    bool throw_after_take = true;
};

}  // namespace chinese_durak
