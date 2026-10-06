"""Optimistic state lands before the command, not after it (#296)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from enki.coordinator import EnkiCoordinator
from enki.domain.models import EnkiDevice
from enki.switch import EnkiOutletSwitch


def _device(**reported) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-plug",
        device_name="Prise",
        device_type="outlets",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["switch_electrical_power", "check_electrical_power"],
        last_reported_value={"power": "OFF", "electrical_power": "OFF", **reported},
    )


def _coordinator(device: EnkiDevice) -> EnkiCoordinator:
    coordinator = EnkiCoordinator.__new__(EnkiCoordinator)
    coordinator.data = [device]
    coordinator._overrides = {}
    coordinator._suspend_notify = False
    coordinator._fan_light_restore = {}
    coordinator.hass = MagicMock()
    coordinator.api = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    return coordinator


@pytest.mark.asyncio
async def test_the_state_is_written_while_the_command_is_still_in_flight() -> None:
    """The cloud takes seconds; waiting for it leaves the entity showing the old value."""
    device = _device()
    coordinator = _coordinator(device)
    in_flight = asyncio.Event()
    seen_during_call: list[str | None] = []

    async def slow_command(*args, **kwargs):
        seen_during_call.append(device.last_reported_value.get("power"))
        in_flight.set()
        await asyncio.sleep(0)

    coordinator.api.async_switch_electrical_power = slow_command
    switch = EnkiOutletSwitch(coordinator, device, endpoint_id=None, suffix="")

    await switch.async_turn_on()

    assert in_flight.is_set()
    assert seen_during_call == ["ON"]


@pytest.mark.asyncio
async def test_a_failed_command_puts_the_state_back() -> None:
    """Otherwise the entity would show a state the device never took."""
    device = _device()
    coordinator = _coordinator(device)

    async def refused(*args, **kwargs):
        raise RuntimeError("gateway said no")

    coordinator.api.async_switch_electrical_power = refused
    switch = EnkiOutletSwitch(coordinator, device, endpoint_id=None, suffix="")

    with pytest.raises(RuntimeError):
        await switch.async_turn_on()

    assert device.last_reported_value["power"] == "OFF"
    assert device.last_reported_value["electrical_power"] == "OFF"
    assert coordinator._overrides == {}


@pytest.mark.asyncio
async def test_a_failure_does_not_discard_an_earlier_held_value() -> None:
    """A refused command must only undo its own write."""
    device = _device()
    coordinator = _coordinator(device)
    coordinator.update_cached_value("node-plug", "brightness", 0.5)

    async def refused(*args, **kwargs):
        raise RuntimeError("gateway said no")

    coordinator.api.async_switch_electrical_power = refused
    switch = EnkiOutletSwitch(coordinator, device, endpoint_id=None, suffix="")

    with pytest.raises(RuntimeError):
        await switch.async_turn_on()

    assert device.last_reported_value["brightness"] == 0.5
    assert ("top", "brightness") in coordinator._overrides["node-plug"]
