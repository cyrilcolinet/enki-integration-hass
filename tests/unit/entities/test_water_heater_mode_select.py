"""Equation water heater mode as a control (#285)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.select import EnkiWaterHeaterModeSelect
from enki.sensor import EnkiWaterHeaterModeSensor, _build_sensor_entities

MODES = ["AUTO", "MANUAL", "BOOST", "BOOST_PLUS", "PROG", "CLEAN"]


def _heater(*, writable: bool = True, **reported) -> EnkiDevice:
    capabilities = ["check_water_heater_mode", "change_thermostat_target_temperature"]
    possible_values = {"check_water_heater_mode": {"values": MODES}}
    if writable:
        capabilities.append("change_water_heater_mode")
        possible_values["change_water_heater_mode"] = {"values": MODES}
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-wh",
        device_name="Water heater",
        device_type="water_heaters",
        is_enabled=True,
        state="ACTIVE",
        capabilities=capabilities,
        possible_values=possible_values,
        last_reported_value=reported,
    )


def _coordinator(device: EnkiDevice) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = [device]
    coordinator.get_device_by_node = lambda node_id: device
    coordinator.api.async_set_water_heater_mode = AsyncMock()
    return coordinator


def test_the_options_are_the_modes_the_heater_declares() -> None:
    device = _heater(water_heater_mode="MANUAL")
    select = EnkiWaterHeaterModeSelect(_coordinator(device), device)

    assert select._attr_options == ["auto", "manual", "boost", "boost_plus", "prog", "clean"]
    assert select.current_option == "manual"


def test_a_mode_outside_the_options_is_no_option() -> None:
    device = _heater(water_heater_mode="VACATION")

    assert EnkiWaterHeaterModeSelect(_coordinator(device), device).current_option is None


@pytest.mark.asyncio
async def test_choosing_a_mode_writes_it_and_holds_it_until_the_heater_catches_up() -> None:
    device = _heater(water_heater_mode="MANUAL")
    coordinator = _coordinator(device)
    select = EnkiWaterHeaterModeSelect(coordinator, device)

    await select.async_select_option("clean")

    coordinator.api.async_set_water_heater_mode.assert_awaited_once_with(
        "home-1", "node-wh", "CLEAN"
    )
    # The heater reported a new mode minutes after the write, not seconds.
    coordinator.update_cached_value.assert_called_once_with(
        "node-wh", "water_heater_mode", "CLEAN", hold_seconds=300.0
    )


def test_a_writable_heater_gets_the_select_instead_of_the_sensor() -> None:
    writable = _heater()
    read_only = _heater(writable=False)

    assert writable.profile.supports_water_heater_mode_change is True
    assert read_only.profile.supports_water_heater_mode_change is False
    assert not any(
        isinstance(entity, EnkiWaterHeaterModeSensor)
        for entity in _build_sensor_entities(_coordinator(writable), writable)
    )
    assert any(
        isinstance(entity, EnkiWaterHeaterModeSensor)
        for entity in _build_sensor_entities(_coordinator(read_only), read_only)
    )
