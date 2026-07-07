"""Enrich anonymized telemetry exports with integration context."""

from __future__ import annotations

from typing import Any

from .capabilities import EnkiCapabilityProfile
from .models import EnkiDiscoveryRecord
from .telemetry_coverage import (
    NOT_PLANNED_CAPABILITIES,
    api_read_errors_need_telemetry,
    capability_is_covered,
    discovery_record_eligible_for_telemetry,
    profile_from_record,
)


def ha_platforms_for_profile(profile: EnkiCapabilityProfile) -> list[str]:
    """Home Assistant platforms that would be created for this profile."""
    platforms: list[str] = []
    if profile.is_fan:
        platforms.append("fan")
    if profile.is_light_controllable:
        platforms.append("light")
    if profile.is_outlet:
        platforms.append("switch")
    if profile.is_inverter:
        platforms.append("sensor")
    if profile.is_cover:
        platforms.append("cover")
    if profile.is_climate:
        platforms.append("climate")
    if profile.is_pilot_wire:
        platforms.append("select")
    if profile.is_roller_shutter_mode:
        platforms.append("select")
    if profile.is_binary_sensor:
        platforms.append("binary_sensor")
    if profile.is_environment_sensor:
        platforms.append("sensor")
    if profile.is_config_switch:
        platforms.append("switch")
    if profile.supports_vibration_sensibility:
        platforms.append("number")
    return sorted(dict.fromkeys(platforms))


def uncovered_capabilities(record: EnkiDiscoveryRecord) -> list[str]:
    """Capabilities not implemented and not marked as admin-only or not planned."""
    profile = profile_from_record(record)
    missing: list[str] = []
    for capability in record.capabilities or []:
        if capability in NOT_PLANNED_CAPABILITIES:
            continue
        if capability_is_covered(capability, profile):
            continue
        missing.append(capability)
    return sorted(missing)


def telemetry_notification_reason(
    record: EnkiDiscoveryRecord,
    *,
    api_read_errors: dict[str, str] | None = None,
    poll_state: dict[str, Any] | None = None,
) -> str | None:
    """Short English reason why a telemetry notification would fire."""
    if not discovery_record_eligible_for_telemetry(record):
        return None
    if not record.supported_by_integration:
        return "unsupported_device"
    if uncovered_capabilities(record):
        return "uncovered_capabilities"
    if api_read_errors and api_read_errors_need_telemetry(
        record,
        api_read_errors,
        poll_state,
    ):
        return "api_read_errors"
    return None


def enrich_telemetry_export(
    export: dict[str, Any],
    record: EnkiDiscoveryRecord,
    *,
    api_read_errors: dict[str, str] | None = None,
    last_poll_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add non-fingerprint fields for diagnostics and GitHub prefill."""
    profile = profile_from_record(record)
    enriched = dict(export)
    platforms = ha_platforms_for_profile(profile)
    if platforms:
        enriched["ha_platforms"] = platforms

    missing = uncovered_capabilities(record)
    if missing:
        enriched["uncovered_capabilities"] = missing

    if last_poll_state:
        enriched["last_poll_state"] = dict(sorted(last_poll_state.items()))

    if api_read_errors:
        enriched["api_read_errors"] = dict(sorted(api_read_errors.items()))

    reason = telemetry_notification_reason(
        record,
        api_read_errors=api_read_errors,
        poll_state=last_poll_state,
    )
    if reason:
        enriched["telemetry_reason"] = reason

    return enriched
