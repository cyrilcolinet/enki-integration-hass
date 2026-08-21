"""Unit tests for EnkiDeviceState accessors."""

from __future__ import annotations

from enki.domain.state import EnkiDeviceState


def test_endpoint_power_reads_string_value() -> None:
    state = EnkiDeviceState(
        {
            "electrical_endpoints": [
                {"id": 2, "lastReportedValue": "ON"},
                {"id": 3, "lastReportedValue": "OFF"},
            ]
        }
    )
    assert state.endpoint_power(2) == "ON"
    assert state.endpoint_power(3) == "OFF"


def test_light_endpoints_have_mixed_power() -> None:
    state = EnkiDeviceState(
        {
            "electrical_endpoints": [
                {"id": 2, "lastReportedValue": "ON"},
                {"id": 3, "lastReportedValue": "OFF"},
            ]
        }
    )
    assert state.light_endpoints_have_mixed_power([2, 3]) is True
    assert state.light_endpoints_have_mixed_power([2]) is False


def test_fan_kit_light_power_prefers_light_power_field() -> None:
    state = EnkiDeviceState({"light_power": "OFF", "power": "ON"})
    assert state.light_power == "OFF"
