#!/usr/bin/env python3
"""Elliott v2: поиск прибыльной модификации стратегии (E1..E5).

Базируется на live-faithful принципах (без lookahead): сигнал известен на
закрытии свечи, продлевающей одноцветную серию до L=3..5; вход — на open
следующей (цвет неизвестен). Строгий HTF-фильтр считается по закрытию
СИГНАЛЬНОЙ свечи (не входной!).

Эксперименты:
  E1  качество x HTF-тренд x тикеры  — складывается ли край.
  E2  ЗЕРКАЛО после «гибели» fade (3 шага в минусе) — 1..5 дней, short/long, эры.
  E3  смена волны входа: волна-2 (продолжение после первого реакционного бара)
      и фибо-вход по extended-импульсу.
  E4  риск-инженерия: 3-й шаг мартингейла вместо «всё-в-100%» -> стоп/разворот.
  E5  честная сетка (q x горизонт x тикеры) с OOS-проверкой по эрам.
  E6  только лонг + докутка при убытке (hold-add) vs «держать до минуса»; 1day и 4h.

Usage (from trading_moex/):
    python3 scripts/backtest_elliott_v2.py --e 1,2,3,4,5,6
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app import elliott_candles as ec  # noqa: E402

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
DEPOSIT = 10_000_000.0
WAR = pd.Timestamp("2022-02-24")
# топ по исторической net (hold-add q>=0.8): SBER, T, NLMK, MOEX, TATN, CHMF, LKOH
TOP6 = ["SBER", "T", "NLMK", "MOEX", "TATN", "MTSS"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_df(ticker: str, db: str, period: str = "1day") -> pd.DataFrame:
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


def prep(t: str, db: str, sma_p: int = 50, period: str = "1day") -> dict:
    """Классификация + вспомогательные массивы (HTF SMA строго по sig-close)."""
    df = ec.classify_candles(load_df(t, db, period), body_ratio_min=0.6, atr_period=14, atr_k=0.5)
    cl = df["close"].values.astype(float)
    sma = pd.Series(cl).rolling(sma_p, min_periods=max(20, sma_p // 2)).mean().values
    up = np.where(np.isnan(sma), True, cl > sma)
    return {
        "df": df, "colors": df["candle_color"].values,
        "o": df["open"].values.astype(float), "c": df["close"].values.astype(float),
        "hi": df["high"].values.astype(float), "lo": df["low"].values.astype(float),
        "up50": up, "up200": np.where(np.isnan(sma), True, cl > sma),
        "n": len(df),
    }


def sigs(prep: dict) -> list[dict]:
    """Все live-faithful сигналы L=3..5 (по достижении L), как в проде."""
    colors, n = prep["colors"], prep["n"]
    out = []
    i = 0
    while i < n:
        c = colors[i]
        if c == "doji":
            i += 1
            continue
        j = i
        while j < n and colors[j] == c:
            j += 1
        run = j - i
        for L in range(3, min(run, 5) + 1):
            sig = i + L - 1
            if sig + 1 >= n:
                break
            wave = ec.Wave(start_idx=i, end_idx=sig, direction=c,
                           candle_count=L, df=prep["df"])
            q = ec.wave_quality_score(wave)["total"]
            out.append({
                "tick": None, "L": L, "sig": sig, "ent": sig + 1,
                "wave_dir": c, "fade": "long" if c == "bear" else "short", "q": q,
            })
        i = j
    return out


def fwd_net(prep: dict, sig: int, dir_: str, h: int, comm: float, slip: float) -> float:
    """Вход open[ent], выход close[ent+h-1]. dir_='long'/'short'. Чистый net."""
    ent = sig + 1
    if ent + h - 1 >= prep["n"]:
        return np.nan
    en = prep["o"][ent]
    ex = prep["c"][ent + h - 1]
    en_adj = en * (1 + slip) if dir_ == "long" else en * (1 - slip)
    ex_adj = ex * (1 - slip) if dir_ == "long" else ex * (1 + slip)
    if dir_ == "long":
        gross = (ex_adj - en_adj) / en_adj
    else:
        gross = (en_adj - ex_adj) / en_adj
    return gross - 2 * comm


def net_mean(a) -> str:
    a = np.asarray(a, dtype=float)
    a = a[~np.isnan(a)]
    if not len(a):
        return "  n=0"
    return (f" n={len(a):>4} win={(a > 0).mean() * 100:5.1f}% "
            f"net_m={a.mean() * 100:+.3f}% med={np.median(a) * 100:+.3f}% net={a.sum() * DEPOSIT * 0.25:+,.0f}")


def entry_net(en: float, ex: float, dir_: str, comm: float, slip: float) -> float:
    """Net-ретурн сделки от open en до close ex с учётом slippage на обеих ногах."""
    en_adj = en * (1 + slip) if dir_ == "long" else en * (1 - slip)
    ex_adj = ex * (1 - slip) if dir_ == "long" else ex * (1 + slip)
    if dir_ == "long":
        gross = (ex_adj - en_adj) / en_adj
    else:
        gross = (en_adj - ex_adj) / en_adj
    return gross - 2 * comm


def era(dt) -> str:
    return "мир" if dt < WAR else "война"


# ---------------------------------------------------------------------------
# E1: качество x HTF-тренд x тикеры
# ---------------------------------------------------------------------------

def run_e1(preps: dict, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("E1. Fade: качество x HTF-SMA50 x тикеры (1 день, строго по sig-close)")
    print("=" * 78)
    combos = [
        ("q>=0.0", 0.0, None, ALL_TICKERS),
        ("q>=0.6", 0.6, None, ALL_TICKERS),
        ("q>=0.8", 0.8, None, ALL_TICKERS),
        ("q>=0.0+тренд", 0.0, "trend", ALL_TICKERS),
        ("q>=0.6+тренд", 0.6, "trend", ALL_TICKERS),
        ("q>=0.8+тренд", 0.8, "trend", ALL_TICKERS),
        ("q>=0.6+тренд+TOP6", 0.6, "trend", TOP6),
        ("q>=0.8+тренд+TOP6", 0.8, "trend", TOP6),
    ]
    print(f"  комиссия={comm * 100:.2f}% слайп={slip * 100:.2f}%/сторона")
    hdr = f"  {'конфиг':<20}{'n':>6} {'win':>6} {'net_mean':>9} {'net(25%)':>12}"
    print(hdr)
    for name, qmin, filt, tickers in combos:
        nets = []
        for t in tickers:
            p = preps[t]
            for s in sigs(p):
                if qmin > 0 and s["q"] < qmin:
                    continue
                if filt == "trend":
                    up = p["up50"][s["sig"]]
                    if s["fade"] == "long" and not up:
                        continue
                    if s["fade"] == "short" and up:
                        continue
                r = fwd_net(p, s["sig"], s["fade"], 1, comm, slip)
                if not np.isnan(r):
                    nets.append(r)
        a = np.asarray(nets)
        if not len(a):
            print(f"  {name:<20} n=0")
            continue
        print(f"  {name:<20}{len(a):>6} {(a > 0).mean() * 100:>5.1f}% "
              f"{a.mean() * 100:>+8.3f}% {a.sum() * DEPOSIT * 0.25:>+12,.0f}")


# ---------------------------------------------------------------------------
# E2: зеркало после «гибели» fade-цикла
# ---------------------------------------------------------------------------

def _cycle_sim(p: dict, s: dict, qmin: float, max_steps: int, comm: float,
               slip: float, size: float) -> tuple[str, list[float], int]:
    """Симулирует мартингейл-цикл. Возвращает (статус, pnl-шагов, последний idx)."""
    if s["q"] < qmin:
        return "skip", [], -1
    fade, ent, n = s["fade"], s["ent"], p["n"]
    pnls = []
    idx = ent
    step = 0
    while step < max_steps and idx < n:
        step += 1
        r = fwd_net(p, idx - 1, fade, 1, comm, slip)  # h=1 -> свеча idx
        if np.isnan(r):
            break
        pnls.append(r)
        idx += 1
        if r >= 0:
            break
    status = "win" if (pnls and pnls[-1] >= 0) else ("death" if len(pnls) >= max_steps else "partial")
    return status, pnls, idx - 1


def run_e2(preps: dict, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("E2. ЗЕРКАЛО (продолжение) после гибели 3-шагового fade, q>=0.6/0.8")
    print("=" * 78)
    for qmin in (0.6, 0.8):
        deaths = []  # (prep, dir_волны, idx_после_гибели, дата)
        for t in ALL_TICKERS:
            p = preps[t]
            for s in sigs(p):
                status, pnls, last = _cycle_sim(p, s, qmin, 3, comm, slip, 0.25)
                if status == "death" and last + 1 < p["n"]:
                    deaths.append((p, s["wave_dir"], last, p["df"].index[last]))
        print(f"\n  q>={qmin}: событий гибели={len(deaths)}")
        # продолжить по волне (mirror) / против (fade) на горизонте h
        for side in ("mirror", "fade"):
            for h in (1, 3, 5):
                nets, nets_long, nets_short = [], [], []
                for p, wdir, last, dt in deaths:
                    dir_ = "long" if (wdir == "bull") == (side == "mirror") else "short"
                    # mirror по волне: bull-волна -> long; fade -> наоборот
                    if side == "mirror":
                        dir_ = "long" if wdir == "bull" else "short"
                    else:
                        dir_ = "long" if wdir == "bear" else "short"
                    if last + h >= p["n"]:
                        continue
                    en = p["o"][last + 1]
                    ex = p["c"][last + h]
                    net = entry_net(en, ex, dir_, comm, slip)
                    nets.append(net)
                    (nets_long if dir_ == "long" else nets_short).append(net)
                for nm, arr in (("long", nets_long), ("short", nets_short)):
                    a = np.asarray(arr)
                    if len(a):
                        print(f"    {side:>6} {nm:<5} h={h}: n={len(a):>4} "
                              f"win={(a > 0).mean() * 100:5.1f}% mean={a.mean() * 100:+.3f}% "
                              f"med={np.median(a) * 100:+.3f}%")
        # по эрам (h=5 mirror short)
        print("    --- по эрам: mirror, h=5 ---")
        for qmin2 in (0.6, 0.8):
            deaths = []
            for t in ALL_TICKERS:
                p = preps[t]
                for s in sigs(p):
                    status, pnls, last = _cycle_sim(p, s, qmin2, 3, comm, slip, 0.25)
                    if status == "death" and last + 1 < p["n"]:
                        deaths.append((p, s["wave_dir"], last, p["df"].index[last]))
            for e in ("мир", "война"):
                nets = []
                for p, wdir, last, dt in deaths:
                    if era(dt) != e:
                        continue
                    dir_ = "long" if wdir == "bull" else "short"
                    if last + 5 >= p["n"]:
                        continue
                    en, ex = p["o"][last + 1], p["c"][last + 5]
                    nets.append(entry_net(en, ex, dir_, comm, slip))
                a = np.asarray(nets)
                if len(a):
                    print(f"      q>={qmin2} {e}: n={len(a):>3} win={(a > 0).mean() * 100:5.1f}% "
                          f"mean={a.mean() * 100:+.3f}%")


# ---------------------------------------------------------------------------
# E3: смена волны входа
# ---------------------------------------------------------------------------

def run_e3(preps: dict, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("E3. Смена волны входа: (A) волна-2 продолжение, (B) фибо-откат extended")
    print("=" * 78)
    # (A) Вход ПО волне после первого реакционного бара.
    # Структура: серия [3..5] цвета c завершена на sig; свеча R=sig+1 — реакция
    # (против c, т.е. в цвете fade). Покупка/продажа В СТОРОНУ волны (продолжение
    # импульса = «волна-2 продолжение») на open R+1, горизонт h.
    print("\n  (A) продолжить волну после реакционного бара (entry open R+1):")
    for h in (1, 2, 3):
        nets = []
        for t in ALL_TICKERS:
            p = preps[t]
            colors = p["colors"]
            for s in sigs(p):
                R = s["sig"] + 1
                if R + 1 >= p["n"]:
                    continue
                Rcol = colors[R]
                if Rcol == "doji" or Rcol == s["wave_dir"]:
                    continue  # только чистый реакционный бар против волны
                dir_ = "long" if s["wave_dir"] == "bull" else "short"
                ent = R + 1
                if ent + h - 1 >= p["n"]:
                    continue
                en, ex = p["o"][ent], p["c"][ent + h - 1]
                nets.append(entry_net(en, ex, dir_, comm, slip))
        a = np.asarray(nets)
        if len(a):
            print(f"    h={h}: n={len(a):>5} win={(a > 0).mean() * 100:5.1f}% "
                  f"mean={a.mean() * 100:+.3f}% med={np.median(a) * 100:+.3f}%")

    # (B) Фибо-вход: extended-импульс, откат в зону 38..62% -> продолжение
    print("\n  (B) extended-импульс + откат в 38..62% фибо -> вход по импульсу:")
    nets = {h: [] for h in (1, 3, 5)}
    n_ev = 0
    for t in ALL_TICKERS:
        p = preps[t]
        for ex in ec.detect_extended_waves(p["df"], wave_min=3, wave_max=5,
                                           macro_min_legs=2, macro_max_candles=13,
                                           corr_max_bars=2, corr_max_retr=1.0,
                                           w4_no_overlap=1):
            sd, ed = ex["start_idx"], ex["end_idx"]
            brk = ex["break_idx"]
            mdir = ex["direction"]
            if brk + 1 >= p["n"]:
                continue
            # размах волны
            if mdir == "bull":
                start_px, end_px = p["o"][sd], max(p["hi"][sd:ed + 1])
            else:
                start_px, end_px = p["o"][sd], min(p["lo"][sd:ed + 1])
            rng = abs(end_px - start_px)
            if rng <= 0:
                continue
            # зона отката 38..62%
            z_hi = start_px + 0.618 * rng if mdir == "bull" else start_px + 0.382 * rng
            z_lo = start_px + 0.382 * rng if mdir == "bull" else start_px + 0.618 * rng
            lo_hi = (max(z_lo, z_hi), min(z_lo, z_hi))
            dipped = False
            confirm = None
            for k in range(brk + 1, min(p["n"], brk + 1 + 12)):
                px = p["lo"][k] if mdir == "bull" else p["hi"][k]
                lo_v, hi_v = lo_hi
                if lo_v <= px <= hi_v:
                    dipped = True
                # подтверждение: свеча в сторону импульса
                col = p["colors"][k]
                if dipped and col == mdir and k + 1 < p["n"]:
                    confirm = k
                    break
            if confirm is None:
                continue
            n_ev += 1
            dir_ = "long" if mdir == "bull" else "short"
            ent = confirm + 1
            for h in nets:
                if ent + h - 1 < p["n"]:
                    en, ex = p["o"][ent], p["c"][ent + h - 1]
                    nets[h].append(entry_net(en, ex, dir_, comm, slip))
    print(f"    входов={n_ev}")
    for h in (1, 3, 5):
        a = np.asarray(nets[h])
        if len(a):
            print(f"    h={h}: n={len(a):>4} win={(a > 0).mean() * 100:5.1f}% "
                  f"mean={a.mean() * 100:+.3f}% med={np.median(a) * 100:+.3f}%")


# ---------------------------------------------------------------------------
# E4: риск-инженерия
# ---------------------------------------------------------------------------

def _mart(p: dict, s: dict, mode: str, comm: float, slip: float) -> list[float]:
    """Мартингейл-цикл. mode: 'classic'(3x), '2stop', '2mirror'."""
    fade, ent, n = s["fade"], s["ent"], p["n"]
    pnls = []
    idx = ent
    size = 1.0
    step = 0
    while step < 3 and idx < n:
        step += 1
        r = fwd_net(p, idx - 1, fade, 1, comm, slip)
        if np.isnan(r):
            break
        pnl = r * size
        pnls.append(pnl)
        idx += 1
        if r >= 0:
            break
        if step == 1 and mode in ("2stop", "2mirror"):
            if mode == "2stop":
                break
            # разворот: зеркальная сделка тем же размером
            mdir = "long" if fade == "short" else "short"
            if idx < n:
                mr = fwd_net(p, idx - 1, mdir, 1, comm, slip)
                if not np.isnan(mr):
                    pnls.append(mr * size)
                idx += 1
            break
        size *= 2.0
    return pnls


def run_e4(preps: dict, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("E4. Риск-инженерия мартингейла 25->50->100 (q>=0.0 и q>=0.8)")
    print("=" * 78)
    for qmin in (0.0, 0.6, 0.8):
        for mode, nm in (("classic", "классика 3 шага"), ("2stop", "2 шага + стоп"),
                         ("2mirror", "1 шаг + разворот")):
            eq = DEPOSIT
            wins = loses = 0
            tot = 0.0
            peak = DEPOSIT
            mdd = 0.0
            for t in ALL_TICKERS:
                p = preps[t]
                for s in sigs(p):
                    if s["q"] < qmin:
                        continue
                    pnls = _mart(p, s, mode, comm, slip)
                    if not pnls:
                        continue
                    cyc = sum(pnls) * (DEPOSIT * 0.25)  # нормировка на 25% базис
                    # реалистично: лоты от текущего эквити; аппроксимируем базой eq
                    cyc = sum(pnls) * (eq * 0.25)
                    eq += cyc
                    peak = max(peak, eq)
                    mdd = max(mdd, (peak - eq) / peak)
                    if cyc > 0:
                        wins += 1
                    else:
                        loses += 1
                    tot += cyc
            n = wins + loses
            if not n:
                continue
            print(f"  q>={qmin} {nm:<16}: n={n:>4} win={wins / n * 100:5.1f}% "
                  f"net={eq - DEPOSIT:>+13,.0f} maxDD={mdd * 100:6.1f}%")


# ---------------------------------------------------------------------------
# E5: сетка q x горизонт x тикеры, OOS по эрам
# ---------------------------------------------------------------------------

def run_e5(preps: dict, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("E5. Сетка: q x горизонт x тикеры; раздельно по эрам (OOS)")
    print("=" * 78)
    rows = []
    for qmin in (0.0, 0.4, 0.6, 0.8):
        for h in (1, 2, 3):
            for subset, name in ((ALL_TICKERS, "все"), (TOP6, "TOP6")):
                for e in ("мир", "война"):
                    nets = []
                    for t in subset:
                        p = preps[t]
                        for s in sigs(p):
                            if s["q"] < qmin:
                                continue
                            r = fwd_net(p, s["sig"], s["fade"], h, comm, slip)
                            if not np.isnan(r) and era(p["df"].index[s["ent"]]) == e:
                                nets.append(r)
                    a = np.asarray(nets)
                    if len(a):
                        rows.append((qmin, h, name, e, len(a), (a > 0).mean() * 100,
                                     a.mean() * 100, a.sum() * DEPOSIT * 0.25))
    hdr = (f"  {'q':<5}{'h':<3}{'тикеры':<6}{'эра':<5}{'n':>5} {'win':>6} "
           f"{'net_mean':>9} {'net(25%)':>12}")
    print(hdr)
    # сортировка: те, где обе эры > 0 по net_mean, сверху
    best = []
    by_qh = {}
    for r in rows:
        by_qh.setdefault((r[0], r[1], r[2]), []).append(r)
    for key, rs in by_qh.items():
        if len(rs) == 2 and all(r[6] > 0.0005 for r in rs):
            best.append((sum(r[7] for r in rs), key, rs))
    for tot, key, rs in sorted(best, reverse=True):
        print(f"  > обе эры положительны: q={key[0]} h={key[1]} {key[2]} суммарн. net={tot:+,.0f}")
    for r in rows:
        qmin, h, name, e, n, w, m, net = r
        print(f"  q={qmin:<4.1f} h={h}  {name:<6}{e:<6}{n:>5} {w:>5.1f}% {m:>+8.3f}% {net:>+12,.0f}")


# ---------------------------------------------------------------------------
# E6: ТОЛЬКО ЛОНГ + ДОКУПКА при убытке (вместо разворота в шорт)
#
# Правило (запрос пользователя, уточнение «только лонг», «докупка лонга вместо
# разворота»): базовая сделка — лонг после медвежьей волны (fade). Если закрытие
# в минусе — НЕ закрываем и НЕ идём в шорт, а ДОБАВЛЯЕМ ещё лот лонга на open
# следующего бара. Если позиция в плюсе — держим. Выход:
#   A. «hold-add» (прод-движок): вся позиция закрывается при суммарном плюсе на
#      закрытии или после max_steps добавок;
#   B. «до минуса»: прибыльную держим, пока флоат не уйдёт в минус/ноль, тогда
#      закрываем (без добавки после выхода в плюс), горизонт ограничен.
# Шортов нигде нет.
# ---------------------------------------------------------------------------

def _long_add_hold_cycle(p: dict, s: dict, H: int, comm: float, slip: float) -> float:
    """Правило B: один лонг, выход при флоате <= 0 или по горизонту H баров."""
    n = p["n"]
    o, c = p["o"], p["c"]
    cur = s["ent"]
    entry_px = o[cur]
    last = cur - 1
    for _ in range(H):
        if cur >= n:
            break
        last = cur
        net = entry_net(entry_px, c[cur], "long", comm, slip)
        if net <= 0:
            return net  # закрылись в минусе/нуле
        cur += 1
    # горизонт исчерпан при положительном флоате — фиксируем профит
    return entry_net(entry_px, c[last], "long", comm, slip)


def _run_long_add(tickers, db, period, qmin, strong_k, mode, comm, slip, H=6):
    """Прогон только-лонг докуток/удержаний. mode='engine'/'holdmin'."""
    res = []
    comm_total = comm + slip
    for t in tickers:
        p = prep(t, db, period=period)
        sig_list = sorted(sigs(p), key=lambda x: x["ent"])
        busy = -1
        for s in sig_list:
            if s["fade"] != "long":
                continue
            if s["ent"] - 1 <= busy:
                continue
            if qmin > 0 and s["q"] < qmin:
                continue
            if strong_k > 0:
                df = p["df"]
                body = df["body_abs"].values.astype(float)
                atr = df["atr"].values.astype(float)
                ws = s["sig"] - s["L"] + 1
                strong = sum(1 for i in range(ws, s["sig"] + 1) if atr[i] > 0 and body[i] >= strong_k * atr[i])
                if strong < 1:
                    continue
            if mode == "holdmin":
                net = _long_add_hold_cycle(p, s, H, comm, slip)
                res.append({"t": t, "dt": p["df"].index[s["ent"]], "net_pct": net,
                            "legs": 1, "busy": s["ent"]})
                busy = s["ent"] + H - 1
            else:  # engine hold_add (выход при суммарном плюсе, до 3 добавок)
                df = load_df(t, db, period)
                bt = ec.run_backtest(df, initial_equity=DEPOSIT, wave_min=3, wave_max=5,
                                     base_pct=0.25, max_steps=3, commission=comm_total,
                                     quality_min=qmin, impulse_strong_k=strong_k,
                                     impulse_strong_min=1, direction=1, hold_add=1)
                # единственный исполняемый цикл — берём все; busy-перекрытие движок учёл
                for cyc in bt["cycles"]:
                    res.append({"t": t, "dt": pd.Timestamp(cyc.wave_end),
                                "net_pct": cyc.total_pnl / (DEPOSIT * 0.25),
                                "legs": len(cyc.trades)})
                break  # движок уже прошёл тикер целиком
    return res


def run_e6(tickers: list, db: str, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("E6. ТОЛЬКО ЛОНГ: минус на закрытии -> ДОКУПКА лота (без шорта); "
          "плюс -> держим")
    print(f"    комиссия {comm*100:.2f}% + слайп {slip*100:.2f}%/сторона")
    print("=" * 78)

    def report(label, res):
        if not res:
            print(f"  {label:<46} нет сделок")
            return
        pnls = np.array([r["net_pct"] for r in res])
        legs = sum(r["legs"] for r in res)
        w = (pnls > 0).sum()
        def split(fn):
            a = [x for x in res if fn(x["dt"])]
            if not a:
                return None
            arr = np.array([x["net_pct"] for x in a])
            return len(arr), (arr > 0).mean() * 100, arr.mean() * 100, arr.sum() * DEPOSIT * 0.25
        era_m = split(lambda d: d < WAR)
        era_w = split(lambda d: d >= WAR)
        fresh = split(lambda d: d >= pd.Timestamp("2024-09-01"))
        s_m = f" | мир n={era_m[0]} m={era_m[2]:+.3f}%" if era_m else ""
        s_w = f" | война n={era_w[0]} m={era_w[2]:+.3f}%" if era_w else ""
        s_f = f" | 24мес n={fresh[0]} m={fresh[2]:+.3f}%" if fresh else ""
        print(f"  {label:<46} n={len(res):>4} win={w/len(res)*100:5.1f}% "
              f"ног={legs:>4} net_m={pnls.mean()*100:+.3f}% net={pnls.sum()*DEPOSIT*0.25:>+12,.0f}"
              f"{s_m}{s_w}{s_f}")

    for period in ("1day", "4h"):
        ticks = [t for t in tickers if not load_df(t, db, period).empty]
        print(f"\n### {period} | тикеры: {','.join(ticks)}")
        for qmin, strong, label in [
            (0.0, 0.0, "q0 все лонг-сигналы"),
            (0.6, 1.0, "q0.6 + сильный импульс"),
            (0.8, 1.0, "q0.8 + сильный импульс"),
        ]:
            # A: прод-движок hold_add (выход при суммарном плюсе)
            resA = _run_long_add(ticks, db, period, qmin, strong, "engine", comm, slip)
            report(f"A. hold-add (выход в плюс) {label}", resA)
            # B: держим прибыль до закрытия с минусом, без добавок
            resB = _run_long_add(ticks, db, period, qmin, strong, "holdmin", comm, slip)
            report(f"B. держать до минуса (без добавки) {label}", resB)


# ---------------------------------------------------------------------------
# FINAL: проверка победителя через прод-движок run_backtest
# ---------------------------------------------------------------------------

def run_final(db: str, comm: float, slip: float) -> None:
    print("\n" + "=" * 78)
    print("FINAL. Проверка q>=0.8 + hold_days=3 (все тикеры) через прод-движок")
    print("=" * 78)
    # у run_backtest нет slippage — считаем по завышенной комиссии (0.09%/сторона)
    comm_total = comm + slip
    agg = {"net": 0.0, "n": 0, "w": 0}
    for t in ALL_TICKERS:
        df = load_df(t, db)
        bt = ec.run_backtest(df, initial_equity=DEPOSIT, wave_min=3, wave_max=5,
                             base_pct=0.25, quality_min=0.8, commission=comm_total,
                             hold_days=3)
        m = bt["metrics"]
        cycles = bt["cycles"]
        pnls = [c.total_pnl for c in cycles]
        net = m.get("total_pnl", 0.0)
        agg["net"] += net
        agg["n"] += len(pnls)
        agg["w"] += sum(1 for p in pnls if p > 0)
        print(f"  {t:<5} циклов={len(pnls):>3} win={(np.array(pnls) > 0).mean() * 100 if pnls else 0:5.1f}% "
              f"net={net:>+12,.0f} maxDD={m.get('max_drawdown_pct', 0):5.1f}%")
    if agg["n"]:
        print(f"  ИТОГО циклов={agg['n']} win={agg['w'] / agg['n'] * 100:.1f}% "
              f"net={agg['net']:+,.0f} (комиссия {comm_total * 100:.2f}%/сторона ≈ 0.04%+слайп)")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Elliott v2 эксперименты E1..E5+FINAL")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--commission", type=float, default=0.0004)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--e", default="1,2,3,4,5,6,final")
    args = parser.parse_args()

    exprs = [x.strip() for x in args.e.split(",") if x.strip()]
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    preps = {t: prep(t, args.db) for t in tickers}

    print(f"Elliott v2 | {len(tickers)} тикеров | 1day | комиссия="
          f"{args.commission * 100:.2f}% слайп={args.slippage * 100:.2f}%/сторона | "
          f"депозит на цикл 25%")

    if "1" in exprs:
        run_e1(preps, args.commission, args.slippage)
    if "2" in exprs:
        run_e2(preps, args.commission, args.slippage)
    if "3" in exprs:
        run_e3(preps, args.commission, args.slippage)
    if "4" in exprs:
        run_e4(preps, args.commission, args.slippage)
    if "5" in exprs:
        run_e5(preps, args.commission, args.slippage)
    if "6" in exprs:
        run_e6(tickers, args.db, args.commission, args.slippage)
    if "final" in exprs:
        run_final(args.db, args.commission, args.slippage)


if __name__ == "__main__":
    main()
