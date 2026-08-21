"""Coverage for the EnkiFanEntity: speed, presets, direction, and power fans."""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.fan import EnkiFanEntity, async_setup_entry
from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntityFeature,
)


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.api.async_set_fan_speed = AsyncMock()
    coordinator.api.async_set_fan_rotation = AsyncMock()
    coordinator.api.async_set_airflow_mode = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    coordinator.update_endpoint_power = MagicMock()
    coordinator.request_reconcile = MagicMock()
    coordinator.remember_fan_light_state = MagicMock()
    coordinator.pop_fan_light_state = MagicMock(return_value=None)
    coordinator.batch_updates = MagicMock(return_value=nullcontext())
    return coordinator


def _speed_fan(**overrides) -> EnkiDevice:
    """Speed-controlled fan (writable range) with airflow presets and rotation."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-fan",
        "node_id": "node-fan",
        "device_name": "Inspire Siroco",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "change_fan_speed",
            "change_fan_rotation_direction",
            "change_airflow_mode",
        ],
        "possible_values": {
            "change_fan_speed": {"format": "RANGE", "range": {"min": 0.0, "max": 6.0}},
            "change_airflow_mode": {
                "format": "VALUES",
                "values": ["MANUAL", "BREEZE", "BOOST"],
            },
        },
        "last_reported_value": {},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def _power_fan(**overrides) -> EnkiDevice:
    """Power-controlled fan without a writable speed range (ON/OFF only)."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-pfan",
        "node_id": "node-pfan",
        "device_name": "Basic Fan",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["switch_electrical_power"],
        "possible_values": {},
        "last_reported_value": {},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


# --- setup / features --------------------------------------------------------


def test_setup_entry_creates_one_fan_per_fan_device() -> None:
    coordinator = _coordinator()
    coordinator.data = [_speed_fan(), _power_fan()]
    entry = MagicMock()
    entry.runtime_data = coordinator
    added: list = []

    import asyncio

    asyncio.run(async_setup_entry(MagicMock(), entry, lambda entities: added.extend(entities)))

    assert len(added) == 2
    assert all(isinstance(entity, EnkiFanEntity) for entity in added)


def test_supported_features_speed_fan_has_speed_direction_preset() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan())
    features = fan.supported_features
    assert features & FanEntityFeature.TURN_ON
    assert features & FanEntityFeature.TURN_OFF
    assert features & FanEntityFeature.SET_SPEED
    assert features & FanEntityFeature.DIRECTION
    assert features & FanEntityFeature.PRESET_MODE


def test_supported_features_power_fan_has_no_speed() -> None:
    fan = EnkiFanEntity(_coordinator(), _power_fan())
    features = fan.supported_features
    assert features & FanEntityFeature.TURN_ON
    assert not features & FanEntityFeature.SET_SPEED


def test_speed_count_and_max_speed() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan())
    assert fan.speed_count == 6
    assert fan._max_fan_speed == 6  # noqa: SLF001


# --- presets -----------------------------------------------------------------


def test_preset_modes_listed_from_metadata() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan())
    assert fan.preset_modes == ["manual", "breeze", "boost"]


def test_preset_modes_none_when_unsupported() -> None:
    fan = EnkiFanEntity(_coordinator(), _power_fan())
    assert fan.preset_modes is None
    assert fan.preset_mode is None


def test_preset_mode_reflects_reported_airflow() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"airflow_mode": "BREEZE"}))
    assert fan.preset_mode == "breeze"


def test_preset_mode_none_when_reported_not_in_list() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"airflow_mode": "SLEEP"}))
    assert fan.preset_mode is None


def test_icon_uses_preset_icon_when_active() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"airflow_mode": "BREEZE"}))
    assert fan.icon == "mdi:weather-windy"


def test_icon_defaults_to_fan_ceiling() -> None:
    fan = EnkiFanEntity(_coordinator(), _power_fan())
    assert fan.icon == "mdi:fan-ceiling"


@pytest.mark.asyncio
async def test_set_preset_mode_writes_enki_mode() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())

    await fan.async_set_preset_mode("breeze")

    coordinator.api.async_set_airflow_mode.assert_awaited_once_with("home-1", "node-fan", "BREEZE")
    coordinator.update_cached_value.assert_called_once_with("node-fan", "airflow_mode", "BREEZE")
    coordinator.request_reconcile.assert_called_once()


@pytest.mark.asyncio
async def test_set_preset_mode_rejects_unknown() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())
    with pytest.raises(ValueError, match="Unsupported preset mode"):
        await fan.async_set_preset_mode("hurricane")


@pytest.mark.asyncio
async def test_set_preset_mode_ignored_when_unsupported() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _power_fan())
    await fan.async_set_preset_mode("breeze")
    coordinator.api.async_set_airflow_mode.assert_not_called()


# --- direction ---------------------------------------------------------------


def test_current_direction_from_reported() -> None:
    fan = EnkiFanEntity(
        _coordinator(), _speed_fan(last_reported_value={"airflow_rotation": DIRECTION_REVERSE})
    )
    assert fan.current_direction == DIRECTION_REVERSE


def test_supports_direction_via_reported_flag() -> None:
    # A fan without a rotation capability but whose cloud state advertises support.
    device = _power_fan(last_reported_value={"airflow_rotation_supported": True})
    fan = EnkiFanEntity(_coordinator(), device)
    assert fan.supported_features & FanEntityFeature.DIRECTION


