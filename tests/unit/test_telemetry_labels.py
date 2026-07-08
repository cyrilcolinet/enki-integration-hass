"""Unit tests for telemetry issue labels."""

from __future__ import annotations

from enki.domain.profile import (
    build_discovery_record,
    format_github_issue_body,
    format_github_issue_title,
    profile_to_export_dict,
)
from enki.lib.telemetry_labels import (
    format_telemetry_issue_title,
    format_telemetry_notification_summary,
    resolve_model_label,
)


def _lexman_remote_export(*, supported: bool = False) -> dict:
    record = build_discovery_record(
        device_type="remote_controls_and_switches",
        bff_device_type="remote_controls_and_switches",
        capabilities=[
            "check_button_double_press_state",
            "check_button_long_press_state",
            "check_button_simple_press_state",
        ],
        possible_values={},
        manufacturer="Lexman",
        model=None,
        firmware_version="2.0.0",
        supported_by_integration=supported,
        referentiel_device_id="f5fe071f734e21b8abcd1234",
    )
    export = profile_to_export_dict(
        record,
        integration_version="1.6.12",
        ha_version="2025.1.0",
    )
    export["telemetry_reason"] = "uncovered_capabilities" if supported else "unsupported_device"
    return export


def test_issue_title_uses_manufacturer_and_ref_instead_of_unknown() -> None:
    title = format_github_issue_title(_lexman_remote_export())
    assert "unknown" not in title.lower()
    assert "[telemetry] Lexman remote control" in title
    assert "ref f5fe071f734e" in title
    assert title.endswith("— unsupported")


def test_issue_title_capability_gap_when_supported() -> None:
    title = format_telemetry_issue_title(_lexman_remote_export(supported=True))
    assert "capability gap" in title


def test_notification_summary_is_readable() -> None:
    summary = format_telemetry_notification_summary(_lexman_remote_export())
    assert summary == "Lexman remote control · ref f5fe071f734e"


def test_github_labels_for_unsupported_remote() -> None:
    from enki.lib.telemetry_labels import telemetry_github_labels

    labels = telemetry_github_labels(_lexman_remote_export())
    assert labels == (
        "device telemetry",
        "unsupported",
        "control",
    )


def test_github_labels_for_capability_gap_cover() -> None:
    from enki.lib.telemetry_labels import telemetry_github_labels

    export = _lexman_remote_export(supported=True)
    export["device_type"] = "access_and_motorizations"
    export["telemetry_reason"] = "uncovered_capabilities"
    labels = telemetry_github_labels(export)
    assert labels == (
        "device telemetry",
        "capability gap",
        "motorization",
    )


def test_issue_body_omits_unknown_placeholders() -> None:
    body = format_github_issue_body(_lexman_remote_export(), "abc123def456")
    assert "unknown" not in body.lower()
    assert "**Referentiel device ID:** `f5fe071f734e21b8abcd1234`" in body
    assert "**Home Assistant:** `2025.1.0`" in body
    assert "**Suggested labels:**" in body
    assert "`unsupported`" in body


def test_model_label_prefers_referentiel_model_number() -> None:
    export = profile_to_export_dict(
        build_discovery_record(
            device_type="heaters_and_pilot_wires",
            bff_device_type="heaters_and_pilot_wires",
            capabilities=["check_thermostat_target_temperature"],
            possible_values={},
            manufacturer="Noirot",
            model="AD123",
            firmware_version="2.0.0",
            supported_by_integration=True,
            referentiel_device_id="67a4b12bae1eca4709a45680",
        ),
        integration_version="1.6.12",
        ha_version="2025.1.0",
    )
    assert resolve_model_label(export) == "AD123"
