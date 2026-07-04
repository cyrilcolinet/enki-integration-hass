"""Guard against routing fan lights or lighting-capable nodes to power-prod."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.fan import EnkiFanEntity
from enki.platforms.light.behavior import EnkiLightBehaviorMixin


def _ceiling_fan(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "AD_TCFL_1",
        "node_id": "node-fan",
        "device_name": "Ventilateur",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "change_fan_speed",
            "check_fan_speed",
            "change_light_state",
            "check_light_state",
            "switch_electrical_power",
            "check_electrical_power",
        ],
        "possible_values": {"change_fan_speed": {"range": {"min": 0, "max": 6}}},
        "main_change_capability_id": "switch_electrical_power",
        "main_change_capability_endpoints": [1, 2, 3],
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


class _LightBehaviorStub(EnkiLightBehaviorMixin):
    _brightness_max = 100
    _color_temp_values: list[int] = []

    def __init__(self, device: EnkiDevice) -> None:
        self._device = device


def test_fan_light_endpoints_never_use_power_api() -> None:
    stub = _LightBehaviorStub(_ceiling_fan())
    assert stub._uses_endpoint_power(2) is False
    assert stub._uses_endpoint_power(3) is False


def test_multi_gang_switch_uses_endpoint_power() -> None:
    device = EnkiDevice(
        home_id="home-1",
        device_id="edisio",
        node_id="node-switch",
        device_name="Prise",
        device_type="switches",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["switch_electrical_power", "check_electrical_power"],
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[2, 3],
    )
    stub = _LightBehaviorStub(device)
    assert stub._uses_endpoint_power(2) is True


def test_fan_is_on_ignores_electrical_power_when_speed_supported() -> None:
    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    entity = EnkiFanEntity(
        coordinator,
        _ceiling_fan(last_reported_value={"electrical_power": "ON"}),
    )
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_fan_turn_on_uses_airflow_when_speed_state_missing() -> None:
    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    entity = EnkiFanEntity(coordinator, _ceiling_fan())

    await entity.async_turn_on()

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 1)
    coordinator.api.async_switch_electrical_power.assert_not_called()


@pytest.mark.asyncio
async def test_fan_turn_off_uses_airflow_when_speed_state_missing() -> None:
    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    entity = EnkiFanEntity(coordinator, _ceiling_fan())

    await entity.async_turn_off()

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 0)
    coordinator.api.async_switch_electrical_power.assert_not_called()


@pytest.mark.asyncio
async def test_fan_turn_on_falls_back_to_power_without_fan_speed_capability() -> None:
    device = EnkiDevice(
        home_id="home-1",
        device_id="simple_fan",
        node_id="node-1",
        device_name="Fan",
        device_type="ceiling_fans",
        is_enabled=True,
        state="ACTIVE",
        capabilities=[
            "switch_electrical_power",
            "check_electrical_power",
            "change_airflow_mode",
            "check_airflow_mode",
        ],
    )
    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    coordinator.update_endpoint_power = MagicMock()
    entity = EnkiFanEntity(coordinator, device)

    await entity.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1",
        "node-1",
        "ON",
        endpoint=None,
    )
    coordinator.api.async_set_fan_speed.assert_not_called()


@pytest.mark.asyncio
async def test_fan_turn_on_uses_power_with_motor_endpoint_when_speed_is_read_only() -> None:
    device = EnkiDevice(
        home_id="home-1",
        device_id="air_fort",
        node_id="node-air-fort",
        device_name="Ventilateur",
        device_type="ceiling_fans",
        is_enabled=True,
        state="ACTIVE",
        capabilities=[
            "check_fan_speed",
            "switch_electrical_power",
            "check_electrical_power",
            "change_light_state",
            "check_light_state",
        ],
        main_change_capability_id="switch_electrical_power",
        main_change_capability_endpoints=[1, 2],
        possible_values={"check_fan_speed": {"range": {"min": 0, "max": 6}}},
    )
    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    coordinator.update_endpoint_power = MagicMock()
    entity = EnkiFanEntity(coordinator, device)

    await entity.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1",
        "node-air-fort",
        "ON",
        endpoint=1,
    )
    coordinator.api.async_set_fan_speed.assert_not_called()


@pytest.mark.asyncio
async def test_fan_set_speed_falls_back_to_power_on_airflow_403() -> None:
    from enki.exceptions import EnkiConnectionError

    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock(
        side_effect=EnkiConnectionError("forbidden", status=403, service="airflow"),
    )
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    coordinator.update_endpoint_power = MagicMock()
    entity = EnkiFanEntity(
        coordinator,
        _ceiling_fan(
            possible_values={"change_fan_speed": {"range": {"min": 0, "max": 6}}},
        ),
    )

    await entity.async_turn_on()

    coordinator.api.async_set_fan_speed.assert_awaited_once()
    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1",
        "node-fan",
        "ON",
        endpoint=1,
    )
