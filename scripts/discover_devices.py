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
sys.path.insert(0, str(ROOT / "custom_components"))

from enki.api import EnkiAPI  # noqa: E402
from enki.device_profile import profile_fingerprint, profile_to_export_dict  # noqa: E402


async def main(username: str, password: str, export: bool) -> None:
    api = EnkiAPI(username, password)
    await api.async_connect()
    await api.async_get_devices()

    profiles = [
        profile_to_export_dict(
            record,
            integration_version="dev",
            ha_version="n/a",
        )
        for record in api.discovery_records
    ]

    if export:
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
