"""Equation water heater operating mode, read-only (#285)."""

from __future__ import annotations

from unittest.mock import MagicMock

from enki.api.capability_routing import CAPABILITY_READS
from enki.domain.models import EnkiDevice
from enki.lib.heating import WATER_HEATER_MODES, water_heater_mode_options
from enki.sensor import EnkiWaterHeaterModeSensor

HEATER_CAPABILITIES = [
    "check_water_heater_mode",
    "check_water_heater_error",
    "change_thermostat_target_temperature",
]

# What an AD-HEWH3-1 (firmware 2.14.0) publishes in its referentiel, from diagnostics.
HEATER_MODES = ["AUTO", "MANUAL", "BOOST", "BOOST_PLUS", "PROG", "CLEAN"]
HEATER_POSSIBLE_VALUES = {
    "check_water_heater_mode": {"values": HEATER_MODES},
    "change_water_heater_mode": {"values": HEATER_MODES},
}


def _heater(
    capabilities: list[str] | None = None,
    possible_values: dict | None = None,
    **reported,
) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-wh",
        device_name="Water heater",
        device_type="water_heaters",
        is_enabled=True,
        state="ACTIVE",
        capabilities=HEATER_CAPABILITIES if capabilities is None else capabilities,
        # `_supports` also reads possible_values, so a relay-only device gets none.
        possible_values=(
            possible_values
            if possible_values is not None
            else HEATER_POSSIBLE_VALUES
            if capabilities is None
            else {}
        ),
        last_reported_value=reported,
    )


def _sensor(device: EnkiDevice) -> EnkiWaterHeaterModeSensor:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    return EnkiWaterHeaterModeSensor(coordinator, device)


def test_the_mode_the_device_reports_becomes_the_state() -> None:
    sensor = _sensor(_heater(water_heater_mode="CLEAN"))

    assert sensor.native_value == "clean"
    # `options` is a SensorEntity property, stubbed away here — assert what we set.
    assert sensor._attr_options == ["auto", "manual", "boost", "boost_plus", "prog", "clean"]


def test_the_options_are_what_the_heater_declares() -> None:
    """Self-clean goes over the wire as CLEAN; a hardcoded SELF_CLEAN read unknown."""
    declared = {"check_water_heater_mode": {"values": ["MANUAL", "CLEAN"]}}

    sensor = _sensor(_heater(possible_values=declared, water_heater_mode="CLEAN"))

    assert sensor._attr_options == ["manual", "clean"]
    assert sensor.native_value == "clean"


def test_a_heater_that_declares_nothing_falls_back_to_the_known_modes() -> None:
    assert water_heater_mode_options({}) == [mode.lower() for mode in WATER_HEATER_MODES]
    assert water_heater_mode_options({"check_water_heater_mode": {"values": []}}) == [
        mode.lower() for mode in WATER_HEATER_MODES
    ]
    assert water_heater_mode_options({"check_water_heater_mode": {"values": "AUTO"}}) == [
        mode.lower() for mode in WATER_HEATER_MODES
    ]


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


def test_the_fallback_matches_what_the_heater_declares() -> None:
    assert list(WATER_HEATER_MODES) == HEATER_POSSIBLE_VALUES["check_water_heater_mode"]["values"]
