"""Diagnostics must explain profiles that telemetry silently drops (see issue #87)."""

from __future__ import annotations

from enki.domain.profile import (
    build_discovery_record,
    format_github_issue_body,
    profile_fingerprint,
    profile_to_export_dict,
)
from enki.domain.telemetry_coverage import (
    discovery_record_eligible_for_telemetry,
    discovery_record_telemetry_exclusion,
)
from enki.domain.telemetry_enrichment import enrich_telemetry_export


def _boiler_record():
    """Water heater relay as Enki reports it: no manufacturer, no capabilities."""
    return build_discovery_record(
        device_type="boiler",
        bff_device_type="boiler",
        capabilities=[],
        possible_values={},
        manufacturer=None,
        model=None,
        firmware_version=None,
        supported_by_integration=False,
        referentiel_device_id="6226fd906ceb9ce2aafcf715",
        main_change_capability_id="switch_electrical_power",
    )


def _export(record) -> dict:
    return profile_to_export_dict(
        record,
        integration_version="1.6.21",
        ha_version="2026.7.4",
    )


def test_whenProfileIsOutOfEnkiScope_thenExclusionIsReported() -> None:
    # Given
    record = _boiler_record()

    # When
    exclusion = discovery_record_telemetry_exclusion(record)

    # Then
    assert exclusion == "out_of_enki_scope"
    assert discovery_record_eligible_for_telemetry(record) is False


def test_whenGatewayProfile_thenExclusionSaysGateway() -> None:
    # Given
    record = build_discovery_record(
        device_type="gateways",
        bff_device_type="gateways",
        capabilities=["gateway_reboot"],
        possible_values={},
        manufacturer="Enki",
        model="EnkiConnectGW001",
        firmware_version="2.0.0",
        supported_by_integration=False,
    )

    # When / Then
    assert discovery_record_telemetry_exclusion(record) == "gateway"


def test_whenSupportedProfile_thenNoExclusion() -> None:
    # Given
    record = build_discovery_record(
        device_type="access_and_motorizations",
        bff_device_type="access_and_motorizations",
        capabilities=["power_on_with_timer"],
        possible_values={},
        manufacturer="Lexman",
        model=None,
        firmware_version="2.0.0",
        supported_by_integration=True,
    )

    # When / Then
    assert discovery_record_telemetry_exclusion(record) is None
    assert "telemetry_excluded" not in enrich_telemetry_export(_export(record), record)


def test_whenDroppedByScope_thenDiagnosticsCarryTheReason() -> None:
    # Given
    record = _boiler_record()

    # When
    enriched = enrich_telemetry_export(_export(record), record)

    # Then
    assert enriched["telemetry_excluded"] == "out_of_enki_scope"
    assert "telemetry_reason" not in enriched


def test_whenReferentielHasNoCapabilities_thenMainChangeCapabilityIsExported() -> None:
    # Given
    record = _boiler_record()

    # When
    export = _export(record)

    # Then
    assert export["capabilities"] == []
    assert export["main_change_capability_id"] == "switch_electrical_power"
    assert "Main change capability" in format_github_issue_body(export, "f" * 64)


def test_whenMainChangeCapabilityChanges_thenFingerprintStaysStable() -> None:
    # Given
    without = _export(
        build_discovery_record(
            device_type="boiler",
            bff_device_type="boiler",
            capabilities=[],
            possible_values={},
            manufacturer=None,
            model=None,
            firmware_version=None,
            supported_by_integration=False,
            referentiel_device_id="6226fd906ceb9ce2aafcf715",
        )
    )

    # When
    with_hint = _export(_boiler_record())

    # Then — adding the hint must not re-notify users about already reported devices.
    assert profile_fingerprint(without) == profile_fingerprint(with_hint)
