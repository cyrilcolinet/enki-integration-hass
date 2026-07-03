"""Unit tests for APK gateway key diff (--check)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402
from extract_gateway_keys import check_against_repo, read_const_keys  # noqa: E402


def _wired_repo_extract() -> dict[str, tuple[str | None, str]]:
    bootstrap("enki.api.gateway_registry")
    registry = load_module("enki.api.gateway_registry")
    const = read_const_keys()
    return {
        svc.const_key: (const.get(svc.const_key) or None, "repo snapshot")
        for svc in registry.ENKI_MICRO_SERVICES
        if svc.wired
    }


def test_check_against_repo_ok_when_matching() -> None:
    assert check_against_repo(_wired_repo_extract()) == []


def test_check_against_repo_detects_mismatch() -> None:
    extracted = _wired_repo_extract()
    extracted["ENKI_LIGHTS_API_KEY"] = ("00000000000000000000000000000000", "test")
    errors = check_against_repo(extracted)
    assert any("ENKI_LIGHTS_API_KEY" in err for err in errors)
