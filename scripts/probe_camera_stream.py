#!/usr/bin/env python3
"""Probe the Lexman camera live-video path (meari WebRTC signaling over WSS).

The Enki app does not stream Lexman cameras over RTSP or HLS: it opens a
WebSocket to the meari signaling server returned by ``check-camera-connect-wss``
and runs a plain WebRTC handshake over it (``option`` -> ``offer`` -> ``answer``
-> ``candidate``), then asks for the live stream with a ``settings``/``preview``
message. Media is relayed by the coturn server the signaling server hands back.

This script replays that handshake to find out, per camera:

  1. which identifier — if any — the meari backend knows the camera by:
     ``check-camera-status`` is retried with every id the node payload carries
     (nodeId, deviceId, externalId, eui64, p2pId, mac), because a 404 on the
     dashboard nodeId can mean "not a meari camera" *or* "wrong key". That is the
     same lookup the ``change-*`` writes do, so it also explains their 404;
  2. whether ``check-camera-connect-wss`` hands back signaling credentials;
  3. (``--handshake``) whether the signaling server authenticates us and returns
     the coturn relay parameters;
  4. (``--offer``) whether the camera answers an SDP offer — i.e. whether a live
     stream is reachable without the app.

Steps 1 and 2 are read-only. ``--handshake`` and ``--offer`` open a signaling
session exactly like the app does (a battery camera wakes up, as it would if you
opened the live view in the app); nothing is written or configured. ``--wake``
additionally POSTs ``wake-up`` first, which is what the app relies on for
dormant cameras.

Output is anonymized: urls, ids, tokens, SDP bodies and ICE candidates are
summarized or redacted — only shapes, statuses and error reasons are printed.

Usage:
    python3 scripts/probe_camera_stream.py '<email>' '<password>'
    python3 scripts/probe_camera_stream.py '<email>' '<password>' --handshake
    python3 scripts/probe_camera_stream.py '<email>' '<password>' --offer
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import secrets
import sys
import uuid
from pathlib import Path
from typing import Any

import aiohttp

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

# Signaling wire format, as sent by the app (kotlinx serial names).
_ACTION_REQUEST = "req"
_COMMAND = "mts"
_METHOD_OPTION = "option"
_METHOD_OFFER = "offer"
_METHOD_ANSWER = "answer"
_METHOD_CANDIDATE = "candidate"
_METHOD_SETTINGS = "settings"
_METHOD_PREVIEW = "preview"

# Errors the app treats as "the camera is asleep / unreachable", not as a bug.
_DORMANT_ERRORS = {
    "device awaken timeout",
    "device offline",
    "session not found",
    "device dormancy",
}


def _headers(http: Any, home_id: str) -> dict[str, str]:
    return http._auth.auth_headers(
        {
            "User-Agent": ENKI_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Correlation-Id": f"iOS_{uuid.uuid4().hex.upper()}",
            "X-Gateway-APIKey": MEARI_KEY,
            "homeId": home_id,
        }
    )


def _parse(body: str) -> Any:
    text = body.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return mask_ids(text[:300])


async def _get(http: Any, home_id: str, path: str) -> tuple[int, Any]:
    await http.ensure_token()
    url = f"{ENKI_BASE_URL}{path}"
    async with http.session.get(url, headers=_headers(http, home_id)) as response:
        return response.status, _parse(await response.text())


async def _post(http: Any, home_id: str, path: str) -> tuple[int, Any]:
    await http.ensure_token()
    url = f"{ENKI_BASE_URL}{path}"
    async with http.session.post(url, headers=_headers(http, home_id), json={}) as response:
        return response.status, _parse(await response.text())


def _synthetic_offer() -> str:
    """A syntactically valid offer shaped like the app's (audio sendrecv + video recvonly).

    The app offers with ``OfferToReceiveAudio``/``OfferToReceiveVideo`` plus a
    sendrecv audio transceiver (two-way talk). We never complete DTLS here — the
    point is only to see whether the camera answers.
    """
    ufrag = secrets.token_hex(4)
    pwd = secrets.token_hex(12)
    fingerprint = ":".join(f"{byte:02X}" for byte in secrets.token_bytes(32))
    common = [
        "c=IN IP4 0.0.0.0",
        "a=rtcp:9 IN IP4 0.0.0.0",
        f"a=ice-ufrag:{ufrag}",
        f"a=ice-pwd:{pwd}",
        "a=ice-options:trickle",
        f"a=fingerprint:sha-256 {fingerprint}",
        "a=setup:actpass",
        "a=rtcp-mux",
    ]
    lines = [
        "v=0",
        "o=- 4611731400430051336 2 IN IP4 127.0.0.1",
        "s=-",
        "t=0 0",
        "a=group:BUNDLE 0 1",
        "a=msid-semantic: WMS",
        "m=audio 9 UDP/TLS/RTP/SAVPF 111 8 0",
        *common,
        "a=mid:0",
        "a=sendrecv",
        "a=rtpmap:111 opus/48000/2",
        "a=fmtp:111 minptime=10;useinbandfec=1",
        "a=rtpmap:8 PCMA/8000",
        "a=rtpmap:0 PCMU/8000",
        "m=video 9 UDP/TLS/RTP/SAVPF 96",
        *common,
        "a=mid:1",
        "a=recvonly",
        "a=rtpmap:96 H264/90000",
        "a=fmtp:96 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f",
    ]
    return "\r\n".join(lines) + "\r\n"


def _summarize_sdp(sdp: str) -> str:
    """Describe an SDP without leaking ICE credentials, IPs or fingerprints."""
    kinds: list[str] = []
    directions: list[str] = []
    codecs: list[str] = []
    for line in sdp.splitlines():
        if line.startswith("m="):
            kinds.append(line[2:].split(" ", 1)[0])
        elif line in {"a=sendrecv", "a=recvonly", "a=sendonly", "a=inactive"}:
            directions.append(line[2:])
        elif line.startswith("a=rtpmap:"):
            with contextlib.suppress(IndexError):
                codecs.append(line.split(" ", 1)[1].split("/")[0])
    return (
        f"{len(sdp)} bytes, m-lines={kinds or '?'} directions={directions or '?'} "
        f"codecs={sorted(set(codecs)) or '?'}"
    )


def _describe(message: dict[str, Any]) -> str:
    """One line per signaling message, with payloads summarized instead of dumped."""
    method = message.get("method")
    params = message.get("params")
    params = params if isinstance(params, dict) else {}

    if "errid" in message:
        reason = message.get("errstr")
        dormant = " (camera asleep / unreachable)" if reason in _DORMANT_ERRORS else ""
        desc = f" desc={message.get('desc')!r}" if message.get("desc") else ""
        return f"exception errid={message.get('errid')} errstr={reason!r}{desc}{dormant}"

    if method == _METHOD_OPTION:
        got = [key for key in ("coturn_host", "coturn_ip", "coturn_port") if params.get(key)]
        creds = all(params.get(key) for key in ("username", "pwd"))
        return f"option (auth OK) coturn={got or 'missing'} credentials={'yes' if creds else 'no'}"

    if method == _METHOD_ANSWER:
        sdp = params.get("sdp")
        return f"answer  {_summarize_sdp(sdp) if isinstance(sdp, str) else 'no sdp!'}"

    if method == _METHOD_CANDIDATE:
        candidate = params.get("candidate")
        candidate = candidate if isinstance(candidate, dict) else {}
        raw = candidate.get("candidate", "")
        kind = raw.split(" typ ", 1)[1].split(" ", 1)[0] if " typ " in raw else "?"
        return f"candidate typ={kind} mid={candidate.get('sdpMid')!r}"

    return f"{method!r} {json.dumps(anonymize(message))[:200]}"


async def _signaling(http: Any, connect: dict[str, Any], send_offer: bool, timeout: float) -> None:
    """Replay the app's signaling session: auth, then optionally an SDP offer."""
    session_id = str(uuid.uuid4()).upper()
    caller = uuid.uuid4().hex[:16]
    callee = connect.get("callee") or ""
    device_code = connect.get("deviceCode") or ""
    url = connect.get("webSocketServerUrl") or ""

    auth = {
        "sid": session_id,
        "method": _METHOD_OPTION,
        "action": _ACTION_REQUEST,
        "cmd": _COMMAND,
        "auth": {
            "accessId": connect.get("accessId"),
            "signature": connect.get("signature"),
            "token": connect.get("token"),
        },
        "params": {
            "caller": caller,
            "callee": callee,
            "devicecode": device_code,
            "expires": connect.get("expires"),
            "continent": "Europe",
            "country": "France",
        },
    }

    print("    opening signaling websocket…")
    async with http.session.ws_connect(url, heartbeat=30) as websocket:
        await websocket.send_str(json.dumps(auth))
        print(f"    -> {_METHOD_OPTION} (authentication)")

        authenticated = False
        offered = False
        answered = False
        deadline = asyncio.get_running_loop().time() + timeout
        while (remaining := deadline - asyncio.get_running_loop().time()) > 0:
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=remaining)
            except TimeoutError:
                break
            if message.type is not aiohttp.WSMsgType.TEXT:
                print(f"    <- websocket {message.type.name}")
                break
            payload = _parse(message.data)
            if not isinstance(payload, dict):
                print(f"    <- non-JSON frame: {payload}")
                continue
            print(f"    <- {_describe(payload)}")

            method = payload.get("method")
            if method == _METHOD_OPTION and not authenticated:
                authenticated = True
                if not send_offer:
                    break
            if method == _METHOD_ANSWER:
                answered = True
            if authenticated and send_offer and not offered:
                offered = True
                offer = {
                    "sid": session_id,
                    "method": _METHOD_OFFER,
                    "action": _ACTION_REQUEST,
                    "cmd": _COMMAND,
                    "params": {
                        "caller": caller,
                        "callee": callee,
                        "devicecode": device_code,
                        "sdp": _synthetic_offer(),
                        "settings": {"method": _METHOD_PREVIEW},
                    },
                }
                await websocket.send_str(json.dumps(offer))
                print(f"    -> {_METHOD_OFFER} (synthetic SDP, audio sendrecv + video recvonly)")
            if answered:
                preview = {
                    "sid": session_id,
                    "method": _METHOD_SETTINGS,
                    "action": _ACTION_REQUEST,
                    "cmd": _COMMAND,
                    "params": {
                        "caller": caller,
                        "callee": callee,
                        "settings": {
                            "sid": session_id,
                            "method": _METHOD_PREVIEW,
                            "streams": [{"channel": 0, "stream": 1, "stop": 0}],
                        },
                    },
                }
                await websocket.send_str(json.dumps(preview))
                print(f"    -> {_METHOD_SETTINGS}/{_METHOD_PREVIEW} (start live stream)")
                answered = False

        if not authenticated:
            print("    signaling: no 'option' response — authentication refused or timed out")
        elif send_offer and not offered:
            print("    signaling: authenticated but never reached the offer")


