#!/usr/bin/env python3
"""Watch a Lexman doorbell's WebRTC negotiation while the app opens the live view (#259).

The doorbell service carries the three reads a WebRTC session needs::

    GET videophone/{nodeId}/check-turn-info             ICE/TURN servers
    GET videophone/{nodeId}/check-sdp-candidates-info   offer, answer, candidates

What they hold at rest says nothing. What they hold *while the Enki app has the
live view open* is the whole sequence: who offers, when the answer lands, how the
candidates trickle in. The app can open the stream at any time, with nobody at
the door, so this needs no choreography — start the script, open the live view,
watch the lines appear.

**Read-only.** It never posts an offer, never answers, never touches
``change-sdp-candidates-info``. It polls the two reads and prints each time their
content changes.

Output is anonymized the same way ``probe_camera.py`` does it: ids, tokens and
opaque values are masked, so the *shape* and the order survive and the secrets do
not. TURN credentials and the SDP's host addresses are redacted — the sequence is
what matters here, not the values.

Usage:
    python3 scripts/probe_videophone_live.py '<email>' '<password>'
    python3 scripts/probe_videophone_live.py '<email>' '<password>' --seconds 180
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
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
VIDEOPHONE_KEY = keys_mod.ENKI_VIDEOPHONE_API_KEY
anonymize = report_mod.anonymize
mask_ids = report_mod.mask_ids

PREFIX = "/api-enki-videophone-prod/v1/videophone"
WATCHED = {
    "turn-info": f"{PREFIX}/{{node_id}}/check-turn-info",
    "sdp-candidates": f"{PREFIX}/{{node_id}}/check-sdp-candidates-info",
}
# An SDP carries host addresses and fingerprints. Only its shape is wanted here.
SDP_KEYS = ("sdp", "offer", "answer", "candidate", "candidates")


def _summarize_sdp(value: Any) -> Any:
    """Keep what an SDP says it is — its lines' types — and drop its contents."""
    if not isinstance(value, str) or "=" not in value:
        return mask_ids(value) if isinstance(value, str) else value
    kinds: list[str] = []
    for line in value.splitlines():
        head, _, rest = line.partition("=")
        if head == "m":
            kinds.append(f"m={rest.split(' ')[0]}")
        elif head and head not in {k.split("=")[0] for k in kinds}:
            kinds.append(head)
    return f"<sdp {len(value)} chars: {' '.join(kinds)}>"


def _scrub(payload: Any) -> Any:
    """Flatten SDP blobs to their shape, before the anonymiser redacts them whole."""
    if isinstance(payload, dict):
        return {
            key: _summarize_sdp(value) if key in SDP_KEYS else _scrub(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_scrub(item) for item in payload]
    return payload


async def _get(http: Any, home_id: str, path: str) -> tuple[int, Any]:
    await http.ensure_token()
    headers = http._auth.auth_headers(
        {
            "User-Agent": ENKI_USER_AGENT,
            "Accept": "application/json",
            "X-Correlation-Id": f"iOS_{uuid.uuid4().hex.upper()}",
            "X-Gateway-APIKey": VIDEOPHONE_KEY,
            "homeId": home_id,
        }
    )
    async with http.session.get(f"{ENKI_BASE_URL}{path}", headers=headers) as response:
        body = (await response.text()).strip()
        try:
            # Summarise before anonymising: `anonymize` redacts a long string
            # outright, which threw away the one thing an SDP is read for.
            parsed = anonymize(_scrub(json.loads(body))) if body else None
        except json.JSONDecodeError:
            parsed = mask_ids(body[:300])
        return response.status, parsed


async def _find_doorbells(http: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for home_id in await http.get_homes():
        dashboard = await http.get_dashboard(home_id)
        sections = dashboard.get("sections", []) if isinstance(dashboard, dict) else []
        for section in sections:
            for item in section.get("items", []) if isinstance(section, dict) else []:
                metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
                if metadata.get("deviceType") == "videophones" and metadata.get("nodeId"):
                    found.append((home_id, metadata["nodeId"]))
    return found


async def watch(username: str, password: str, seconds: float, interval: float) -> None:
    api = EnkiAPI(username, password)
    await api.async_connect()
    http = await api._get_http()
    try:
        doorbells = await _find_doorbells(http)
        if not doorbells:
            print("Nothing on the dashboard with deviceType == 'videophones'.")
            return

        home_id, node_id = doorbells[0]
        print(f"Watching 1 of {len(doorbells)} doorbell(s) for {seconds:.0f}s.")
        print("Open the live view in the Enki app now — a ring is not needed.\n")

        last: dict[str, Any] = {}
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            for label, template in WATCHED.items():
                status, payload = await _get(http, home_id, template.format(node_id=node_id))
                current = (status, json.dumps(payload, sort_keys=True, default=str))
                if current == last.get(label):
                    continue
                last[label] = current
                elapsed = time.monotonic() - started
                print(f"[{elapsed:6.1f}s] {label} HTTP {status}")
                print(f"          {json.dumps(payload, indent=2, default=str)}\n")
            await asyncio.sleep(interval)

        print("Done. Nothing was written: these are both read routes.")
    finally:
        await api.async_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument(
        "--seconds", type=float, default=120.0, help="How long to watch (default: 120)"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Seconds between polls (default: 1)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(watch(args.username, args.password, args.seconds, args.interval))
