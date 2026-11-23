import csv
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.simulate_lstm_paper_execution import load, simulate as simulate_raw


def simulate(data, period, **kwargs):
    return simulate_raw(data, period, futures_multiplier=10,
                        futures_initial_margin=500, **kwargs)


def rows(count=12):
    return [{"timestamp": datetime(2026, 1, 1, 10) + timedelta(minutes=5*i),
             "open": 100 + i, "high": 101 + i, "low": 99 + i,
             "close": 100.5 + i, "probability": .8 if i % 2 == 0 else .2,
             "futures_open": 200 + i, "futures_close": 200.5 + i} for i in range(count)]


def test_two_legs_use_opposite_directions_and_close_forced():
    result = simulate(rows(), "5min")
    assert result["stock_long"]["trades"] == result["futures_short"]["trades"]
    assert result["stock_long"]["forced_exits"] == 1
    assert result["futures_short"]["forced_exits"] == 1
    assert result["stock_long"]["unrealized_pnl"] == 0
    assert result["stock_long"]["trades"] == 1


def test_trades_do_not_overlap():
    result = simulate(rows(40), "5min")
    ledger = result["stock_long"]["trades_ledger"]
    for previous, current in zip(ledger, ledger[1:]):
        assert current["entry"] > previous["exit"]


def test_rejects_bad_or_unsorted_predictions(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("timestamp,open,high,low,close,probability,futures_open,futures_close\n2026-01-01 10:05:00,1,2,0.5,1,.5,2,2\n2026-01-01 10:00:00,1,2,0.5,1,.5,2,2\n")
    with pytest.raises(ValueError, match="sorted"):
        load(path)


def test_no_signal_is_no_trade():
    data = rows(8)
    for row in data:
        row["probability"] = .5
    result = simulate(data, "15min")
    assert result["stock_long"]["trades"] == 0
    assert result["futures_short"]["trades"] == 0


def test_margin_rejects_instead_of_forcing_one_contract():
    result = simulate(rows(), "5min", cash=100)
    assert result["futures_short"]["trades"] == 0
    assert result["futures_short"]["margin_rejects"] > 0


@pytest.mark.parametrize('period,minutes', [('5min', 5), ('15min', 15)])
@pytest.mark.parametrize('hour,minute,allowed', [(6, 55, False), (7, 0, True),
    (14, 45, True), (15, 0, False), (16, 0, False)])
def test_moscow_session(period, minutes, hour, minute, allowed):
    entry = datetime(2026, 11, 21, hour, minute)  # Saturday; input is UTC.
    data = rows(17)
    for i, row in enumerate(data):
        row.update(timestamp=entry + timedelta(minutes=(i-1)*minutes),
                   probability=.8 if i == 0 else .5)
    leg = simulate(data, period)['stock_long']
    assert leg['trades'] == int(allowed)
    if allowed:
        assert leg['trades_ledger'][0]['exit'] == (entry + timedelta(minutes=75)).isoformat(' ')


def test_missing_holding_bar_does_not_fill_next_day():
    data = rows()
    data[-1]['timestamp'] += timedelta(days=1)
    with pytest.raises(ValueError, match='missing holding bar'):
        simulate(data, '5min')


def test_futures_use_separate_prices_and_multiplier():
    trade = simulate(rows(), "5min")["futures_short"]["trades_ledger"][0]
    assert trade["entry_price"] == pytest.approx(202 * .9998)
    assert trade["gross_pnl"] == pytest.approx((202 * .9998 - 211.5 * 1.0002) * 10)
    assert trade["contracts"] == 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, -1])
def test_invalid_contract_parameters(value):
    with pytest.raises(ValueError):
        simulate_raw(rows(), "5min", futures_multiplier=value, futures_initial_margin=500)


def test_missing_futures_prices_never_falls_back():
    data = rows()
    del data[0]["futures_open"]
    with pytest.raises(KeyError):
        simulate(data, "5min")


def test_nonfinite_prices_rejected():
    data = rows()
    data[0]["futures_close"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        simulate(data, "5min")


@pytest.mark.parametrize("expired", [False, True])
def test_cli_artifacts_and_expiry(tmp_path, monkeypatch, expired):
    import json
    from scripts.simulate_lstm_paper_execution import main

    path = tmp_path / "predictions.csv"
    data = rows()
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    run = tmp_path / "run"
    monkeypatch.setattr("sys.argv", ["simulate", "--predictions", str(path),
        "--period", "5min", "--run-dir", str(run), "--futures-contract", "SYNTHETIC",
        "--futures-multiplier", "10", "--futures-initial-margin", "500",
        "--futures-expiry", "2026-01-01" if expired else "2026-02-01"])
    if expired:
        with pytest.raises(ValueError, match="expiry"):
            main()
        assert not run.exists()
    else:
        assert main() == 0
        manifest = json.loads((run / "manifest.json").read_text())
        assert manifest["execution"]["live_ready"] is False
        assert manifest["parameters"]["futures_multiplier"] == 10
        assert (run / "trades.csv.gz").exists()
        assert (run / "run.log").exists()
