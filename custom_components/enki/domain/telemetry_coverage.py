"""Decide whether an opt-in telemetry notification is useful."""

from __future__ import annotations

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


def discovery_record_needs_telemetry(record: EnkiDiscoveryRecord) -> bool:
    """Return True when the user should be nudged to open a GitHub issue."""
    if not record.supported_by_integration:
        return True

    profile = profile_from_record(record)
    for capability in record.capabilities or []:
        if not capability_is_covered(capability, profile):
            return True
    return False
