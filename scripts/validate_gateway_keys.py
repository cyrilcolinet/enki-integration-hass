#!/usr/bin/env python3
"""Validate wired gateway API keys in gateway_keys_data.py.

Shape is the easy half. The half that has actually bitten is a key quietly
swapped for a neighbouring micro-service's (#45, #256, #268, #270): it looks
perfectly valid and fails only against the live gateway, with a 403 that reads
like Adeo closing the API product. CI has no APK, so it cannot follow a key to
its call site — but it can hold every wired key to what the last extractor run
proved, recorded in gateway_key_evidence.json (#275).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KEYS_PY = REPO_ROOT / "custom_components" / "enki" / "gateway_keys_data.py"
EVIDENCE_JSON = REPO_ROOT / "scripts" / "gateway_key_evidence.json"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402

bootstrap("enki.api.gateway_registry")
registry = load_module("enki.api.gateway_registry")
ENKI_MICRO_SERVICES = registry.ENKI_MICRO_SERVICES

KEY_PATTERN = re.compile(r"^[A-Za-z0-9]{32}$")
ASSIGN_PATTERN = re.compile(r'^(ENKI_[A-Z_]+)\s*=\s*"([^"]*)"')


def read_keys() -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in KEYS_PY.read_text(encoding="utf-8").splitlines():
        match = ASSIGN_PATTERN.match(line.strip())
        if match and match.group(1).endswith("_API_KEY"):
            keys[match.group(1)] = match.group(2)
    return keys


def evidence_errors(keys: dict[str, str]) -> list[str]:
    """Every wired key must match the APK call site the extractor recorded."""
    if not EVIDENCE_JSON.is_file():
        return [f"{EVIDENCE_JSON.name} is missing — run extract_gateway_keys.py --write-evidence"]

    recorded = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8")).get("services", {})
    errors: list[str] = []
    for svc in ENKI_MICRO_SERVICES:
        if not svc.wired:
            continue
        proof = recorded.get(svc.const_key)
        if proof is None:
            errors.append(
                f"{svc.const_key} has no recorded call site ({svc.slug}) — "
                "re-run extract_gateway_keys.py --write-evidence against the current APK"
            )
        elif proof.get("key") != keys.get(svc.const_key, ""):
            errors.append(
                f"{svc.const_key} does not match the APK call site "
                f"{proof.get('interface')} recorded for {proof.get('slug')}"
            )
    return errors


def main() -> int:
    if not KEYS_PY.is_file():
        print(f"Missing {KEYS_PY}", file=sys.stderr)
        return 1

    keys = read_keys()
    errors: list[str] = []

    for svc in ENKI_MICRO_SERVICES:
        if not svc.wired:
            continue
        value = keys.get(svc.const_key, "")
        if not value:
            errors.append(f"{svc.const_key} is empty (wired: {svc.slug})")
        elif not KEY_PATTERN.fullmatch(value):
            errors.append(f"{svc.const_key} is not a 32-char gateway key")

    errors.extend(evidence_errors(keys))

    if errors:
        print("Gateway key validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    wired = sum(1 for svc in ENKI_MICRO_SERVICES if svc.wired)
    print(f"OK — {wired} wired micro-services match their recorded APK call site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
