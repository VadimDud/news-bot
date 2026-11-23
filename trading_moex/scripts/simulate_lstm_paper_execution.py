"""Paper-only LSTM execution simulator: stock long or futures short."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
from datetime import datetime, time, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.timezones import to_market
SPECS = {
    "15min": {"horizon": 5, "stock_commission": .0005, "stock_slippage": .0005,
              "futures_commission": .0002, "futures_slippage": .0002},
    "5min": {"horizon": 15, "stock_commission": .0005, "stock_slippage": .0005,
             "futures_commission": .0002, "futures_slippage": .0002},
}


def load(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {"timestamp", "open", "high", "low", "close", "probability",
                "futures_open", "futures_close"}
    if not rows or not required <= set(rows[0]):
        raise ValueError("prediction CSV has missing required columns")
    previous = None
    result = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["timestamp"])
        if timestamp.tzinfo or (previous is not None and timestamp <= previous):
            raise ValueError("timestamps must be UTC-naive, sorted and unique")
        values = {key: float(row[key]) for key in ("open", "high", "low", "close", "probability",
                                                   "futures_open", "futures_close")}
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError("prices and probability must be finite")
        if not 0 <= values["probability"] <= 1 or not 0 < values["low"] <= values["open"] <= values["high"]:
            raise ValueError("invalid prediction or OHLC")
        if not values["low"] <= values["close"] <= values["high"] or values["futures_open"] <= 0 or values["futures_close"] <= 0:
            raise ValueError("close outside OHLC range")
        result.append({"timestamp": timestamp, **values})
        previous = timestamp
    return result


def _trade(entry, exit_, direction, commission, slippage, forced, *, futures, multiplier, contracts):
    open_key, close_key = (("futures_open", "futures_close") if futures else ("open", "close"))
    entry_price = entry[open_key] * (1 + slippage * direction)
    exit_price = exit_[close_key] * (1 - slippage * direction)
    gross = direction * (exit_price - entry_price) * multiplier * contracts
    notional = entry_price * multiplier * contracts
    costs = (entry_price + exit_price) * multiplier * contracts * commission
    return {"entry": entry["timestamp"].isoformat(" "), "exit": exit_["timestamp"].isoformat(" "),
            "direction": direction, "entry_price": entry_price, "exit_price": exit_price,
            "notional": notional, "contracts": contracts, "gross_pnl": gross, "commission": costs,
            "slippage": (abs(entry_price - entry[open_key]) + abs(exit_[close_key] - exit_price)) * multiplier * contracts,
            "net_pnl": gross - costs, "forced_exit": forced}


def simulate(rows: list[dict], period: str, cash: float = 100_000.0, *,
             futures_multiplier: float, futures_initial_margin: float) -> dict:
    if not all(math.isfinite(v) and v > 0 for v in
               (cash, futures_multiplier, futures_initial_margin)):
        raise ValueError("cash, multiplier and initial margin must be finite and positive")
    # Validate direct callers as well as CSV inputs; never substitute spot prices.
    previous = None
    for row in rows:
        values = [row[k] for k in ("open", "high", "low", "close", "probability",
                                   "futures_open", "futures_close")]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("prices and probability must be finite")
        if (not 0 <= row["probability"] <= 1
                or not 0 < row["low"] <= row["open"] <= row["high"]
                or not row["low"] <= row["close"] <= row["high"]
                or min(row["futures_open"], row["futures_close"]) <= 0):
            raise ValueError("invalid prediction or prices")
        if row["timestamp"].tzinfo or (previous is not None and row["timestamp"] <= previous):
            raise ValueError("timestamps must be UTC-naive, sorted and unique")
        previous = row["timestamp"]
    spec = SPECS[period]
    bar = timedelta(minutes=int(period.removesuffix('min')))
    legs = {"stock_long": (spec["stock_commission"], spec["stock_slippage"], 1, False),
            "futures_short": (spec["futures_commission"], spec["futures_slippage"], -1, True)}
    output = {}
    for name, (commission, slippage, direction, futures) in legs.items():
        trades = []
        index = 0
        exposure_bars = 0
        notional_bars = 0.0
        available_cash = cash
        margin_rejects = 0
        session_rejects = 0
        while index < len(rows):
            row = rows[index]
            probability = row["probability"]
            if (direction == 1 and probability < .55) or (direction == -1 and probability > .45):
                index += 1
                continue
            entry_index = index + 1
            exit_index = index + spec["horizon"]
            if entry_index >= len(rows):
                break
            forced = exit_index >= len(rows)
            exit_index = min(exit_index, len(rows) - 1)
            entry_row = rows[entry_index]
            entry_time = to_market(entry_row['timestamp'])
            deadline = entry_time.replace(hour=19, minute=0, second=0, microsecond=0)
            if (entry_row['timestamp'] != row['timestamp'] + bar
                    or entry_time.time() < time(10)
                    or entry_time + spec['horizon'] * bar > deadline):
                session_rejects += 1
                index += 1
                continue
            price = entry_row["futures_open"] if futures else entry_row["open"]
            fill = price * (1 + slippage * direction)
            multiplier = futures_multiplier if futures else 1.0
            required_cash = (futures_initial_margin if futures else fill) + fill * multiplier * commission
            if available_cash < required_cash:
                margin_rejects += 1
                index += 1
                continue
            # A missing holding bar invalidates the run; never invent a fill or
            # use a later session's close for an already open position.
            exit_close = rows[exit_index]['timestamp'] + bar
            if any(rows[k]['timestamp'] != rows[k-1]['timestamp'] + bar
                   for k in range(entry_index + 1, exit_index + 1)):
                raise ValueError('missing holding bar: cannot verify in-session exit')
            trade = _trade(rows[entry_index], rows[exit_index], direction, commission, slippage, forced,
                                 futures=futures, multiplier=futures_multiplier if futures else 1.0,
                                 contracts=1)
            trade['exit'] = exit_close.isoformat(' ')
            trades.append(trade)
            available_cash += trade["net_pnl"]
            exposure_bars += exit_index - entry_index + 1
            notional_bars += trade["notional"] * (exit_index - entry_index + 1)
            index = exit_index + 1
        net = sum(trade["net_pnl"] for trade in trades)
        gross = sum(trade["gross_pnl"] for trade in trades)
        wins = [trade["net_pnl"] for trade in trades if trade["net_pnl"] > 0]
        losses = [trade["net_pnl"] for trade in trades if trade["net_pnl"] < 0]
        equity = cash
        peak = cash
        max_drawdown = 0.0
        for trade in trades:
            equity += trade["net_pnl"]
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        exposure = notional_bars / len(rows) if rows else 0.0
        output[name] = {"trades": len(trades), "realized_pnl": round(net, 8),
                        "diagnostic_only": True, "margin_rejects": margin_rejects,
                        "session_rejects": session_rejects,
                        "exposure_pct": round(exposure_bars / len(rows) * 100, 8) if rows else 0.0,
                        "average_notional_exposure": exposure,
                        "forced_exit_pnl": sum(t["net_pnl"] for t in trades if t["forced_exit"]),
                        "unrealized_pnl": 0.0, "gross_pnl": round(gross, 8),
                        "commission": round(sum(t["commission"] for t in trades), 8),
                        "slippage": round(sum(t["slippage"] for t in trades), 8),
                        "return_pct": round(net / cash * 100, 8),
                        "return_on_exposure_pct": round(net / exposure * 100, 8) if exposure else 0.0,
                        "max_drawdown": round(max_drawdown, 8),
                        "win_rate_pct": round(len(wins) / len(trades) * 100, 8) if trades else 0.0,
                        "profit_factor": round(sum(wins) / abs(sum(losses)), 8) if losses else None,
                        "forced_exits": sum(t["forced_exit"] for t in trades), "trades_ledger": trades}
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--period", choices=tuple(SPECS), required=True)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--futures-contract", required=True)
    parser.add_argument("--futures-multiplier", required=True, type=float,
                        help="RUB per quoted price point per contract")
    parser.add_argument("--futures-initial-margin", required=True, type=float,
                        help="Fixed initial margin in RUB per contract; diagnostic only")
    parser.add_argument("--futures-expiry", required=True, type=datetime.fromisoformat,
                        help="UTC-naive expiry boundary; all input bars must precede it")
    args = parser.parse_args()
    if args.run_dir.exists():
        raise SystemExit("run directory already exists")
    rows = load(args.predictions)
    if args.futures_expiry.tzinfo or rows[-1]["timestamp"] >= args.futures_expiry:
        raise ValueError("input must precede UTC-naive contract expiry; rollover is unsupported")
    metrics = simulate(rows, args.period, futures_multiplier=args.futures_multiplier,
                       futures_initial_margin=args.futures_initial_margin)
    args.run_dir.mkdir(parents=True)
    manifest = {"study_id": "LSTM-PAPER-EXECUTION-001", "period": args.period,
                "status": "completed", "input_sha256": hashlib.sha256(args.predictions.read_bytes()).hexdigest(),
                "parameters": {"long_probability": .55, "short_probability": .45,
                                "horizon": SPECS[args.period]["horizon"], "cash": 100_000.0,
                                "futures_multiplier": args.futures_multiplier,
                                "futures_initial_margin": args.futures_initial_margin,
                                "futures_contract": args.futures_contract,
                                "futures_expiry": args.futures_expiry.isoformat()},
                "execution": {"stock": "long", "short": "futures", "orders_enabled": False,
                               "contract_multiplier_modeled": True, "diagnostic_only": True,
                               "capital_mode": "independent_legs", "quantity": 1,
                               "execution_window_moscow": "10:00 <= entry < exit <= 19:00",
                               "live_ready": False, "variation_margin_modeled": False},
                "storage_timezone": "UTC-naive", "market_timezone": "Europe/Moscow"}
    (args.run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (args.run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    with gzip.open(args.run_dir / "trades.csv.gz", "wt", newline="") as stream:
        fields = ["leg", "entry", "exit", "direction", "entry_price", "exit_price", "contracts", "gross_pnl", "commission", "slippage", "net_pnl", "forced_exit"]
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for leg, values in metrics.items():
            for trade in values["trades_ledger"]:
                writer.writerow({"leg": leg, **{key: trade[key] for key in fields[1:]}})
    (args.run_dir / "checks.json").write_text(json.dumps({"input_validation_passed": True,
        "live_ready": False, "read_only": True,
        "orders_enabled": False, "open_positions": 0, "ledger_rows": sum(v["trades"] for v in metrics.values())}, indent=2))
    (args.run_dir / "run.log").write_text("Diagnostic independent-leg simulation only; no orders.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
