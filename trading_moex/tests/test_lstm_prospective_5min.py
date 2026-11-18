import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("prospective_5min", SCRIPTS / "run_lstm_prospective_5min.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def candles(n, start="2020-01-01"):
    """Generate synthetic 5-minute candles."""
    close = 100 + 3 * np.sin(np.arange(n) / 5)
    return pd.DataFrame(dict(open=close, high=close+1, low=close-1,
                             close=close, volume=10 + np.arange(n) % 17),
                        index=pd.date_range(start, periods=n, freq="5min", name="timestamp"))


def test_5min_training_is_causal_and_boundaries_purged():
    """Verify 5-minute training uses causal boundaries correctly."""
    frame = candles(2600)
    history, forward = frame.iloc[:600], frame.iloc[600:]
    train, test, counts, boundary = runner.prepare(history, forward, [])
    changed = forward.copy()
    changed.loc[:, ["open", "high", "low", "close"]] *= 2
    train2, _, _, _ = runner.prepare(history, changed, [])
    np.testing.assert_array_equal(train.X, train2.X)
    np.testing.assert_array_equal(train.y, train2.y)
    assert len(train.y) == 485  # unmasked train: 500 training bars, horizon=15
    assert len(test.y) == 1985  # unmasked forward: 2000 eval bars, horizon=15
    assert train.outcome_timestamps.max() <= history.index[-1]
    assert test.decision_timestamps.min() == forward.index[0]
    assert test.outcome_timestamps.max() == forward.index[-1]
    assert counts == {"train": 0, "forward": 0}
    assert boundary == {"train": 15, "forward": 15}


def test_5min_calendar_mask_and_exact_size():
    """Verify 5-minute calendar masking and partition size."""
    frame = candles(2600)
    _, test, counts, _ = runner.prepare(frame.iloc[:600], frame.iloc[600:], ["2020-01-09"])
    assert counts["forward"] == 15  # 15 * 5min = 75min; outcomes crossing
    assert len(test.y) == 1970  # 1985 unmasked - 15 masked by dividend
    with pytest.raises(ValueError, match="partition sizes"):
        runner.prepare(frame.iloc[:600], frame.iloc[600:-1], [])


def test_5min_enroll_wait_hash_and_duplicate_evaluation(tmp_path, monkeypatch):
    """Test 5-minute enrollment, check, and single evaluation."""
    db = tmp_path / "db.sqlite"
    history = candles(600)
    with sqlite3.connect(db) as conn:
        data = history.reset_index()
        data["timestamp"] = data.timestamp.astype(str)
        data = data.rename(columns={"timestamp": "begin"})
        data["ticker"], data["period"] = "SBER", "5min"
        data.to_sql("candles", conn, index=False)
        conn.execute("CREATE TABLE dividends (ticker TEXT, cutoff_date TEXT, source TEXT)")
        conn.execute("INSERT INTO dividends VALUES ('SBER','2020-01-03','smartlab')")

    monkeypatch.setattr(runner, "_git", lambda *args: "" if args[0] == "status" else "abc123")
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "test")
    root = tmp_path / "runs"

    def invoke(action, *extra):
        monkeypatch.setattr(sys, "argv", ["runner", action, "--db", str(db), "--artifacts-dir", str(root), *extra])
        code = runner.main()
        result = sorted(root.iterdir())[-1]
        return code, result, json.loads((result / "manifest.json").read_text())

    code, enrollment, manifest = invoke("enroll", "--prior-inspected-watermark", "2020-01-01T00:00:00Z")
    assert code == 0
    assert manifest["status"] == "enrolled"
    assert manifest["parameters"]["horizon"] == 15
    assert manifest["study_id"] == "LSTM-SBER-5MIN-001"

    code, output, manifest = invoke("evaluate", "--enrollment", str(enrollment))
    assert code == 0 and manifest["status"] == "waiting"
    assert not (output / "metrics.json").exists()
    assert not (enrollment / "evaluation.claim").exists()

    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE candles SET begin='invalid-time' WHERE rowid=1")

    code, output, manifest = invoke("check", "--enrollment", str(enrollment))
    assert code == 1
    assert "invalid candle timestamp" in manifest["failure_reason"]
    assert not (output / "metrics.json").exists()


