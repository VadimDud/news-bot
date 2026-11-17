import json
import hashlib
from datetime import datetime, timedelta
import pytest
import sqlite3
import subprocess
import sys
from pathlib import Path


def make_db(path: Path, count: int = 10) -> None:
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE candles (ticker TEXT, period TEXT, begin TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)")
        db.execute("CREATE TABLE dividends (ticker TEXT, cutoff_date TEXT, source TEXT)")
        db.executemany(
            "INSERT INTO candles VALUES ('SBER', '15min', ?, 1, 2, 0.5, 1.5, 10)",
            [((datetime(2026, 1, 1, 9) + timedelta(minutes=15 * i)).isoformat(" "),) for i in range(count)],
        )
        db.execute("INSERT INTO dividends VALUES ('SBER', '2026-01-03', 'smartlab')")


def run(script: Path, db: Path, artifacts: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(script), "--db", str(db), "--artifacts-dir", str(artifacts), *extra],
        capture_output=True, text=True,
    )


def test_enrollment_records_watermark_without_metrics(tmp_path):
    db, artifacts = tmp_path / "db.sqlite", tmp_path / "artifacts"
    make_db(db)
    original_db_hash = hashlib.sha256(db.read_bytes()).hexdigest()
    script = Path(__file__).parents[1] / "scripts" / "enroll_prospective_lstm.py"
    result = run(script, db, artifacts)
    assert result.returncode == 0, result.stderr
    run_dir = next(artifacts.iterdir())
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["evaluation_bars"] == 2000
    assert manifest["status"] == "snapshot_recorded"
    assert manifest["enrollment_authorized"] is False
    assert manifest["freeze_time_utc"] is None
    assert manifest["inspected_ohlcv_rows"] == 10
    assert manifest["inspected_data_watermark_utc"] == "2026-01-01T11:15:00+00:00"
    assert manifest["inspected_ohlcv_sha256"] == hashlib.sha256((run_dir / "ohlcv.csv").read_bytes()).hexdigest()
    assert manifest["dividend_calendar_sha256"] == hashlib.sha256(json.dumps(
        manifest["dividend_calendar"], sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    assert manifest["dividend_calendar"][0]["source"] == "smartlab"
    assert manifest["no_training_or_interim_metrics"] is True
    assert not (run_dir / "metrics.json").exists()
    assert hashlib.sha256(db.read_bytes()).hexdigest() == original_db_hash
    assert manifest["calendar_read_time_utc"]


def test_enrollment_fails_for_empty_calendar(tmp_path):
    db, artifacts = tmp_path / "db.sqlite", tmp_path / "artifacts"
    make_db(db)
    with sqlite3.connect(db) as connection:
        connection.execute("DELETE FROM dividends")
    script = Path(__file__).parents[1] / "scripts" / "enroll_prospective_lstm.py"
    result = run(script, db, artifacts)
    assert result.returncode == 1
    manifest = json.loads(next(artifacts.iterdir()).joinpath("manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert "calendar" in manifest["failure_reason"]


def test_enrollment_rejects_untrusted_dividend_source(tmp_path):
    db, artifacts = tmp_path / "db.sqlite", tmp_path / "artifacts"
    make_db(db, count=2000)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE dividends SET source = 'tinkoff'")
    script = Path(__file__).parents[1] / "scripts" / "enroll_prospective_lstm.py"
    result = run(script, db, artifacts)
    assert result.returncode == 1
    manifest = json.loads(next(artifacts.iterdir()).joinpath("manifest.json").read_text())
    assert "untrusted dividend source" in manifest["failure_reason"]


def test_enrollment_requires_exactly_2000(tmp_path):
    db, artifacts = tmp_path / "db.sqlite", tmp_path / "artifacts"
    make_db(db)
    script = Path(__file__).parents[1] / "scripts" / "enroll_prospective_lstm.py"
    result = run(script, db, artifacts, "--evaluation-bars", "1000")
    assert result.returncode == 2


@pytest.mark.parametrize("column,value", [
    ("begin", "2026-01-01 09:499:45:00"),
    ("begin", "2026-01-01T09:00:00+03:00"),
    ("begin", "2999-01-01 09:00:00"),
    ("close", None), ("close", float("inf")),
    ("volume", -1), ("low", 0), ("high", 1),
    ("begin", "2026-01-01 09:00:00"),
])
def test_invalid_snapshot_fails_closed(tmp_path, column, value):
    db, artifacts = tmp_path / "db.sqlite", tmp_path / "artifacts"
    make_db(db)
    with sqlite3.connect(db) as connection:
        connection.execute(f"UPDATE candles SET {column} = ? WHERE rowid = 10", (value,))
    script = Path(__file__).parents[1] / "scripts" / "enroll_prospective_lstm.py"
    result = run(script, db, artifacts)
    assert result.returncode == 1, result.stderr
    manifest = json.loads(next(artifacts.iterdir()).joinpath("manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["enrollment_authorized"] is False
    assert manifest["storage_timezone"] == "UTC-naive"


@pytest.mark.parametrize("extra", [("--ticker", "GAZP"), ("--period", "15m")])
def test_fixed_contract(tmp_path, extra):
    script = Path(__file__).parents[1] / "scripts" / "enroll_prospective_lstm.py"
    result = run(script, tmp_path / "missing.db", tmp_path / "artifacts", *extra)
    assert result.returncode == 2
    assert not (tmp_path / "artifacts").exists()
