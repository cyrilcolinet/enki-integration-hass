"""RGB (hue/saturation) capabilities must count as covered (#187)."""

from __future__ import annotations

from enki.domain.capabilities import EnkiCapabilityProfile
from enki.domain.profile import build_discovery_record
from enki.domain.telemetry_coverage import capability_is_covered
from enki.domain.telemetry_enrichment import uncovered_capabilities

# Lexman connected light v2 (ref 603f0fa8f91f) from the #187 telemetry report.
_LEXMAN_RGB_CAPS = [
    "change_brightness",
    "change_color_temperature",
    "change_hue",
    "change_light_state",
    "change_saturation",
    "check_electrical_power",
    "check_light_state",
    "switch_electrical_power",
]


def _profile(caps: list[str]) -> EnkiCapabilityProfile:
    return EnkiCapabilityProfile(
        device_type="lights",
        capabilities=frozenset(caps),
        possible_values={},
        bff_device_type="lights",
    )


def test_supports_rgb_color_needs_both_hue_and_saturation() -> None:
    assert _profile(_LEXMAN_RGB_CAPS).supports_rgb_color is True
    assert _profile(["change_hue"]).supports_rgb_color is False
    assert _profile(["change_saturation"]).supports_rgb_color is False


def test_hue_and_saturation_are_covered_for_rgb_light() -> None:
    profile = _profile(_LEXMAN_RGB_CAPS)
    assert capability_is_covered("change_hue", profile) is True
    assert capability_is_covered("change_saturation", profile) is True


def test_rgb_light_reports_no_uncovered_color_capabilities() -> None:
    record = build_discovery_record(
        device_type="lights",
        bff_device_type="lights",
        capabilities=_LEXMAN_RGB_CAPS,
        possible_values={},
        manufacturer="Lexman",
        model="ref 603f0fa8f91f",
        firmware_version="2.0.0",
        supported_by_integration=True,
    )
    missing = uncovered_capabilities(record)
    assert "change_hue" not in missing
    assert "change_saturation" not in missing
