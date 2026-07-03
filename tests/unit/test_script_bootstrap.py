"""Verify standalone scripts import without Home Assistant."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def test_fetch_gateway_keys_help_without_homeassistant() -> None:
    result = subprocess.run(
        [PYTHON, str(REPO / "scripts/fetch_gateway_keys.py"), "--help"],
        capture_output=True,
        text=True,
        cwd="/tmp",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "homeassistant" not in result.stderr.lower()


def test_extract_gateway_keys_imports_without_homeassistant() -> None:
    code = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'''{REPO}''') / "scripts"))
from enki_bootstrap import bootstrap_fetch_keys, load_module
bootstrap_fetch_keys()
assert load_module("enki.const").ENKI_HOME_API_KEY
print("ok")
"""
    result = subprocess.run(
        [PYTHON, "-c", code],
        capture_output=True,
        text=True,
        cwd="/tmp",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == "ok"


def test_discover_devices_imports_without_homeassistant() -> None:
    code = f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'''{REPO}''') / "scripts"))
from enki_bootstrap import bootstrap_api_client, load_module
client_mod = bootstrap_api_client()
profile_mod = load_module("enki.domain.profile")
assert client_mod.EnkiAPI
assert profile_mod.profile_fingerprint
print("ok")
"""
    result = subprocess.run(
        [PYTHON, "-c", code],
        capture_output=True,
        text=True,
        cwd="/tmp",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == "ok"
