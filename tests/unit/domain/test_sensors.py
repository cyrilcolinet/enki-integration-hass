"""Unit tests for environmental sensor capabilities."""

from __future__ import annotations

from enki.domain.capabilities import device_is_supported
from enki.domain.models import EnkiDevice
from enki.lib.battery import battery_health_to_percent


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


def test_motion_sensor_supported() -> None:
    device = _device(capabilities=["check_motion_detection"])
    assert device.profile.is_binary_sensor is True
    assert device_is_supported(device) is True


def test_temperature_sensor_supported() -> None:
    device = _device(
        capabilities=["check_current_temperature", "check_current_humidity"],
    )
    profile = device.profile
    assert profile.is_environment_sensor is True
    assert profile.supports_current_temperature is True
    assert device_is_supported(device) is True


def test_siren_switch_supported() -> None:
    device = _device(
        capabilities=["switch_siren_status", "check_siren_global_state"],
    )
    assert device.profile.is_config_switch is True
    assert device_is_supported(device) is True


def test_battery_health_mapping() -> None:
    assert battery_health_to_percent("GOOD") == 80
    assert battery_health_to_percent("CRITICAL") == 5
    assert battery_health_to_percent("UNKNOWN") is None


def test_illuminance_sensor_supported() -> None:
    device = _device(capabilities=["check_illuminance_level"])
    profile = device.profile
    assert profile.supports_illuminance_level is True
    assert profile.is_environment_sensor is True
    assert device_is_supported(device) is True
