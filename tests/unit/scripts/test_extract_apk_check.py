"""Unit tests for APK gateway key diff (--check)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402
from extract_gateway_keys import Resolved, check_against_repo, read_const_keys  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_enki_import_stubs() -> None:
    """enki_bootstrap registers partial package stubs; drop them after each test."""
    before = set(sys.modules)
    yield
    for key in list(sys.modules):
        if (key == "enki" or key.startswith("enki.")) and key not in before:
            del sys.modules[key]


def _wired_repo_extract() -> dict[str, Resolved]:
    bootstrap("enki.api.gateway_registry")
    registry = load_module("enki.api.gateway_registry")
    const = read_const_keys()
    return {
        svc.const_key: Resolved(const.get(svc.const_key) or None, "repo snapshot", verified=True)
        for svc in registry.ENKI_MICRO_SERVICES
        if svc.wired
    }


def test_check_against_repo_ok_when_matching() -> None:
    assert check_against_repo(_wired_repo_extract()) == []


def test_check_against_repo_detects_mismatch() -> None:
    extracted = _wired_repo_extract()
    extracted["ENKI_LIGHTS_API_KEY"] = Resolved(
        "00000000000000000000000000000000", "test", verified=True
    )
    errors = check_against_repo(extracted)
    assert any("ENKI_LIGHTS_API_KEY" in err for err in errors)


def test_an_unverified_key_is_refused_for_a_wired_service() -> None:
    """A key the extractor could not tie to a call site must not pass (#275)."""
    extracted = _wired_repo_extract()
    current = extracted["ENKI_LIGHTS_API_KEY"]
    extracted["ENKI_LIGHTS_API_KEY"] = Resolved(current.key, "proximity guess")

    errors = check_against_repo(extracted)

    assert any("not tied to a call site" in err for err in errors)
