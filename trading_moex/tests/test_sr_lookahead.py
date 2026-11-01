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
