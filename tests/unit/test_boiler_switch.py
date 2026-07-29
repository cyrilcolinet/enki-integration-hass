"""Unit tests for the water-heater on/off relay exposed as a switch (#87)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.switch import EnkiBoilerSwitch, _build_switch_entities
from homeassistant.components.switch import SwitchDeviceClass


def _boiler_device(**kwargs) -> EnkiDevice:
    """The re-skinned relay: type `boiler`, empty referentiel, no control hints."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-boiler",
        "device_name": "Chauffe-eau",
        "device_type": "boiler",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [],
        "main_change_capability_id": None,
    }
    defaults.update(kwargs)
    return EnkiDevice(**defaults)


def _coordinator_for_device(device: EnkiDevice) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = [device]
    coordinator.get_device_by_node = lambda node_id: next(
        (entry for entry in coordinator.data if entry.node_id == node_id),
        None,
    )
    coordinator.update_cached_value = MagicMock()
    coordinator.update_endpoint_power = MagicMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    return coordinator


def test_boiler_device_builds_a_single_switch() -> None:
    device = _boiler_device()
    entities = _build_switch_entities(_coordinator_for_device(device), device)

    assert len(entities) == 1
    entity = entities[0]
    assert isinstance(entity, EnkiBoilerSwitch)
    assert entity._attr_device_class == SwitchDeviceClass.SWITCH  # noqa: SLF001
    assert entity._attr_translation_key == "boiler"  # noqa: SLF001
    assert entity._attr_unique_id == "enki-node-boiler-boiler"  # noqa: SLF001


@pytest.mark.asyncio
async def test_boiler_switch_turn_on_calls_power_api_without_endpoint() -> None:
    device = _boiler_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiBoilerSwitch(coordinator, device)

    await entity.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1",
        "node-boiler",
        "ON",
        endpoint=None,
    )
    # No endpoint → cache the node-level power, not an endpoint slot.
    coordinator.update_endpoint_power.assert_not_called()


@pytest.mark.asyncio
async def test_boiler_switch_turn_off_calls_power_api() -> None:
    device = _boiler_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiBoilerSwitch(coordinator, device)

    await entity.async_turn_off()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1",
        "node-boiler",
        "OFF",
        endpoint=None,
    )


def test_boiler_switch_reflects_reported_power() -> None:
    on = EnkiBoilerSwitch(
        _coordinator_for_device(_boiler_device(last_reported_value={"power": "ON"})),
        _boiler_device(last_reported_value={"power": "ON"}),
    )
    off = EnkiBoilerSwitch(
        _coordinator_for_device(_boiler_device(last_reported_value={"power": "OFF"})),
        _boiler_device(last_reported_value={"power": "OFF"}),
    )
    unknown = EnkiBoilerSwitch(
        _coordinator_for_device(_boiler_device()),
        _boiler_device(),
    )

    assert on.is_on is True
    assert off.is_on is False
    assert unknown.is_on is None
