"""Capability → micro-service routing for state reads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.capabilities import EnkiCapabilityProfile


@dataclass(frozen=True, slots=True)
class CapabilityRead:
    """Maps a referentiel check_* capability to a transport read."""

    transport_id: str
    capability: str
    state_key: str
    skip: Callable[[EnkiCapabilityProfile], bool] | None = None


CAPABILITY_READS: tuple[CapabilityRead, ...] = (
    CapabilityRead(
        "temperature_humidity",
        "check_current_temperature",
        "current_temperature",
    ),
    CapabilityRead("temperature_humidity", "check_current_humidity", "current_humidity"),
    CapabilityRead("battery_health", "check_battery_health", "battery_health"),
    CapabilityRead("luminosity_sensor", "check_illuminance_level", "illuminance_level"),
    CapabilityRead("luminosity_sensor", "check_brightness_level", "illuminance_level"),
    CapabilityRead("presence_detector", "check_motion_detection", "motion_detection"),
    CapabilityRead("presence_detector", "check_presence_detection", "presence_detection"),
    CapabilityRead("presence_detector", "check_motion_detector_state", "motion_detector_state"),
    CapabilityRead("contact_sensor", "check_contact_sensor_state", "contact_sensor_state"),
    CapabilityRead("contact_sensor", "check_vibration_detection", "vibration_detection"),
    CapabilityRead(
        "contact_sensor",
        "check_vibration_detection_activation",
        "vibration_detection_activation",
    ),
    CapabilityRead(
        "contact_sensor",
        "check_contact_detection_activation",
        "contact_detection_activation",
    ),
    CapabilityRead(
        "contact_sensor",
        "check_vibration_sensibility_level",
        "vibration_sensibility_level",
    ),
    CapabilityRead(
        "power",
        "check_dry_contact_for_electric_strike_state",
        "dry_contact_state",
    ),
    CapabilityRead("power", "check_channel1_electrical_power", "channel1_electrical_power"),
    CapabilityRead("power", "check_channel2_electrical_power", "channel2_electrical_power"),
    CapabilityRead("siren", "check_siren_global_state", "siren_global_state"),
    CapabilityRead("water_sensor", "check_water_sensor_state", "water_sensor_state"),
    CapabilityRead("thermostat", "check_pilot_wire_state", "pilot_wire_state"),
    CapabilityRead(
        "thermostat",
        "check_thermostat_target_temperature",
        "thermostat_target_temperature",
    ),
    CapabilityRead("thermostat", "check_thermostat_running_state", "thermostat_running_state"),
    CapabilityRead("thermostat", "check_window_open_detection", "window_open_detection"),
    CapabilityRead(
        "thermostat",
        "check_window_open_detection_mode",
        "window_open_detection_mode",
    ),
    CapabilityRead("thermostat", "check_offset_temperature", "offset_temperature"),
    CapabilityRead("thermostat", "check_child_lock", "child_lock"),
    CapabilityRead("thermostat", "check_preheating_status", "preheating_status"),
    CapabilityRead("presence_detector", "check_occupancy", "occupancy"),
    CapabilityRead("presence_detector", "check_occupancy_mode", "occupancy_mode"),
    CapabilityRead(
        "lexman_envertech",
        "check_power_production",
        "power_production",
        skip=lambda profile: not profile.is_inverter,
    ),
    CapabilityRead(
        "lexman_envertech",
        "check_energy_production",
        "energy_production",
        skip=lambda profile: not profile.is_inverter,
    ),
)
