from datetime import datetime, timedelta, timezone

from scripts.cleanup_research import find_candidates, quarantine


def test_cleanup_only_finds_old_cache_and_scratch(tmp_path):
    root = tmp_path / "artifacts"
    old = datetime.now(timezone.utc) - timedelta(days=20)
    cache = root / "cache" / "old.bin"
    scratch = root / "scratch" / "old.txt"
    protected = root / "runs" / "run-1" / "metrics.json"
    for path in (cache, scratch, protected):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data")
        timestamp = old.timestamp()
        import os
        os.utime(path, (timestamp, timestamp))

    candidates = find_candidates(root, now=datetime.now(timezone.utc))
    assert {item.path for item in candidates} == {cache, scratch}
    assert all(item.size_bytes == 4 for item in candidates)


def test_quarantine_preserves_relative_path_and_does_not_overwrite(tmp_path):
    root = tmp_path / "artifacts"
    source = root / "cache" / "old.bin"
    source.parent.mkdir(parents=True)
    source.write_text("data")
    candidate = find_candidates(root, now=datetime.now(timezone.utc) + timedelta(days=15))
    moved = quarantine(candidate, root, now=datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert moved[0] == root / "quarantine" / "20260102T000000Z" / "cache" / "old.bin"
    assert moved[0].read_text() == "data"
    assert not source.exists()
