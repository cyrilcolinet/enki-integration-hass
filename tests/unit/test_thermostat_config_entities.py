"""Unit tests for thermostat config knobs: offset, child-lock, preheating.

Routes and enum values come from the Enki app (2.26.x): all three live on the
already-wired ``api-enki-thermostat-prod`` service. child-lock is LOCK/UNLOCK,
preheating-status is ENABLED/DISABLED, offset-temperature is a float °C.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.api.capability_routing import CAPABILITY_READS
from enki.api.gateway_registry import WIRED_PATH_PREFIXES
from enki.domain.capabilities import EnkiCapabilityProfile
from enki.domain.models import EnkiDevice
from enki.lib.capability_path import capability_to_path_segment
from enki.lib.heating import offset_temperature_range
from enki.number import EnkiOffsetTemperatureNumber
from enki.switch import EnkiConfigSwitch, _build_switch_entities

THERMO_CAPS = [
    "change_thermostat_target_temperature",
    "check_thermostat_target_temperature",
    "change_offset_temperature",
    "check_offset_temperature",
    "change_child_lock",
    "check_child_lock",
    "change_preheating_status",
    "check_preheating_status",
]


def _thermo_device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-thermo",
        "device_name": "Thermostat",
        "device_type": "heaters_and_pilot_wires",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": list(THERMO_CAPS),
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
    coordinator.api.async_set_capability_value = AsyncMock()
    return coordinator


def _route(transport_id: str, capability: str) -> str | None:
    for read in CAPABILITY_READS:
        if read.transport_id == transport_id and read.capability == capability:
            prefix = WIRED_PATH_PREFIXES[transport_id]
            return f"{prefix}/{{nodeId}}/{capability_to_path_segment(capability)}"
    return None


# --- capability gates -------------------------------------------------------


def test_profile_gates_detect_the_three_knobs() -> None:
    profile = _thermo_device().profile
    assert profile.supports_offset_temperature
    assert profile.supports_child_lock
    assert profile.supports_preheating
    # child-lock + preheating flow through the config-switch platform.
    assert profile.is_config_switch


def test_gates_absent_without_capabilities() -> None:
    profile = EnkiCapabilityProfile(
        device_type="heaters_and_pilot_wires",
        capabilities=frozenset(["check_thermostat_target_temperature"]),
        possible_values={},
        bff_device_type="heaters_and_pilot_wires",
    )
    assert not profile.supports_offset_temperature
    assert not profile.supports_child_lock
    assert not profile.supports_preheating


# --- reads ------------------------------------------------------------------


def test_reads_route_to_thermostat_prod() -> None:
    assert _route("thermostat", "check_offset_temperature") == (
        "/api-enki-thermostat-prod/v1/heating/{nodeId}/check-offset-temperature"
    )
    assert _route("thermostat", "check_child_lock") == (
        "/api-enki-thermostat-prod/v1/heating/{nodeId}/check-child-lock"
    )
    assert _route("thermostat", "check_preheating_status") == (
        "/api-enki-thermostat-prod/v1/heating/{nodeId}/check-preheating-status"
    )


# --- offset number ----------------------------------------------------------


def test_offset_range_default_and_from_possible_values() -> None:
    assert offset_temperature_range({}) == (-5.0, 5.0, 0.5)
    meta = {"change_offset_temperature": {"range": {"min": -3, "max": 3, "step": 0.1}}}
    assert offset_temperature_range(meta) == (-3.0, 3.0, 0.1)


def test_offset_number_reads_and_writes_float() -> None:
    device = _thermo_device(last_reported_value={"offset_temperature": 1.5})
    coordinator = _coordinator_for_device(device)
    entity = EnkiOffsetTemperatureNumber(coordinator, device)

    assert entity._attr_unique_id == "enki-node-thermo-offset-temperature"  # noqa: SLF001
    assert entity.native_value == 1.5


@pytest.mark.asyncio
async def test_offset_number_set_posts_change_offset_temperature() -> None:
    device = _thermo_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiOffsetTemperatureNumber(coordinator, device)

    await entity.async_set_native_value(-2.0)

    coordinator.api.async_set_capability_value.assert_awaited_once_with(
        "home-1",
        "node-thermo",
        "thermostat",
        "change_offset_temperature",
        -2.0,
    )
    coordinator.update_cached_value.assert_called_once_with(
        "node-thermo",
        "offset_temperature",
        -2.0,
    )


# --- child-lock + preheating switches ---------------------------------------


def _config_switch(device: EnkiDevice, suffix: str) -> EnkiConfigSwitch:
    coordinator = _coordinator_for_device(device)
    entities = [
        entity
        for entity in _build_switch_entities(coordinator, device)
        if isinstance(entity, EnkiConfigSwitch) and entity._attr_unique_id.endswith(suffix)  # noqa: SLF001
    ]
    assert len(entities) == 1
    return entities[0]


def test_child_lock_switch_maps_lock_unlock() -> None:
    locked = _config_switch(
        _thermo_device(last_reported_value={"child_lock": "LOCK"}), "child_lock"
    )
    unlocked = _config_switch(
        _thermo_device(last_reported_value={"child_lock": "UNLOCK"}), "child_lock"
    )
    assert locked.is_on is True
    assert unlocked.is_on is False


@pytest.mark.asyncio
async def test_child_lock_turn_on_posts_lock() -> None:
    device = _thermo_device()
    entity = _config_switch(device, "child_lock")
    await entity.async_turn_on()
    entity.coordinator.api.async_set_capability_value.assert_awaited_once_with(
        "home-1",
        "node-thermo",
        "thermostat",
        "change_child_lock",
        "LOCK",
    )


def test_preheating_switch_maps_enabled_disabled() -> None:
    on = _config_switch(
        _thermo_device(last_reported_value={"preheating_status": "ENABLED"}), "preheating"
    )
    off = _config_switch(
        _thermo_device(last_reported_value={"preheating_status": "DISABLED"}), "preheating"
    )
    assert on.is_on is True
    assert off.is_on is False


@pytest.mark.asyncio
async def test_preheating_turn_off_posts_disabled() -> None:
    device = _thermo_device()
    entity = _config_switch(device, "preheating")
    await entity.async_turn_off()
    entity.coordinator.api.async_set_capability_value.assert_awaited_once_with(
        "home-1",
        "node-thermo",
        "thermostat",
        "change_preheating_status",
        "DISABLED",
    )
