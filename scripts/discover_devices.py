#!/usr/bin/env python3
"""Discover Enki devices and print anonymized API metadata.

Usage:
    python3 scripts/discover_devices.py <email> <password>
    python3 scripts/discover_devices.py <email> <password> --export
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enki_bootstrap import bootstrap_api_client, load_module  # noqa: E402

client_mod = bootstrap_api_client()
profile_mod = load_module("enki.domain.profile")
enrichment_mod = load_module("enki.domain.telemetry_enrichment")
EnkiAPI = client_mod.EnkiAPI
profile_fingerprint = profile_mod.profile_fingerprint
profile_to_export_dict = profile_mod.profile_to_export_dict
enrich_telemetry_export = enrichment_mod.enrich_telemetry_export


async def main(username: str, password: str, export_json: bool) -> None:
    api = EnkiAPI(username, password)
    await api.async_connect()
    await api.async_get_devices()

    profiles = []
    for record in api.discovery_records:
        profile_export = profile_to_export_dict(
            record,
            integration_version="dev",
            ha_version="n/a",
        )
        fingerprint = profile_fingerprint(profile_export)
        profiles.append(
            enrich_telemetry_export(
                profile_export,
                record,
                api_read_errors=api.read_errors_for_fingerprint(fingerprint) or None,
                last_poll_state=api.poll_state_for_fingerprint(fingerprint) or None,
            )
        )

    if export_json:
        print(json.dumps(profiles, indent=2, sort_keys=True))
    else:
        for profile in profiles:
            profile["fingerprint"] = profile_fingerprint(profile)
            print(json.dumps(profile, indent=2, sort_keys=True))
            print("---")

    await api.async_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover Enki devices")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument(
        "--export",
        action="store_true",
        help="Output a single JSON array (anonymized profiles)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.username, args.password, args.export))
