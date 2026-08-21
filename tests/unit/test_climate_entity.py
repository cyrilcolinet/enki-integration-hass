"""Unit tests for the thermostat climate entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.climate import EnkiThermostatClimate
from enki.domain.models import EnkiDevice
from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "Radiator",
        "device_type": "heaters_and_pilot_wires",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["change_thermostat_target_temperature"],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _entity(reported: dict) -> EnkiThermostatClimate:
    device = _device(last_reported_value=reported)
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    coordinator.update_cached_value = MagicMock()
    coordinator.api.async_set_thermostat_target_temperature = AsyncMock()
    return EnkiThermostatClimate(coordinator, device)


def test_reports_current_and_target_temperature() -> None:
    e = _entity({"current_temperature": 20.5, "thermostat_target_temperature": 21.0})
    assert e.current_temperature == 20.5
    assert e.target_temperature == 21.0


def test_hvac_mode_off_at_frost_setpoint() -> None:
    # default range min is 7 °C → target at/below that is "off".
    assert _entity({"thermostat_target_temperature": 7.0}).hvac_mode == HVACMode.OFF
    assert _entity({"thermostat_target_temperature": 20.0}).hvac_mode == HVACMode.HEAT


def test_hvac_action_maps_running_state() -> None:
    assert _entity({"thermostat_running_state": "HEAT"}).hvac_action == HVACAction.HEATING
    assert _entity({"thermostat_running_state": "IDLE"}).hvac_action == HVACAction.IDLE
    assert _entity({}).hvac_action is None


@pytest.mark.asyncio
async def test_set_temperature_posts_and_caches() -> None:
    e = _entity({})
    await e.async_set_temperature(**{ATTR_TEMPERATURE: 19.5})
    e.coordinator.api.async_set_thermostat_target_temperature.assert_awaited_once_with(
        "home-1", "node-1", 19.5
    )
    e.coordinator.update_cached_value.assert_called_once_with(
        "node-1", "thermostat_target_temperature", 19.5
    )


@pytest.mark.asyncio
async def test_set_temperature_ignored_without_value() -> None:
    e = _entity({})
    await e.async_set_temperature()
    e.coordinator.api.async_set_thermostat_target_temperature.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_hvac_off_drops_to_frost() -> None:
    e = _entity({"thermostat_target_temperature": 21.0})
    await e.async_set_hvac_mode(HVACMode.OFF)
    # off → target set to the range minimum (7 °C default).
    args = e.coordinator.api.async_set_thermostat_target_temperature.await_args.args
    assert args[2] == 7.0


@pytest.mark.asyncio
async def test_set_hvac_heat_from_off_sets_default_target() -> None:
    e = _entity({"thermostat_target_temperature": 7.0})
    await e.async_set_hvac_mode(HVACMode.HEAT)
    args = e.coordinator.api.async_set_thermostat_target_temperature.await_args.args
    assert args[2] > 7.0
