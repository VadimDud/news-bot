#!/usr/bin/env python3
"""Paper-only prospective enrollment, readiness checks and terminal evaluation for 5-minute candles.

This is a separate study for 5-minute bars. It mirrors run_lstm_prospective.py with:
- period changed from 15min to 5min
- horizon changed from 5 to 15 (75-minute forward window)
- distinct study_id LSTM-SBER-5MIN-001
- parameters otherwise identical (train500, seq50, eval2000)

Feature sequence spans 50 bars × 5min = 250 minutes of history. Horizon spans 15 bars × 5min = 75 minutes
of forward price movement. Feature windows are bar-based; outcomes may cross session gaps.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enroll_prospective_lstm import _git, _write_json
from app.lstm_features import FeatureScaler, candle_features, make_sequence_partition

PARAMS = dict(train_bars=500, evaluation_bars=2000, sequence_length=50,
              horizon=15, threshold=0.003, cost_rate=0.001, hidden_size=32,
              num_layers=2, dropout=0.2, learning_rate=0.001, batch_size=32,
              epochs=50, seed=42)
DIVIDEND_SEMANTICS = "smartlab_trusted_cutoff_date_used_as_ex_date"


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def calendar(db):
    rows = db.execute("SELECT cutoff_date, source FROM dividends WHERE ticker='SBER' ORDER BY cutoff_date").fetchall()
    if not rows:
        raise ValueError("empty dividend calendar")
    for cutoff, source in rows:
        if source != "smartlab" or datetime.strptime(cutoff, "%Y-%m-%d").strftime("%Y-%m-%d") != cutoff:
            raise ValueError("invalid Smartlab calendar")
    return [dict(cutoff_date=d, source=s) for d, s in rows]


def validate(frame):
    if frame.empty:
        raise ValueError("empty candles")
    stamps = [datetime.fromisoformat(v) for v in frame.pop("timestamp")]
    if any(v.tzinfo is not None for v in stamps):
        raise ValueError("expected UTC-naive candles")
    frame.index = pd.DatetimeIndex(stamps, name="timestamp")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("unordered or duplicate timestamps")
    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite OHLCV")
    if ((frame.low <= 0) | (frame.volume < 0) | (frame.open < frame.low)
            | (frame.close < frame.low) | (frame.open > frame.high)
            | (frame.close > frame.high)).any():
        raise ValueError("invalid OHLCV bounds")
    return frame


def snapshot(output, name, frame):
    payload = frame.to_csv(date_format="%Y-%m-%dT%H:%M:%S.%f").encode()
    with (output / name).open("xb") as stream:
        stream.write(payload)
    return digest(payload)


def prepare(history, forward, events):
    """Fit on 500 frozen rows; earlier rows provide causal warmup only.

    Horizon for 5min bars is 15 (75-minute forward window). Feature sequence spans
    50 bars = 250 minutes of history, bar-based (not time-aligned). Horizon can cross
    session gaps.
    """
    if len(history) < 500 or len(forward) != 2000:
        raise ValueError("incorrect partition sizes")
    combined = pd.concat([history, forward])
    if combined.index.has_duplicates or not combined.index.is_monotonic_increasing:
        raise ValueError("overlapping partitions")
    end = len(history)
    scaler = FeatureScaler.fit(candle_features(history).iloc[-500:])
    parts, excluded, boundary_excluded = [], {}, {}
    for name, start, stop in (("train", end - 500, end), ("forward", end, end + 2000)):
        kwargs = dict(feature_start=0, decision_start=start, decision_end=stop,
                      sequence_length=50, horizon=15, threshold=0.003,
                      cost_rate=0.001, scaler=scaler)
        raw = make_sequence_partition(combined, **kwargs)
        masked = make_sequence_partition(combined, excluded_outcome_dates=events, **kwargs)
        excluded[name] = len(raw.y) - len(masked.y)
        boundary_excluded[name] = min(PARAMS["horizon"], stop - start)
        if len(np.unique(masked.y)) != 2:
            raise ValueError(f"single-class {name} partition")
        parts.append(masked)
    return parts[0], parts[1], excluded, boundary_excluded


def evaluate(train, forward):
    from app.lstm_neural import LSTMConfig, train_lstm_classifier, predict_lstm_probabilities
    from app.lstm_baseline import (fit_logistic_baseline, predict_logistic,
                                   majority_probabilities, classification_metrics)
    config = LSTMConfig(input_size=train.X.shape[2], **{
        k: PARAMS[k] for k in ("hidden_size", "num_layers", "dropout", "learning_rate", "batch_size", "epochs", "seed")})
    # Fixed epochs, no model selection. API validation uses training data only.
    model, _ = train_lstm_classifier(train.X, train.y, train.X, train.y, config)
    weights, bias = fit_logistic_baseline(train.X, train.y)
    predictions = {
        "lstm": predict_lstm_probabilities(model, forward.X),
        "logistic": predict_logistic(forward.X, weights, bias),
        "prevalence": majority_probabilities(train.y, len(forward.y)),
    }
    metrics = {}
    for name, probabilities in predictions.items():
        metrics[name] = asdict(classification_metrics(forward.y, probabilities))
        metrics[name]["confusion_matrix"] = [
            [int(((forward.y == truth) & ((probabilities >= .5) == pred)).sum())
             for pred in (0, 1)] for truth in (0, 1)]
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("enroll", "check", "evaluate"))
    parser.add_argument("--db", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--enrollment")
    parser.add_argument("--prior-inspected-watermark", help="Required audited UTC timestamp for enrollment")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    output = Path(args.artifacts_dir) / f"{now:%Y%m%dT%H%M%S%fZ}_LSTM-PROSPECTIVE-5MIN_{args.action}"
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(study_id="LSTM-SBER-5MIN-001", action=args.action,
                    started_at_utc=now.isoformat(), parameters=PARAMS,
                    command=[sys.executable, *sys.argv], git_commit=_git("rev-parse", "HEAD"),
                    git_status=_git("status", "--porcelain"), database_identifier=str(Path(args.db).resolve()),
                    storage_timezone="UTC-naive", market_timezone="Europe/Moscow",
                    dividend_date_semantics=DIVIDEND_SEMANTICS)
    try:
        manifest["dependency_versions"] = {
            name: importlib.metadata.version(name) for name in ("numpy", "pandas", "torch")}
        manifest["dependency_versions"]["python"] = sys.version
        if manifest["git_status"] != "" or manifest["git_commit"] == "unknown":
            raise ValueError("clean committed worktree required")
        enrollment = None
        if args.action != "enroll":
            if not args.enrollment:
                raise ValueError("--enrollment required")
            directory = Path(args.enrollment)
            enrollment = json.loads((directory / "manifest.json").read_text())
            if (enrollment["status"] != "enrolled" or enrollment["parameters"] != PARAMS
                    or enrollment.get("dividend_date_semantics") != DIVIDEND_SEMANTICS
                    or enrollment["git_commit"] != manifest["git_commit"]
                    or enrollment["database_identifier"] != manifest["database_identifier"]
                    or enrollment["dependency_versions"] != manifest["dependency_versions"]):
                raise ValueError("enrollment contract or environment changed")
            history_bytes = (directory / "history.csv").read_bytes()
            if digest(history_bytes) != enrollment["history_sha256"]:
                raise ValueError("history hash mismatch")
            history = validate(pd.read_csv(directory / "history.csv"))
            manifest["enrollment_manifest_sha256"] = digest((directory / "manifest.json").read_bytes())
            if digest(json.dumps(enrollment["dividend_calendar"], sort_keys=True,
                                 separators=(",", ":")).encode()) != enrollment["dividend_calendar_sha256"]:
                raise ValueError("enrollment calendar hash mismatch")
            boundary = max(pd.Timestamp(enrollment["freeze_time_utc"]), pd.Timestamp(enrollment["inspected_data_watermark_utc"]))
        with closing(sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("BEGIN")
            events = calendar(db)
            manifest["calendar_read_time_utc"] = datetime.now(timezone.utc).isoformat()
            if enrollment is None:
                frame = pd.read_sql_query("SELECT begin AS timestamp, open, high, low, close, volume FROM candles WHERE ticker='SBER' AND period='5min' ORDER BY begin", db)
            else:
                # SQLite maps invalid dates to NULL, silently removing them from
                # the boundary query. Reject them before selecting a fixed window.
                invalid = db.execute(
                    "SELECT 1 FROM candles WHERE ticker='SBER' AND period='5min' "
                    "AND julianday(begin) IS NULL LIMIT 1"
                ).fetchone()
                if invalid:
                    raise ValueError("invalid candle timestamp in source database")
                # julianday handles both ISO T and space-separated stored timestamps.
                frame = pd.read_sql_query("SELECT begin AS timestamp, open, high, low, close, volume FROM candles WHERE ticker='SBER' AND period='5min' AND julianday(begin)>julianday(?) ORDER BY julianday(begin) LIMIT 2000", db, params=(boundary.isoformat(),))
        manifest["dividend_calendar"] = events
        manifest["dividend_calendar_sha256"] = digest(json.dumps(events, sort_keys=True, separators=(",", ":")).encode())
        if enrollment is None:
            prior = pd.Timestamp(args.prior_inspected_watermark)
            if pd.isna(prior) or prior.tzinfo is None:
                raise ValueError("audited prior inspected watermark with timezone required")
            history = validate(frame)
            watermark = max(prior.tz_convert("UTC"), history.index[-1].tz_localize("UTC"))
            history = history[history.index + pd.Timedelta(minutes=5) <= pd.Timestamp(now).tz_localize(None)]
            if len(history) < 500:
                raise ValueError("at least 500 completed historical candles required")
            manifest.update(history_sha256=snapshot(output, "history.csv", history),
                            inspected_data_watermark_utc=watermark.isoformat(),
                            prior_inspected_watermark_utc=prior.isoformat(),
                            freeze_time_utc=datetime.now(timezone.utc).isoformat(),
                            train_start_utc=history.index[-500].isoformat(),
                            train_end_utc=history.index[-1].isoformat(), status="enrolled")
        else:
            if manifest["dividend_calendar_sha256"] != enrollment["dividend_calendar_sha256"]:
                raise ValueError("calendar changed since enrollment")
            forward = validate(frame) if not frame.empty else frame
            if not forward.empty:
                forward = forward[forward.index + pd.Timedelta(minutes=5) <= pd.Timestamp(now).tz_localize(None)]
            manifest["completed_forward_bars"] = len(forward)
            manifest["status"] = "waiting" if len(forward) < 2000 else "ready"
            if args.action == "evaluate" and len(forward) == 2000:
                # Permanent exclusive claim also prevents retries after a failed evaluation.
                with (directory / "evaluation.claim").open("x") as stream:
                    stream.write(str(output.resolve()))
                manifest["forward_sha256"] = snapshot(output, "forward.csv", forward)
                manifest["evaluation_start_utc"] = forward.index[0].tz_localize("UTC").isoformat()
                manifest["evaluation_end_utc"] = forward.index[-1].tz_localize("UTC").isoformat()
                train, test, excluded, boundary_excluded = prepare(
                    history, forward, [e["cutoff_date"] for e in events])
                manifest["dividend_samples_excluded"] = excluded
                manifest["outcome_boundary_excluded"] = boundary_excluded
                metrics = evaluate(train, test)
                json.dumps(metrics, allow_nan=False)
                _write_json(output / "metrics.json", metrics)
                manifest["status"] = "completed"
        manifest["exit_status"] = 0
    except Exception as exc:
        manifest.update(status="inconclusive" if isinstance(exc, ValueError) else "failed",
                        failure_reason=str(exc), exit_status=1)
    _write_json(output / "checks.json", {"status": manifest["status"], "read_only_database": True})
    _write_json(output / "manifest.json", manifest)
    return manifest["exit_status"]


if __name__ == "__main__":
    raise SystemExit(main())
