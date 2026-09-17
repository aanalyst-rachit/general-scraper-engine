from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmark" / "phase16" / "runner.py"
RESULTS = ROOT / "benchmark" / "phase16" / "results" / "matrix.json"


def test_phase16_benchmark_matrix(tmp_path):
    result = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert RESULTS.exists()

    matrix = json.loads(RESULTS.read_text(encoding="utf-8"))

    assert matrix["all_passed"] is True
    assert matrix["passed_workloads"] == matrix["total_workloads"]
    assert matrix["total_workloads"] == 10
