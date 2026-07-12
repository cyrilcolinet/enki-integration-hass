"""Unit tests for capability-based device detection."""

from __future__ import annotations

from enki.domain.capabilities import (
    device_is_supported,
    device_uses_power_api_only,
    fan_max_speed,
    is_fan_device,
    is_inverter_device,
    is_light_controllable,
    main_change_capability_endpoints,
)
from enki.domain.models import EnkiDevice
from enki.lib.bff import parse_bff_power


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


def test_is_inverter_without_bff_power() -> None:
    device = _device(
        device_type="inverters",
        capabilities=["check_power_production", "check_energy_production"],
        power_production=None,
    )
    assert is_inverter_device(device) is True
    assert device.profile.supports_energy_production is True


def test_device_uses_power_api_only() -> None:
    device = _device(
        capabilities=["switch_electrical_power", "check_electrical_power"],
    )
    assert device_uses_power_api_only(device) is True
    assert device.profile.is_outlet is True
    assert is_light_controllable(device) is False
    assert device_is_supported(device) is True


def test_main_change_capability_endpoints() -> None:
    device = _device(
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[2, 3],
    )
    assert main_change_capability_endpoints(device) == [2, 3]


def _unschemed_fan_light_device(**overrides) -> EnkiDevice:
    """AD_TCFL_1-shaped device: change_light_state is listed in capabilities
    but has no possibleValues schema, while switch_electrical_power (endpoint
    1) does — the referentiel's real bare on/off channel.
    """
    defaults = {
        "device_type": "ceiling_fans",
        "capabilities": ["change_fan_speed", "change_light_state", "check_light_state"],
        "possible_values": {
            "change_fan_speed": {"format": "RANGE", "range": {"min": 0.0, "max": 6.0}},
            "switch_electrical_power": {"format": "VALUES", "values": ["ON", "OFF"]},
        },
        "main_change_capability_id": "switch_electrical_power",
        "main_change_capability_endpoints": [1],
    }
    defaults.update(overrides)
    return _device(**defaults)


def test_light_state_has_schema_false_when_capability_tag_without_possible_values() -> None:
    device = _unschemed_fan_light_device()
    assert device.profile.supports_light_state is True
    assert device.profile.light_state_has_schema is False


def test_light_state_has_schema_true_when_possible_values_present() -> None:
    device = _device(
        device_type="lights",
        capabilities=["change_light_state", "check_light_state"],
        possible_values={"change_light_state": {"format": "VALUES", "values": ["ON", "OFF"]}},
    )
    assert device.profile.light_state_has_schema is True


def test_bare_power_fallback_endpoint_used_when_light_state_unschemed() -> None:
    device = _unschemed_fan_light_device()
    assert device.profile.bare_power_fallback_endpoint == 1


def test_bare_power_fallback_endpoint_none_when_light_state_has_schema() -> None:
    device = _unschemed_fan_light_device(
        possible_values={
            "change_light_state": {"format": "VALUES", "values": ["ON", "OFF"]},
            "switch_electrical_power": {"format": "VALUES", "values": ["ON", "OFF"]},
        },
    )
    assert device.profile.bare_power_fallback_endpoint is None


def test_bare_power_fallback_endpoint_none_without_power_switch_endpoint() -> None:
    device = _unschemed_fan_light_device(
        main_change_capability_id=None,
        main_change_capability_endpoints=[],
    )
    assert device.profile.bare_power_fallback_endpoint is None


def test_fan_light_endpoints_excludes_motor() -> None:
    from enki.domain.capabilities import fan_light_endpoints

    device = _device(
        device_type="ceiling_fans",
        capabilities=["change_fan_speed", "change_light_state"],
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[1, 2, 3],
    )
    assert fan_light_endpoints(device) == [2, 3]


def test_fan_light_endpoints_radix_motor_on_middle_endpoint() -> None:
    from enki.domain.capabilities import fan_light_endpoints

    device = _device(
        device_type="ceiling_fans",
        device_name="Inspire Radix",
        capabilities=["change_fan_speed", "change_light_state"],
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[1, 2, 3],
    )
    assert fan_light_endpoints(device) == [1, 3]
    assert device.profile.fan_motor_endpoints == [2]


def test_fan_max_speed_from_metadata() -> None:
    device = _device(
        possible_values={"change_fan_speed": {"range": {"min": 0, "max": 5}}},
    )
    assert fan_max_speed(device) == 5


def test_supports_fan_speed_control_requires_change_and_range() -> None:
    with_change = _device(
        capabilities=["change_fan_speed", "check_fan_speed"],
        possible_values={"change_fan_speed": {"range": {"min": 0, "max": 6}}},
    )
    check_only = _device(
        capabilities=["check_fan_speed", "switch_electrical_power"],
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[1, 2],
    )
    assert with_change.profile.supports_fan_speed_control is True
    assert check_only.profile.supports_fan_speed_control is False


def test_impulse_relay_supported_not_cover() -> None:
    device = _device(
        device_type="access_and_motorizations",
        capabilities=["power_on_with_timer"],
    )
    profile = device.profile
    assert profile.is_impulse_relay is True
    assert profile.is_cover is False
    assert device_is_supported(device) is True
