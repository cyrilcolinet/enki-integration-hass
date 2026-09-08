"""One-shot census of devices skipped because their brand is unknown.

Per-profile telemetry only ever covers devices the integration already claims:
anything outside :func:`device_in_enki_scope` is dropped before the nudge, so a
supportable product can sit on hundreds of accounts without ever being heard of.
That is exactly what happened with DIO outlets (#203) — a plain
``switch_electrical_power`` device, missing only from the brand list.

The fix must not turn into noise for people running third-party Zigbee on the
hub, so this stays deliberately quiet: one aggregated card per brand set, never
one per device, and the brands that clearly belong in Zigbee2MQTT / ZHA are
filtered out entirely.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from urllib.parse import quote

from ..const import TELEMETRY_GITHUB_REPO
from ..lib.enki_scope import device_in_enki_scope
from .models import EnkiDiscoveryRecord
from .telemetry_coverage import discovery_record_is_gateway

# Brands the README already routes to Zigbee2MQTT / ZHA. Missing one only costs
# a single card, so the list stays short rather than trying to be exhaustive.
_THIRD_PARTY_BRANDS = frozenset(
    {
        "aqara",
        "blitzwolf",
        "bosch",
        "heiman",
        "ikea",
        "innr",
        "lidl",
        "moes",
        "osram",
        "sengled",
        "silvercrest",
        "sonoff",
        "tradfri",
        "tuya",
        "xiaomi",
    }
)

# Brands Enki drives through a dedicated micro-service: seeing one skipped is a
# strong signal, not noise — DIO was one of these.
_ENKI_PARTNER_BRANDS = frozenset(
    {
        "avidsen",
        "diagral",
        "dio",
        "enocean",
        "netatmo",
        "philips",
        "sauter",
        "somfy",
        "tahoma",
        "tapo",
        "wiz",
    }
)


@dataclass(frozen=True, slots=True)
class UnknownBrandEntry:
    """One brand / device-type pair seen on the account, with how many."""

    manufacturer: str
    device_type: str
    count: int
    partner: bool


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _is_third_party(manufacturer: str) -> bool:
    normalized = _normalize(manufacturer)
    return any(brand in normalized for brand in _THIRD_PARTY_BRANDS)


def _is_partner(manufacturer: str) -> bool:
    normalized = _normalize(manufacturer)
    return any(brand in normalized for brand in _ENKI_PARTNER_BRANDS)


def unknown_brand_census(records: list[EnkiDiscoveryRecord]) -> list[UnknownBrandEntry]:
    """Group the skipped-by-brand devices worth telling the maintainer about.

    Devices already covered by per-profile telemetry are left out — they nudge on
    their own — and so are hubs and third-party Zigbee.
    """
    counter: Counter[tuple[str, str]] = Counter()
    for record in records:
        manufacturer = (record.manufacturer or "").strip()
        if not manufacturer:
            continue
        if device_in_enki_scope(
            manufacturer=manufacturer,
            device_type=record.device_type,
        ):
            continue
        if discovery_record_is_gateway(record):
            # The hub is skipped by design, whatever brand it carries.
            continue
        if _is_third_party(manufacturer):
            continue
        counter[(manufacturer, record.device_type or "unknown")] += 1

    return [
        UnknownBrandEntry(
            manufacturer=manufacturer,
            device_type=device_type,
            count=count,
            partner=_is_partner(manufacturer),
        )
        for (manufacturer, device_type), count in sorted(counter.items())
    ]


def unknown_brand_fingerprint(census: list[UnknownBrandEntry]) -> str:
    """Stable id for a brand set, so the card appears once and not per device.

    Counts are deliberately excluded: buying an eighth plug of a brand already
    reported must not raise a second card.
    """
    brands = sorted({_normalize(entry.manufacturer) for entry in census})
    return hashlib.sha256("|".join(brands).encode()).hexdigest()


def format_unknown_brand_summary(census: list[UnknownBrandEntry]) -> str:
    return ", ".join(
        f"{entry.manufacturer} {entry.device_type} (×{entry.count})" for entry in census
    )


def build_unknown_brand_issue_url(census: list[UnknownBrandEntry], fingerprint: str) -> str:
    """Pre-filled GitHub issue asking whether these brands should be supported."""
    brands = sorted({entry.manufacturer for entry in census})
    title = f"[telemetry] Unsupported brands: {', '.join(brands)}"
    lines = [
        "Devices on my account that the integration skips because their brand is unknown.",
        "",
        "| Brand | Type | Count | Enki micro-service |",
        "|-------|------|-------|--------------------|",
    ]
    lines += [
        f"| {entry.manufacturer} | {entry.device_type} | {entry.count} | "
        f"{'yes' if entry.partner else 'unknown'} |"
        for entry in census
    ]
    lines += [
        "",
        "Run `python3 scripts/discover_devices.py <email> <password>` for the full "
        "capability dump of one of these devices.",
        "",
        f"Census id: `{fingerprint[:16]}`",
    ]
    body = "\n".join(lines)
    base = f"https://github.com/{TELEMETRY_GITHUB_REPO}/issues/new"
    return f"{base}?title={quote(title)}&body={quote(body)}&labels={quote('unsupported')}"
