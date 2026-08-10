"""Enrich anonymized telemetry exports with integration context."""

from __future__ import annotations

from typing import Any

from ..api.capability_routes_data import CAPABILITY_ROUTES
from ..api.gateway_registry import ENKI_MICRO_SERVICES
from .capabilities import EnkiCapabilityProfile
from .models import EnkiDiscoveryRecord
from .telemetry_coverage import (
    NOT_PLANNED_CAPABILITIES,
    api_read_errors_need_telemetry,
    capability_is_covered,
    discovery_record_eligible_for_telemetry,
    discovery_record_telemetry_exclusion,
    profile_from_record,
)

_SERVICE_WIRED: dict[str, bool] = {svc.slug: svc.wired for svc in ENKI_MICRO_SERVICES}


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
    if profile.supports_shutter_preset or profile.supports_power_on_with_timer:
        platforms.append("button")
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


def capability_routing_hints(capabilities: list[str]) -> dict[str, dict[str, Any]]:
    """Map each capability to its APK-catalogued route(s), service, and wiring state.

    Turns an "unsupported device" report into an actionable one: it says which
    micro-service and path serve each capability and whether that service is
    already wired, so the implementation effort is visible without a round-trip.
    Route matching is by name, so absence is a hint (derived server-side or a
    differently-named endpoint), not proof.
    """
    hints: dict[str, dict[str, Any]] = {}
    for capability in capabilities:
        routes = CAPABILITY_ROUTES.get(capability)
        if not routes:
            hints[capability] = {
                "services": [],
                "effort": "no direct route found — derived server-side or renamed endpoint",
            }
            continue
        services = [
            {"service": slug, "route": path, "wired": _SERVICE_WIRED.get(slug, False)}
            for slug, path in sorted(routes.items())
        ]
        if any(service["wired"] for service in services):
            effort = "service wired — add a CapabilityRead + entity"
        else:
            effort = "service not wired — wire the gateway service, then add a CapabilityRead"
        hints[capability] = {"services": services, "effort": effort}
    return hints


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
    api_read_reports: dict[str, dict[str, Any]] | None = None,
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
        enriched["capability_routing"] = capability_routing_hints(missing)

    if last_poll_state:
        enriched["last_poll_state"] = dict(sorted(last_poll_state.items()))

    if api_read_errors:
        enriched["api_read_errors"] = dict(sorted(api_read_errors.items()))

    if api_read_reports:
        enriched["api_read_reports"] = dict(sorted(api_read_reports.items()))

    reason = telemetry_notification_reason(
        record,
        api_read_errors=api_read_errors,
        poll_state=last_poll_state,
    )
    if reason:
        enriched["telemetry_reason"] = reason

    if exclusion := discovery_record_telemetry_exclusion(record):
        enriched["telemetry_excluded"] = exclusion

    return enriched
