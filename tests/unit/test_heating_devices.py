"""Unit tests for heating / water device capabilities."""

from __future__ import annotations

from enki.domain.capabilities import device_is_supported
from enki.domain.models import EnkiDevice
from enki.domain.state import EnkiDeviceState
from enki.lib.heating import (
    pilot_wire_options,
    thermostat_running_to_hvac_action,
    thermostat_temperature_range,
)


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "device",
        "node_id": "node",
        "device_name": "Test",
        "device_type": "sensors",
        "is_enabled": True,
        "state": "ACTIVE",
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def test_water_leak_sensor_supported() -> None:
    device = _device(
        capabilities=["check_water_sensor_state", "check_battery_health"],
    )
    profile = device.profile
    assert profile.supports_water_leak is True
    assert profile.is_binary_sensor is True
    assert device_is_supported(device) is True


def test_pilot_wire_supported() -> None:
    device = _device(
        device_type="heaters",
        capabilities=["check_pilot_wire_state", "switch_pilot_wire_mode"],
        possible_values={
            "switch_pilot_wire_mode": {
                "values": ["COMFORT", "ECO", "OFF"],
            },
        },
    )
    profile = device.profile
    assert profile.is_pilot_wire is True
    assert pilot_wire_options(profile.possible_values) == ["comfort", "eco", "off"]
    assert device_is_supported(device) is True


def test_thermostat_climate_supported() -> None:
    device = _device(
        device_type="heaters",
        capabilities=[
            "check_thermostat_target_temperature",
            "change_thermostat_target_temperature",
            "check_thermostat_running_state",
            "check_current_temperature",
            "check_window_open_detection",
            "check_occupancy",
        ],
        possible_values={
            "change_thermostat_target_temperature": {
                "range": {"min": 7.0, "max": 28.0, "step": 0.5},
            },
        },
    )
    profile = device.profile
    assert profile.is_climate is True
    assert profile.is_environment_sensor is False
    assert profile.supports_window_open_detection is True
    assert thermostat_temperature_range(profile.possible_values) == (7.0, 28.0, 0.5)
    assert device_is_supported(device) is True


def test_thermostat_running_state_mapping() -> None:
    assert thermostat_running_to_hvac_action("HEAT") == "heating"
    assert thermostat_running_to_hvac_action("IDLE") == "idle"


def test_heating_state_accessors() -> None:
    state = EnkiDeviceState(
        {
            "water_sensor_state": "WATER_DETECTED",
            "pilot_wire_state": "ECO",
            "thermostat_target_temperature": 20.5,
            "thermostat_running_state": "HEAT",
            "current_temperature": 19.0,
        }
    )
    assert state.water_sensor_state == "WATER_DETECTED"
    assert state.pilot_wire_state == "ECO"
    assert state.thermostat_target_temperature == 20.5
    assert state.thermostat_running_state == "HEAT"
    assert state.current_temperature == 19.0
