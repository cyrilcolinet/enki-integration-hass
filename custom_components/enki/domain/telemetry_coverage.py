"""Decide whether an opt-in telemetry notification is useful."""

from __future__ import annotations

from typing import Any

from ..api.capability_routing import CAPABILITY_READS
from ..lib.enki_scope import device_in_enki_scope
from .capabilities import EnkiCapabilityProfile
from .models import EnkiDiscoveryRecord

# Device lifecycle / admin — not exposed as Home Assistant entities.
_TELEMETRY_IGNORED_CAPABILITIES = frozenset(
    {
        "change_esdk_certificate",
        "check_certificate_renewal_confirmation",
        "check_current_firmware_version",
        "check_esdk_certificate_renewal",
        "execute_generic_ota_command",
        "ota_inventory",
    }
)

# Map referentiel capability names to EnkiCapabilityProfile probes.
_CAPABILITY_PROBES: dict[str, str] = {
    "activate_contact_detection": "supports_contact_detection_activation",
    "activate_vibration_detection": "supports_vibration_detection_activation",
    "change_airflow_mode": "supports_airflow_mode",
    "change_brightness": "supports_brightness_control",
    "change_color_temperature": "supports_color_temperature",
    "change_fan_rotation_direction": "supports_fan_rotation",
    "change_fan_speed": "supports_fan_speed",
    "change_light_state": "supports_light_state",
    "change_shutter_position": "supports_shutter_position",
    "change_vibration_sensibility_level": "supports_vibration_sensibility",
    "check_airflow_mode": "supports_airflow_mode",
    "check_battery_health": "supports_battery_health",
    "check_brightness": "supports_brightness_control",
    "check_color_temperature": "supports_color_temperature",
    "check_contact_detection_activation": "supports_contact_detection_activation",
    "check_contact_sensor_state": "supports_contact_sensor",
    "check_current_humidity": "supports_current_humidity",
    "check_current_temperature": "supports_current_temperature",
    "check_illuminance_level": "supports_illuminance_level",
    "check_electrical_power": "supports_electrical_power",
    "check_electrical_consumption": "supports_electrical_consumption",
    "check_fan_rotation_direction": "supports_fan_rotation",
    "check_fan_speed": "supports_fan_speed",
    "check_light_state": "supports_light_state",
    "check_motion_detection": "supports_motion_detection",
    "check_motion_detector_state": "supports_motion_detection",
    "check_power_production": "supports_power_production",
    "check_shutter_opening": "supports_shutter_opening",
    "check_shutter_position": "supports_shutter_position",
    "check_siren_global_state": "supports_siren",
    "check_vibration_detection": "supports_vibration_detection",
    "check_vibration_detection_activation": "supports_vibration_detection_activation",
    "check_vibration_sensibility_level": "supports_vibration_sensibility",
    "switch_electrical_power": "supports_electrical_power",
    "switch_siren_status": "supports_siren",
    "switch_pilot_wire_mode": "supports_pilot_wire",
    "check_pilot_wire_state": "supports_pilot_wire",
    "change_thermostat_target_temperature": "supports_thermostat",
    "check_thermostat_target_temperature": "supports_thermostat",
    "check_thermostat_running_state": "supports_thermostat",
    "change_occupancy_mode": "supports_occupancy_mode",
    "check_occupancy_mode": "supports_occupancy_mode",
    "change_window_open_detection_mode": "supports_window_open_detection_mode",
    "check_window_open_detection_mode": "supports_window_open_detection_mode",
    "check_window_open_detection": "supports_window_open_detection",
    "check_occupancy": "supports_occupancy",
    "check_water_sensor_state": "supports_water_leak",
}

# Referentiel capabilities with no HA entity planned (timers, energy totals, …).
NOT_PLANNED_CAPABILITIES = frozenset(
    {
        "cancel_electrical_power_switch_in",
        "next_electrical_power_switch_in",
        "switch_electrical_power_in",
        "total_supply_charge_consumption",
    }
)

# Hub / infrastructure — never actionable as HA entity support requests.
_GATEWAY_DEVICE_TYPES = frozenset({"gateways", "gateway"})
_GATEWAY_CAPABILITY_MARKERS = frozenset(
    {
        "gateway_inventory",
        "gateway_reboot",
        "gateway_logs",
        "change_gateway_certificate",
        "check_gateway_state",
    }
)

