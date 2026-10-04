"""Equation water heater operating mode, read-only (#285)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.domain.models import EnkiDevice
from enki.sensor import WATER_HEATER_MODES, EnkiWaterHeaterModeSensor

HEATER_CAPABILITIES = [
    "check_water_heater_mode",
    "check_water_heater_error",
    "change_thermostat_target_temperature",
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
        last_reported_value=reported,
    )


def _sensor(device: EnkiDevice) -> EnkiWaterHeaterModeSensor:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    return EnkiWaterHeaterModeSensor(coordinator, device)


def test_the_mode_the_device_reports_becomes_the_state() -> None:
    sensor = _sensor(_heater(water_heater_mode="SELF_CLEAN"))

    assert sensor.native_value == "self_clean"
    # `options` is a SensorEntity property, stubbed away here — assert what we set.
    assert sensor._attr_options == ["auto", "boost", "boost_plus", "eco", "manual", "self_clean"]


def test_a_mode_outside_the_options_is_dropped() -> None:
    """A state outside `options` makes HA log an error on every poll."""
    sensor = _sensor(_heater(water_heater_mode="VACATION"))

    assert sensor.native_value is None


def test_nothing_reported_yet_is_unknown() -> None:
    assert _sensor(_heater()).native_value is None


def test_only_a_heater_that_advertises_the_capability_gets_the_sensor() -> None:
    assert _heater().profile.supports_water_heater_mode is True
    assert _heater(capabilities=["switch_electrical_power"]).profile.supports_water_heater_mode is (
        False
    )


def test_the_read_is_wired_to_its_own_service() -> None:
    """The route lives on api-enki-equation-water-heater-prod, not the thermostat."""
    read = next(r for r in CAPABILITY_READS if r.capability == "check_water_heater_mode")

    assert read.transport_id == "equation_water_heater"
    assert read.state_key == "water_heater_mode"
    assert read.skip is not None
    assert read.skip(_heater(capabilities=["switch_electrical_power"]).profile) is True
    assert read.skip(_heater().profile) is False


def test_the_modes_match_what_the_app_offers() -> None:
    assert WATER_HEATER_MODES == ("AUTO", "BOOST", "BOOST_PLUS", "ECO", "MANUAL", "SELF_CLEAN")
