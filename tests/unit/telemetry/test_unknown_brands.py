"""Aggregated census of brands the integration skips (#203)."""

from __future__ import annotations

from enki.domain.models import EnkiDiscoveryRecord
from enki.domain.unknown_brands import (
    build_unknown_brand_issue_url,
    format_unknown_brand_summary,
    unknown_brand_census,
    unknown_brand_fingerprint,
)


def _record(manufacturer: str | None, device_type: str = "outlets", **overrides):
    defaults = {
        "device_type": device_type,
        "bff_device_type": device_type,
        "capabilities": ["switch_electrical_power"],
        "possible_values": {},
        "manufacturer": manufacturer,
        "model": None,
        "firmware_version": None,
        "supported_by_integration": False,
    }
    defaults.update(overrides)
    return EnkiDiscoveryRecord(**defaults)


def test_counts_unknown_brands_per_type() -> None:
    census = unknown_brand_census(
        [_record("Acme Home"), _record("Acme Home"), _record("Acme Home", "lights")]
    )
    assert [(e.manufacturer, e.device_type, e.count) for e in census] == [
        ("Acme Home", "lights", 1),
        ("Acme Home", "outlets", 2),
    ]


def test_known_enki_brand_is_not_reported() -> None:
    # In scope: it already nudges through the per-profile path.
    assert unknown_brand_census([_record("Lexman")]) == []


def test_dio_is_no_longer_unknown() -> None:
    # It was the case that motivated this census; it is supported since v1.21.
    assert unknown_brand_census([_record("Dio")]) == []


def test_third_party_zigbee_stays_silent() -> None:
    # These belong in Zigbee2MQTT / ZHA, nudging about them is noise.
    assert unknown_brand_census([_record("Sonoff"), _record("Tuya"), _record("Aqara")]) == []


def test_gateways_are_not_a_brand_question() -> None:
    assert unknown_brand_census([_record("Essentielb", "gateways")]) == []


def test_records_without_a_brand_are_skipped() -> None:
    assert unknown_brand_census([_record(None), _record("  ")]) == []


def test_enki_partner_brands_are_flagged() -> None:
    # Wiz has its own Enki micro-service: seeing one skipped is a strong signal,
    # unlike a brand nobody recognizes.
    census = unknown_brand_census([_record("Wiz"), _record("Acme Corp")])
    flags = {entry.manufacturer: entry.partner for entry in census}
    assert flags == {"Wiz": True, "Acme Corp": False}


def test_fingerprint_ignores_counts_so_the_card_shows_once() -> None:
    one = unknown_brand_census([_record("Acme Home")])
    seven = unknown_brand_census([_record("Acme Home") for _ in range(7)])
    assert unknown_brand_fingerprint(one) == unknown_brand_fingerprint(seven)


def test_fingerprint_changes_when_a_new_brand_appears() -> None:
    before = unknown_brand_census([_record("Acme Home")])
    after = unknown_brand_census([_record("Acme Home"), _record("Acme Corp")])
    assert unknown_brand_fingerprint(before) != unknown_brand_fingerprint(after)


def test_summary_and_issue_url_carry_the_census() -> None:
    census = unknown_brand_census([_record("Acme Home"), _record("Acme Home")])
    assert format_unknown_brand_summary(census) == "Acme Home outlets (×2)"

    url = build_unknown_brand_issue_url(census, "abc123")
    assert url.startswith("https://github.com/cyrilcolinet/enki-integration-hass/issues/new?")
    assert "Acme" in url
    assert "labels=unsupported" in url
