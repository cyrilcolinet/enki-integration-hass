"""Unit tests for ESDK fan light on/off state merge in change-light-state."""

from __future__ import annotations

from enki.lib.conversion import merge_light_state_payload


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


def test_merge_light_state_payload_color_temp_sets_ct_mode() -> None:
    current = {"power": "ON", "colorMode": "hs", "hue": 0.5, "saturation": 0.8}
    payload = merge_light_state_payload(current, {"colorTemperature": "T3500K"})
    assert payload["colorMode"] == "ct"
    assert payload["colorTemperature"] == "T3500K"


def test_fan_light_power_from_lighting_last_reported() -> None:
    last_reported = {"power": "OFF", "brightness": 0.2}
    assert last_reported.get("power", "OFF") == "OFF"
