"""Unit tests for electrical power state parsing."""

from __future__ import annotations

from enki.helpers import normalize_power_state


def test_normalize_power_state_string() -> None:
    assert normalize_power_state("ON", 2) == "ON"
    assert normalize_power_state("OFF", 2) == "OFF"


def test_normalize_power_state_endpoint_map() -> None:
    assert normalize_power_state({"1": "OFF", "2": "ON"}, 2) == "ON"
    assert normalize_power_state({"1": "ON", "2": "OFF"}, 1) == "ON"


def test_normalize_power_state_single_entry_map() -> None:
    assert normalize_power_state({"2": "ON"}, 2) == "ON"


def test_normalize_power_state_unknown_defaults_off() -> None:
    assert normalize_power_state(None, 2) == "OFF"
    assert normalize_power_state(42, 2) == "OFF"
