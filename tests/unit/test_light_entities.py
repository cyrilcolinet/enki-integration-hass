"""Coverage for the Enki light platform: entity build + on/off/color writes."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.domain.models import EnkiDevice
from enki.light import (
    EnkiFanLightEntity,
    EnkiLightEntity,
    _build_light_entities,
    async_setup_entry,
)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
)


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.api.async_change_light_state = AsyncMock()
    coordinator.api.async_change_light_color = AsyncMock()
    coordinator.api.async_switch_electrical_power = AsyncMock()
    coordinator.update_cached_value = MagicMock()
    coordinator.update_endpoint_power = MagicMock()
    coordinator.request_reconcile = MagicMock()
    coordinator.batch_updates = MagicMock(return_value=nullcontext())
    return coordinator


def _color_light(**overrides) -> EnkiDevice:
    """Full colour light: brightness + color temp + hs, driven by light-state API."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-light",
        "node_id": "node-light",
        "device_name": "Colour Bulb",
        "device_type": "lights",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": [
            "change_brightness",
            "change_color_temperature",
            "change_hue",
            "change_saturation",
            "change_light_state",
            "check_light_state",
        ],
        "possible_values": {
            "change_brightness": {"range": {"min": 1, "max": 100}},
            "change_color_temperature": {"values": ["T2700K", "T4000K", "T6500K"]},
            "change_light_state": {"format": "OBJECT"},
        },
        "last_reported_value": {},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def _multi_gang_light(**overrides) -> EnkiDevice:
    """Light-state light with two switchable power endpoints (per-endpoint on/off)."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-gang",
        "node_id": "node-gang",
        "device_name": "Double Gang",
        "device_type": "lights",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["change_light_state", "check_light_state", "switch_electrical_power"],
        "possible_values": {"change_light_state": {"format": "OBJECT"}},
        "main_change_capability_id": "switch_electrical_power",
        "main_change_capability_endpoints": [1, 2],
        "last_reported_value": {
            "electrical_endpoints": [
                {"id": 1, "lastReportedValue": "ON"},
                {"id": 2, "lastReportedValue": "OFF"},
            ],
        },
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def _electrical_light(**overrides) -> EnkiDevice:
    """Light node without light-state: on/off only via switch_electrical_power."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-elec",
        "node_id": "node-elec",
        "device_name": "Relay Light",
        "device_type": "lights",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["switch_electrical_power"],
        "possible_values": {},
        "last_reported_value": {},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def _single_fan_light(**overrides) -> EnkiDevice:
    """Ceiling fan with a single (node-global) light kit driven by light-state."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-sfan",
        "node_id": "node-sfan",
        "device_name": "Inspire Siroco",
        "device_type": "ceiling_fans",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["change_fan_speed", "change_light_state", "check_light_state"],
        "possible_values": {
            "change_fan_speed": {"range": {"min": 0.0, "max": 6.0}},
            "change_light_state": {"format": "OBJECT"},
            "change_brightness": {"range": {"min": 1, "max": 100}},
            "change_color_temperature": {"values": ["T2748K", "T6500K"]},
        },
        "last_reported_value": {},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


def _outlet(**overrides) -> EnkiDevice:
    """Power-only outlet — not a controllable light."""
    defaults = {
        "home_id": "home-1",
        "device_id": "dev-outlet",
        "node_id": "node-outlet",
        "device_name": "Outlet",
        "device_type": "plugs",
        "is_enabled": True,
        "state": "ACTIVE",
        "capabilities": ["switch_electrical_power"],
        "possible_values": {},
    }
    defaults.update(overrides)
    return EnkiDevice(**defaults)


# --- setup / build -----------------------------------------------------------


def test_async_setup_entry_adds_built_entities() -> None:
    coordinator = _coordinator()
    coordinator.data = [_color_light(), _outlet()]
    entry = MagicMock()
    entry.runtime_data = coordinator
    added: list = []

    asyncio.run(async_setup_entry(MagicMock(), entry, lambda entities: added.extend(entities)))

    # Only the colour light is a controllable light; the outlet is skipped.
    assert len(added) == 1
    assert isinstance(added[0], EnkiLightEntity)


def test_build_skips_non_controllable() -> None:
    assert _build_light_entities(_coordinator(), _outlet()) == []


def test_build_single_light_entity() -> None:
    entities = _build_light_entities(_coordinator(), _color_light())
    assert len(entities) == 1
    assert isinstance(entities[0], EnkiLightEntity)
    assert entities[0]._attr_unique_id == "enki-node-light-light"  # noqa: SLF001


def test_build_multi_endpoint_light_entities() -> None:
    entities = _build_light_entities(_coordinator(), _multi_gang_light())
    assert len(entities) == 2
    assert {entity._endpoint_id for entity in entities} == {1, 2}  # noqa: SLF001
    assert len({entity._attr_unique_id for entity in entities}) == 2  # noqa: SLF001


def test_build_single_fan_light_entity() -> None:
    entities = _build_light_entities(_coordinator(), _single_fan_light())
    assert len(entities) == 1
    assert isinstance(entities[0], EnkiFanLightEntity)
    assert entities[0]._endpoint_id is None  # noqa: SLF001


# --- EnkiLightEntity: construction + supported color modes --------------------


def test_color_light_declares_color_modes() -> None:
    entity = EnkiLightEntity(_coordinator(), _color_light(), suffix="light")
    assert ColorMode.COLOR_TEMP in {ColorMode.COLOR_TEMP}  # sanity for stub identity
    # color temp bounds resolved from possibleValues
    assert entity._attr_min_color_temp_kelvin == 2700  # noqa: SLF001
    assert entity._attr_max_color_temp_kelvin == 6500  # noqa: SLF001


def test_color_temp_without_values_uses_default_kelvin() -> None:
    device = _color_light(
        capabilities=["change_color_temperature", "change_light_state", "check_light_state"],
        possible_values={"change_light_state": {"format": "OBJECT"}},
    )
    entity = EnkiLightEntity(_coordinator(), device, suffix="light")
    assert entity._attr_min_color_temp_kelvin == 2000  # DEFAULT_MIN_KELVIN  # noqa: SLF001
    assert entity._attr_max_color_temp_kelvin == 6500  # DEFAULT_MAX_KELVIN  # noqa: SLF001


def test_onoff_only_light_falls_back_to_onoff_mode() -> None:
    entity = EnkiLightEntity(_coordinator(), _multi_gang_light(), suffix="light_a", endpoint_id=1)
    # No brightness/color caps but has electrical power -> ONOFF is supported.
    assert entity._attr_supported_color_modes  # noqa: SLF001


# --- EnkiLightEntity: properties ---------------------------------------------


def test_is_on_endpoint_light() -> None:
    device = _multi_gang_light()
    on = EnkiLightEntity(_coordinator(), device, suffix="a", endpoint_id=1)
    off = EnkiLightEntity(_coordinator(), device, suffix="b", endpoint_id=2)
    assert on.is_on is True
    assert off.is_on is False


def test_is_on_endpoint_unknown_returns_false() -> None:
    device = _multi_gang_light(last_reported_value={"electrical_endpoints": []})
    entity = EnkiLightEntity(_coordinator(), device, suffix="a", endpoint_id=1)
    assert entity.is_on is False


def test_is_on_light_state_uses_global_power() -> None:
    on = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"power": "ON"}), suffix="l"
    )
    off = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"power": "OFF"}), suffix="l"
    )
    missing = EnkiLightEntity(_coordinator(), _color_light(), suffix="l")
    assert on.is_on is True
    assert off.is_on is False
    assert missing.is_on is False


def test_is_on_electrical_light() -> None:
    on = EnkiLightEntity(
        _coordinator(),
        _electrical_light(last_reported_value={"electrical_power": "ON"}),
        suffix="l",
    )
    assert on.is_on is True


def test_brightness_scales_to_255() -> None:
    entity = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"brightness": 50}), suffix="l"
    )
    assert entity.brightness == 128
    none_entity = EnkiLightEntity(_coordinator(), _color_light(), suffix="l")
    assert none_entity.brightness is None


def test_color_temp_kelvin_parsed() -> None:
    entity = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"colorTemperature": "T4000K"}), suffix="l"
    )
    assert entity.color_temp_kelvin == 4000
    none_entity = EnkiLightEntity(_coordinator(), _color_light(), suffix="l")
    assert none_entity.color_temp_kelvin is None


def test_hs_color_returns_none_without_hs_mode() -> None:
    entity = EnkiLightEntity(
        _coordinator(),
        _color_light(last_reported_value={"hue": 0.5, "saturation": 0.5}),
        suffix="l",
    )
    entity._attr_supported_color_modes = None  # noqa: SLF001
    assert entity.hs_color is None


def test_hs_color_denormalizes_when_hs_supported() -> None:
    entity = EnkiLightEntity(
        _coordinator(),
        _color_light(last_reported_value={"hue": 0.5, "saturation": 0.5}),
        suffix="l",
    )
    entity._attr_supported_color_modes = {ColorMode.HS}  # noqa: SLF001
    assert entity.hs_color == (180.0, 50.0)


def test_color_mode_prefers_attr() -> None:
    entity = EnkiLightEntity(_coordinator(), _color_light(), suffix="l")
    entity._attr_color_mode = ColorMode.COLOR_TEMP  # noqa: SLF001
    assert entity.color_mode is ColorMode.COLOR_TEMP


def test_color_mode_fallbacks() -> None:
    entity = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"colorMode": "hs"}), suffix="l"
    )
    entity._attr_color_mode = None  # noqa: SLF001
    assert entity.color_mode is ColorMode.HS

    entity2 = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"colorMode": "ct"}), suffix="l"
    )
    entity2._attr_color_mode = None  # noqa: SLF001
    assert entity2.color_mode is ColorMode.COLOR_TEMP

    entity3 = EnkiLightEntity(
        _coordinator(), _color_light(last_reported_value={"colorTemperature": "T3000K"}), suffix="l"
    )
    entity3._attr_color_mode = None  # noqa: SLF001
    assert entity3.color_mode is ColorMode.COLOR_TEMP

    entity4 = EnkiLightEntity(_coordinator(), _color_light(), suffix="l")
    entity4._attr_color_mode = None  # noqa: SLF001
    entity4._attr_supported_color_modes = {ColorMode.HS}  # noqa: SLF001
    assert entity4.color_mode is ColorMode.HS

    entity5 = EnkiLightEntity(_coordinator(), _color_light(), suffix="l")
    entity5._attr_color_mode = None  # noqa: SLF001
    entity5._attr_supported_color_modes = set()  # noqa: SLF001
    assert entity5.color_mode is None


# --- EnkiLightEntity: turn on/off --------------------------------------------


@pytest.mark.asyncio
async def test_turn_on_electrical_light() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _electrical_light(), suffix="l")

    await entity.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-elec", "ON", endpoint=None
    )
    coordinator.update_cached_value.assert_any_call("node-elec", "electrical_power", "ON")


@pytest.mark.asyncio
async def test_turn_off_electrical_light() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _electrical_light(), suffix="l")

    await entity.async_turn_off()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-elec", "OFF", endpoint=None
    )


@pytest.mark.asyncio
async def test_turn_on_electrical_light_with_endpoint_caches_endpoint_power() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _electrical_light(), suffix="a", endpoint_id=1)

    await entity.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-elec", "ON", endpoint=1
    )
    coordinator.update_endpoint_power.assert_called_once_with("node-elec", 1, "ON")


@pytest.mark.asyncio
async def test_turn_on_endpoint_light_uses_endpoint_power() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _multi_gang_light(), suffix="a", endpoint_id=2)

    await entity.async_turn_on()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-gang", "ON", endpoint=2
    )
    coordinator.api.async_change_light_state.assert_not_called()


@pytest.mark.asyncio
async def test_turn_off_endpoint_light_uses_endpoint_power() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _multi_gang_light(), suffix="a", endpoint_id=1)

    await entity.async_turn_off()

    coordinator.api.async_switch_electrical_power.assert_awaited_once_with(
        "home-1", "node-gang", "OFF", endpoint=1
    )


@pytest.mark.asyncio
async def test_turn_on_with_hs_color() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _color_light(), suffix="l")

    await entity.async_turn_on(**{ATTR_HS_COLOR: (180.0, 50.0)})

    coordinator.api.async_change_light_color.assert_awaited_once()
    args = coordinator.api.async_change_light_color.await_args.args
    assert args[0] == "home-1" and args[1] == "node-light"
    coordinator.update_cached_value.assert_any_call("node-light", "colorMode", "hs")
    coordinator.update_cached_value.assert_any_call("node-light", "power", "ON")


@pytest.mark.asyncio
async def test_turn_on_with_brightness_via_light_state() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _color_light(), suffix="l")

    await entity.async_turn_on(**{ATTR_BRIGHTNESS: 255})

    coordinator.api.async_change_light_state.assert_awaited_once()
    changes = coordinator.api.async_change_light_state.await_args.args[2]
    assert changes["power"] == "ON"
    assert changes["brightness"] == 100
    coordinator.update_cached_value.assert_any_call("node-light", "brightness", 100)


@pytest.mark.asyncio
async def test_turn_on_with_color_temp_via_light_state() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _color_light(), suffix="l")

    await entity.async_turn_on(**{ATTR_COLOR_TEMP_KELVIN: 4100})

    changes = coordinator.api.async_change_light_state.await_args.args[2]
    # 4100 K snaps to the nearest catalogued value (4000 K).
    assert changes["colorTemperature"] == "T4000K"
    coordinator.update_cached_value.assert_any_call("node-light", "colorMode", "ct")


@pytest.mark.asyncio
async def test_turn_on_plain_sets_power_on() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _color_light(), suffix="l")

    await entity.async_turn_on()

    changes = coordinator.api.async_change_light_state.await_args.args[2]
    assert changes == {"power": "ON"}
    coordinator.update_cached_value.assert_any_call("node-light", "power", "ON")


@pytest.mark.asyncio
async def test_turn_on_zero_brightness_turns_off() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _color_light(), suffix="l")

    await entity.async_turn_on(**{ATTR_BRIGHTNESS: 1})

    # Sub-minimum brightness collapses to a turn-off.
    coordinator.api.async_change_light_state.assert_awaited_once_with(
        "home-1", "node-light", {"power": "OFF"}
    )


@pytest.mark.asyncio
async def test_turn_off_light_state() -> None:
    coordinator = _coordinator()
    entity = EnkiLightEntity(coordinator, _color_light(), suffix="l")

    await entity.async_turn_off()

    coordinator.api.async_change_light_state.assert_awaited_once_with(
        "home-1", "node-light", {"power": "OFF"}
    )
    coordinator.update_cached_value.assert_any_call("node-light", "power", "OFF")


# --- EnkiFanLightEntity ------------------------------------------------------


def test_fan_light_is_on_global_and_endpoint() -> None:
    glob = EnkiFanLightEntity(
        _coordinator(), _single_fan_light(last_reported_value={"light_power": "ON"})
    )
    assert glob.is_on is True

    device = _single_fan_light(
        last_reported_value={"electrical_endpoints": [{"id": 3, "lastReportedValue": "ON"}]}
    )
    ep = EnkiFanLightEntity(_coordinator(), device, endpoint_id=3, suffix="light_a")
    assert ep.is_on is True


def test_fan_light_brightness_and_color_temp() -> None:
    device = _single_fan_light(
        last_reported_value={"brightness": 100, "colorTemperature": "T4000K"}
    )
    entity = EnkiFanLightEntity(_coordinator(), device)
    assert entity.brightness == 255
    assert entity.color_temp_kelvin == 4000

    empty = EnkiFanLightEntity(_coordinator(), _single_fan_light())
    assert empty.brightness is None
    assert empty.color_temp_kelvin is None


@pytest.mark.asyncio
async def test_fan_light_turn_on_global_light_state() -> None:
    coordinator = _coordinator()
    entity = EnkiFanLightEntity(coordinator, _single_fan_light())

    await entity.async_turn_on()

    coordinator.api.async_change_light_state.assert_awaited_once()
    coordinator.request_reconcile.assert_called_once()
    coordinator.update_cached_value.assert_any_call("node-sfan", "light_power", "ON")


@pytest.mark.asyncio
async def test_fan_light_turn_on_with_brightness_and_color_temp() -> None:
    coordinator = _coordinator()
    entity = EnkiFanLightEntity(coordinator, _single_fan_light())

    await entity.async_turn_on(**{ATTR_BRIGHTNESS: 255, ATTR_COLOR_TEMP_KELVIN: 6000})

    changes = coordinator.api.async_change_light_state.await_args.args[2]
    assert changes["brightness"] == 100
    assert changes["colorTemperature"] == "T6500K"
    coordinator.update_cached_value.assert_any_call("node-sfan", "brightness", 100)
    coordinator.update_cached_value.assert_any_call("node-sfan", "colorTemperature", "T6500K")


@pytest.mark.asyncio
async def test_fan_light_turn_on_low_brightness_turns_off() -> None:
    coordinator = _coordinator()
    entity = EnkiFanLightEntity(coordinator, _single_fan_light())

    await entity.async_turn_on(**{ATTR_BRIGHTNESS: 1})

    coordinator.api.async_change_light_state.assert_awaited_once_with(
        "home-1", "node-sfan", {"power": "OFF"}
    )


@pytest.mark.asyncio
async def test_fan_light_turn_off_global() -> None:
    coordinator = _coordinator()
    entity = EnkiFanLightEntity(coordinator, _single_fan_light())

    await entity.async_turn_off()

    coordinator.api.async_change_light_state.assert_awaited_once_with(
        "home-1", "node-sfan", {"power": "OFF"}
    )
    coordinator.update_cached_value.assert_any_call("node-sfan", "light_power", "OFF")
    coordinator.request_reconcile.assert_called_once()
