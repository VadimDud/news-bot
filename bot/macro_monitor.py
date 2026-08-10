"""Macro monitor — CBR data trends and ОФЗ-ИН (inflation-linked bonds) risk alert.

Watches two CBR data points once a day:
  * USD/RUB official rate (daily XML) — "девальвация"
  * Inflation, % г/г, and the key rate (weekly page "Инфляция и ключевая ставка")

When BOTH the ruble strengthens (devaluation falls) and inflation falls, the
inflation-linked OFZ (SU52002RMFS2 / SU52003RMFS8, т.е. 52002 и 52003) lose
their appeal: their face value and coupons are indexed to inflation. The bot
then sends a Telegram alert so the holder can review the position.
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import httpx

from . import config
from .database import (
    save_macro_indicator,
    get_macro_history,
    get_macro_state,
    set_macro_state,
)
from .retry_utils import async_retry

logger = logging.getLogger(__name__)

CBR_FX_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
CBR_INFL_URL = "https://cbr.ru/hd_base/infl/"

# ОФЗ-ИН (линкеры) в портфеле
LINKER_TICKERS = ["SU52002RMFS2", "SU52003RMFS8"]
LINKER_LABELS = {
    "SU52002RMFS2": "ОФЗ-ИН 52002",
    "SU52003RMFS8": "ОФЗ-ИН 52003",
}

_STATE_ACTIVE = "linker_alert_active"


def _to_float(value: str | None) -> float | None:
    """Parse a Russian-style decimal string ('14,25') into a float."""
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def parse_usd_rub(xml_bytes: bytes) -> float | None:
    """Extract the USD/RUB official rate from the CBR daily XML response."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    for valute in root.findall("Valute"):
        if valute.findtext("CharCode") == "USD":
            return _to_float(valute.findtext("Value"))
    return None


def parse_inflation_page(html_text: str) -> dict:
    """Parse the CBR "Инфляция и ключевая ставка" page.

    Table rows look like: <td>06.2026</td><td>14,25</td><td>6,02</td><td>4,00</td>
    (period, key rate, inflation % г/г, inflation target). The first row is the
    latest month. Returns {} on failure.
    """
    rows = re.findall(
        r"<td>(\d{2}\.\d{4})</td>\s*<td>([\d,.]+)</td>\s*<td>([\d,.]+)</td>\s*<td>([\d,.]+)</td>",
        html_text,
    )
    if not rows:
        return {}
    month, key_rate, inflation_yy, target = rows[0]
    return {
        "month": month,
        "key_rate": _to_float(key_rate),
        "inflation_yy": _to_float(inflation_yy),
        "target": _to_float(target),
    }


@async_retry(max_retries=2, base_delay=2.0)
async def fetch_usd_rub_rate() -> float | None:
    """Fetch the official USD/RUB rate from the CBR daily XML API."""
    async with httpx.AsyncClient(
        timeout=15, follow_redirects=True, proxy=config.HTTP_PROXY or None
    ) as client:
        resp = await client.get(CBR_FX_URL)
        if resp.status_code != 200:
            return None
        return parse_usd_rub(resp.content)


@async_retry(max_retries=2, base_delay=2.0)
async def fetch_macro_snapshot() -> dict:
    """Fetch the current USD/RUB rate, inflation (% г/г) and key rate from CBR.

    Returns a dict with keys: usd_rub, inflation_yy, key_rate, month.
    Any value may be None if that source was unavailable.
    """
    async with httpx.AsyncClient(
        timeout=15, follow_redirects=True, proxy=config.HTTP_PROXY or None
    ) as client:
        fx_resp = await client.get(CBR_FX_URL)
        usd_rub = parse_usd_rub(fx_resp.content) if fx_resp.status_code == 200 else None

        infl_resp = await client.get(CBR_INFL_URL)
        infl = parse_inflation_page(infl_resp.text) if infl_resp.status_code == 200 else {}

    return {
        "usd_rub": usd_rub,
        "inflation_yy": infl.get("inflation_yy"),
        "key_rate": infl.get("key_rate"),
        "month": infl.get("month", ""),
    }


