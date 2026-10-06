"""Home Assistant hears about the optimistic write before the command returns (#296)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from enki.coordinator import EnkiCoordinator
from enki.domain.models import EnkiDevice
from enki.light import EnkiFanLightEntity


def _cadix() -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-cadix",
        device_name="Ventilateur",
        device_type="ceiling_fans",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["switch_electrical_power", "check_electrical_power"],
        main_change_capability_endpoints=[1, 3],
        last_reported_value={
            "power": "ON",
            "light_power": "ON",
            "electrical_endpoints": [
                {"id": 1, "lastReportedValue": "ON"},
                {"id": 3, "lastReportedValue": "ON"},
            ],
        },
    )


def _coordinator(device: EnkiDevice, refreshes: list) -> EnkiCoordinator:
    coordinator = EnkiCoordinator.__new__(EnkiCoordinator)
    coordinator.data = [device]
    coordinator._overrides = {}
    coordinator._suspend_notify = False
    coordinator._fan_light_restore = {}
    coordinator.hass = MagicMock()
    coordinator.api = MagicMock()
    coordinator.async_set_updated_data = lambda data: refreshes.append(data)
    coordinator.async_request_refresh = MagicMock()
    return coordinator


@pytest.mark.asyncio
async def test_the_refresh_reaches_home_assistant_before_the_command_returns() -> None:
    """Writing the cache is not enough: a batch that spans the await hides it."""
    device = _cadix()
    refreshes: list = []
    coordinator = _coordinator(device, refreshes)
    seen_during_call: list[int] = []

    async def slow_command(*args, **kwargs):
        seen_during_call.append(len(refreshes))

    coordinator.api.async_switch_electrical_power = slow_command
    light = EnkiFanLightEntity(coordinator, device, endpoint_id=1, suffix="main")

    await light.async_turn_off()

    assert seen_during_call == [1], "Home Assistant was told only after the command returned"
