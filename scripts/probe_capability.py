#!/usr/bin/env python3
"""Ask one capability route whether it answers, on your own devices.

The referentiel advertises capabilities the app never calls, and a capability's
name and its route's name do not always match — the doorbell advertises
``check_videophone_media_events`` while the app calls ``check-videophone-events``
(#233). So "does this read work on your device" is not answerable from the app's
code alone, and it is the question behind most capability-gap reports.

This asks. It signs in, walks your devices and calls one capability read through
the integration's own transport, so the service key, the path prefix and the
path derived from the capability name are exactly the ones the integration would
use. Whatever comes back is what the integration would see.

**Read-only.** It only ever issues GETs, and nothing it prints identifies you:
ids and opaque values are masked the way diagnostics are.

Usage:
    # a capability the catalogue already routes
    python3 scripts/probe_capability.py '<email>' '<password>' check_child_lock

    # a capability the catalogue does not route: name the service yourself
    python3 scripts/probe_capability.py '<email>' '<password>' \
        check_thermostat_running_state --service thermostat

    # one device only, by node id
    python3 scripts/probe_capability.py '<email>' '<password>' check_child_lock --node abc123
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enki_bootstrap import bootstrap_api_client, load_module  # noqa: E402

client_mod = bootstrap_api_client()
routes_mod = load_module("enki.api.capability_routes_data")
registry_mod = load_module("enki.api.gateway_registry")
report_mod = load_module("enki.lib.request_report")
exceptions_mod = load_module("enki.exceptions")

EnkiAPI = client_mod.EnkiAPI
CAPABILITY_ROUTES = routes_mod.CAPABILITY_ROUTES
SLUG_TO_CONST_KEY = registry_mod.SLUG_TO_CONST_KEY
WIRED_PATH_PREFIXES = registry_mod.WIRED_PATH_PREFIXES
ENKI_MICRO_SERVICES = registry_mod.ENKI_MICRO_SERVICES
anonymize = report_mod.anonymize
EnkiConnectionError = exceptions_mod.EnkiConnectionError


def services_for(capability: str) -> list[str]:
    """The wired services the catalogue says serve this capability."""
    slugs = CAPABILITY_ROUTES.get(capability, {})
    by_slug = {svc.slug: svc for svc in ENKI_MICRO_SERVICES}
    found = []
    for slug in slugs:
        service = by_slug.get(slug)
        if service is not None and service.wired and service.transport_id:
            found.append(service.transport_id)
    return found


async def probe(
    username: str,
    password: str,
    capability: str,
    service: str | None,
    node: str | None,
) -> None:
    candidates = [service] if service else services_for(capability)
    if not candidates:
        print(f"No wired service routes {capability}.")
        print("Pass --service <alias> to try one anyway, e.g. --service thermostat.")
        print(f"Known aliases: {', '.join(sorted(WIRED_PATH_PREFIXES))}")
        return

    api = EnkiAPI(username, password)
    await api.async_connect()
    http = await api._get_http()
    try:
        devices = await api.async_get_devices()
        if node:
            devices = [d for d in devices if d.node_id == node]
        if not devices:
            print("No matching device on this account.")
            return

        for device in devices:
            for alias in candidates:
                print(f"\n{device.device_name} ({device.device_type}) via {alias}")
                advertised = capability in (device.capabilities or ())
                print(f"  referentiel advertises it: {'yes' if advertised else 'no'}")
                try:
                    payload: Any = await http.capability_get(
                        alias, device.home_id, device.node_id, capability
                    )
                except EnkiConnectionError as err:
                    print(f"  refused: {err}")
                    continue
                if not payload:
                    # 404, 204 or an empty body all arrive here as {}.
                    print("  nothing: not found, no content, or no key for that service")
                    continue
                print(f"  answered: {json.dumps(anonymize(payload), indent=2, default=str)}")
    finally:
        await api.async_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("capability", help="e.g. check_thermostat_running_state")
    parser.add_argument(
        "--service",
        help="Transport alias to ask, when the catalogue routes the capability nowhere",
    )
    parser.add_argument("--node", help="Only this node id")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(probe(args.username, args.password, args.capability, args.service, args.node))
