"""Append sandbox candles and run the frozen prospective check/evaluation once.

Key requirements:
- Explicit INSERT columns to prevent schema drift
- Close all DB connections properly
- Validate sorted normalized 15min timestamps
- Recheck STOP/claim under lock
- Preserve batch provenance SHA and source hashes
- Transient download errors retry later; validation errors STOP
- Separate frozen artifacts (git validation) from live DB paths
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]

# Frozen artifacts for git validation and evaluation
FROZEN_ROOT = ROOT / "artifacts/lstm_frozen/trading_moex/trading_moex"
DB = ROOT / "artifacts/runs/sber_research_20261117T091017677811Z/research.db"
ENROLL = ROOT / "artifacts/runs/lstm_prospective/20261117T091059077116Z_LSTM-PROSPECTIVE_enroll"

# Runtime state (not tracked by git)
RUNTIME = ROOT / "artifacts/runs/lstm_automation"
PYTHON = "/tmp/opencode/lstm-venv/bin/python"
SOURCE_DB = Path("/home/vadman1/Trader_Bot/backend/trading_moex/data/trader.db")


def main() -> int:
    """Main entry point with file lock and STOP check."""
    RUNTIME.mkdir(parents=True, exist_ok=True)
    lock_file = RUNTIME / "worker.lock"
    
    with lock_file.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        
        # Recheck STOP/claim under lock
        if (RUNTIME / "STOP").exists():
            return 0
        if (ENROLL / "evaluation.claim").exists():
            return 0
        
        return _run()


def _run() -> int:
    """Execute one worker cycle: download, validate, append, check/evaluate."""
    now = datetime.now(timezone.utc)
    run = RUNTIME / now.strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(exist_ok=False)
    status = {"time_utc": now.isoformat(), "orders_enabled": False}
    
    conn = None
    try:
        # Load and validate frozen enrollment
        enrollment = json.loads((ENROLL / "manifest.json").read_text())
        
        # Git validation
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=FROZEN_ROOT, text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=FROZEN_ROOT, text=True
        ).strip()
        if commit != enrollment["git_commit"] or dirty:
            raise ValueError("frozen checkout changed")
        
        # History hash validation
        history_path = ENROLL / "history.csv"
        if not history_path.exists():
            raise ValueError("history.csv missing")
        history_hash = hashlib.sha256(history_path.read_bytes()).hexdigest()
        if history_hash != enrollment["history_sha256"]:
            raise ValueError("history hash changed")
        
        # Calendar validation (using absolute DB path from enrollment)
        source_conn = None
        try:
            source_conn = sqlite3.connect(f"file:{SOURCE_DB}?mode=ro", uri=True)
            calendar = [
                dict(cutoff_date=d, source=s)
                for d, s in source_conn.execute(
                    "SELECT cutoff_date, source FROM dividends WHERE ticker=? ORDER BY cutoff_date",
                    ("SBER",)
                )
            ]
        finally:
            if source_conn:
                source_conn.close()
        
        if calendar != enrollment["dividend_calendar"]:
            raise ValueError("source calendar changed; review required")
        
        # Get latest timestamp from research DB
        conn = sqlite3.connect(DB.resolve().as_uri() + "?mode=rw", uri=True)
        cursor = conn.execute(
            "SELECT MAX(begin) FROM candles WHERE ticker=? AND period=?",
            ("SBER", "15min")
        )
        latest = cursor.fetchone()[0]
        cursor.close()
        
        if not latest:
            raise ValueError("no existing candles in research DB")
        
        # Download new candles starting 1 day before latest (overlap for safety)
        start = datetime.fromisoformat(latest).replace(tzinfo=timezone.utc) - timedelta(days=1)
        
        status.update(frozen_commit=commit, database_identifier=str(DB.resolve()),
                      storage_timezone="UTC-naive", market_timezone="Europe/Moscow",
                      requested_start_utc=start.isoformat(),
                      worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        collector_path = ROOT / "scripts/lstm_sandbox_collect.py"
        status["collector_sha256"] = hashlib.sha256(collector_path.read_bytes()).hexdigest()
        with collector_path.open("rb") as script:
            try:
                collector = subprocess.run(
                    ["docker", "exec", "-i", "trader-bot-engine", "python", "-", start.isoformat()],
                    stdin=script, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, timeout=300,
                )
            except subprocess.TimeoutExpired:
                collector = subprocess.CompletedProcess([], 1, stdout="")
        
        # Transient download errors: don't STOP, just retry next cycle
        if collector.returncode == 2:
            raise ValueError("collector rejected invalid market data")
        if collector.returncode:
            status.update(status="download_failed", reason="sandbox API unavailable")
            (run / "status.json").write_text(json.dumps(status, indent=2))
            (RUNTIME / "status.json").write_text(json.dumps(status, indent=2))
            return 0  # Normal exit, will retry later
        
        payload = json.loads(collector.stdout)
        
        # Validation errors: STOP immediately
        if "error" in payload:
            raise ValueError(f"collector error: {payload['error']}")
        if payload.get("source") != "sandbox-invest-public-api.tbank.ru":
            raise ValueError(f"unexpected source: {payload.get('source')}")
        if "source_sha256" not in payload:
            raise ValueError("missing source_sha256")
        
        # Save provenance
        (run / "candles.json").write_text(json.dumps(payload, indent=2))
        status["source_sha256"] = payload["source_sha256"]
        
        rows = payload["rows"]
        if hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest() != payload["source_sha256"]:
            raise ValueError("batch hash mismatch")
        
        # Validate sorted timestamps
        for i in range(len(rows) - 1):
            if rows[i][0] >= rows[i + 1][0]:
                raise ValueError(f"timestamps not sorted: {rows[i][0]} >= {rows[i + 1][0]}")
        
        # Append new candles
        added = 0
        skipped_existing = 0
        
        with conn:  # Transaction context
            for row in rows:
                timestamp_str = row[0]
                stamp = datetime.fromisoformat(timestamp_str)
                if stamp.isoformat(" ") != timestamp_str or stamp.replace(tzinfo=timezone.utc) < start:
                    raise ValueError("noncanonical or out-of-range timestamp")
                values = row[1:]
                
                # Validate timestamp normalization
                if stamp.tzinfo is not None:
                    raise ValueError(f"timestamp has tzinfo: {timestamp_str}")
                if stamp.replace(tzinfo=timezone.utc) + timedelta(minutes=15) > datetime.now(timezone.utc):
                    raise ValueError(f"incomplete candle: {timestamp_str}")
                if stamp.minute % 15 != 0 or stamp.second != 0 or stamp.microsecond != 0:
                    raise ValueError(f"not 15min boundary: {timestamp_str}")
                
                # Validate OHLCV
                if not all(math.isfinite(v) for v in values):
                    raise ValueError(f"non-finite values at {timestamp_str}")
                
                opening, high, low, close, volume = values
                if not (0 < low <= opening <= high):
                    raise ValueError(f"invalid OHLC at {timestamp_str}")
                if not (low <= close <= high):
                    raise ValueError(f"close out of range at {timestamp_str}")
                if volume < 0:
                    raise ValueError(f"negative volume at {timestamp_str}")
                
                # Check for existing row
                cursor = conn.execute(
                    "SELECT open, high, low, close, volume FROM candles "
                    "WHERE ticker=? AND period=? AND begin=?",
                    ("SBER", "15min", timestamp_str),
                )
                old = cursor.fetchone()
                cursor.close()
                
                if old is not None:
                    # Revision detection
                    if tuple(values) != old:
                        raise ValueError(f"existing candle revised at {timestamp_str}")
                    skipped_existing += 1
                    continue
                
                # Prevent late historical insertion
                if timestamp_str <= latest:
                    raise ValueError("late historical insertion")
                
                # Explicit column INSERT to prevent schema drift
                conn.execute(
                    "INSERT INTO candles (ticker, period, begin, open, high, low, close, volume) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("SBER", "15min", timestamp_str, opening, high, low, close, volume),
                )
                added += 1
        
        status["added_rows"] = added
        status["skipped_existing"] = skipped_existing
        
        # Close DB before subprocess calls
        conn.close()
        conn = None
        
        # Run check and optionally evaluate
        env = dict(
            os.environ,
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1"
        )
        
        for action in ("check", "evaluate"):
            destination = run / action
            result = subprocess.run(
                [
                    PYTHON, str(FROZEN_ROOT / "scripts/run_lstm_prospective.py"), action,
                    "--db", str(DB),
                    "--enrollment", str(ENROLL),
                    "--artifacts-dir", str(destination),
                ],
                cwd=FROZEN_ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3600,
            )
            
            manifests = list(destination.glob("*/manifest.json"))
            if result.returncode or len(manifests) != 1:
                raise RuntimeError(f"{action} failed; inspect worker artifacts")
            
            result_manifest = json.loads(manifests[0].read_text())
            status.update(
                status=result_manifest["status"],
                completed_forward_bars=result_manifest.get("completed_forward_bars"),
            )
            
            # If check says "waiting", don't evaluate yet
            if action == "check" and result_manifest["status"] != "ready":
                break
            if action == "check" and result_manifest.get("completed_forward_bars") != 2000:
                raise ValueError("ready without exactly 2000 forward bars")
    
    except Exception as exc:
        status.update(status="stopped", reason=str(exc))
        (RUNTIME / "STOP").write_text("Review status.json before clearing this guard.\n")
    
    finally:
        # Ensure DB is closed
        if conn:
            conn.close()
    
    # Write status files
    (run / "status.json").write_text(json.dumps(status, indent=2))
    (RUNTIME / "status.json").write_text(json.dumps(status, indent=2))
    
    return 0 if status.get("status") in {"waiting", "ready", "completed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
