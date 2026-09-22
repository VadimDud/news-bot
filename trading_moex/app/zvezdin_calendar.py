"""Deterministic trading-session calendar used by the Zvezdin backtester."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class SessionCalendar:
    """UTC calendar with explicit full holidays and early-close dates."""

    holidays: frozenset[str] = frozenset()
    early_closes: Mapping[str, int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "holidays", frozenset(str(day) for day in self.holidays))
        object.__setattr__(self, "early_closes", dict(self.early_closes or {}))
        for day, close_minute in self.early_closes.items():
            if not isinstance(day, str) or not 0 <= int(close_minute) < 24 * 60:
                raise ValueError("early close entries must contain valid UTC minutes")

    def is_holiday(self, day: str) -> bool:
        return day in self.holidays

    def close_minute(self, day: str, regular_close_minute: int) -> int | None:
        if self.is_holiday(day):
            return None
        return int(self.early_closes.get(day, regular_close_minute))

    def is_valid_bar(self, day: str, minute_of_day: int, session_start: int, regular_close: int) -> bool:
        close = self.close_minute(day, regular_close)
        return close is not None and session_start <= minute_of_day <= close

    def is_valid_rvol_day(self, day: str) -> bool:
        return not self.is_holiday(day) and day not in self.early_closes


def load_calendar(path: str | Path | None) -> SessionCalendar:
    if path is None:
        return SessionCalendar()
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("calendar must be a JSON object")
    holidays = document.get("holidays", [])
    early_closes = document.get("early_closes", {})
    if not isinstance(holidays, list) or not isinstance(early_closes, dict):
        raise ValueError("calendar holidays must be an array and early_closes an object")
    return SessionCalendar(frozenset(holidays), early_closes)
