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
spec = importlib.util.spec_from_file_location("prospective", SCRIPTS / "run_lstm_prospective.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def candles(n, start="2020-01-01"):
    close = 100 + 3 * np.sin(np.arange(n) / 5)
    return pd.DataFrame(dict(open=close, high=close+1, low=close-1,
                             close=close, volume=10 + np.arange(n) % 17),
                        index=pd.date_range(start, periods=n, freq="15min", name="timestamp"))


def test_training_is_causal_and_boundaries_purged():
    frame = candles(2600)
    history, forward = frame.iloc[:600], frame.iloc[600:]
    train, test, counts, boundary = runner.prepare(history, forward, [])
    changed = forward.copy()
    changed.loc[:, ["open", "high", "low", "close"]] *= 2
    train2, _, _, _ = runner.prepare(history, changed, [])
    np.testing.assert_array_equal(train.X, train2.X)
    np.testing.assert_array_equal(train.y, train2.y)
    assert len(train.y) == 495
    assert len(test.y) == 1995
    assert train.outcome_timestamps.max() <= history.index[-1]
    assert test.decision_timestamps.min() == forward.index[0]
    assert test.outcome_timestamps.max() == forward.index[-1]
    assert counts == {"train": 0, "forward": 0}
    assert boundary == {"train": 5, "forward": 5}


def test_calendar_mask_and_exact_size():
    frame = candles(2600)
    _, test, counts, _ = runner.prepare(frame.iloc[:600], frame.iloc[600:], ["2020-01-09"])
    assert counts["forward"] == 5
    assert len(test.y) == 1990
    with pytest.raises(ValueError, match="partition sizes"):
        runner.prepare(frame.iloc[:600], frame.iloc[600:-1], [])


def test_enroll_wait_hash_and_duplicate_evaluation(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    history = candles(600)
    with sqlite3.connect(db) as conn:
        data = history.reset_index()
        data["timestamp"] = data.timestamp.astype(str)
        data = data.rename(columns={"timestamp": "begin"})
        data["ticker"], data["period"] = "SBER", "15min"
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
    assert manifest["parameters"]["train_bars"] == 500
    code, output, manifest = invoke("evaluate", "--enrollment", str(enrollment))
    assert code == 0 and manifest["status"] == "waiting"
    assert not (output / "metrics.json").exists()
    assert not (enrollment / "evaluation.claim").exists()
    (enrollment / "history.csv").write_text("tampered")
    code, output, manifest = invoke("check", "--enrollment", str(enrollment))
    assert code == 1
    assert "hash mismatch" in manifest["failure_reason"]


@pytest.mark.parametrize("real_training", [False, True], ids=["mock", "pytorch"])
def test_complete_forward_and_permanent_claim(tmp_path, monkeypatch, request, real_training):
    if real_training:
        torch = pytest.importorskip("torch")
        previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        # Restore global thread settings even if an assertion fails.
        request.addfinalizer(lambda: torch.set_num_threads(previous_threads))
    class Clock(datetime):
        current = datetime(2020, 2, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            cls.current += timedelta(microseconds=1)
            return cls.current

    monkeypatch.setattr(runner, "datetime", Clock)
    monkeypatch.setattr(runner, "_git", lambda *args: "" if args[0] == "status" else "abc123")
    if not real_training:
        monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "test")
    db = tmp_path / "db.sqlite"
    root = tmp_path / "runs"

    def insert(frame, mode):
        data = frame.reset_index().rename(columns={"timestamp": "begin"})
        data["begin"] = data.begin.astype(str)
        data["ticker"], data["period"] = "SBER", "15min"
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
    insert(candles(2001, "2020-02-01 00:15:00"), "append")
    Clock.current = datetime(2020, 3, 1, tzinfo=timezone.utc)
    calls = []

    def fake_evaluate(train, forward):
        calls.append(len(forward.y))
        assert train.outcome_timestamps.max() < forward.decision_timestamps.min()
        return {"mock_only": True}

    if not real_training:
        monkeypatch.setattr(runner, "evaluate", fake_evaluate)
    code, output, manifest = invoke("evaluate", "--enrollment", str(enrollment))
    assert code == 0, manifest
    assert manifest["status"] == "completed"
    assert manifest["completed_forward_bars"] == 2000
    assert len(pd.read_csv(output / "forward.csv")) == 2000
    if real_training:
        metrics = json.loads((output / "metrics.json").read_text())
        assert set(metrics) == {"lstm", "logistic", "prevalence"}
        for values in metrics.values():
            assert values["samples"] == 1995
            assert np.isfinite(values["log_loss"])
            assert np.asarray(values["confusion_matrix"]).sum() == 1995
        assert manifest["parameters"]["epochs"] == 50
    else:
        assert calls == [1995]
    code, output, manifest = invoke("evaluate", "--enrollment", str(enrollment))
    assert code == 1
    assert calls == ([] if real_training else [1995])
    assert not (output / "metrics.json").exists()
