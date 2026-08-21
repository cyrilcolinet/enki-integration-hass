"""Unit tests for telemetry enrichment."""

from __future__ import annotations

from enki.domain.capabilities import EnkiCapabilityProfile
from enki.domain.profile import (
    build_discovery_record,
    format_github_issue_body,
    profile_to_export_dict,
)
from enki.domain.telemetry_coverage import discovery_record_needs_telemetry
from enki.domain.telemetry_enrichment import (
    capability_routing_hints,
    enrich_telemetry_export,
    ha_platforms_for_profile,
)


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
    errors = {"thermostat/check_thermostat_target_temperature": "HTTP 500"}
    assert discovery_record_needs_telemetry(record, api_read_errors=errors) is True


def test_supported_profile_skips_telemetry_when_poll_state_has_primary_values() -> None:
    record = _noirot_record()
    errors = {
        "consumption/check_electrical_consumption": "HTTP 403",
        "thermostat/check_thermostat_target_temperature": "HTTP 500",
    }
    poll_state = {"thermostat_target_temperature": 21.0, "occupancy": "UNOCCUPIED"}
    assert (
        discovery_record_needs_telemetry(
            record,
            api_read_errors=errors,
            poll_state=poll_state,
        )
        is False
    )


def test_enrich_export_omits_telemetry_reason_when_poll_state_is_healthy() -> None:
    record = _noirot_record()
    export = profile_to_export_dict(record, integration_version="1.6.8", ha_version="2025.1")
    enriched = enrich_telemetry_export(
        export,
        record,
        api_read_errors={"consumption/check_electrical_consumption": "HTTP 403"},
        last_poll_state={"thermostat_target_temperature": 21.0},
    )
    assert "telemetry_reason" not in enriched


def test_enrich_export_includes_platforms_and_api_errors() -> None:
    record = _noirot_record()
    export = profile_to_export_dict(record, integration_version="1.6.5", ha_version="2025.1")
    enriched = enrich_telemetry_export(
        export,
        record,
        api_read_errors={"thermostat/check_thermostat_target_temperature": "HTTP 500"},
        last_poll_state={"thermostat_target_temperature": 21.0},
    )
    assert "climate" in enriched["ha_platforms"]
    assert "telemetry_reason" not in enriched
    errors = enriched["api_read_errors"]
    assert "HTTP 500" in errors["thermostat/check_thermostat_target_temperature"]
    assert enriched["last_poll_state"]["thermostat_target_temperature"] == 21.0


def test_enrich_export_marks_api_read_errors_when_poll_state_missing() -> None:
    record = _noirot_record()
    export = profile_to_export_dict(record, integration_version="1.6.5", ha_version="2025.1")
    enriched = enrich_telemetry_export(
        export,
        record,
        api_read_errors={"thermostat/check_thermostat_target_temperature": "HTTP 500"},
    )
    assert enriched["telemetry_reason"] == "api_read_errors"


def test_github_issue_body_is_english_and_includes_api_errors() -> None:
    record = _noirot_record()
    export = enrich_telemetry_export(
        profile_to_export_dict(record, integration_version="1.6.5", ha_version="2025.1"),
        record,
        api_read_errors={"thermostat/check_thermostat_target_temperature": "HTTP 500"},
        last_poll_state={"thermostat_target_temperature": 21.0},
    )
    body = format_github_issue_body(export, "abc123")
    assert "Referentiel type:" in body
    assert "Last poll state (anonymized)" in body
    assert "thermostat_target_temperature" in body
    assert "API read errors (last poll)" in body
    assert "HTTP 500" in body
    assert "Profil appareil" not in body


def test_capability_routing_hints_flags_wired_service() -> None:
    hints = capability_routing_hints(["check_motion_detection"])
    entry = hints["check_motion_detection"]
    services = entry["services"]
    assert len(services) == 1
    assert services[0]["service"] == "api-enki-presence-detector-prod"
    assert services[0]["wired"] is True
    assert entry["effort"] == "service wired — add a CapabilityRead + entity"


def test_capability_routing_hints_flags_unwired_service() -> None:
    hints = capability_routing_hints(["check_camera_events"])
    entry = hints["check_camera_events"]
    assert entry["services"][0]["service"] == "api-enki-lexman-camera-meari-prod"
    assert entry["services"][0]["wired"] is False
    assert entry["effort"].startswith("service not wired")


def test_capability_routing_hints_reports_missing_route() -> None:
    hints = capability_routing_hints(["check_camera_last_event"])
    entry = hints["check_camera_last_event"]
    assert entry["services"] == []
    assert entry["effort"].startswith("no direct route")


def test_enrich_export_adds_capability_routing_for_uncovered() -> None:
    record = build_discovery_record(
        device_type="cameras",
        bff_device_type="cameras",
        capabilities=["check_camera_connect_wss"],
        possible_values={},
        manufacturer="Meari",
        model="camera",
        firmware_version="1.0.0",
        supported_by_integration=False,
    )
    export = profile_to_export_dict(record, integration_version="1.13.2", ha_version="2025.1")
    enriched = enrich_telemetry_export(export, record)
    assert "check_camera_connect_wss" in enriched["uncovered_capabilities"]
    routing = enriched["capability_routing"]["check_camera_connect_wss"]
    assert routing["services"][0]["service"] == "api-enki-lexman-camera-meari-prod"


def test_enrich_export_includes_api_read_reports_when_provided() -> None:
    record = _noirot_record()
    export = profile_to_export_dict(record, integration_version="1.14.0", ha_version="2026.8")
    reports = {
        "lighting/check-light-state": {
            "method": "GET",
            "path": "/api-enki-lighting-prod/v1/lighting/{id}/check-light-state",
            "status": 400,
            "response_body": {"message": "invalid request"},
        }
    }
    enriched = enrich_telemetry_export(
        export,
        record,
        api_read_errors={"lighting/check-light-state": "HTTP 400"},
        api_read_reports=reports,
    )
    assert enriched["api_read_reports"]["lighting/check-light-state"]["status"] == 400


def test_ha_platforms_include_button_for_shutter_presets() -> None:
    profile = EnkiCapabilityProfile(
        device_type="access_and_motorizations",
        capabilities=frozenset(
            [
                "change_shutter_position",
                "check_shutter_position",
                "execute_preset",
            ]
        ),
        possible_values={"execute_preset": {"values": ["MORNING"]}},
        bff_device_type="access_and_motorizations",
    )

    assert ha_platforms_for_profile(profile) == ["button", "cover"]


def test_ha_platforms_include_button_for_impulse_relay() -> None:
    profile = EnkiCapabilityProfile(
        device_type="access_and_motorizations",
        capabilities=frozenset(["power_on_with_timer"]),
        possible_values={},
        bff_device_type="access_and_motorizations",
    )

    assert ha_platforms_for_profile(profile) == ["button"]
