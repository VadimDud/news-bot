"""Tests for LSTM sandbox worker with real tmp SQLite and importlib dynamic loading.

Key test scenarios:
- Idempotent append: duplicate candles skipped, no error
- Revised row detection: validation STOP on conflicting data
- Waiting state: no evaluation when check returns waiting
- Ready state: evaluate once when check returns ready
- Download failure: no STOP, allows retry
- Dirty git: STOP
- Malformed OHLCV: rollback transaction
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def source_db(tmp_path: Path) -> Path:
    """Create real source DB with dividend calendar."""
    db_path = tmp_path / "source.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS dividends "
        "(ticker TEXT, cutoff_date TEXT, source TEXT)"
    )
    conn.execute(
        "INSERT INTO dividends VALUES (?, ?, ?)",
        ("SBER", "2026-03-15", "moex")
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_workspace(tmp_path: Path, source_db: Path, request):
    """Create temporary workspace with real SQLite fixtures."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create directory structure
    artifacts = workspace / "artifacts"
    (artifacts / "lstm_frozen/trading_moex").mkdir(parents=True)
    (artifacts / "runs/sber_research_20261117T091017677811Z").mkdir(parents=True)
    enroll_dir = artifacts / "runs/lstm_prospective/20261117T091059077116Z_LSTM-PROSPECTIVE_enroll"
    enroll_dir.mkdir(parents=True)
    (artifacts / "runs/lstm_automation").mkdir(parents=True)
    
    # Create scripts directory with dummy collector
    scripts = workspace / "scripts"
    scripts.mkdir()
    (scripts / "lstm_sandbox_collect.py").write_text("# dummy collector script\n")
    
    # Create research DB with real schema
    db_path = artifacts / "runs/sber_research_20261117T091017677811Z/research.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE candles (ticker TEXT, period TEXT, begin TEXT, "
        "open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    
    # Insert baseline candles: 5 candles starting 2026-11-01 10:00:00
    baseline = datetime(2026, 11, 1, 10, 0, 0)
    for i in range(5):
        timestamp = (baseline + timedelta(minutes=15 * i)).isoformat(" ")
        conn.execute(
            "INSERT INTO candles (ticker, period, begin, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("SBER", "15min", timestamp, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 1000.0)
        )
    conn.commit()
    conn.close()
    
    # Create enrollment manifest with actual history sha256
    history_content = b"dummy history"
    history_sha = hashlib.sha256(history_content).hexdigest()
    
    manifest = {
        "git_commit": "abc123def456",
        "history_sha256": history_sha,
        "dividend_calendar": [
            {"cutoff_date": "2026-03-15", "source": "moex"}
        ],
    }
    (enroll_dir / "manifest.json").write_text(json.dumps(manifest))
    (enroll_dir / "history.csv").write_bytes(history_content)
    
    return workspace, source_db


def load_worker_module(workspace: Path, source_db: Path):
    """Load run_lstm_sandbox_worker module dynamically using importlib with patched globals."""
    script_path = Path(__file__).parent.parent / "scripts/run_lstm_sandbox_worker.py"
    spec = importlib.util.spec_from_file_location("run_lstm_sandbox_worker", script_path)
    module = importlib.util.module_from_spec(spec)
    
    # Execute the module first (this sets module-level globals to real paths)
    spec.loader.exec_module(module)
    
    # THEN override with test paths (this overwrites the module-level globals)
    module.ROOT = workspace
    module.FROZEN_ROOT = workspace / "artifacts/lstm_frozen/trading_moex"
    module.DB = workspace / "artifacts/runs/sber_research_20261117T091017677811Z/research.db"
    module.ENROLL = workspace / "artifacts/runs/lstm_prospective/20261117T091059077116Z_LSTM-PROSPECTIVE_enroll"
    module.RUNTIME = workspace / "artifacts/runs/lstm_automation"
    module.PYTHON = "/usr/bin/python3"
    module.SOURCE_DB = source_db
    
    return module