def test_5min_horizon_in_params():
    """Verify 5-minute runner uses horizon=15."""
    assert runner.PARAMS["horizon"] == 15
    assert runner.PARAMS["sequence_length"] == 50
    assert runner.PARAMS["evaluation_bars"] == 2000
    assert runner.PARAMS["train_bars"] == 500


def test_5min_complete_forward_and_permanent_claim(tmp_path, monkeypatch, request):
    """Test 5-minute full forward completion with real training."""
    torch = pytest.importorskip("torch")
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    request.addfinalizer(lambda: torch.set_num_threads(previous_threads))

    class Clock(datetime):
        current = datetime(2020, 2, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            cls.current += timedelta(microseconds=1)
            return cls.current

    monkeypatch.setattr(runner, "datetime", Clock)
    monkeypatch.setattr(runner, "_git", lambda *args: "" if args[0] == "status" else "abc123")
    db = tmp_path / "db.sqlite"
    root = tmp_path / "runs"

    def insert(frame, mode):
        data = frame.reset_index().rename(columns={"timestamp": "begin"})
        data["begin"] = data.begin.astype(str)
        data["ticker"], data["period"] = "SBER", "5min"
        with sqlite3.connect(db) as conn:
            data.to_sql("candles", conn, index=False, if_exists=mode)

    insert(candles(600), "replace")
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE dividends (ticker TEXT, cutoff_date TEXT, source TEXT)")
        conn.execute("INSERT INTO dividends VALUES ('SBER','2019-01-03','smartlab')")

    def invoke(action, *extra):
        monkeypatch.setattr(sys, "argv", ["runner", action, "--db", str(db), "--artifacts-dir", str(root), *extra])
        code = runner.main()
        output = sorted(root.iterdir())[-1]
        return code, output, json.loads((output / "manifest.json").read_text())

    _, enrollment, _ = invoke("enroll", "--prior-inspected-watermark", "2020-01-20T00:00:00Z")
    insert(candles(2001, "2020-02-01 00:05:00"), "append")
    Clock.current = datetime(2020, 3, 1, tzinfo=timezone.utc)

    code, output, manifest = invoke("evaluate", "--enrollment", str(enrollment))
    assert code == 0, manifest
    assert manifest["status"] == "completed"
    assert manifest["completed_forward_bars"] == 2000
    assert len(pd.read_csv(output / "forward.csv")) == 2000

    metrics = json.loads((output / "metrics.json").read_text())
    assert set(metrics) == {"lstm", "logistic", "prevalence"}
    for values in metrics.values():
        assert values["samples"] == 1985  # 2000 - 15 boundary excluded
        assert np.isfinite(values["log_loss"])
        assert np.asarray(values["confusion_matrix"]).sum() == 1985

    # Second evaluation should fail due to exclusive claim
    code, output, manifest = invoke("evaluate", "--enrollment", str(enrollment))
    assert code == 1
    assert not (output / "metrics.json").exists()
    assert (enrollment / "evaluation.claim").exists()


def test_5min_database_queries():
    """Verify 5-minute runner queries use correct 5min period and horizon."""
    # Verify hardcoded parameters
    assert runner.PARAMS["horizon"] == 15
    # Verify source contains correct period and study_id
    import inspect
    source = inspect.getsource(runner.main)
    assert "period='5min'" in source
    assert "LSTM-SBER-5MIN-001" in source


def test_worker_uses_separate_enrollment_and_permanent_claim(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("worker5", SCRIPTS / "run_lstm_sandbox_worker_5min.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    assert worker.DB != worker.ROOT / "artifacts/runs/sber_research_20261117T091017677811Z/research.db"
    directory = tmp_path / "enrolled"
    directory.mkdir()
    config = tmp_path / "enrollment.json"
    config.write_text(json.dumps({"directory": str(directory)}))
    monkeypatch.setattr(worker, "ENROLL", config)
    monkeypatch.setattr(worker, "RUNTIME", tmp_path / "runtime")
    calls = []
    monkeypatch.setattr(worker, "_run", lambda path: calls.append(path) or 0)
    assert worker.main() == 0
    assert calls == [directory]
    (directory / "evaluation.claim").write_text("terminal")
    assert worker.main() == 0
    assert calls == [directory]


def test_worker_surfaces_stop_guard(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("worker5_stop", SCRIPTS / "run_lstm_sandbox_worker_5min.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "STOP").write_text("review required")
    monkeypatch.setattr(worker, "RUNTIME", runtime)
    assert worker.main() == 1
