#!/usr/bin/env python3
"""Прогон ВСЕХ зарегистрированных стратегий на TGLD (золото) на таймфреймах >=1h.

Usage (from repo root):
    PYTHONPATH=trading_moex no_proxy="moex.com,iss.moex.com" \
        python3 trading_moex/scripts/backtest_tgld_all.py [--days 120] [--periods 60min,2h,4h]

Стратегии без backtrader-класса (cls=None, напр. elliott_candles) пропускаются:
у них нет прямого backtest-раннера в этом реестре.
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import data, storage
from app.backtest import run_backtest
from app.strategies import STRATEGIES, strategy_defaults

TICKER = "TGLD"
DEFAULT_PERIODS = ["60min", "2h", "4h"]
DEFAULT_DAYS = 120
DEFAULT_CASH = 100_000.0


def load_df(ticker: str, period: str, start: date, end: date, cache_first: bool = False):
    """Данные для бэктеста.

    ``cache_first``: moexalgo.candles() отдаёт только ~90 дней истории, поэтому
    для длинных окон сначала берём локальный кэш (там может быть полная история,
    залитая через ISS), и лишь при его отсутствии идём в сеть.
    """
    def _from_cache():
        try:
            raw = storage.get_candles(ticker, period, start=start, end=end)
            if raw.empty:
                return None
            df = raw.copy()
            df["begin"] = pd.to_datetime(df["begin"])
            df = df.set_index("begin").sort_index()
            df.index.name = "datetime"
            return df[["open", "high", "low", "close", "volume"]].drop_duplicates()
        except Exception:  # noqa: BLE001
            return None

    if cache_first:
        cached = _from_cache()
        if cached is not None and len(cached) >= 60:
            return cached
    try:
        return data.fetch_history(ticker, period, start, end)
    except Exception as e:  # noqa: BLE001
        print(f"  WARN {ticker} {period}: MOEX недоступен ({e}), пробую кэш...")
        return _from_cache()


def main():
    parser = argparse.ArgumentParser(description="Все стратегии на TGLD, TF >= 1h")
    parser.add_argument("--ticker", default=TICKER)
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH)
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--refresh", action="store_true",
                        help="тянуть из сети (moexalgo отдаёт лишь ~90 дней); по умолчанию кэш-first")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    periods = [p.strip() for p in args.periods.split(",") if p.strip()]
    start = date.today() - timedelta(days=args.days)
    end = date.today()

    strategy_keys = [k for k, v in STRATEGIES.items() if v.get("cls") is not None]
    skipped = [k for k, v in STRATEGIES.items() if v.get("cls") is None]

    print(f"\n{'='*100}")
    print(f"  {ticker}: {len(strategy_keys)} стратегий x {len(periods)} таймфреймов "
          f"({start}..{end}, days={args.days}, cash={args.cash:.0f})")
    if skipped:
        print(f"  Пропущены (нет backtest-класса): {', '.join(skipped)}")
    print(f"{'='*100}\n")

    rows = []
    for period in periods:
        df = load_df(ticker, period, start, end, cache_first=not args.refresh)
        if df is None or len(df) < 60:
            print(f"  {ticker} {period}: данных мало ({0 if df is None else len(df)}), пропуск\n")
            continue
        bh = (float(df["close"].iloc[-1]) / float(df["close"].iloc[0]) - 1) * 100
        print(f"=== {ticker} {period}: {len(df)} бар, {df.index.min()} .. {df.index.max()} | buy&hold {bh:+.2f}% ===")

        for key in strategy_keys:
            params = strategy_defaults(key, ticker)
            try:
                m = run_backtest(df, STRATEGIES[key]["cls"], params,
                                 cash=args.cash, commission=args.commission)
            except Exception as e:  # noqa: BLE001
                print(f"  {key:16s}: ОШИБКА {type(e).__name__}: {str(e)[:90]}")
                rows.append({"period": period, "strategy": key, "error": type(e).__name__})
                continue
            pf = m.get("profit_factor")
            pf_s = "—" if pf is None else f"{pf:.2f}"
            rows.append({
                "period": period, "strategy": key,
                "ret": m["total_return_pct"], "trades": m["trades_total"],
                "win": m["win_rate_pct"], "pf": pf_s,
                "dd": m["max_drawdown_pct"], "sharpe": m.get("sharpe"),
            })
            print(f"  {key:16s}: ret={m['total_return_pct']:+7.2f}%  "
                  f"trades={m['trades_total']:>3d}  win={m['win_rate_pct']:5.1f}%  "
                  f"pf={pf_s:>5s}  dd={m['max_drawdown_pct']:5.2f}%  sharpe={m.get('sharpe')}")
        print()

    if rows:
        print(f"\n{'='*100}")
        print(f"  ИТОГО: {len(rows)} прогонов")
        print(f"{'='*100}")
        ok = [r for r in rows if "ret" in r]
        if ok:
            ok.sort(key=lambda r: r["ret"], reverse=True)
            print(f"\n  ТОП-10 по доходности:")
            for r in ok[:10]:
                print(f"    {r['period']:>6s} {r['strategy']:16s} ret={r['ret']:+7.2f}%  "
                      f"trades={r['trades']:>3d}  win={r['win']:5.1f}%  pf={r['pf']}")
            print(f"\n  ХУДШИЕ-5:")
            for r in ok[-5:]:
                print(f"    {r['period']:>6s} {r['strategy']:16s} ret={r['ret']:+7.2f}%  trades={r['trades']}")
            profitable = [r for r in ok if r["ret"] > 0 and r["trades"] > 0]
            print(f"\n  Прибыльных прогонов (ret>0, trades>0): {len(profitable)}/{len(ok)}")


if __name__ == "__main__":
    main()