# Poll keys for optional sensors — API read failures alone should not nag the user.
_OPTIONAL_POLL_STATE_KEYS = frozenset(
    {
        "electrical_consumption",
        "electrical_consumption_unit",
    }
)

_CAPABILITY_TO_POLL_STATE_KEY: dict[str, str] = {
    read.capability: read.state_key for read in CAPABILITY_READS
}
_CAPABILITY_TO_POLL_STATE_KEY.update(
    {
        "check_electrical_power": "electrical_power",
        "check_electrical_consumption": "electrical_consumption",
    }
)

_ALTERNATE_POLL_STATE_KEYS: dict[str, tuple[str, ...]] = {
    "electrical_power": ("power",),
    "power": ("electrical_power",),
}


def profile_from_record(record: EnkiDiscoveryRecord) -> EnkiCapabilityProfile:
    return EnkiCapabilityProfile(
        device_type=record.device_type,
        capabilities=frozenset(record.capabilities or []),
        possible_values=record.possible_values or {},
        bff_device_type=record.bff_device_type or "",
    )


def capability_is_covered(capability: str, profile: EnkiCapabilityProfile) -> bool:
    """Return True when the integration implements this capability or it is admin-only."""
    if capability in _TELEMETRY_IGNORED_CAPABILITIES:
        return True
    probe_name = _CAPABILITY_PROBES.get(capability)
    if probe_name is None:
        return False
    return bool(getattr(profile, probe_name))


def _normalize_type(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower().replace(" ", "_")


def discovery_record_eligible_for_telemetry(record: EnkiDiscoveryRecord) -> bool:
    """Return False for out-of-scope or hub profiles that should not spam GitHub."""
    if not device_in_enki_scope(
        manufacturer=record.manufacturer,
        device_type=record.device_type,
    ):
        return False

    device_type = _normalize_type(record.device_type)
    bff_type = _normalize_type(record.bff_device_type)
    if device_type in _GATEWAY_DEVICE_TYPES or bff_type in _GATEWAY_DEVICE_TYPES:
        return False

    caps = record.capabilities or []
    return not (caps and any(cap in _GATEWAY_CAPABILITY_MARKERS for cap in caps))


def _poll_state_has_key(poll_state: dict[str, Any], state_key: str) -> bool:
    if state_key in poll_state:
        return True
    for alternate in _ALTERNATE_POLL_STATE_KEYS.get(state_key, ()):
        if alternate in poll_state:
            return True
    return False


def api_read_errors_need_telemetry(
    record: EnkiDiscoveryRecord,
    api_read_errors: dict[str, str],
    poll_state: dict[str, Any] | None,
) -> bool:
    """Return True when API read failures likely mean broken primary entities."""
    if not api_read_errors:
        return False

    poll_state = poll_state or {}
    profile = profile_from_record(record)
    saw_unknown_error = False

    for error_key in api_read_errors:
        capability = error_key.split("/", 1)[-1]
        if capability in NOT_PLANNED_CAPABILITIES:
            continue
        if not capability_is_covered(capability, profile):
            continue

        state_key = _CAPABILITY_TO_POLL_STATE_KEY.get(capability)
        if state_key is None:
            saw_unknown_error = True
            continue
        if state_key in _OPTIONAL_POLL_STATE_KEYS:
            continue
        if not _poll_state_has_key(poll_state, state_key):
            return True

    return bool(saw_unknown_error and not poll_state)


def discovery_record_needs_telemetry(
    record: EnkiDiscoveryRecord,
    *,
    api_read_errors: dict[str, str] | None = None,
    poll_state: dict[str, Any] | None = None,
) -> bool:
    """Return True when the user should be nudged to open a GitHub issue."""
    if not discovery_record_eligible_for_telemetry(record):
        return False

    if not record.supported_by_integration:
        return True

    profile = profile_from_record(record)
    for capability in record.capabilities or []:
        if capability in NOT_PLANNED_CAPABILITIES:
            continue
        if not capability_is_covered(capability, profile):
            return True

    return bool(
        api_read_errors
        and api_read_errors_need_telemetry(
            record,
            api_read_errors,
            poll_state,
        )
    )
