from app.strategies import SupportResistanceMtfStrategy


def _bare_strategy():
    strategy = object.__new__(SupportResistanceMtfStrategy)
    strategy.p = type("Params", (), {"slow_tf_minutes": 240, "swing_left": 2, "swing_right": 2,
                                     "level_lookback": 80, "zone_atr_mult": 0.2})()
    strategy._slow_bars = []
    strategy._levels = []
    return strategy


def test_pivot_is_unavailable_until_right_confirmation_bars_are_complete():
    strategy = _bare_strategy()
    strategy._slow_bars = [(10, 5, 7, 1), (11, 6, 8, 1), (15, 7, 12, 1), (12, 6, 9, 1)]
    strategy._find_levels()
    assert strategy._levels == []

    strategy._slow_bars.append((11, 5, 8, 1))
    strategy._find_levels()
    assert any(level[0] == 15 and level[1] == "resistance" for level in strategy._levels)


def _levels_after(bars):
    strategy = _bare_strategy()
    strategy._slow_bars = list(bars)
    strategy._find_levels()
    return list(strategy._levels)


def test_a_pivot_never_appears_before_its_right_bars_exist():
    series = [(10, 5, 7, 1), (11, 6, 8, 1), (15, 7, 12, 1), (12, 6, 9, 1), (11, 5, 8, 1)]
    for cut in range(len(series) - 1):
        assert _levels_after(series[: cut + 1]) == [], (
            f"pivot at index 2 must stay hidden with only {cut + 1} bars"
        )
    assert _levels_after(series), "the pivot becomes visible once both right bars are closed"


def test_levels_are_monotonic_when_bars_are_appended_online():
    series = [(10, 5, 7, 1), (11, 6, 8, 1), (15, 7, 12, 1), (12, 6, 9, 1), (11, 5, 8, 1), (13, 8, 10, 1)]
    previous: list = []
    for cut in range(1, len(series) + 1):
        current = _levels_after(series[:cut])
        for level in previous:
            assert level in current, f"level {level} disappeared when bars were appended"
        previous = current


def test_pivot_uses_only_completed_slow_bars_and_ignores_the_live_bar():
    complete = [(10, 5, 7, 1), (11, 6, 8, 1), (15, 7, 12, 1), (12, 6, 9, 1), (11, 5, 8, 1)]
    expected = _levels_after(complete)
    assert expected, "the completed series must yield a level"
    assert any(level[0] == 15 for level in expected), "the confirmed pivot must anchor at 15"
    with_live_bar = _levels_after(complete + [(99, 1, 50, 1)])
    assert (15, "resistance", 2, 1) in with_live_bar or any(
        level[0] == 15 and level[1] == "resistance" for level in with_live_bar
    )
    assert all(level[0] < 99 for level in with_live_bar), "the unconfirmed live bar cannot become a level"