@pytest.mark.asyncio
async def test_set_direction_writes_and_reconciles() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())

    await fan.async_set_direction(DIRECTION_FORWARD)

    coordinator.api.async_set_fan_rotation.assert_awaited_once_with(
        "home-1", "node-fan", DIRECTION_FORWARD
    )
    coordinator.update_cached_value.assert_called_once_with(
        "node-fan", "airflow_rotation", DIRECTION_FORWARD
    )
    coordinator.request_reconcile.assert_called_once()


@pytest.mark.asyncio
async def test_set_direction_ignores_invalid() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())
    await fan.async_set_direction("sideways")
    coordinator.api.async_set_fan_rotation.assert_not_called()


# --- on/off + percentage (speed fan) -----------------------------------------


def test_is_on_speed_fan_tracks_speed() -> None:
    on = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"fan_speed": 3}))
    off = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"fan_speed": 0}))
    unknown = EnkiFanEntity(_coordinator(), _speed_fan())
    assert on.is_on is True
    assert off.is_on is False
    assert unknown.is_on is False


def test_percentage_speed_fan() -> None:
    fan = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"fan_speed": 3}))
    assert fan.percentage == 50
    zero = EnkiFanEntity(_coordinator(), _speed_fan(last_reported_value={"fan_speed": 0}))
    assert zero.percentage == 0
    unknown = EnkiFanEntity(_coordinator(), _speed_fan())
    assert unknown.percentage is None


def test_percentage_none_for_power_fan() -> None:
    fan = EnkiFanEntity(_coordinator(), _power_fan())
    assert fan.percentage is None


@pytest.mark.asyncio
async def test_turn_on_with_percentage_sets_speed() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())

    await fan.async_turn_on(percentage=50)

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 3)
    coordinator.update_cached_value.assert_any_call("node-fan", "fan_speed", 3)


@pytest.mark.asyncio
async def test_turn_on_zero_percentage_turns_off() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan(last_reported_value={"fan_speed": 2}))

    await fan.async_turn_on(percentage=0)

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 0)


@pytest.mark.asyncio
async def test_turn_on_without_percentage_restores_last_speed() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan(last_reported_value={"fan_speed": 4}))

    await fan.async_turn_on()

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 4)


@pytest.mark.asyncio
async def test_turn_on_without_speed_defaults_to_one() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())

    await fan.async_turn_on()

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 1)


@pytest.mark.asyncio
async def test_turn_on_applies_preset_when_given() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())

    await fan.async_turn_on(preset_mode="boost", percentage=17)

    coordinator.api.async_set_airflow_mode.assert_awaited_once_with("home-1", "node-fan", "BOOST")
    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 1)


@pytest.mark.asyncio
async def test_turn_off_speed_fan_sets_zero() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan(last_reported_value={"fan_speed": 3}))

    await fan.async_turn_off()

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 0)


@pytest.mark.asyncio
async def test_set_percentage_maps_to_speed() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan())

    await fan.async_set_percentage(100)

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 6)


@pytest.mark.asyncio
async def test_set_percentage_zero_turns_off() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _speed_fan(last_reported_value={"fan_speed": 2}))

    await fan.async_set_percentage(0)

    coordinator.api.async_set_fan_speed.assert_awaited_once_with("home-1", "node-fan", 0)


@pytest.mark.asyncio
async def test_set_percentage_ignored_for_power_fan() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _power_fan())

    await fan.async_set_percentage(50)

    coordinator.api.async_set_fan_speed.assert_not_called()


# --- on/off (power fan) ------------------------------------------------------


def test_is_on_power_fan_prefers_power_signal() -> None:
    on = EnkiFanEntity(_coordinator(), _power_fan(last_reported_value={"power": "ON"}))
    off = EnkiFanEntity(_coordinator(), _power_fan(last_reported_value={"power": "OFF"}))
    assert on.is_on is True
    assert off.is_on is False


def test_is_on_power_fan_falls_back_to_electrical_power() -> None:
    fan = EnkiFanEntity(_coordinator(), _power_fan(last_reported_value={"electrical_power": "ON"}))
    assert fan.is_on is True


def test_is_on_power_fan_falls_back_to_speed() -> None:
    # No power signals at all -> last resort is the (non-writable) fan speed.
    fan = EnkiFanEntity(_coordinator(), _power_fan(last_reported_value={"fan_speed": 2}))
    assert fan.is_on is True


@pytest.mark.asyncio
async def test_turn_on_power_fan_switches_power() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _power_fan())

    await fan.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-pfan", "ON", endpoint=None
    )
    coordinator.update_cached_value.assert_any_call("node-pfan", "power", "ON")
    coordinator.request_reconcile.assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_power_fan_zero_percentage_does_nothing() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _power_fan())

    await fan.async_turn_on(percentage=0)

    coordinator.api.async_switch_electrical_power.assert_not_called()


@pytest.mark.asyncio
async def test_turn_off_power_fan_switches_power_off() -> None:
    coordinator = _coordinator()
    fan = EnkiFanEntity(coordinator, _power_fan())

    await fan.async_turn_off()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-pfan", "OFF", endpoint=None
    )
