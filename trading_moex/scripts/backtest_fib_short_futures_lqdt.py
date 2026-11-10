#!/usr/bin/env python3
"""Сравнение Fib short 1day: акции (с переносом) vs фьючерс + LQDT на маржу.

Гипотеза (проверяется на тех же сделках, что и шорт акциями): стратегия Fib
short 1day убыточна из-за платы за одалживание акций (70/175 ₽/ночь). Если ту же
экспозицию открывать фьючерсом, а высвободившийся капитал держать в LQDT,
заёмных процентов не возникает, а обеспечение приносит доход фонда.

Три плеча сравниваются на одном и том же потоке сделок (сигналы и цены входа/
выхода совпадают, меняется только учёт издержек и доходности капитала):

  1. ``stock``    — текущий шорт акциями: комиссия 0.05%/сторона; перенос
                    175 ₽/ночь при неционале ≤250 000 (70 ₽ при ≤100 000);
                    свободный капитал не приносит дохода.
  2. ``futures``  — фьючерсный шорт (вечная экспозиция без экспирации): комиссия
                    биржи/брокера на сторону + ГО, свободная маржа в LQDT.
  3. ``fut_no_lqdt`` — контрольный: фьючерс без дохода LQDT (изолирует вклад
                    маржинального обеспечения).

Все ставки — параметры командной строки, ни одна не подобрана по результату.

Ограничения (см. отчёт): фьючерсная нога моделируется как доля нецинала, а не
как целое число контрактов; доход LQDT начисляется от свободной маржи; база
данных не содержит свечей LQDT/фьючерсов, поэтому ставка LQDT задаётся
константой (годовая доходность → дневная).

Usage (from trading_moex/):
  python3 scripts/backtest_fib_short_futures_lqdt.py \
      --db data/trader_4h.db --period 1day --lqdt-annual-pct 16
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import backtrader as bt  # noqa: E402
import pandas as pd  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
CASH_PER_TICKER = 100_000.0
STOCK_COMMISSION = 0.0005
STOCK_SLIPPAGE = 0.0005


@dataclass(frozen=True)
class CostModel:
    """Издержки и доходность одной ноги; все ставки задаются снаружи."""

    name: str
    commission_per_side: float
    slippage_per_side: float
    carry_flat: float = 0.0
    carry_large: float = 0.0
    carry_small_threshold: float = 100_000.0
    carry_large_threshold: float = 250_000.0
    margin_rate: float = 0.0
    lqdt_daily_pct: float = 0.0
    lqdt_on_free_margin: bool = False

    def carry(self, notional: float, nights: int) -> float:
        if self.carry_flat <= 0 or nights <= 0:
            return 0.0
        rate = self.carry_flat if notional <= self.carry_small_threshold else self.carry_large
        return rate * nights


class _Recorder(FibPullbackStrategy):
    """Фиксирует вход/выход, нецинал и размер для последующего учёта ног."""

    def __init__(self):
        super().__init__()
        self.closed: list[dict] = []
        self._open: dict = {}

    def notify_trade(self, trade):
        key = getattr(trade.data, "_name", None) or str(id(trade.data))
        if trade.justopened:
            size = abs(float(trade.size))
            entry = float(trade.price) if trade.price else 0.0
            self._open[key] = (size, entry, entry * size)
        if trade.isclosed:
            size, entry, notional = self._open.pop(key, (0.0, 0.0, 0.0))
            self.closed.append({
                "open": bt.num2date(trade.dtopen),
                "close": bt.num2date(trade.dtclose),
                "entry": entry,
                "size": size,
                "notional": notional,
                "pnl_gross": float(trade.pnlcomm or 0.0),
                "ticker": key,
            })
        super().notify_trade(trade)


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def base_params(ticker: str, bracket: dict | None = None) -> dict:
    """Прод-конфиг шорта 1day: TICKER_OVERRIDES + direction=-1, без EOD-флэта."""
    params = dict(_FIB_PULLBACK_PARAMS_TUPLE)
    overrides = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for key, value in overrides.items():
        if key not in ("direction", "timeframe"):
            params[key] = value
    params["direction"] = -1
    params["flat_mode"] = 0
    if bracket:
        params.update(bracket)
    return params


def run_ticker(ticker: str, df: pd.DataFrame, cost: CostModel,
               bracket: dict | None = None) -> list[dict]:
    cb = _setup_cerebro(
        _Recorder, base_params(ticker, bracket), CASH_PER_TICKER,
        cost.commission_per_side, slippage=cost.slippage_per_side,
    )
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    return strat.closed


def _has_weekend_candles(df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    dow = df.index.dayofweek
    return bool((dow == 5).any() or (dow == 6).any())


def nights_held(op, close, weekend_trading: bool = False) -> int:
    """Ночи переноса; при weekend_trading каждая календарная ночь = 1."""
    carries = 0
    cur = op.date()
    while cur < close.date():
        nxt = cur + timedelta(days=1)
        if weekend_trading:
            carries += 1
        elif nxt.weekday() == 5:
            carries += 3
        elif nxt.weekday() < 5:
            carries += 1
        cur = nxt
    return carries


def build_ledger(trades: list[dict], weekend_trading: bool, cost: CostModel) -> list[dict]:
    """Считает итог по каждой сделке для одной ноги без побочных эффектов."""
    ledger = []
    for trade in trades:
        nights = nights_held(trade["open"], trade["close"], weekend_trading)
        notional = float(trade["notional"])
        carry = cost.carry(notional, nights)
        commission_cost = notional * cost.commission_per_side * 2
        slippage_cost = notional * cost.slippage_per_side * 2
        margin = notional * cost.margin_rate if cost.margin_rate > 0 else notional
        free_cash = max(CASH_PER_TICKER - margin, 0.0)
        lqdt_income = (
            free_cash * cost.lqdt_daily_pct / 100.0 * nights
            if cost.lqdt_on_free_margin else 0.0
        )
        gross_with_stock_costs = float(trade["pnl_gross"])
        net = gross_with_stock_costs - carry - commission_cost - slippage_cost + lqdt_income
        ledger.append({
            "ticker": trade["ticker"],
            "open": trade["open"].isoformat(),
            "close": trade["close"].isoformat(),
            "size": round(float(trade["size"]), 4),
            "notional": round(notional, 2),
            "nights": nights,
            "pnl_gross": round(gross_with_stock_costs, 2),
            "carry": round(carry, 2),
            "commission": round(commission_cost, 2),
            "slippage": round(slippage_cost, 2),
            "lqdt_income": round(lqdt_income, 2),
            "net_leg_pnl": round(net, 2),
        })
    return ledger


def summarize(leg: str, ledger: list[dict], initial_cash: float) -> dict:
    wins = [r for r in ledger if r["net_leg_pnl"] > 0]
    losses = [r for r in ledger if r["net_leg_pnl"] < 0]
    gross = sum(r["pnl_gross"] for r in ledger)
    net = sum(r["net_leg_pnl"] for r in ledger)
    return {
        "leg": leg,
        "trades": len(ledger),
        "win_rate_pct": round(len(wins) / len(ledger) * 100, 2) if ledger else 0.0,
        "gross_pnl": round(gross, 2),
        "carry_total": round(sum(r["carry"] for r in ledger), 2),
        "commission_total": round(sum(r["commission"] for r in ledger), 2),
        "slippage_total": round(sum(r["slippage"] for r in ledger), 2),
        "lqdt_income_total": round(sum(r["lqdt_income"] for r in ledger), 2),
        "net_pnl": round(net, 2),
        "net_return_pct": round(net / initial_cash * 100, 4) if initial_cash else 0.0,
        "profit_factor": (
            round(sum(r["net_leg_pnl"] for r in wins) / abs(sum(r["net_leg_pnl"] for r in losses)), 4)
            if losses else None
        ),
        "trades_opened_at_price": [
            {"open": r["open"], "close": r["close"], "notional": r["notional"]}
            for r in ledger
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--lqdt-annual-pct", type=float, default=16.0,
                        help="Годовая доходность LQDT, %%")
    parser.add_argument("--futures-commission", type=float, default=0.0002,
                        help="Комиссия фьючерсной ноги на сторону (доля нецинала)")
    parser.add_argument("--futures-slippage", type=float, default=0.0002,
                        help="Проскальзывание фьючерсной ноги на сторону")
    parser.add_argument("--futures-margin", type=float, default=0.20,
                        help="Ставка ГО фьючерса как доля нецинала")
    parser.add_argument("--sr-variant", default="baseline",
                        choices=["baseline", "sr_tp", "sr_tp_min", "sr_tp_sl", "sr_min_sl"],
                        help="Вариант брекета с S/R (см. scripts/backtest_fib_sr.py)")
    parser.add_argument("--weak-params", default="{}",
                        help="JSON доп. параметров фильтра ослабления (напр. "
                             "'{\"weak_need_upper_shadow\": 0.5}')")
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args()

    bracket = {
        "baseline": {},
        "sr_tp": {"sr_tp_mode": 1},
        "sr_tp_min": {"sr_tp_mode": 2},
        "sr_tp_sl": {"sr_tp_mode": 1, "sr_sl_mode": 1},
        "sr_min_sl": {"sr_tp_mode": 2, "sr_sl_mode": 1},
    }[args.sr_variant]
    bracket.update(json.loads(args.weak_params))

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    lqdt_daily = args.lqdt_annual_pct / 365.0

    models = {
        "stock": CostModel(
            name="stock",
            commission_per_side=0.0, slippage_per_side=0.0,
            carry_flat=70.0, carry_large=175.0,
        ),
        "futures": CostModel(
            name="futures",
            commission_per_side=args.futures_commission,
            slippage_per_side=args.futures_slippage,
            margin_rate=args.futures_margin,
            lqdt_daily_pct=lqdt_daily,
            lqdt_on_free_margin=True,
        ),
        "fut_no_lqdt": CostModel(
            name="fut_no_lqdt",
            commission_per_side=args.futures_commission,
            slippage_per_side=args.futures_slippage,
            margin_rate=args.futures_margin,
            lqdt_daily_pct=lqdt_daily,
            lqdt_on_free_margin=False,
        ),
    }

    # Цены/сигналы считаются один раз: ноги отличаются только издержками.
    raw_trades: dict[str, list[dict]] = {}
    weekend: dict[str, bool] = {}
    trade_cost = CostModel(
        name="signal_only",
        commission_per_side=0.0, slippage_per_side=0.0,
    )
    for ticker in tickers:
        df = load_df(ticker, args.db, args.period)
        if df.empty:
            continue
        weekend[ticker] = _has_weekend_candles(df)
        raw_trades[ticker] = run_ticker(ticker, df, trade_cost, bracket)

    initial_cash = CASH_PER_TICKER * max(len(raw_trades), 1)
    summaries = {}
    all_ledgers = {}
    for leg, model in models.items():
        ledger = []
        for ticker, trades in raw_trades.items():
            ledger.extend(build_ledger(trades, weekend[ticker], model))
        all_ledgers[leg] = ledger
        summaries[leg] = summarize(leg, ledger, initial_cash)

    print(f"Fib short {args.period} | брекет={args.sr_variant} | {len(raw_trades)} тикеров | "
          f"капитал {initial_cash:,.0f} ₽")
    print(f"LQDT {args.lqdt_annual_pct:.2f}%/год = {lqdt_daily:.4f}%/день; "
          f"фьючерс: комиссия {args.futures_commission*100:.3f}%/стор., "
          f"ГО {args.futures_margin*100:.0f}%\n")
    print(f"{'нога':<12} {'сделок':>7} {'win%':>6} {'gross':>10} {'перенос':>9} "
          f"{'комис':>8} {'slip':>7} {'LQDT':>8} {'NET':>11} {'ret%':>8}")
    for leg in ("stock", "futures", "fut_no_lqdt"):
        s = summaries[leg]
        print(f"{leg:<12} {s['trades']:>7} {s['win_rate_pct']:>6.1f} {s['gross_pnl']:>10,.0f} "
              f"{s['carry_total']:>9,.0f} {s['commission_total']:>8,.0f} "
              f"{s['slippage_total']:>7,.0f} {s['lqdt_income_total']:>8,.0f} "
              f"{s['net_pnl']:>11,.0f} {s['net_return_pct']:>8.2f}")

    report = {
        "study": "FIB-SHORT-FUT-LQDT-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db": args.db,
        "period": args.period,
        "bracket_variant": args.sr_variant,
        "tickers": list(raw_trades),
        "cash_per_ticker": CASH_PER_TICKER,
        "initial_cash": initial_cash,
        "lqdt_annual_pct": args.lqdt_annual_pct,
        "lqdt_daily_pct": lqdt_daily,
        "models": {name: asdict(model) for name, model in models.items()},
        "summaries": summaries,
        "ledgers": all_ledgers,
        "limitations": [
            "Фьючерсная нога моделируется долей нецинала, не целыми контрактами.",
            "Нет свечей LQDT/фьючерсов в БД: ставка LQDT и комиссия фьючерса — константы.",
            "Нет учета доходности GO-денег до входа в сделку и после выхода.",
            "Акционный шорт учитывает перенос только по неционалу на момент входа.",
        ],
    }
    if args.run_dir:
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        pd.DataFrame(
            [{"leg": leg, **row} for leg in ("stock", "futures", "fut_no_lqdt")
             for row in all_ledgers[leg]]
        ).to_csv(run_dir / "trades.csv.gz", index=False, compression="gzip")
        print(f"\nАртефакты: {run_dir}")


if __name__ == "__main__":
    main()
