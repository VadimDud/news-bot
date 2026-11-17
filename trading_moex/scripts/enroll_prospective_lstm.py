#!/usr/bin/env python3
"""Record a diagnostic pre-enrollment snapshot, without training or enrollment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.timezones import MARKET_TZ_NAME


def _write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--ticker", default="SBER")
    parser.add_argument("--period", default="15min")
    parser.add_argument("--evaluation-bars", type=int, default=2000)
    parser.add_argument("--artifacts-dir", required=True)
    args = parser.parse_args()
    if args.evaluation_bars != 2000:
        parser.error("evaluation-bars is fixed at 2000 by the prospective protocol")
    if args.ticker.upper() != "SBER" or args.period != "15min":
        parser.error("this protocol is fixed to ticker SBER and period 15min")

    started = datetime.now(timezone.utc)
    commit = _git("rev-parse", "HEAD")
    run_id = f"{started:%Y%m%dT%H%M%S%fZ}_LSTM-SNAPSHOT_{commit[:12]}_SBER"
    output = Path(args.artifacts_dir) / run_id
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id, "study_id": "LSTM-BASELINE-001",
        "evaluation_mode": "pre-enrollment-snapshot", "run_class": "diagnostic",
        "enrollment_authorized": False, "freeze_time_utc": None,
        "snapshot_time_utc": started.isoformat(),
        "ticker": "SBER", "period": "15min", "evaluation_bars": 2000,
        "command": [sys.executable, *sys.argv],
        "database_identifier": str(Path(args.db).resolve()),
        "dependency_versions": {"python": sys.version, "pandas": pd.__version__,
                                "sqlite": sqlite3.sqlite_version},
        "git_commit": commit, "git_status": _git("status", "--porcelain"),
        "storage_timezone": "UTC-naive", "market_timezone": MARKET_TZ_NAME,
        "no_training_or_interim_metrics": True,
        "watermark_scope": "selected database candles only; prior artifacts not audited",
        "evaluation_end_rule": "2000th completed candle strictly after enrollment freeze and inspected watermark",
        "evaluation_end_utc": None,
    }
    checks = {"read_only_database": True, "no_metrics_emitted": True}
    try:
        with closing(sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True)) as db:
            # Both reads must observe the same SQLite snapshot, including WAL data.
            db.execute("BEGIN")
            candles = pd.read_sql_query(
                "SELECT begin AS timestamp, open, high, low, close, volume FROM candles "
                "WHERE ticker = ? AND period = ? ORDER BY begin",
                db, params=("SBER", "15min"),
            )
            rows = db.execute(
                "SELECT cutoff_date, source FROM dividends WHERE ticker = ? ORDER BY cutoff_date",
                ("SBER",),
            ).fetchall()
            manifest["calendar_read_time_utc"] = datetime.now(timezone.utc).isoformat()
        if candles.empty:
            raise ValueError("no candles available for inspected watermark")
        timestamps = []
        for value in candles.pop("timestamp"):
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is not None:
                raise ValueError("candle timestamp must be UTC-naive")
            timestamps.append(stamp)
        if any(a >= b for a, b in zip(timestamps, timestamps[1:])):
            raise ValueError("candle timestamps must be strictly ordered and unique")
        if timestamps[-1].replace(tzinfo=timezone.utc) + timedelta(minutes=15) > started:
            raise ValueError("latest candle is still forming or in the future")
        if not all(isinstance(v, (int, float)) and math.isfinite(v)
                   for row in candles.itertuples(index=False, name=None) for v in row):
            raise ValueError("OHLCV contains non-finite or non-numeric values")
        for opening, high, low, close, volume in candles.itertuples(index=False, name=None):
            if low <= 0 or not low <= opening <= high or not low <= close <= high or volume < 0:
                raise ValueError("invalid OHLCV price bounds or volume")
        if not rows:
            raise ValueError("Smartlab dividend calendar is empty")
        calendar = []
        for cutoff, source in rows:
            if source != "smartlab":
                raise ValueError("untrusted dividend source")
            if date.fromisoformat(cutoff).isoformat() != cutoff:
                raise ValueError("invalid dividend cutoff date")
            calendar.append({"cutoff_date": cutoff, "source": source})
        candles.index = pd.DatetimeIndex(timestamps, name="timestamp")
        payload = candles.to_csv(date_format="%Y-%m-%dT%H:%M:%S.%f").encode("utf-8")
        with (output / "ohlcv.csv").open("xb") as stream:
            stream.write(payload)
        manifest.update({
            "status": "snapshot_recorded", "exit_status": 0,
            "inspected_data_watermark_utc": timestamps[-1].replace(tzinfo=timezone.utc).isoformat(),
            "completed_candle_only": True,
            "inspected_ohlcv_rows": len(candles), "ohlcv_snapshot": "ohlcv.csv",
            "inspected_ohlcv_sha256": hashlib.sha256(payload).hexdigest(),
            "dividend_date_semantics": "smartlab_trusted_cutoff_date_used_as_ex_date",
            "dividend_calendar": calendar,
            "dividend_calendar_sha256": hashlib.sha256(json.dumps(
                calendar, sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest(),
        })
        checks["snapshot_valid"] = True
    except Exception as exc:
        manifest.update(status="failed", exit_status=1, failure_reason=str(exc))
        checks["snapshot_valid"] = False
    manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(output / "checks.json", checks)
    _write_json(output / "manifest.json", manifest)
    return manifest["exit_status"]


if __name__ == "__main__":
    raise SystemExit(main())
