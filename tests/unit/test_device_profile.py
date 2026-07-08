"""Unit tests for anonymized device profiles."""

from __future__ import annotations

from enki.domain.models import EnkiDiscoveryRecord
from enki.domain.profile import (
    build_discovery_record,
    build_github_new_issue_url,
    format_github_issue_title,
    profile_fingerprint,
    profile_to_export_dict,
)


def _sample_record(*, supported: bool = False) -> EnkiDiscoveryRecord:
    return build_discovery_record(
        device_type="equation_radiator",
        bff_device_type="radiators",
        capabilities=["check_temperature", "change_setpoint"],
        possible_values={
            "change_setpoint": {"values": [16, 17, 18], "type": "number"},
            "homeId": "must-not-appear",
        },
        manufacturer="equation",
        model="neo_wifi",
        firmware_version="1.2.3",
        supported_by_integration=supported,
    )


def test_profile_to_export_dict_excludes_sensitive_keys() -> None:
    export = profile_to_export_dict(
        _sample_record(),
        integration_version="1.0.7",
        ha_version="2024.12.0",
    )
    assert export["device_type"] == "equation_radiator"
    assert export["manufacturer"] == "equation"
    assert "homeId" not in export["possible_values"]


def test_profile_fingerprint_stable_across_versions() -> None:
    record = _sample_record()
    first = profile_to_export_dict(record, integration_version="1.0.0", ha_version="2024.1")
    second = profile_to_export_dict(record, integration_version="9.9.9", ha_version="2025.1")
    assert profile_fingerprint(first) == profile_fingerprint(second)


def test_format_github_issue_title_unsupported() -> None:
    export = profile_to_export_dict(_sample_record(), integration_version="1.0.7", ha_version="x")
    title = format_github_issue_title(export)
    assert "[telemetry]" in title
    assert "Equation" in title or "equation" in title.lower()
    assert "neo_wifi" in title
    assert "unknown" not in title.lower()


def test_build_github_new_issue_url_contains_repo_and_body() -> None:
    export = profile_to_export_dict(
        _sample_record(),
        integration_version="1.0.7",
        ha_version="2024.12",
    )
    fingerprint = profile_fingerprint(export)
    url = build_github_new_issue_url(export, fingerprint)
    assert "github.com/cyrilcolinet/enki-integration-hass/issues/new" in url
    assert "title=" in url
    assert "body=" in url
    assert "labels=" in url
    assert "device%20telemetry" in url or "device telemetry" in url
    assert "equation_radiator" in url
