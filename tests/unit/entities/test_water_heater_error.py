"""Equation water heater fault code, read-only diagnostic (#352)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.domain.models import EnkiDevice
from enki.domain.telemetry_coverage import capability_is_covered
from enki.domain.telemetry_enrichment import ha_platforms_for_profile
from enki.lib.heating import WATER_HEATER_ERRORS, water_heater_error_options
from enki.sensor import EnkiWaterHeaterErrorSensor, _build_sensor_entities

HEATER_CAPABILITIES = [
    "check_water_heater_mode",
    "check_water_heater_error",
    "check_instant_power_consumption",
    "check_electrical_consumption",
    "change_thermostat_target_temperature",
]

HEATER_ERRORS = [
    "NO_ERROR",
    "NO_WATER",
    "LEFT_TANK_SENSOR_MALFUNCTION",
    "RIGHT_TANK_SENSOR_MALFUNCTION",
]


def _heater(capabilities: list[str] | None = None, **reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-wh",
        device_name="Water heater",
        device_type="water_heaters",
        is_enabled=True,
        state="ACTIVE",
        capabilities=HEATER_CAPABILITIES if capabilities is None else capabilities,
        # `_supports` also reads possible_values, so an overridden capability set gets none.
        possible_values=(
            {"check_water_heater_error": {"values": HEATER_ERRORS}} if capabilities is None else {}
        ),
        last_reported_value=reported,
    )


def _sensor(device: EnkiDevice) -> EnkiWaterHeaterErrorSensor:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    return EnkiWaterHeaterErrorSensor(coordinator, device)


def test_the_fault_the_device_reports_becomes_the_state() -> None:
    sensor = _sensor(_heater(water_heater_error="NO_WATER"))

    assert sensor.native_value == "no_water"
    assert sensor._attr_options == [code.lower() for code in HEATER_ERRORS]


def test_a_code_outside_the_options_is_dropped() -> None:
    assert _sensor(_heater(water_heater_error="METEOR_STRIKE")).native_value is None


def test_nothing_reported_yet_is_unknown() -> None:
    assert _sensor(_heater()).native_value is None


def test_a_heater_that_declares_nothing_falls_back_to_the_known_codes() -> None:
    assert water_heater_error_options({}) == [code.lower() for code in WATER_HEATER_ERRORS]


def test_only_a_heater_that_advertises_the_capability_gets_the_sensor() -> None:
    assert _heater().profile.supports_water_heater_error is True
    assert _heater(
        capabilities=["switch_electrical_power"]
    ).profile.supports_water_heater_error is (False)


def test_the_gate_loads_the_sensor_platform_and_builds_the_entity() -> None:
    profile = _heater().profile
    assert "sensor" in ha_platforms_for_profile(profile)

    built = _build_sensor_entities(MagicMock(), _heater())
    assert any(isinstance(e, EnkiWaterHeaterErrorSensor) for e in built)


def test_the_read_is_wired_to_its_own_service() -> None:
    read = next(r for r in CAPABILITY_READS if r.capability == "check_water_heater_error")

    assert read.transport_id == "equation_water_heater"
    assert read.state_key == "water_heater_error"
    assert read.skip(_heater(capabilities=["switch_electrical_power"]).profile) is True
    assert read.skip(_heater().profile) is False


def test_both_fault_and_instant_power_count_as_covered() -> None:
    """A heater that advertises these no longer reports a (false) capability gap (#352)."""
    profile = _heater().profile
    assert capability_is_covered("check_water_heater_error", profile) is True
    assert capability_is_covered("check_instant_power_consumption", profile) is True
