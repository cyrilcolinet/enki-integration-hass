#!/usr/bin/env python3
"""Test-write a single Lexman camera control (meari service) — one at a time.

The camera config endpoints are POST *writes* on api-enki-lexman-camera-meari-prod
and aren't advertised in every camera's referentiel, so this validates them one
by one before wiring entities. It changes camera settings, so it only ever sends
the command you pass explicitly — no defaults, and format-sd-card is not exposed.

Run `--list` first to see the safe commands and what your camera actually
advertises. Then try one, e.g.:

    python3 scripts/probe_camera_control.py '<email>' '<password>' \\
        --command night-vision --value AUTO

Output is anonymized (ids / urls / tokens redacted).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enki_bootstrap import bootstrap_api_client, load_module  # noqa: E402

client_mod = bootstrap_api_client()
const_mod = load_module("enki.const")
keys_mod = load_module("enki.gateway_keys_data")
report_mod = load_module("enki.lib.request_report")

EnkiAPI = client_mod.EnkiAPI
ENKI_BASE_URL = const_mod.ENKI_BASE_URL
ENKI_USER_AGENT = const_mod.ENKI_USER_AGENT
MEARI_KEY = keys_mod.ENKI_LEXMAN_CAMERA_MEARI_API_KEY
anonymize = report_mod.anonymize
mask_ids = report_mod.mask_ids

_MEARI_PREFIX = "/api-enki-lexman-camera-meari-prod/v1/camera"

# Reversible, non-destructive controls only. format-sd-card is deliberately absent.
_COMMANDS: dict[str, str] = {
    "night-vision": "change-night-vision-mode",
    "motion-detection": "change-motion-detection-mode",
    "motion-sensitivity": "change-motion-detection-sensitivity-level",
    "humanoid-sensitivity": "change-humanoid-detection-sensitivity-level",
    "indicator-light": "change-indicator-light-mode",
    "light-mode": "change-light-mode",
    "flip-screen": "change-flip-screen-mode",
    "recording-duration": "change-recording-duration",
}


def _coerce(value: str) -> Any:
    return int(value) if value.lstrip("-").isdigit() else value


async def _cameras(http: Any) -> list[tuple[str, str, list[str]]]:
    """Return (home_id, node_id, referentiel_capabilities) for each camera."""
    out: list[tuple[str, str, list[str]]] = []
    for home_id in await http.get_homes():
        dashboard = await http.get_dashboard(home_id)
        sections = dashboard.get("sections", []) if isinstance(dashboard, dict) else []
        for section in sections:
            for item in section.get("items", []) if isinstance(section, dict) else []:
                metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
                if metadata.get("deviceType") != "cameras":
                    continue
                node_id = metadata.get("nodeId")
                device_id = metadata.get("deviceId")
                if not node_id or not device_id:
                    continue
                caps: list[str] = []
                try:
                    dev = await http.get_referentiel_device(device_id)
                    caps = dev.get("capabilities", []) or []
                except Exception:  # noqa: BLE001 - best effort
                    pass
                out.append((home_id, node_id, caps))
    return out


async def _post(http: Any, home_id: str, path: str, body: dict[str, Any]) -> tuple[int, Any]:
    await http.ensure_token()
    headers = http._auth.auth_headers(
        {
            "User-Agent": ENKI_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Correlation-Id": f"iOS_{uuid.uuid4().hex.upper()}",
            "X-Gateway-APIKey": MEARI_KEY,
            "homeId": home_id,
        }
    )
    async with http.session.post(f"{ENKI_BASE_URL}{path}", headers=headers, json=body) as response:
        text = (await response.text()).strip()
        try:
            parsed = anonymize(json.loads(text)) if text else None
        except json.JSONDecodeError:
            parsed = mask_ids(text[:300])
        return response.status, parsed


async def run(username: str, password: str, command: str | None, value: str | None) -> None:
    api = EnkiAPI(username, password)
    await api.async_connect()
    http = await api._get_http()

    cameras = await _cameras(http)
    if not cameras:
        print("No camera found on the dashboard.")
        await api.async_close()
        return

    for index, (_home, _node, caps) in enumerate(cameras):
        advertised = sorted(c for c in caps if c.startswith(("change_", "check_")))
        print(f"camera #{index}: referentiel capabilities = {advertised or '(none)'}")

    if command is None:
        print("\nSafe commands (pass one with --command --value):")
        for name, segment in _COMMANDS.items():
            print(f"  {name:22} → {segment}")
        await api.async_close()
        return

    segment = _COMMANDS[command]
    body = {"value": _coerce(value)} if value is not None else {}
    for index, (home_id, node_id, _caps) in enumerate(cameras):
        path = f"{_MEARI_PREFIX}/{node_id}/{segment}"
        try:
            status, parsed = await _post(http, home_id, path, body)
        except Exception as err:  # noqa: BLE001 - report, never crash
            print(f"camera #{index} {segment}: ERROR {type(err).__name__}: {err}")
            continue
        suffix = f"  {json.dumps(parsed)}" if parsed is not None else ""
        print(f"camera #{index} {segment} value={body.get('value')!r}: HTTP {status}{suffix}")

    await api.async_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test one Lexman camera control write")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--command", choices=sorted(_COMMANDS), help="Control to test")
    parser.add_argument("--value", help="Value to send (e.g. AUTO, ON, OFF, or a number)")
    parser.add_argument("--list", action="store_true", help="List commands + camera capabilities")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    command = None if args.list else args.command
    asyncio.run(run(args.username, args.password, command, args.value))
