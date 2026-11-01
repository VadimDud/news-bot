"""Safely inspect and quarantine stale generated research artifacts.

The default action is a dry-run. Permanent deletion is deliberately not
implemented here: quarantined files require a separate review and approval.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROTECTED_NAMES = {"manifest.json", "metrics.json", "checks.json", "trades.csv.gz"}
PROTECTED_SUFFIXES = {".db", ".pem", ".key", ".env"}


@dataclass(frozen=True)
class Candidate:
    path: Path
    age_days: int
    size_bytes: int
    reason: str


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _is_protected(path: Path, root: Path) -> bool:
    if not _inside(path, root) or path.name in PROTECTED_NAMES:
        return True
    if path.suffix.lower() in PROTECTED_SUFFIXES:
        return True
    relative = path.relative_to(root)
    return "runs" in relative.parts and path.name not in {"run.log"}


def find_candidates(root: str | Path, now: datetime | None = None) -> list[Candidate]:
    """Find old cache/scratch files, never source data or run evidence."""
    artifact_root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    candidates: list[Candidate] = []
    for bucket, threshold, reason in (
        ("cache", 14, "rebuildable cache older than 14 days"),
        ("scratch", 14, "scratch output older than 14 days"),
    ):
        directory = artifact_root / bucket
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_symlink() or not path.is_file() or _is_protected(path, artifact_root):
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            age = (now - modified).days
            if age >= threshold:
                candidates.append(Candidate(path, age, path.stat().st_size, reason))
    return sorted(candidates, key=lambda item: str(item.path))


def quarantine(candidates: list[Candidate], root: str | Path, now: datetime | None = None) -> list[Path]:
    """Move candidates into a dated quarantine directory without overwriting."""
    artifact_root = Path(root).resolve()
    quarantine_root = artifact_root / "quarantine" / (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    moved: list[Path] = []
    for candidate in candidates:
        if candidate.path.is_symlink() or not _inside(candidate.path, artifact_root) or _is_protected(candidate.path, artifact_root):
            raise ValueError(f"refusing unsafe cleanup path: {candidate.path}")
        relative = candidate.path.relative_to(artifact_root)
        destination = quarantine_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        shutil.move(str(candidate.path), str(destination))
        moved.append(destination)
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="artifacts", help="Artifact root")
    parser.add_argument("--quarantine", action="store_true", help="Move candidates after confirmation")
    args = parser.parse_args()
    candidates = find_candidates(args.root)
    for candidate in candidates:
        print(
            f"CANDIDATE {candidate.path} size_bytes={candidate.size_bytes} "
            f"age_days={candidate.age_days} reason={candidate.reason} replacement=none"
        )
    if not args.quarantine:
        print(f"DRY-RUN candidates={len(candidates)}")
        return
    if not candidates:
        print("QUARANTINE candidates=0")
        return
    answer = input(f"Move {len(candidates)} candidate(s) to quarantine? Type 'quarantine': ")
    if answer != "quarantine":
        print("ABORTED")
        return
    moved = quarantine(candidates, args.root)
    print(f"QUARANTINE moved={len(moved)}")


if __name__ == "__main__":
    main()
