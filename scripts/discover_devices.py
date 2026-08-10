#!/usr/bin/env python3
"""Discover Enki devices and print anonymized API metadata.

Usage:
    python3 scripts/discover_devices.py <email> <password>
    python3 scripts/discover_devices.py <email> <password> --export
    python3 scripts/discover_devices.py <email> <password> --raw
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


async def dump_raw(username: str, password: str) -> None:
    """Print the shape of the homes + dashboard responses (keys/counts only, no ids).

    Helps diagnose empty discovery: shows whether homes are returned and whether
    the dashboard actually carries device items, without leaking any identifiers.
    """
    api = EnkiAPI(username, password)
    await api.async_connect()
    http = await api._get_http()

    homes = await http.get_homes()
    print(f"homes: {len(homes)}")
    for index, home_id in enumerate(homes):
        dashboard = await http.get_dashboard(home_id)
        sections = dashboard.get("sections", []) if isinstance(dashboard, dict) else []
        print(f"home[{index}]: dashboard_keys={sorted(dashboard)} sections={len(sections)}")
        for s_index, section in enumerate(sections):
            items = section.get("items", []) if isinstance(section, dict) else []
            print(f"  section[{s_index}]: keys={sorted(section)} items={len(items)}")
            for item in items:
                metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
                print(
                    f"    item: keys={sorted(item)} "
                    f"metadata_keys={sorted(metadata)} deviceType={metadata.get('deviceType')!r}"
                )
    await api.async_close()


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
                api_read_reports=api.read_reports_for_fingerprint(fingerprint) or None,
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
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Dump the homes + dashboard shape (keys/counts only) to debug empty discovery",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.raw:
        asyncio.run(dump_raw(args.username, args.password))
    else:
        asyncio.run(main(args.username, args.password, args.export))
