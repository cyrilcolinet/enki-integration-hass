"""Unit tests for the pilot-wire and roller-shutter-mode selects."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.select import EnkiPilotWireSelect, EnkiRollerShutterModeSelect


def _device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "Heater",
        "device_type": "heaters_and_pilot_wires",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [],
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _coordinator(device: EnkiDevice) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    coordinator.update_cached_value = MagicMock()
    coordinator.api.async_set_pilot_wire_mode = AsyncMock()
    coordinator.api.async_set_roller_shutter_mode = AsyncMock()
    return coordinator


# --- pilot wire -------------------------------------------------------------


def test_pilot_wire_default_options_and_current() -> None:
    device = _device(last_reported_value={"pilot_wire_state": "ECO"})
    entity = EnkiPilotWireSelect(_coordinator(device), device)
    assert "eco" in entity._attr_options  # noqa: SLF001
    assert entity.current_option == "eco"


def test_pilot_wire_current_none_when_unknown_value() -> None:
    device = _device(last_reported_value={"pilot_wire_state": 123})
    assert EnkiPilotWireSelect(_coordinator(device), device).current_option is None


@pytest.mark.asyncio
async def test_pilot_wire_select_posts_uppercase() -> None:
    device = _device()
    coordinator = _coordinator(device)
    await EnkiPilotWireSelect(coordinator, device).async_select_option("comfort")
    coordinator.api.async_set_pilot_wire_mode.assert_awaited_once_with(
        "home-1", "node-1", "COMFORT"
    )
    coordinator.update_cached_value.assert_called_once_with("node-1", "pilot_wire_state", "COMFORT")


# --- roller shutter mode ----------------------------------------------------


def test_shutter_mode_options_and_current() -> None:
    device = _device(last_reported_value={"roller_shutter_mode": "INVERTED"})
    entity = EnkiRollerShutterModeSelect(_coordinator(device), device)
    assert entity._attr_options == ["normal", "inverted"]  # noqa: SLF001
    assert entity.current_option == "inverted"


@pytest.mark.asyncio
async def test_shutter_mode_select_posts_uppercase() -> None:
    device = _device()
    coordinator = _coordinator(device)
    await EnkiRollerShutterModeSelect(coordinator, device).async_select_option("normal")
    coordinator.api.async_set_roller_shutter_mode.assert_awaited_once_with(
        "home-1", "node-1", "NORMAL"
    )
    coordinator.update_cached_value.assert_called_once_with(
        "node-1", "roller_shutter_mode", "NORMAL"
    )