async def _node(http: Any, home_id: str, node_id: str) -> dict[str, Any]:
    try:
        node = await http.get_node(home_id, node_id)
    except Exception as err:  # noqa: BLE001 - report, never crash the sweep
        print(f"    node payload unavailable ({type(err).__name__})")
        return {}
    return node if isinstance(node, dict) else {}


def _generation(node: dict[str, Any]) -> str:
    """Tell the two camera generations apart from the node payload.

    A node carrying ``p2pId`` / ``p2pAuthKey`` / ``p2pPassword`` is driven by the
    native TUTK Kalay SDK — no meari signaling, so no live stream reachable from
    here. Only the presence of the keys is printed, never their values.
    """
    if not node:
        return "unknown"
    present = [key for key in ("p2pId", "p2pAuthKey", "p2pPassword") if node.get(key)]
    if present:
        return f"TUTK Kalay P2P — node carries {present} (native SDK only)"
    return "no TUTK credentials on the node (meari candidate)"


def _id_candidates(node: dict[str, Any], node_id: str, device_id: str) -> list[tuple[str, str]]:
    """Every id the meari routes could be keyed on, dashboard nodeId first.

    A 404 on every meari route can mean "not a meari camera" *or* "right camera,
    wrong identifier" — the app builds its paths from its own node model, and the
    ids in the node payload (externalId, eui64, p2pId…) are all plausible keys.
    """
    seen = {""}
    candidates: list[tuple[str, str]] = []
    sources = [
        ("nodeId", node_id),
        ("deviceId", device_id),
        ("node.id", str(node.get("id") or "")),
        ("node.deviceId", str(node.get("deviceId") or "")),
        ("node.externalId", str(node.get("externalId") or "")),
        ("node.eui64", str(node.get("eui64") or "")),
        ("node.p2pId", str(node.get("p2pId") or "")),
        ("node.macAddress", str(node.get("macAddress") or "").replace(":", "")),
    ]
    for label, value in sources:
        if value not in seen:
            seen.add(value)
            candidates.append((label, value))
    return candidates


