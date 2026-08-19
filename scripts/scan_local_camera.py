#!/usr/bin/env python3
"""Scan the local network for a camera exposing RTSP / ONVIF.

The Enki cloud live stream is TUTK Kalay P2P (native SDK, unreachable from
Python). But if the camera *also* serves a local RTSP/ONVIF stream, Home
Assistant can use it directly, bypassing Enki entirely. This script must run on
the same LAN as the camera (e.g. the Home Assistant OS box).

Steps:
  1. ONVIF WS-Discovery (UDP multicast) — cameras that answer are RTSP-capable.
  2. TCP scan of the local /24 for open RTSP ports (554, 8554).
  3. RTSP OPTIONS on every open port to confirm a real RTSP server.

No dependencies beyond the standard library.

Usage:
    python3 scripts/scan_local_camera.py
"""

from __future__ import annotations

import asyncio
import socket

WS_DISCOVERY_ADDR = ("239.255.255.250", 3702)
_PROBE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"'
    ' xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
    ' xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"'
    ' xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
    "<e:Header><w:MessageID>uuid:enki-scan-0001</w:MessageID>"
    '<w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
    '<w:Action e:mustUnderstand="true">'
    "http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>"
    "<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>"
    "</e:Envelope>"
)
RTSP_PORTS = (554, 8554)


def _local_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def onvif_discover(timeout: float = 3.0) -> list[str]:
    """Send a WS-Discovery probe; return XAddr service URLs that answer."""
    found: list[str] = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(timeout)
        sock.sendto(_PROBE.encode(), WS_DISCOVERY_ADDR)
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except TimeoutError:
                break
            text = data.decode("utf-8", "replace")
            for token in text.split("<"):
                if "XAddrs>" in token:
                    urls = token.split(">", 1)[-1].strip()
                    if urls:
                        found.append(f"{addr[0]} → {urls}")
    return found


async def check_rtsp(host: str, port: int, timeout: float = 1.0) -> str | None:
    """Return the RTSP OPTIONS status line if host:port speaks RTSP."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except (TimeoutError, OSError):
        return None
    try:
        writer.write(f"OPTIONS rtsp://{host}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode())
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    except (TimeoutError, OSError):
        return None
    finally:
        writer.close()
    text = line.decode("latin-1", "replace").strip()
    return text if text.startswith("RTSP/") else "(open, no RTSP banner)"


async def scan_subnet(prefix: str) -> list[str]:
    """Probe every host in prefix.1-254 on the RTSP ports."""

    async def one(host: str, port: int) -> str | None:
        banner = await check_rtsp(host, port)
        return f"{host}:{port}  {banner}" if banner else None

    tasks = [one(f"{prefix}.{i}", port) for i in range(1, 255) for port in RTSP_PORTS]
    return [hit for hit in await asyncio.gather(*tasks) if hit]


async def main() -> None:
    ip = _local_ip()
    print(f"local ip: {ip or 'unknown'}")

    print("\n== ONVIF WS-Discovery ==")
    onvif = onvif_discover()
    if onvif:
        for entry in onvif:
            print(f"  {entry}")
    else:
        print("  no ONVIF device answered (camera is likely cloud-only)")

    if not ip:
        print("\nCan't derive the local subnet — skipping RTSP scan.")
        return

    prefix = ip.rsplit(".", 1)[0]
    print(f"\n== RTSP port scan ({prefix}.1-254 on {', '.join(map(str, RTSP_PORTS))}) ==")
    hits = await scan_subnet(prefix)
    if hits:
        for hit in hits:
            print(f"  {hit}")
    else:
        print("  no open RTSP port found")


if __name__ == "__main__":
    asyncio.run(main())
