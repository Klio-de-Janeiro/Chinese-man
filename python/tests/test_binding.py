import chinese_durak as durak


def test_rules_version() -> None:
    assert durak.RULES_VERSION == "chinese-durak/0.2.0-draft"


def test_python_engine_smoke() -> None:
    engine = durak.GameEngine()
    engine.start(player_count=2, seed=42, dealer=1)

    state = engine.state
    attacker = state["main_attacker"]
    actions = engine.legal_actions(attacker)

    assert state["phase"] == durak.Phase.OPENING_ATTACK
    assert state["dealer"] == 1
    assert state["discard_count"] == 0
    assert len(state["players"]) == 2
    assert len(actions) == 6

    engine.apply(attacker, actions[0])

    assert engine.state["phase"] == durak.Phase.DEFENSE
    assert engine.state["attack_count"] == 1


def test_card_rules() -> None:
    seven_clubs = durak.make_card(
        durak.Suit.CLUBS,
        durak.Rank.SEVEN,
    )
    nine_clubs = durak.make_card(
        durak.Suit.CLUBS,
        durak.Rank.NINE,
    )

    assert durak.card_name(seven_clubs) == "7C"
    assert durak.beats(
        nine_clubs,
        seven_clubs,
        durak.Suit.HEARTS,
    )
