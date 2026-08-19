#!/usr/bin/env python3
"""Intelligent, read-only sweep of every Enki camera on the account.

For each camera found on the dashboard it:
  1. identifies it (manufacturer / model / referentiel type + i18n key) so a
     Lexman camera is easy to tell apart from a Google Nest one;
  2. for each ``check_*`` capability the device actually advertises, looks the
     endpoint up in the APK route catalog and calls the *exact* route on the
     *exact* micro-service, with that service's shipped gateway key;
  3. prints the HTTP status and an anonymized body (including the gateway's
     rejection reason on 4xx/5xx), then a per-camera summary of which service —
     if any — authorized the reads.

It never touches write / delete / pairing / stream (connect-wss) endpoints.
Output is anonymized: urls, ids, tokens, serials and long/opaque values are
redacted, so only the response *shape* and status codes are shown.

Usage:
    python3 scripts/probe_camera.py '<email>' '<password>'
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enki_bootstrap import bootstrap_api_client, load_module  # noqa: E402

client_mod = bootstrap_api_client()
const_mod = load_module("enki.const")
keys_mod = load_module("enki.gateway_keys_data")
registry_mod = load_module("enki.api.gateway_registry")
routes_mod = load_module("enki.api.capability_routes_data")
report_mod = load_module("enki.lib.request_report")

EnkiAPI = client_mod.EnkiAPI
ENKI_BASE_URL = const_mod.ENKI_BASE_URL
ENKI_USER_AGENT = const_mod.ENKI_USER_AGENT
CAPABILITY_ROUTES = routes_mod.CAPABILITY_ROUTES
SLUG_TO_CONST_KEY = registry_mod.SLUG_TO_CONST_KEY
anonymize = report_mod.anonymize
mask_ids = report_mod.mask_ids

# Stream/session endpoints hand back signed URLs or tokens — never probe them.
_SKIP_CAPABILITIES = {"check_camera_connect_wss"}

# Capabilities whose APK Retrofit signature declares a required @Query("day").
# Omitting it returns HTTP 400; the exact date format isn't obvious from the
# APK, so we try a few and let the 200 tell us which one the API wants.
_DAY_QUERY_CAPS = frozenset({"check_camera_events"})


def _day_formats(day: str) -> list[str]:
    try:
        parsed = date.fromisoformat(day)
    except ValueError:
        return [day]
    return [
        parsed.isoformat(),  # 2026-08-09
        parsed.strftime("%Y%m%d"),  # 20260809
        parsed.strftime("%Y/%m/%d"),  # 2026/08/09
        parsed.strftime("%d-%m-%Y"),  # 09-08-2026
        parsed.strftime("%d/%m/%Y"),  # 09/08/2026
    ]


async def _get(http: Any, home_id: str, path: str, api_key: str) -> tuple[int, Any]:
    await http.ensure_token()
    headers = http._auth.auth_headers(
        {
            "User-Agent": ENKI_USER_AGENT,
            "Accept": "application/json",
            "X-Correlation-Id": f"iOS_{uuid.uuid4().hex.upper()}",
            "X-Gateway-APIKey": api_key,
            "homeId": home_id,
        }
    )
    async with http.session.get(f"{ENKI_BASE_URL}{path}", headers=headers) as response:
        body = (await response.text()).strip()
        try:
            parsed = anonymize(json.loads(body)) if body else None
        except json.JSONDecodeError:
            parsed = mask_ids(body[:300])
        return response.status, parsed


async def _identify(http: Any, home_id: str, node_id: str, device_id: str) -> dict[str, Any]:
    node_info: dict[str, Any] = {}
    device_info: dict[str, Any] = {}
    # Identification is best-effort: a missing node/referentiel must not stop the sweep.
    with contextlib.suppress(Exception):
        node_info = await http.get_node(home_id, node_id)
    with contextlib.suppress(Exception):
        device_info = await http.get_referentiel_device(device_id)
    return {
        "manufacturer": node_info.get("manufacturerId")
        or device_info.get("manufacturerId")
        or device_info.get("manufacturer")
        or "unknown",
        "model": node_info.get("model") or device_info.get("model") or "?",
        "type": device_info.get("type") or "cameras",
        "i18n": device_info.get("i18n") or "?",
        "capabilities": device_info.get("capabilities", []) or [],
    }


async def _probe_camera(
    http: Any, home_id: str, node_id: str, info: dict[str, Any], day: str
) -> None:
    print(f"    manufacturer={info['manufacturer']!r} model={info['model']!r}")
    print(f"    type={info['type']!r} i18n={info['i18n']!r}")

    # Also try check-camera-status even if the referentiel doesn't advertise it:
    # it needs no day param and would expose SD-card / connection state.
    advertised = {
        cap
        for cap in info["capabilities"]
        if cap.startswith("check_") and cap not in _SKIP_CAPABILITIES
    }
    read_caps = sorted(advertised | {"check_camera_status"})
    if not read_caps:
        print("    no readable check_* capabilities advertised")
        return

    authorized: set[str] = set()
    rejected: set[str] = set()
    for cap in read_caps:
        routes = CAPABILITY_ROUTES.get(cap)
        if not routes:
            print(f"    {cap}: no APK route (derived server-side or renamed)")
            continue
        for slug, path in sorted(routes.items()):
            api_key = getattr(keys_mod, SLUG_TO_CONST_KEY.get(slug, ""), "")
            if not api_key:
                print(f"    {cap} [{slug}]: no gateway key shipped")
                continue
            base_path = path.replace("{nodeId}", node_id)
            if cap in _DAY_QUERY_CAPS:
                attempts = [
                    (f" day={fmt}", f"{base_path}?{urlencode({'day': fmt})}")
                    for fmt in _day_formats(day)
                ]
            else:
                attempts = [("", base_path)]
            for label, full_path in attempts:
                try:
                    status, parsed = await _get(http, home_id, full_path, api_key)
                except Exception as err:  # noqa: BLE001 - report, never crash the sweep
                    print(f"    {cap} [{slug}]{label}: ERROR {type(err).__name__}: {err}")
                    continue
                # Show the body for any status — a 4xx reason is the whole point.
                suffix = f"  {json.dumps(parsed)}" if parsed is not None else ""
                print(f"    {cap} [{slug}]{label}: HTTP {status}{suffix}")
                (authorized if status == 200 else rejected).add(slug)

    if authorized:
        print(f"    => authorized service(s): {', '.join(sorted(authorized))}")
    elif rejected:
        print(f"    => all reads rejected (services tried: {', '.join(sorted(rejected))})")


async def sweep(username: str, password: str, day: str) -> None:
    api = EnkiAPI(username, password)
    await api.async_connect()
    http = await api._get_http()

    index = 0
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
                print(f"=== camera #{index} ===")
                info = await _identify(http, home_id, node_id, device_id)
                await _probe_camera(http, home_id, node_id, info, day)
                index += 1

    if index == 0:
        print("No camera found on the dashboard (deviceType == 'cameras').")

    await api.async_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Intelligent read-only Enki camera sweep")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument(
        "--day",
        default=date.today().isoformat(),
        help="Day (YYYY-MM-DD) for check-camera-events; defaults to today",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(sweep(args.username, args.password, args.day))