async def _meari_id(
    http: Any, home_id: str, candidates: list[tuple[str, str]]
) -> tuple[str, Any] | None:
    """Find which identifier — if any — the meari backend knows this camera by."""
    for label, value in candidates:
        status, body = await _get(http, home_id, f"{_MEARI_PREFIX}/{value}/check-camera-status")
        print(f"    GET check-camera-status [{label}]: HTTP {status} {json.dumps(anonymize(body))}")
        if status == 200:
            return value, body
        if status not in (400, 404):
            # 401/403 is an auth problem, not an unknown camera — stop guessing.
            return None
    return None


async def _probe_camera(
    http: Any,
    home_id: str,
    node_id: str,
    device_id: str,
    caps: list[str],
    handshake: bool,
    send_offer: bool,
    wake: bool,
    timeout: float,
) -> None:
    print(f"    referentiel capabilities = {sorted(caps)}")
    node = await _node(http, home_id, node_id)
    print(f"    node generation: {_generation(node)}")

    if wake:
        status, body = await _post(http, home_id, f"{_MEARI_PREFIX}/{node_id}/wake-up")
        print(f"    POST wake-up: HTTP {status} {json.dumps(anonymize(body))}")

    found = await _meari_id(http, home_id, _id_candidates(node, node_id, device_id))
    if found is None:
        print(
            "    -> no identifier is known to the meari backend: every meari write "
            "(change-*) and the live stream 404 the same way"
        )
        return
    node_id, _ = found

    status, body = await _get(http, home_id, f"{_MEARI_PREFIX}/{node_id}/check-camera-connect-wss")
    if status != 200 or not isinstance(body, dict):
        print(f"    GET check-camera-connect-wss: HTTP {status} {json.dumps(anonymize(body))}")
        return

    expected = (
        "webSocketServerUrl",
        "accessId",
        "signature",
        "token",
        "expires",
        "callee",
        "deviceCode",
    )
    missing = [key for key in expected if not body.get(key)]
    scheme = str(body.get("webSocketServerUrl", "")).split("://", 1)[0]
    print(
        f"    GET check-camera-connect-wss: HTTP 200 scheme={scheme!r} "
        f"fields={'complete' if not missing else f'missing {missing}'}"
    )

    if not handshake:
        print("    (re-run with --handshake to authenticate against the signaling server)")
        return
    if missing:
        print("    skipping handshake: incomplete signaling credentials")
        return

    try:
        await _signaling(http, body, send_offer, timeout)
    except Exception as err:  # noqa: BLE001 - report, never crash the sweep
        print(f"    signaling ERROR {type(err).__name__}: {err}")


