"""Unit tests for Enki cover and shutter preset button entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.button import EnkiImpulseRelayButton, EnkiShutterPresetButton
from enki.cover import EnkiCoverEntity
from enki.domain.models import EnkiDevice
from homeassistant.components.cover import CoverEntityFeature


def _cover_device(**kwargs) -> EnkiDevice:
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-1",
        "node_id": "node-1",
        "device_name": "VR Salon",
        "device_type": "access_and_motorizations",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "change_shutter_position",
            "check_shutter_position",
            "stop_change_shutter_position",
            "check_roller_shutter_state",
        ],
        "last_reported_value": {
            "shutter_position": 42,
            "shutter_opening": "OPEN",
            "roller_shutter_state": "OPENING",
        },
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
    coordinator.api.async_set_shutter_position = AsyncMock()
    coordinator.api.async_switch_roller_shutter = AsyncMock()
    coordinator.api.async_stop_shutter = AsyncMock()
    coordinator.api.async_execute_shutter_preset = AsyncMock()
    coordinator.api.async_power_on_with_timer = AsyncMock()
    return coordinator


def test_cover_supported_features_with_position_and_stop() -> None:
    device = _cover_device()
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    features = entity.supported_features
    assert features & CoverEntityFeature.OPEN
    assert features & CoverEntityFeature.CLOSE
    assert features & CoverEntityFeature.SET_POSITION
    assert features & CoverEntityFeature.STOP


def test_cover_supported_features_without_position() -> None:
    device = _cover_device(
        capabilities=["check_shutter_opening"],
        last_reported_value={"shutter_opening": "CLOSED"},
    )
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    features = entity.supported_features
    assert features & CoverEntityFeature.OPEN
    assert features & CoverEntityFeature.CLOSE
    assert not (features & CoverEntityFeature.SET_POSITION)
    assert not (features & CoverEntityFeature.STOP)


def test_cover_state_properties() -> None:
    device = _cover_device()
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    assert entity.current_cover_position == 42
    assert entity.is_closed is False
    assert entity.is_opening is True
    assert entity.is_closing is False


def test_cover_is_closed_from_position_when_opening_missing() -> None:
    device = _cover_device(
        last_reported_value={"shutter_position": 0},
    )
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    assert entity.is_closed is True


@pytest.mark.asyncio
async def test_cover_open_sets_full_position() -> None:
    device = _cover_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiCoverEntity(coordinator, device)

    await entity.async_open_cover()

    coordinator.api.async_set_shutter_position.assert_awaited_once_with("home-1", "node-1", 100)
    coordinator.update_cached_value.assert_any_call("node-1", "shutter_position", 100)
    coordinator.update_cached_value.assert_any_call("node-1", "shutter_opening", "OPEN")


@pytest.mark.asyncio
async def test_cover_close_sets_zero_position() -> None:
    device = _cover_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiCoverEntity(coordinator, device)

    await entity.async_close_cover()

    coordinator.api.async_set_shutter_position.assert_awaited_once_with("home-1", "node-1", 0)
    coordinator.update_cached_value.assert_any_call("node-1", "shutter_opening", "CLOSED")


@pytest.mark.asyncio
async def test_cover_stop_calls_api_and_caches_state() -> None:
    device = _cover_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiCoverEntity(coordinator, device)

    await entity.async_stop_cover()

    coordinator.api.async_stop_shutter.assert_awaited_once_with("home-1", "node-1")
    coordinator.update_cached_value.assert_called_once_with(
        "node-1",
        "roller_shutter_state",
        "STOPPED",
    )


def _rts_device(**kwargs) -> EnkiDevice:
    """Somfy RTS motorization from issue #96: open/close only, no feedback."""
    return _cover_device(
        capabilities=["switch_roller_shutter", "stop_change_shutter_position"],
        possible_values={"switch_roller_shutter": {"values": ["OPEN", "CLOSED"]}},
        last_reported_value={},
        **kwargs,
    )


def test_rts_cover_is_discovered_and_exposes_open_close_stop() -> None:
    device = _rts_device()
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    assert device.profile.is_cover is True
    features = entity.supported_features
    assert features & CoverEntityFeature.OPEN
    assert features & CoverEntityFeature.CLOSE
    assert features & CoverEntityFeature.STOP
    assert not (features & CoverEntityFeature.SET_POSITION)


def test_rts_cover_has_no_position_and_assumes_its_state() -> None:
    device = _rts_device()
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    assert entity.current_cover_position is None
    assert entity.is_closed is None
    assert entity.assumed_state is True


def test_cover_with_feedback_does_not_assume_its_state() -> None:
    device = _cover_device()
    entity = EnkiCoverEntity(_coordinator_for_device(device), device)

    assert entity.assumed_state is False


@pytest.mark.asyncio
async def test_rts_cover_open_switches_instead_of_setting_position() -> None:
    device = _rts_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiCoverEntity(coordinator, device)

    await entity.async_open_cover()

    coordinator.api.async_switch_roller_shutter.assert_awaited_once_with(
        "home-1",
        "node-1",
        "OPEN",
    )
    coordinator.api.async_set_shutter_position.assert_not_awaited()
    coordinator.update_cached_value.assert_called_once_with("node-1", "shutter_opening", "OPEN")


@pytest.mark.asyncio
async def test_rts_cover_close_switches_and_reports_closed() -> None:
    device = _rts_device()
    coordinator = _coordinator_for_device(device)
    entity = EnkiCoverEntity(coordinator, device)

    await entity.async_close_cover()

    coordinator.api.async_switch_roller_shutter.assert_awaited_once_with(
        "home-1",
        "node-1",
        "CLOSED",
    )
    device.last_reported_value["shutter_opening"] = "CLOSED"
    assert entity.is_closed is True


@pytest.mark.asyncio
async def test_positional_cover_keeps_using_position_api() -> None:
    # Given a shutter that also happens to expose the RTS switch
    device = _cover_device(
        capabilities=[
            "change_shutter_position",
            "check_shutter_position",
            "switch_roller_shutter",
        ],
    )
    coordinator = _coordinator_for_device(device)
    entity = EnkiCoverEntity(coordinator, device)

    # When
    await entity.async_open_cover()

    # Then position stays authoritative
    coordinator.api.async_set_shutter_position.assert_awaited_once_with("home-1", "node-1", 100)
    coordinator.api.async_switch_roller_shutter.assert_not_awaited()


@pytest.mark.asyncio
async def test_shutter_preset_button_press() -> None:
    device = _cover_device(
        capabilities=["execute_preset"],
        possible_values={"execute_preset": {"values": ["MORNING"]}},
    )
    coordinator = _coordinator_for_device(device)
    entity = EnkiShutterPresetButton(coordinator, device, "MORNING")

    await entity.async_press()

    coordinator.api.async_execute_shutter_preset.assert_awaited_once_with(
        "home-1",
        "node-1",
        "MORNING",
    )


@pytest.mark.asyncio
async def test_impulse_relay_button_press() -> None:
    device = _cover_device(capabilities=["power_on_with_timer"])
    coordinator = _coordinator_for_device(device)
    entity = EnkiImpulseRelayButton(coordinator, device)

    await entity.async_press()

    coordinator.api.async_power_on_with_timer.assert_awaited_once_with("home-1", "node-1")
