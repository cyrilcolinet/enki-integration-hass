"""Unit tests for capability-based device detection."""

from __future__ import annotations

from enki.capabilities import (
    device_is_supported,
    device_uses_power_api_only,
    fan_max_speed,
    is_fan_device,
    is_inverter_device,
    is_light_controllable,
    main_change_capability_endpoints,
    parse_bff_power,
)
from enki.models import EnkiDevice


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "device",
        "node_id": "node",
        "device_name": "Test",
        "device_type": "unknown",
        "is_enabled": True,
        "state": "ACTIVE",
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def test_parse_bff_power() -> None:
    assert parse_bff_power({"value": "109 W"}) == 109.0
    assert parse_bff_power({"value": "bad"}) is None


def test_is_fan_device_from_capabilities() -> None:
    device = _device(
        device_type="ventilation",
        capabilities=["change_fan_speed"],
    )
    assert is_fan_device(device) is True


def test_is_inverter_device() -> None:
    device = _device(
        device_type="inverters",
        capabilities=["check_power_production"],
        power_production=250.0,
    )
    assert is_inverter_device(device) is True
    assert device_is_supported(device) is True


def test_device_uses_power_api_only() -> None:
    device = _device(
        capabilities=["switch_electrical_power", "check_electrical_power"],
    )
    assert device_uses_power_api_only(device) is True
    assert is_light_controllable(device) is True


def test_main_change_capability_endpoints() -> None:
    device = _device(
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[2, 3],
    )
    assert main_change_capability_endpoints(device) == [2, 3]


def test_fan_max_speed_from_metadata() -> None:
    device = _device(
        possible_values={"change_fan_speed": {"range": {"min": 0, "max": 5}}},
    )
    assert fan_max_speed(device) == 5
