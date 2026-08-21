#!/usr/bin/env python3
"""Report Enki capabilities the app exposes but the integration doesn't handle.

Cross-references the APK-derived route catalog (every capability the Enki app can
call) with what the integration actually covers (reads, entity probes, and the
intentionally-ignored / not-planned lists). Whatever's left is an auto-discovered
gap — a capability the app supports that we don't, with its service, route, and
whether that gateway service is already wired.

Usage:
    python scripts/capability_coverage.py            # human report
    python scripts/capability_coverage.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from enki_bootstrap import bootstrap, load_module  # noqa: E402

bootstrap(
    "enki.api.capability_routes_data",
    "enki.api.capability_routing",
    "enki.api.gateway_registry",
    "enki.domain.telemetry_coverage",
    "enki.domain.telemetry_enrichment",
)
routes_mod = load_module("enki.api.capability_routes_data")
routing_mod = load_module("enki.api.capability_routing")
coverage_mod = load_module("enki.domain.telemetry_coverage")
enrich_mod = load_module("enki.domain.telemetry_enrichment")

CAPABILITY_ROUTES = routes_mod.CAPABILITY_ROUTES
capability_routing_hints = enrich_mod.capability_routing_hints

# Lifecycle / admin verbs we will never expose as entities — reported as a count only.
_ADMIN_PREFIXES = (
    "pair",
    "finish",
    "start",
    "remove",
    "delete",
    "execute",
    "update",
    "ack",
    "send",
    "format",
    "wake",
    "reset",
    "reboot",
    "provision",
    "onboard",
)


def _handled_capabilities() -> set[str]:
    handled = set(coverage_mod._CAPABILITY_PROBES)
    handled |= set(coverage_mod._TELEMETRY_IGNORED_CAPABILITIES)
    handled |= set(coverage_mod.NOT_PLANNED_CAPABILITIES)
    handled |= {read.capability for read in routing_mod.CAPABILITY_READS}
    return handled


def _bucket(capability: str) -> str:
    if capability.startswith("check_"):
        return "reads"
    if capability.startswith(("change_", "switch_", "activate_", "set_")):
        return "controls"
    if capability.startswith(_ADMIN_PREFIXES):
        return "admin"
    return "other"


def analyze() -> dict[str, list[str]]:
    catalog = set(CAPABILITY_ROUTES)
    unhandled = sorted(catalog - _handled_capabilities())
    buckets: dict[str, list[str]] = {"reads": [], "controls": [], "admin": [], "other": []}
    for capability in unhandled:
        buckets[_bucket(capability)].append(capability)
    return buckets


def _describe(capability: str) -> str:
    hint = capability_routing_hints([capability])[capability]
    services = hint["services"]
    if not services:
        return f"  {capability}  → (no direct route)"
    parts = [f"{s['service']} {'[wired]' if s['wired'] else '[not wired]'}" for s in services]
    return f"  {capability}  → {', '.join(parts)}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    buckets = analyze()

    if args.json:
        print(json.dumps(buckets, indent=2))
        return 0

    catalog = len(CAPABILITY_ROUTES)
    total_unhandled = sum(len(v) for v in buckets.values())
    print(f"APK catalog capabilities: {catalog}")
    print(f"Unhandled by the integration: {total_unhandled}\n")

    print(f"== Unhandled reads (candidate sensors) — {len(buckets['reads'])} ==")
    for capability in buckets["reads"]:
        print(_describe(capability))

    print(f"\n== Unhandled controls (candidate switches/selects) — {len(buckets['controls'])} ==")
    for capability in buckets["controls"]:
        print(_describe(capability))

    print(f"\n== Other unhandled (non-admin) — {len(buckets['other'])} ==")
    for capability in buckets["other"]:
        print(_describe(capability))

    print(f"\n== Admin / lifecycle (not planned) — {len(buckets['admin'])} ==")
    print("  " + ", ".join(buckets["admin"]) if buckets["admin"] else "  (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
