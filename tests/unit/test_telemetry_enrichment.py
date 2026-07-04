"""Unit tests for telemetry enrichment."""

from __future__ import annotations

from enki.domain.profile import (
    build_discovery_record,
    format_github_issue_body,
    profile_to_export_dict,
)
from enki.domain.telemetry_coverage import discovery_record_needs_telemetry
from enki.domain.telemetry_enrichment import enrich_telemetry_export


def _noirot_record():
    return build_discovery_record(
        device_type="heaters_and_pilot_wires",
        bff_device_type="heaters_and_pilot_wires",
        capabilities=[
            "change_thermostat_target_temperature",
            "check_thermostat_target_temperature",
            "check_thermostat_running_state",
            "check_window_open_detection",
            "total_supply_charge_consumption",
        ],
        possible_values={},
        manufacturer="Noirot",
        model="radiator",
        firmware_version="2.15.0",
        supported_by_integration=True,
    )


def test_noirot_profile_does_not_need_telemetry_without_api_errors() -> None:
    record = _noirot_record()
    assert discovery_record_needs_telemetry(record) is False


def test_supported_profile_needs_telemetry_when_api_errors_present() -> None:
    record = _noirot_record()
    errors = {"heating/check_thermostat_target_temperature": "HTTP 500"}
    assert discovery_record_needs_telemetry(record, api_read_errors=errors) is True


def test_enrich_export_includes_platforms_and_api_errors() -> None:
    record = _noirot_record()
    export = profile_to_export_dict(record, integration_version="1.6.5", ha_version="2025.1")
    enriched = enrich_telemetry_export(
        export,
        record,
        api_read_errors={"heating/check_thermostat_target_temperature": "HTTP 500"},
        last_poll_state={"thermostat_target_temperature": 21.0},
    )
    assert "climate" in enriched["ha_platforms"]
    assert enriched["telemetry_reason"] == "api_read_errors"
    assert "HTTP 500" in enriched["api_read_errors"]["heating/check_thermostat_target_temperature"]
    assert enriched["last_poll_state"]["thermostat_target_temperature"] == 21.0


def test_github_issue_body_is_english_and_includes_api_errors() -> None:
    record = _noirot_record()
    export = enrich_telemetry_export(
        profile_to_export_dict(record, integration_version="1.6.5", ha_version="2025.1"),
        record,
        api_read_errors={"heating/check_thermostat_target_temperature": "HTTP 500"},
        last_poll_state={"thermostat_target_temperature": 21.0},
    )
    body = format_github_issue_body(export, "abc123")
    assert "Referentiel type:" in body
    assert "Last poll state (anonymized)" in body
    assert "thermostat_target_temperature" in body
    assert "API read errors (last poll)" in body
    assert "HTTP 500" in body
    assert "Profil appareil" not in body
