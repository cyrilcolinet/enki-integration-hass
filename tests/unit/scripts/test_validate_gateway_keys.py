"""Unit tests for gateway key validation script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_validate_gateway_keys_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_gateway_keys.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
