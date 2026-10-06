"""Equation air conditioner as a climate entity (#286)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from enki.climate import EnkiAirConditionerClimate
from enki.domain.airco import build_airconditioner_payload, parse_airconditioner_state
from enki.domain.models import EnkiDevice
from homeassistant.components.climate.const import HVACMode

# What the reporter's AD-WMACKC-U1 returned, from its diagnostics.
REPORTED = {
    "airco_current_temperature": 25.0,
    "airco_fan_speed": "AUTO",
    "airco_frost_protection_mode": False,
    "airco_health_mode": False,
    "airco_operating_mode": "COOL",
    "airco_power": "ON",
    "airco_quiet_mode": False,
    "airco_self_clean_mode": False,
    "airco_sleep_mode": False,
    "airco_target_temperature": 24.0,
}


def _aircon(**overrides) -> EnkiDevice:
    return EnkiDevice(
        home_id="home-1",
        device_id="dev-1",
        node_id="node-ac",
        device_name="Clim",
        device_type="air_conditioners",
        is_enabled=True,
        state="ACTIVE",
        capabilities=["check_airconditioner_state", "change_airconditioner_state"],
        last_reported_value={**REPORTED, **overrides},
    )


def _entity(device: EnkiDevice) -> tuple[EnkiAirConditionerClimate, MagicMock]:
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.get_device_by_node = lambda node_id: device
    coordinator.api.async_set_airconditioner_state = AsyncMock(return_value={})
    return EnkiAirConditionerClimate(coordinator, device), coordinator


def test_the_reported_state_becomes_the_entity() -> None:
    entity, _ = _entity(_aircon())

    assert entity.hvac_mode == HVACMode.COOL
    assert entity.fan_mode == "auto"
    assert entity.target_temperature == 24.0
    assert entity.current_temperature == 25.0


def test_a_unit_that_is_off_reads_off_whatever_its_mode() -> None:
    entity, _ = _entity(_aircon(airco_power="OFF"))

    assert entity.hvac_mode == HVACMode.OFF


def test_writing_one_field_keeps_everything_else() -> None:
    """The app rebuilds the whole object, so a partial write would blank the rest."""
    payload = build_airconditioner_payload(REPORTED, targetTemperature=22.0)

    assert payload["targetTemperature"] == 22.0
    assert payload["operatingMode"] == "COOL"
    assert payload["fanSpeed"] == "AUTO"
    assert payload["power"] == "ON"
    assert payload["sleepMode"] is False


@pytest.mark.asyncio
async def test_setting_a_temperature_sends_the_whole_state() -> None:
    device = _aircon()
    entity, coordinator = _entity(device)

    await entity.async_set_temperature(temperature=22.0)

    coordinator.api.async_set_airconditioner_state.assert_awaited_once_with(
        "home-1", "node-ac", device.last_reported_value, targetTemperature=22.0
    )
    coordinator.update_cached_value.assert_called_once_with(
        "node-ac", "airco_target_temperature", 22.0
    )


@pytest.mark.asyncio
async def test_choosing_a_mode_also_turns_the_unit_on() -> None:
    """Picking Heat on a unit that is off should start it, not just set the mode."""
    device = _aircon(airco_power="OFF")
    entity, coordinator = _entity(device)

    await entity.async_set_hvac_mode(HVACMode.HEAT)

    _, kwargs = coordinator.api.async_set_airconditioner_state.call_args
    assert kwargs == {"power": "ON", "operatingMode": "HEAT"}


@pytest.mark.asyncio
async def test_turning_off_keeps_the_mode_it_had() -> None:
    device = _aircon()
    entity, coordinator = _entity(device)

    await entity.async_set_hvac_mode(HVACMode.OFF)

    _, kwargs = coordinator.api.async_set_airconditioner_state.call_args
    assert kwargs == {"power": "OFF"}


@pytest.mark.asyncio
async def test_setting_a_fan_speed_uses_the_wire_value() -> None:
    device = _aircon()
    entity, coordinator = _entity(device)

    await entity.async_set_fan_mode("medium")

    _, kwargs = coordinator.api.async_set_airconditioner_state.call_args
    assert kwargs == {"fanSpeed": "MEDIUM"}


def test_an_unreported_swing_is_not_invented() -> None:
    """The reporter's unit sends no swing; the write must not claim one."""
    payload = build_airconditioner_payload(parse_airconditioner_state({"lastReportedValue": {}}))

    assert payload["swingOrientation"] is None


def test_a_write_keeps_the_louvres_where_the_user_left_them() -> None:
    """Sending a null orientation would straighten louvres on every temperature change."""
    state = {**REPORTED, "airco_swing_vertical": "NIV_2", "airco_swing_horizontal": "AUTO"}

    payload = build_airconditioner_payload(state, targetTemperature=22.0)

    assert payload["swingOrientation"] == {"horizontal": "AUTO", "vertical": "NIV_2"}


def test_a_unit_that_reports_no_louvres_sends_none() -> None:
    assert build_airconditioner_payload(REPORTED)["swingOrientation"] is None


@pytest.mark.asyncio
async def test_setting_a_swing_step_sends_only_that_louvre() -> None:
    device = _aircon(airco_swing_vertical="AUTO", airco_swing_horizontal="NIV_3")
    entity, coordinator = _entity(device)

    await entity.async_set_swing_mode("niv_2")

    _, kwargs = coordinator.api.async_set_airconditioner_state.call_args
    assert kwargs == {"airco_swing_vertical": "NIV_2"}
    coordinator.update_cached_value.assert_called_once_with(
        "node-ac", "airco_swing_vertical", "NIV_2"
    )


def test_the_two_louvres_have_their_own_steps() -> None:
    """Horizontal goes to 5, vertical to 4: one shared list would offer a dead step."""
    entity, _ = _entity(_aircon(airco_swing_vertical="NIV_4", airco_swing_horizontal="NIV_5"))

    assert entity.swing_mode == "niv_4"
    assert entity.swing_horizontal_mode == "niv_5"
    assert entity._attr_swing_modes == ["auto", "niv_1", "niv_2", "niv_3", "niv_4"]
    assert "niv_5" in entity._attr_swing_horizontal_modes