def evaluate_linker_risk(history: list[dict],
                         window_days: int | None = None,
                         fx_threshold_pct: float | None = None,
                         inflation_drop_pp: float | None = None) -> dict:
    """Decide whether devaluation and inflation are BOTH falling.

    Args:
        history: macro snapshots ordered oldest -> newest, each with
                 observed_on (YYYY-MM-DD), usd_rub, inflation_yy.
        window_days: minimum history span required before the check fires.
        fx_threshold_pct: ruble strengthening threshold, % vs window start.
        inflation_drop_pp: inflation (г/г) drop threshold, percentage points.

    Returns a dict with:
        risk, fx_strengthening, inflation_falling, enough_history,
        fx_change_pct, inflation_change_pp, current, baseline.
    """
    window_days = window_days if window_days is not None else config.MACRO_WINDOW_DAYS
    fx_threshold_pct = fx_threshold_pct if fx_threshold_pct is not None else config.FX_STRENGTH_THRESHOLD_PCT
    inflation_drop_pp = inflation_drop_pp if inflation_drop_pp is not None else config.INFLATION_DROP_PP

    out = {
        "risk": False,
        "fx_strengthening": False,
        "inflation_falling": False,
        "enough_history": False,
        "fx_change_pct": None,
        "inflation_change_pp": None,
        "current": None,
        "baseline": None,
    }
    if len(history) < 2:
        return out

    current = history[-1]
    baseline = history[0]
    out["current"] = current
    out["baseline"] = baseline

    try:
        span = (date.fromisoformat(current["observed_on"]) - date.fromisoformat(baseline["observed_on"])).days
    except (KeyError, TypeError, ValueError):
        span = 0
    out["enough_history"] = span >= window_days
    if not out["enough_history"]:
        return out

    cur_fx = current.get("usd_rub")
    base_fx = baseline.get("usd_rub")
    cur_inf = current.get("inflation_yy")
    base_inf = baseline.get("inflation_yy")

    if cur_fx is not None and base_fx:
        change_pct = (cur_fx - base_fx) / base_fx * 100
        out["fx_change_pct"] = round(change_pct, 2)
        out["fx_strengthening"] = change_pct <= -fx_threshold_pct
    if cur_inf is not None and base_inf is not None:
        out["inflation_change_pp"] = round(cur_inf - base_inf, 2)
        out["inflation_falling"] = (base_inf - cur_inf) >= inflation_drop_pp

    out["risk"] = out["fx_strengthening"] and out["inflation_falling"]
    return out


def format_linker_alert(risk: dict) -> str:
    """Build the Telegram message for a detected linker risk."""
    current = risk["current"]
    baseline = risk["baseline"]
    fx_change = abs(risk.get("fx_change_pct") or 0.0)
    inf_change = abs(risk.get("inflation_change_pp") or 0.0)

    cur_fx = current.get("usd_rub")
    base_fx = baseline.get("usd_rub")
    cur_inf = current.get("inflation_yy")
    base_inf = baseline.get("inflation_yy")
    cur_rate = current.get("key_rate")

    fx_line = f"Курс USD/RUB: <b>{cur_fx:.2f}</b> (был {base_fx:.2f})" if cur_fx is not None and base_fx is not None else "Курс USD/RUB: —"
    infl_line = f"Инфляция (г/г): <b>{cur_inf:.2f}%</b> (была {base_inf:.2f}%)" if cur_inf is not None and base_inf is not None else "Инфляция (г/г): —"
    rate_line = f"Ключевая ставка ЦБ: {cur_rate:.2f}%" if cur_rate is not None else "Ключевая ставка ЦБ: —"

    tickers = ", ".join(LINKER_LABELS.values())
    return (
        "⚠️ <b>Внимание: риск падения ОФЗ-ИН (линкеров)</b>\n"
        "\n"
        f"В портфеле: {tickers}\n"
        "\n"
        "В России одновременно складывается ситуация, при которой линкеры "
        "могут потерять привлекательность:\n"
        f"• Рубль укрепился к доллару примерно на <b>{fx_change:.1f}%</b> "
        "(девальвация снижается)\n"
        f"• Годовая инфляция снизилась примерно на <b>{inf_change:.1f} п.п.</b>\n"
        "\n"
        "Номинал и купон ОФЗ-ИН индексируются на инфляцию, поэтому при её "
        "замедлении и укреплении рубля цена линкеров может пойти вниз.\n"
        "\n"
        f"{fx_line}\n"
        f"{infl_line}\n"
        f"{rate_line}\n"
        "\n"
        "Стоит пересмотреть долю линкеров в портфеле.\n"
        "⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    )


async def build_linker_alert() -> str | None:
    """Run the daily macro check and return a formatted alert if it just fired.

    Fetches fresh CBR data, stores the daily snapshot, evaluates the trend and
    returns a message ONLY on the inactive -> active transition, so the user is
    not spammed every day while the conditions persist.
    """
    snapshot = await fetch_macro_snapshot()
    if snapshot.get("usd_rub") is None and snapshot.get("inflation_yy") is None:
        logger.warning("Macro check: no data from CBR, skipping")
        return None

    observed_on = date.today().isoformat()
    await save_macro_indicator(
        observed_on,
        snapshot.get("usd_rub"),
        snapshot.get("inflation_yy"),
        snapshot.get("key_rate"),
    )

    history = await get_macro_history()
    risk = evaluate_linker_risk(history)
    was_active = await get_macro_state(_STATE_ACTIVE) == "1"

    if not risk["risk"]:
        if was_active:
            await set_macro_state(_STATE_ACTIVE, "0")
            logger.info("Macro check: conditions cleared, linker alert reset")
        else:
            logger.info(
                "Macro check: no linker risk (fx change %s%%, inflation change %s п.п., "
                "enough_history=%s)",
                risk.get("fx_change_pct"), risk.get("inflation_change_pp"),
                risk.get("enough_history"),
            )
        return None

    if was_active:
        logger.info("Macro check: linker risk still active, no repeat alert")
        return None

    await set_macro_state(_STATE_ACTIVE, "1")
    logger.info(
        "Macro check: linker risk detected (fx %s%%, inflation %s п.п.) — sending alert",
        risk.get("fx_change_pct"), risk.get("inflation_change_pp"),
    )
    return format_linker_alert(risk)
