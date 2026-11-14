from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_sensitivity_runner_declares_27_cells() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "research_volume_islands_sensitivity.py"
    result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--tickers" in result.stdout
