"""Unit tests for ESDK fan light on/off state merge in change-light-state."""

from __future__ import annotations

from enki.domain.models import EnkiDevice
from enki.lib.conversion import merge_light_state_payload
from enki.platforms.light.behavior import EnkiLightBehaviorMixin
from homeassistant.components.light import ATTR_BRIGHTNESS


class _FakeFanLightEntity(EnkiLightBehaviorMixin):
    """Minimal double exposing only what _bare_power_fallback_endpoint needs."""

    def __init__(self, device: EnkiDevice, endpoint_id: int | None) -> None:
        self._device = device
        self._endpoint_id = endpoint_id


def _unschemed_fan_light_device(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home",
        "device_id": "device",
        "node_id": "node",
        "device_name": "Test",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["change_fan_speed", "change_light_state", "check_light_state"],
        "possible_values": {
            "change_fan_speed": {"format": "RANGE", "range": {"min": 0.0, "max": 6.0}},
            "switch_electrical_power": {"format": "VALUES", "values": ["ON", "OFF"]},
        },
        "main_change_capability_id": "switch_electrical_power",
        "main_change_capability_endpoints": [1],
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def test_merge_light_state_payload_power_off_wins() -> None:
    current = {"power": "ON", "brightness": 0.5, "colorTemperature": "T4000K"}
    payload = merge_light_state_payload(current, {"power": "OFF"})
    assert payload["power"] == "OFF"
    assert payload["brightness"] == 0.5


def test_merge_light_state_payload_turn_on_defaults_power() -> None:
    current = {"power": "OFF", "brightness": 0.5, "colorTemperature": "T4000K"}
    payload = merge_light_state_payload(current, {"power": "ON"})
    assert payload["power"] == "ON"
    assert payload["brightness"] == 0.5


def test_merge_light_state_payload_brightness_update_keeps_on() -> None:
    current = {"power": "OFF", "brightness": 0.2}
    payload = merge_light_state_payload(current, {"brightness": 0.8})
    assert payload["power"] == "ON"
    assert payload["brightness"] == 0.8


def test_merge_light_state_payload_zero_brightness_forces_off() -> None:
    current = {"power": "ON", "brightness": 50.0}
    payload = merge_light_state_payload(current, {"brightness": 0})
    assert payload["power"] == "OFF"
    assert payload["brightness"] == 0


def test_merge_light_state_payload_color_temp_sets_ct_mode() -> None:
    current = {"power": "ON", "colorMode": "hs", "hue": 0.5, "saturation": 0.8}
    payload = merge_light_state_payload(current, {"colorTemperature": "T3500K"})
    assert payload["colorMode"] == "ct"
    assert payload["colorTemperature"] == "T3500K"


def test_fan_light_power_from_lighting_last_reported() -> None:
    last_reported = {"power": "OFF", "brightness": 0.2}
    assert last_reported.get("power", "OFF") == "OFF"


def test_bare_power_fallback_endpoint_uses_own_endpoint_on_multi_gang_device() -> None:
    # Siroco+-style multi-endpoint fan light (endpoints 2 and 3): this entity
    # represents endpoint 3 specifically, so the fallback must target 3, not
    # the profile's first declared power-switch endpoint (2).
    device = _unschemed_fan_light_device(
        main_change_capability_endpoints=[2, 3],
    )
    entity = _FakeFanLightEntity(device, endpoint_id=3)
    assert entity._bare_power_fallback_endpoint({}) == 3


def test_bare_power_fallback_endpoint_uses_profile_default_when_endpoint_id_unset() -> None:
    device = _unschemed_fan_light_device(main_change_capability_endpoints=[1])
    entity = _FakeFanLightEntity(device, endpoint_id=None)
    assert entity._bare_power_fallback_endpoint({}) == 1


def test_bare_power_fallback_endpoint_none_when_brightness_given() -> None:
    device = _unschemed_fan_light_device()
    entity = _FakeFanLightEntity(device, endpoint_id=None)
    assert entity._bare_power_fallback_endpoint({ATTR_BRIGHTNESS: 128}) is None


def test_bare_power_fallback_endpoint_none_when_light_state_has_schema() -> None:
    device = _unschemed_fan_light_device(
        possible_values={
            "change_light_state": {"format": "VALUES", "values": ["ON", "OFF"]},
            "switch_electrical_power": {"format": "VALUES", "values": ["ON", "OFF"]},
        },
    )
    entity = _FakeFanLightEntity(device, endpoint_id=None)
    assert entity._bare_power_fallback_endpoint({}) is None