def test_idempotent_append(temp_workspace: tuple, source_db: Path):
    """Test that duplicate and overlapping candles are skipped without error."""
    temp_workspace, _ = temp_workspace
    baseline = datetime(2026, 11, 1, 10, 0, 0)
    rows = []
    for i in range(3, 8):  # Overlap with existing (3,4), add new (5,6,7)
        timestamp = (baseline + timedelta(minutes=15 * i)).isoformat(" ")
        rows.append([timestamp, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 1000.0])
    
    # Compute actual source_sha256
    source_sha = hashlib.sha256(
        json.dumps(rows, separators=(',', ':')).encode()
    ).hexdigest()
    
    collector_output = {
        "source": "sandbox-invest-public-api.tbank.ru",
        "rows": rows,
        "source_sha256": source_sha,
    }
    
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        
        if cmd[0] == "docker":
            # Collector call
            result.stdout = json.dumps(collector_output)
            return result
        
        if "run_lstm_prospective.py" in str(cmd):
            # Check/evaluate call
            action = cmd[2]
            artifacts_dir = Path(cmd[cmd.index("--artifacts-dir") + 1])
            run_dir = artifacts_dir / "result"
            run_dir.mkdir(parents=True)
            manifest = {
                "status": "waiting" if action == "check" else "completed",
                "completed_forward_bars": 0,
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            return result
        
        raise ValueError(f"Unexpected command: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        mock_check_output.side_effect = lambda cmd, **kw: (
            "abc123def456\n" if "rev-parse" in cmd else ""
        )
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                assert result == 0
                
                # Verify DB state: 3 new rows added
                db_path = temp_workspace / "artifacts/runs/sber_research_20261117T091017677811Z/research.db"
                conn = sqlite3.connect(db_path)
                count = conn.execute(
                    "SELECT COUNT(*) FROM candles WHERE ticker=? AND period=?",
                    ("SBER", "15min")
                ).fetchone()[0]
                conn.close()
                
                assert count == 8  # 5 original + 3 new


def test_revised_row_rollback(temp_workspace: tuple, source_db: Path):
    """Test that revised candle data causes rollback and STOP file."""
    temp_workspace, _ = temp_workspace
    baseline = datetime(2026, 11, 1, 10, 0, 0)
    rows = [
        # Existing timestamp with DIFFERENT values -> conflict
        [(baseline + timedelta(minutes=15 * 3)).isoformat(" "), 999.0, 1000.0, 998.0, 999.5, 5000.0],
    ]
    
    source_sha = hashlib.sha256(
        json.dumps(rows, separators=(',', ':')).encode()
    ).hexdigest()
    
    collector_output = {
        "source": "sandbox-invest-public-api.tbank.ru",
        "rows": rows,
        "source_sha256": source_sha,
    }
    
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        
        if cmd[0] == "docker":
            result.stdout = json.dumps(collector_output)
            return result
        
        raise ValueError(f"Should not reach: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        mock_check_output.side_effect = lambda cmd, **kw: (
            "abc123def456\n" if "rev-parse" in cmd else ""
        )
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                # Should create STOP file on validation error
                stop_path = temp_workspace / "artifacts/runs/lstm_automation/STOP"
                assert stop_path.exists()
                
                # Verify no new rows added (rollback)
                db_path = temp_workspace / "artifacts/runs/sber_research_20261117T091017677811Z/research.db"
                conn = sqlite3.connect(db_path)
                count = conn.execute(
                    "SELECT COUNT(*) FROM candles WHERE ticker=? AND period=?",
                    ("SBER", "15min")
                ).fetchone()[0]
                conn.close()
                
                assert count == 5  # Still original 5


def test_waiting_no_evaluate(temp_workspace: tuple, source_db: Path):
    """Test that evaluate is skipped when check returns waiting."""
    temp_workspace, _ = temp_workspace
    baseline = datetime(2026, 11, 1, 10, 0, 0)
    rows = [
        [(baseline + timedelta(minutes=15 * 5)).isoformat(" "), 105.0, 106.0, 104.0, 105.5, 1000.0],
    ]
    
    source_sha = hashlib.sha256(
        json.dumps(rows, separators=(',', ':')).encode()
    ).hexdigest()
    
    collector_output = {
        "source": "sandbox-invest-public-api.tbank.ru",
        "rows": rows,
        "source_sha256": source_sha,
    }
    
    action_calls = []
    
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        
        if cmd[0] == "docker":
            result.stdout = json.dumps(collector_output)
            return result
        
        if "run_lstm_prospective.py" in str(cmd):
            action = cmd[2]
            action_calls.append(action)
            
            artifacts_dir = Path(cmd[cmd.index("--artifacts-dir") + 1])
            run_dir = artifacts_dir / "result"
            run_dir.mkdir(parents=True)
            manifest = {
                "status": "waiting",
                "completed_forward_bars": 10,
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            return result
        
        raise ValueError(f"Unexpected: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        mock_check_output.side_effect = lambda cmd, **kw: (
            "abc123def456\n" if "rev-parse" in cmd else ""
        )
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                assert result == 0
                assert "check" in action_calls
                assert "evaluate" not in action_calls  # Skipped


def test_ready_evaluate_once(temp_workspace: tuple, source_db: Path):
    """Test that evaluate runs once when check returns ready."""
    temp_workspace, _ = temp_workspace
    baseline = datetime(2026, 11, 1, 10, 0, 0)
    rows = [
        [(baseline + timedelta(minutes=15 * 5)).isoformat(" "), 105.0, 106.0, 104.0, 105.5, 1000.0],
    ]
    
    source_sha = hashlib.sha256(
        json.dumps(rows, separators=(',', ':')).encode()
    ).hexdigest()
    
    collector_output = {
        "source": "sandbox-invest-public-api.tbank.ru",
        "rows": rows,
        "source_sha256": source_sha,
    }
    
    action_calls = []
    
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        
        if cmd[0] == "docker":
            result.stdout = json.dumps(collector_output)
            return result
        
        if "run_lstm_prospective.py" in str(cmd):
            action = cmd[2]
            action_calls.append(action)
            
            artifacts_dir = Path(cmd[cmd.index("--artifacts-dir") + 1])
            run_dir = artifacts_dir / "result"
            run_dir.mkdir(parents=True)
            manifest = {
                "status": "ready" if action == "check" else "completed",
                "completed_forward_bars": 96,
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            return result
        
        raise ValueError(f"Unexpected: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        mock_check_output.side_effect = lambda cmd, **kw: (
            "abc123def456\n" if "rev-parse" in cmd else ""
        )
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                assert result == 0
                assert action_calls == ["check", "evaluate"]


def test_download_failure_no_stop(temp_workspace: tuple, source_db: Path):
    """Test that download failure returns 0 without STOP."""
    temp_workspace, _ = temp_workspace
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        if cmd[0] == "docker":
            result.returncode = 1  # Download failed
            result.stdout = ""
            return result
        raise ValueError(f"Unexpected: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        mock_check_output.side_effect = lambda cmd, **kw: (
            "abc123def456\n" if "rev-parse" in cmd else ""
        )
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                assert result == 0  # Transient error, no STOP
                stop_path = temp_workspace / "artifacts/runs/lstm_automation/STOP"
                assert not stop_path.exists()


def test_dirty_git_stop(temp_workspace: tuple, source_db: Path):
    """Test that dirty git repo creates STOP."""
    temp_workspace, _ = temp_workspace
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        raise ValueError(f"Should not reach: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        def check_side_effect(cmd, **kw):
            if "rev-parse" in cmd:
                return "abc123def456\n"
            if "status" in cmd:
                return " M scripts/run_lstm_sandbox_worker.py\n"  # Dirty
            raise ValueError(f"Unexpected: {cmd}")
        
        mock_check_output.side_effect = check_side_effect
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                stop_path = temp_workspace / "artifacts/runs/lstm_automation/STOP"
                assert stop_path.exists()


def test_malformed_ohlcv_rollback(temp_workspace: tuple, source_db: Path):
    """Test that invalid OHLCV causes rollback and STOP."""
    temp_workspace, _ = temp_workspace
    baseline = datetime(2026, 11, 1, 10, 0, 0)
    rows = [
        # Invalid: low > close
        [(baseline + timedelta(minutes=15 * 5)).isoformat(" "), 100.0, 101.0, 102.0, 99.0, 1000.0],
    ]
    
    source_sha = hashlib.sha256(
        json.dumps(rows, separators=(',', ':')).encode()
    ).hexdigest()
    
    collector_output = {
        "source": "sandbox-invest-public-api.tbank.ru",
        "rows": rows,
        "source_sha256": source_sha,
    }
    
    def mock_subprocess_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        if cmd[0] == "docker":
            result.stdout = json.dumps(collector_output)
            return result
        raise ValueError(f"Unexpected: {cmd}")
    
    module = load_worker_module(temp_workspace, source_db)
    
    with patch.object(module.subprocess, "check_output") as mock_check_output:
        mock_check_output.side_effect = lambda cmd, **kw: (
            "abc123def456\n" if "rev-parse" in cmd else ""
        )
        
        with patch.object(module.subprocess, "run", side_effect=mock_subprocess_run):
            with patch.dict(os.environ, {}, clear=False):
                result = module.main()
                
                stop_path = temp_workspace / "artifacts/runs/lstm_automation/STOP"
                assert stop_path.exists()
                
                # Verify no rows added (rollback)
                db_path = temp_workspace / "artifacts/runs/sber_research_20261117T091017677811Z/research.db"
                conn = sqlite3.connect(db_path)
                count = conn.execute(
                    "SELECT COUNT(*) FROM candles WHERE ticker=? AND period=?",
                    ("SBER", "15min")
                ).fetchone()[0]
                conn.close()
                
                assert count == 5  # Still original 5
