"""Two independent light kits on a single ceiling fan (Inspire Cadix, AD_TCFL_1).

The Cadix drives its motor via change_fan_speed and exposes two light circuits
through switch_electrical_power on endpoints 1 and 3, while the electrical-power
service also reports the motor on the unlisted endpoint 2. Each light must map
to its own Home Assistant entity with independent per-endpoint on/off state.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.light import EnkiFanLightEntity, _build_light_entities


def _cadix(**overrides) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "AD_TCFL_1",
        "node_id": "node-cadix",
        "device_name": "Inspire Cadix",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "change_fan_speed",
            "change_light_state",
            "check_light_state",
            "switch_electrical_power",
        ],
        "possible_values": {
            "change_fan_speed": {"format": "RANGE", "range": {"min": 0.0, "max": 6.0}},
            "switch_electrical_power": {"format": "VALUES", "values": ["ON", "OFF"]},
        },
        "main_change_capability_id": "switch_electrical_power",
        "main_change_capability_endpoints": [1, 3],
        "last_reported_value": {
            "electrical_endpoints": [
                {"id": 1, "lastReportedValue": "ON"},
                {"id": 2, "lastReportedValue": "ON"},
                {"id": 3, "lastReportedValue": "OFF"},
            ],
        },
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.api.async_change_light_state = AsyncMock()
    coordinator.update_endpoint_power = MagicMock()
    coordinator.update_cached_value = MagicMock()
    return coordinator


def test_cadix_builds_two_independent_light_entities() -> None:
    entities = _build_light_entities(_coordinator(), _cadix())
    assert len(entities) == 2
    assert all(isinstance(entity, EnkiFanLightEntity) for entity in entities)
    endpoints = sorted(entity._endpoint_id for entity in entities)
    assert endpoints == [1, 3]
    # Distinct unique ids and numbered names so both are addressable in HA.
    assert len({entity._attr_unique_id for entity in entities}) == 2
    assert {entity._attr_translation_key for entity in entities} == {"fan_light_numbered"}
    assert {entity._attr_translation_placeholders["number"] for entity in entities} == {"1", "2"}


def test_cadix_light_is_on_reads_its_own_endpoint() -> None:
    device = _cadix()
    light_1 = EnkiFanLightEntity(_coordinator(), device, endpoint_id=1, suffix="light_a")
    light_3 = EnkiFanLightEntity(_coordinator(), device, endpoint_id=3, suffix="light_b")
    assert light_1.is_on is True  # endpoint 1 reported ON
    assert light_3.is_on is False  # endpoint 3 reported OFF


@pytest.mark.asyncio
async def test_cadix_turn_on_targets_only_its_endpoint() -> None:
    coordinator = _coordinator()
    device = _cadix()
    light_3 = EnkiFanLightEntity(coordinator, device, endpoint_id=3, suffix="light_b")

    await light_3.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-cadix", "ON", endpoint=3
    )
    coordinator.api.async_change_light_state.assert_not_called()


@pytest.mark.asyncio
async def test_cadix_turn_off_targets_only_its_endpoint() -> None:
    coordinator = _coordinator()
    device = _cadix()
    light_1 = EnkiFanLightEntity(coordinator, device, endpoint_id=1, suffix="light_a")

    await light_1.async_turn_off()

    # No schema on change_light_state → per-endpoint power, not a global off.
    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-cadix", "OFF", endpoint=1
    )
    coordinator.api.async_change_light_state.assert_not_called()
    coordinator.update_endpoint_power.assert_called_once_with("node-cadix", 1, "OFF")