async def sweep(
    username: str,
    password: str,
    handshake: bool,
    send_offer: bool,
    wake: bool,
    timeout: float,
) -> None:
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
                caps: list[str] = []
                with contextlib.suppress(Exception):
                    device = await http.get_referentiel_device(device_id)
                    caps = device.get("capabilities", []) or []
                print(f"=== camera #{index} ===")
                await _probe_camera(
                    http,
                    home_id,
                    node_id,
                    device_id,
                    caps,
                    handshake,
                    send_offer,
                    wake,
                    timeout,
                )
                index += 1

    if index == 0:
        print("No camera found on the dashboard (deviceType == 'cameras').")

    await api.async_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe the Lexman camera live-video path")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument(
        "--handshake",
        action="store_true",
        help="Open the signaling websocket and authenticate (wakes the camera, like the app)",
    )
    parser.add_argument(
        "--offer",
        action="store_true",
        help="Also send an SDP offer and report the camera's answer (implies --handshake)",
    )
    parser.add_argument(
        "--wake",
        action="store_true",
        help="POST wake-up before reading, for cameras that sleep between events",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=25.0,
        help="Seconds to wait for signaling messages (default: 25)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        sweep(
            args.username,
            args.password,
            args.handshake or args.offer,
            args.offer,
            args.wake,
            args.timeout,
        )
    )
