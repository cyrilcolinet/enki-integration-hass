#!/usr/bin/env python3
"""Probe Enki mobile-config and document how to obtain missing gateway keys.

The Enki app calls GET /api-enki-mobile-config-prod/v1/settings (not config/app/).
That endpoint returns app version flags (minIOSVersion, maintenance, …) — it does
**not** expose X-Gateway-APIKey values for heating, water leak, or rolling.

For missing keys (ENKI_HEATING_API_KEY, ENKI_WATER_SENSOR_API_KEY,
ENKI_ACCESS_MOTORIZATION_API_KEY), use mitmproxy — see docs/BETA_VOLETS_KEY.md —
or scan an APK with scripts/extract_gateway_keys.py.

Usage:
    python scripts/fetch_gateway_keys.py
    python scripts/fetch_gateway_keys.py --username your@email.com

Credentials are read interactively (password via getpass, not argv / shell history).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enki_bootstrap import bootstrap_fetch_keys, load_module  # noqa: E402

bootstrap_fetch_keys()

const = load_module("enki.const")
auth_mod = load_module("enki.api.auth")
gateway_keys_mod = load_module("enki.api.gateway_keys")
EnkiAuthSession = auth_mod.EnkiAuthSession
MOBILE_CONFIG_PATH = gateway_keys_mod.MOBILE_CONFIG_PATH
ENKI_BASE_URL = const.ENKI_BASE_URL
ENKI_MOBILE_CONFIG_API_KEY = const.ENKI_MOBILE_CONFIG_API_KEY

MISSING_KEYS = (
    "ENKI_HEATING_API_KEY",
    "ENKI_WATER_SENSOR_API_KEY",
    "ENKI_ACCESS_MOTORIZATION_API_KEY",
)


async def fetch_settings(username: str, password: str) -> dict:
    import aiohttp

    auth = EnkiAuthSession(username, password)
    async with aiohttp.ClientSession() as session:
        await auth.connect(session)
        url = f"{ENKI_BASE_URL}{MOBILE_CONFIG_PATH}"
        if not ENKI_MOBILE_CONFIG_API_KEY:
            raise RuntimeError("ENKI_MOBILE_CONFIG_API_KEY is empty in const.py")
        # App Retrofit interface bhg: only X-Gateway-APIKey (no Authorization).
        headers = {"X-Gateway-APIKey": ENKI_MOBILE_CONFIG_API_KEY}
        async with session.get(url, headers=headers) as response:
            body = await response.text()
            if response.status != 200:
                raise RuntimeError(
                    f"GET {MOBILE_CONFIG_PATH} failed: HTTP {response.status}\n{body[:500]}"
                )
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Non-JSON response from mobile-config: {exc}\n{body[:500]}"
                ) from exc
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"Unexpected mobile-config payload type: {type(payload)!r}"
                )
            return payload


def print_missing_key_help() -> None:
    empty = [key for key in MISSING_KEYS if not getattr(const, key, "")]
    if not empty:
        return
    print("\n=== Missing gateway keys (not in mobile-config) ===", file=sys.stderr)
    for key in empty:
        print(f"  - {key}", file=sys.stderr)
    print(
        "\nCapture X-Gateway-APIKey from the Enki app (mitmproxy): docs/BETA_VOLETS_KEY.md",
        file=sys.stderr,
    )
    print(
        "Or scan an APK: python scripts/extract_gateway_keys.py path/to/enki.apk",
        file=sys.stderr,
    )


def prompt_credentials(username: str | None) -> tuple[str, str]:
    """Ask for Enki login; password never read from argv."""
    email = (username or input("Enki e-mail: ")).strip()
    if not email:
        print("E-mail required.", file=sys.stderr)
        raise SystemExit(1)
    password = getpass.getpass("Enki password: ")
    if not password:
        print("Password required.", file=sys.stderr)
        raise SystemExit(1)
    return email, password


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Enki mobile-config settings (login interactive).",
    )
    parser.add_argument(
        "-u",
        "--username",
        help="Enki account e-mail (if omitted, prompted on stdin)",
    )
    args = parser.parse_args()

    username, password = prompt_credentials(args.username)

    try:
        payload = asyncio.run(fetch_settings(username, password))
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1
    finally:
        password = ""

    print(json.dumps(payload, indent=2, sort_keys=True))
    print(
        f"\n(mobile-config OK — endpoint {MOBILE_CONFIG_PATH}; no gateway keys here)",
        file=sys.stderr,
    )
    print_missing_key_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
